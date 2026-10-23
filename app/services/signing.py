"""Подписание договора кодом, который показывается и вводится в интерфейсе (симуляция ЭП)."""

import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.adapters.base import AdapterError, Adapters
from app.domain.errors import InvalidTransition, ServiceUnavailable, ValidationFailed
from app.domain.state_machine import Actor
from app.domain.statuses import Status
from app.extensions import db
from app.models import Application, Signature, User
from app.services.applications import get_client_application
from app.services.pipeline import JobKind, current_offer, enqueue_job
from app.services.transitions import transition

CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5


def _hash_code(code: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()


def _document_hash(application: Application) -> str:
    offer = current_offer(application)
    terms = {
        "application_id": application.id,
        "amount": offer.amount if offer else None,
        "term_months": offer.term_months if offer else None,
        "rate": str(offer.rate) if offer else None,
        "monthly_payment": str(offer.monthly_payment) if offer else None,
    }
    return hashlib.sha256(json.dumps(terms, sort_keys=True).encode()).hexdigest()


def _signature(application: Application) -> Signature | None:
    return db.session.scalars(
        select(Signature).where(Signature.application_id == application.id)
    ).first()


def request_code(user: User, application_id: int) -> dict[str, Any]:
    application = get_client_application(user, application_id)
    if application.status is not Status.ACCEPTED:
        raise InvalidTransition("Код подписи можно получить после принятия предложения")
    code = f"{secrets.randbelow(10**6):06d}"
    salt = secrets.token_hex(8)
    signature = _signature(application) or Signature(application_id=application.id)
    signature.status = "pending"
    signature.code_salt = salt
    signature.code_hash = _hash_code(code, salt)
    signature.attempts = 0
    signature.expires_at = datetime.now(UTC) + CODE_TTL
    signature.document_hash = _document_hash(application)
    db.session.add(signature)
    db.session.commit()
    return {
        "code": code,
        "expires_at": signature.expires_at,
        "document_hash": signature.document_hash,
        "simulated": True,
    }


def confirm(user: User, application_id: int, code: str, adapters: Adapters) -> Application:
    application = get_client_application(user, application_id)
    if application.status in (Status.SIGNED, Status.ISSUED):
        return application  # уже подписано: повтор идемпотентен
    if application.status is not Status.ACCEPTED:
        raise InvalidTransition("Подписать можно только принятое предложение")
    signature = _signature(application)
    if signature is None or signature.status != "pending":
        raise ValidationFailed("Сначала получите код подписи", errors={"code": ["Код не запрошен"]})
    if datetime.now(UTC) > signature.expires_at:
        raise ValidationFailed("Код устарел, получите новый", errors={"code": ["Код устарел"]})
    if signature.attempts >= MAX_ATTEMPTS:
        raise ValidationFailed(
            "Слишком много попыток, получите новый код", errors={"code": ["Попытки закончились"]}
        )
    if not hmac.compare_digest(signature.code_hash, _hash_code(code.strip(), signature.code_salt)):
        signature.attempts += 1
        db.session.commit()
        raise ValidationFailed("Неверный код", errors={"code": ["Код не совпадает"]})

    try:
        response = adapters.esign.sign(
            application_id=application.id,
            document_hash=signature.document_hash,
            signer=user.login,
        )
    except AdapterError as exc:
        raise ServiceUnavailable("Сервис подписи временно недоступен, попробуйте ещё раз") from exc

    signature.status = "signed"
    signature.signature_reference = str(response.get("signature_id", ""))
    signature.signed_at = datetime.now(UTC)
    transition(application, Status.SIGNED, actor=Actor.CLIENT, actor_user=user)
    enqueue_job(application, JobKind.DISBURSEMENT)
    db.session.commit()
    return application
