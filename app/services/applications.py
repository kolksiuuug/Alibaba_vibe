"""Заявки клиента: черновик, полнота анкеты, отправка, дозапрос, предложение, просмотр."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.domain.errors import AccessDenied, InvalidTransition, NotFound, ValidationFailed
from app.domain.form_fields import (
    ALLOWED_FORM_FIELDS,
    BASE_REQUIRED_FIELDS,
    NUMERIC_FIELDS,
    PURPOSES,
    field_label,
)
from app.domain.loan_math import payment_schedule
from app.domain.state_machine import Actor
from app.domain.statuses import Status
from app.extensions import db
from app.models import (
    Application,
    AuditEvent,
    Decision,
    Disbursement,
    InfoRequest,
    Product,
    ScoringResult,
    Signature,
    User,
)
from app.scoring.decision_engine import missing_product_fields
from app.scoring.metrics import money
from app.scoring.types import ProductTerms
from app.services.offers import get_product
from app.services.pipeline import current_offer, enqueue_job
from app.services.transitions import transition

S = Status
OFFER_VISIBLE = {S.OFFER, S.ACCEPTED, S.SIGNED, S.ISSUED, S.DECLINED}


# --- проверка входных данных ----------------------------------------------------------------


def _validate_terms(product: Product, amount: int, term_months: int, purpose: str) -> None:
    errors: dict[str, list[str]] = {}
    if not product.min_amount <= amount <= product.max_amount:
        errors["amount"] = [
            f"Для продукта «{product.name}» сумма — от {money(product.min_amount)} "
            f"до {money(product.max_amount)} ₽"
        ]
    if not product.min_term_months <= term_months <= product.max_term_months:
        errors["term_months"] = [
            f"Для продукта «{product.name}» срок — от {product.min_term_months} "
            f"до {product.max_term_months} мес."
        ]
    if purpose not in PURPOSES:
        errors["purpose"] = ["Выберите цель кредита из списка"]
    if errors:
        raise ValidationFailed("Проверьте условия заявки", errors=errors)


def clean_form(form: Mapping[str, Any]) -> dict[str, Any]:
    """Оставить известные поля анкеты, обрезать пробелы, привести числа."""
    unknown = sorted(set(form) - ALLOWED_FORM_FIELDS)
    if unknown:
        raise ValidationFailed(
            "В анкете есть неизвестные поля",
            errors={"form_data": {key: ["Неизвестное поле"] for key in unknown}},
        )
    cleaned: dict[str, Any] = {}
    for key, value in form.items():
        if value is None:
            cleaned[key] = None
        elif key in NUMERIC_FIELDS:
            try:
                number = int(str(value).replace(" ", "").replace(" ", ""))
            except ValueError:
                raise ValidationFailed(
                    "Проверьте анкету", errors={"form_data": {key: ["Укажите число в рублях"]}}
                ) from None
            if number <= 0:
                raise ValidationFailed(
                    "Проверьте анкету",
                    errors={"form_data": {key: ["Сумма должна быть больше нуля"]}},
                )
            cleaned[key] = number
        else:
            cleaned[key] = str(value).strip()[:2000]
    return cleaned


def _labelled(codes: list[str] | tuple[str, ...]) -> list[dict[str, str]]:
    return [{"code": code, "label": field_label(code)} for code in codes]


def completeness(application: Application) -> dict[str, Any]:
    form = application.form_data or {}
    missing_required = [f for f in BASE_REQUIRED_FIELDS if not str(form.get(f) or "").strip()]
    missing_for_product = missing_product_fields(form, ProductTerms.from_model(application.product))
    return {
        "ready_to_submit": not missing_required,
        "missing_required": _labelled(missing_required),
        "missing_for_product": _labelled(missing_for_product),
    }


# --- чтение ---------------------------------------------------------------------------------


def get_client_application(user: User, application_id: int) -> Application:
    application = db.session.get(Application, application_id)
    if application is None:
        raise NotFound("Заявка не найдена")
    if application.company_id != user.company_id:
        raise AccessDenied("Это заявка другой компании")
    return application


def list_company_applications(user: User) -> list[Application]:
    return list(
        db.session.scalars(
            select(Application)
            .where(Application.company_id == user.company_id)
            .order_by(Application.id.desc())
        )
    )


def open_info_request(application: Application) -> InfoRequest | None:
    return db.session.scalars(
        select(InfoRequest)
        .where(InfoRequest.application_id == application.id, InfoRequest.responded_at.is_(None))
        .order_by(InfoRequest.id.desc())
    ).first()


def latest_decision(application: Application) -> Decision | None:
    return db.session.scalars(
        select(Decision)
        .where(Decision.application_id == application.id)
        .order_by(Decision.id.desc())
    ).first()


def latest_scoring(application: Application) -> ScoringResult | None:
    return db.session.scalars(
        select(ScoringResult)
        .where(ScoringResult.application_id == application.id)
        .order_by(ScoringResult.id.desc())
    ).first()


def offer_view(application: Application, decision: Decision) -> dict[str, Any]:
    assert decision.amount is not None and decision.term_months is not None
    assert decision.rate is not None
    schedule = payment_schedule(decision.amount, decision.term_months, decision.rate)
    total = sum(row.payment for row in schedule)
    return {
        "amount": decision.amount,
        "term_months": decision.term_months,
        "rate": decision.rate,
        "monthly_payment": decision.monthly_payment,
        "is_counter": decision.is_counter,
        "decided_by": decision.decided_by,
        "requested_amount": application.amount,
        "requested_term_months": application.term_months,
        "total_payment": total,
        "overpayment": total - decision.amount,
        "reasons": decision.reasons,
        "comment": decision.comment if decision.decided_by == "analyst" else None,
        "schedule": schedule,
    }


def info_request_view(info: InfoRequest) -> dict[str, Any]:
    return {
        "id": info.id,
        "requested_by": info.requested_by,
        "message": info.message,
        "fields": _labelled(info.fields),
        "response": info.response,
        "responded_at": info.responded_at,
        "created_at": info.created_at,
    }


def client_factor_view(scoring: ScoringResult | None) -> list[dict[str, Any]]:
    if scoring is None:
        return []
    by_code = {factor["code"]: factor for factor in scoring.factors}
    return [by_code[code] for code in scoring.client_factors if code in by_code]


def client_view(application: Application) -> dict[str, Any]:
    """Всё, что клиент видит в карточке заявки: статус, этапы, предложение, факторы, дозапрос."""
    status = application.status
    offer = current_offer(application) if status in OFFER_VISIBLE else None
    decision = latest_decision(application)
    info = open_info_request(application) if status is S.INFO_REQUESTED else None
    disbursement = db.session.scalars(
        select(Disbursement).where(Disbursement.application_id == application.id)
    ).first()
    signature = db.session.scalars(
        select(Signature).where(Signature.application_id == application.id)
    ).first()
    show_reasons = status in {S.REJECTED, S.MANUAL_REVIEW} and decision is not None
    return {
        "application": application,
        "completeness": completeness(application),
        "offer": offer_view(application, offer) if offer else None,
        "info_request": info_request_view(info) if info else None,
        "factors": client_factor_view(latest_scoring(application)) if decision else [],
        "reasons": decision.reasons if show_reasons and decision else [],
        "decision_comment": (
            decision.comment
            if decision and decision.decided_by == "analyst" and status is S.REJECTED
            else None
        ),
        "signature": (
            {"signed_at": signature.signed_at, "signature_reference": signature.signature_reference}
            if signature and signature.status == "signed"
            else None
        ),
        "disbursement": (
            {
                "amount": disbursement.amount,
                "abs_reference": disbursement.abs_reference,
                "created_at": disbursement.created_at,
            }
            if disbursement
            else None
        ),
    }


def events(application: Application, *, with_comments: bool) -> list[dict[str, Any]]:
    rows = db.session.scalars(
        select(AuditEvent)
        .where(AuditEvent.application_id == application.id)
        .order_by(AuditEvent.at, AuditEvent.id)
    )
    return [
        {
            "id": event.id,
            "from_status": event.from_status,
            "to_status": event.to_status,
            "actor": event.actor,
            "reason": event.reason,
            "comment": event.comment if with_comments else None,
            "at": event.at,
        }
        for event in rows
    ]


# --- действия клиента -----------------------------------------------------------------------


def create_draft(
    user: User,
    *,
    product_code: str,
    amount: int,
    term_months: int,
    purpose: str,
    form_data: Mapping[str, Any],
) -> Application:
    product = get_product(product_code)
    _validate_terms(product, amount, term_months, purpose)
    application = Application(
        company_id=user.company_id,
        created_by=user,
        product=product,
        amount=amount,
        term_months=term_months,
        purpose=purpose,
        form_data=clean_form(form_data),
    )
    db.session.add(application)
    db.session.flush()
    db.session.add(
        AuditEvent(
            application_id=application.id,
            from_status=None,
            to_status=S.DRAFT.value,
            actor=Actor.CLIENT.value,
            actor_user_id=user.id,
            reason="draft_created",
        )
    )
    db.session.commit()
    return application


def update_draft(user: User, application_id: int, changes: Mapping[str, Any]) -> Application:
    application = get_client_application(user, application_id)
    if application.status is not S.DRAFT:
        raise InvalidTransition("Изменить можно только черновик заявки")
    product = (
        get_product(changes["product_code"]) if "product_code" in changes else application.product
    )
    amount = changes.get("amount", application.amount)
    term_months = changes.get("term_months", application.term_months)
    purpose = changes.get("purpose", application.purpose)
    _validate_terms(product, amount, term_months, purpose)
    application.product = product
    application.amount, application.term_months, application.purpose = amount, term_months, purpose
    if "form_data" in changes:
        application.form_data = {
            **(application.form_data or {}),
            **clean_form(changes["form_data"]),
        }
    db.session.commit()
    return application


def submit(user: User, application_id: int) -> Application:
    application = get_client_application(user, application_id)
    if application.status is S.DRAFT:
        check = completeness(application)
        if not check["ready_to_submit"]:
            raise ValidationFailed(
                "Заполните анкету перед отправкой",
                errors={
                    "form_data": {
                        f["code"]: ["Обязательное поле"] for f in check["missing_required"]
                    }
                },
            )
    result = transition(application, S.SUBMITTED, actor=Actor.CLIENT, actor_user=user)
    if result.changed:
        application.submitted_at = datetime.now(UTC)
        enqueue_job(application)
    db.session.commit()
    return application


def cancel(user: User, application_id: int) -> Application:
    application = get_client_application(user, application_id)
    transition(application, S.CANCELLED, actor=Actor.CLIENT, actor_user=user)
    db.session.commit()
    return application


def respond_to_info_request(
    user: User, application_id: int, answers: Mapping[str, Any], comment: str | None
) -> Application:
    application = get_client_application(user, application_id)
    if application.status is S.CHECKING:
        return application  # ответ уже принят: повтор идемпотентен
    if application.status is not S.INFO_REQUESTED:
        raise InvalidTransition("Банк сейчас не ждёт ответа по этой заявке")
    info = open_info_request(application)
    cleaned = clean_form(answers)
    merged = {**(application.form_data or {}), **cleaned}
    requested = info.fields if info else []
    missing = [f for f in requested if not str(merged.get(f) or "").strip()]
    if missing:
        raise ValidationFailed(
            "Ответьте на все вопросы банка",
            errors={"answers": {f: ["Нужно заполнить"] for f in missing}},
        )
    comment = (comment or "").strip() or None
    if not requested and not comment:
        raise ValidationFailed("Напишите ответ банку", errors={"comment": ["Нужно заполнить"]})
    application.form_data = merged
    if info is not None:
        info.response = {"answers": cleaned, "comment": comment}
        info.responded_at = datetime.now(UTC)
    transition(application, S.CHECKING, actor=Actor.CLIENT, actor_user=user, reason="info_provided")
    enqueue_job(application)
    db.session.commit()
    return application


def accept_offer(user: User, application_id: int) -> Application:
    application = get_client_application(user, application_id)
    transition(application, S.ACCEPTED, actor=Actor.CLIENT, actor_user=user)
    db.session.commit()
    return application


def decline_offer(user: User, application_id: int) -> Application:
    application = get_client_application(user, application_id)
    transition(application, S.DECLINED, actor=Actor.CLIENT, actor_user=user)
    db.session.commit()
    return application
