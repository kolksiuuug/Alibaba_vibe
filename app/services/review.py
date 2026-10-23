"""Работа кредитного аналитика: очередь заявок, карточка, решения по ручному рассмотрению."""

from decimal import Decimal
from typing import Any

from flask import current_app
from sqlalchemy import select

from app.domain.errors import NotFound, ValidationFailed
from app.domain.form_fields import FIELD_LABELS, field_label
from app.domain.loan_math import annuity_payment
from app.domain.state_machine import Actor, check_transition
from app.domain.statuses import Status
from app.extensions import db
from app.models import Application, CheckResult, Decision, InfoRequest, ScoringResult, User
from app.scoring.config import load_config
from app.services.applications import client_view, events, info_request_view, latest_scoring
from app.services.offers import base_rate
from app.services.transitions import transition

ACTIONS = {
    "approve": Status.OFFER,
    "change_terms": Status.OFFER,
    "request_info": Status.INFO_REQUESTED,
    "reject": Status.REJECTED,
}


def get_application(application_id: int) -> Application:
    application = db.session.get(Application, application_id)
    if application is None:
        raise NotFound("Заявка не найдена")
    return application


def queue(status: str | None) -> list[dict[str, Any]]:
    stmt = select(Application).where(Application.status != Status.DRAFT.value)
    if status:
        try:
            Status(status)
        except ValueError:
            raise ValidationFailed(
                "Неизвестный статус", errors={"status": [f"Нет статуса «{status}»"]}
            ) from None
        stmt = stmt.where(Application.status == status)
    applications = db.session.scalars(stmt.order_by(Application.status_changed_at.desc()))
    items = []
    for application in applications:
        scoring: ScoringResult | None = latest_scoring(application)
        items.append(
            {
                "id": application.id,
                "status": application.status,
                "company_name": application.company.name,
                "company_inn": application.company.inn,
                "product_name": application.product.name,
                "amount": application.amount,
                "term_months": application.term_months,
                "score": scoring.score if scoring else None,
                "grade": scoring.grade if scoring else None,
                "submitted_at": application.submitted_at,
                "status_changed_at": application.status_changed_at,
            }
        )
    return items


def analyst_card(application: Application) -> dict[str, Any]:
    checks = db.session.scalars(
        select(CheckResult)
        .where(CheckResult.application_id == application.id)
        .order_by(CheckResult.source)
    )
    decisions = db.session.scalars(
        select(Decision).where(Decision.application_id == application.id).order_by(Decision.id)
    )
    info_requests = db.session.scalars(
        select(InfoRequest)
        .where(InfoRequest.application_id == application.id)
        .order_by(InfoRequest.id)
    )
    scoring = latest_scoring(application)
    return {
        **client_view(application),
        "checks": list(checks),
        "scoring": scoring,
        "decisions": list(decisions),
        "info_requests": [info_request_view(info) for info in info_requests],
        "events": events(application, with_comments=True),
    }


def _engine_recommendation(application: Application) -> Decision | None:
    return db.session.scalars(
        select(Decision)
        .where(
            Decision.application_id == application.id,
            Decision.decided_by == "engine",
            Decision.amount.is_not(None),
        )
        .order_by(Decision.id.desc())
    ).first()


def _analyst_rate(application: Application) -> Decimal:
    """Ставка для решения аналитика: как у движка для пограничного грейда C."""
    premium = Decimal(str(load_config()["decision"]["rate_premium"]["C"]))
    return base_rate(application.product, Decimal(str(current_app.config["KEY_RATE"]))) + premium


def _offer_decision(
    application: Application, analyst: User, comment: str, amount: int, term: int, code: str
) -> Decision:
    recommendation = _engine_recommendation(application)
    rate = (
        recommendation.rate
        if recommendation and recommendation.rate
        else _analyst_rate(application)
    )
    texts = {
        "analyst_approved": "Заявку одобрил кредитный аналитик.",
        "analyst_changed_terms": "Кредитный аналитик предложил другие условия.",
    }
    return Decision(
        application_id=application.id,
        outcome="offer",
        decided_by="analyst",
        analyst_id=analyst.id,
        is_counter=(amount, term) != (application.amount, application.term_months),
        amount=amount,
        term_months=term,
        rate=rate,
        monthly_payment=annuity_payment(amount, term, Decimal(rate)),
        reasons=[{"code": code, "text": texts[code]}],
        comment=comment,
    )


def decide(
    analyst: User,
    application_id: int,
    *,
    action: str,
    comment: str | None,
    amount: int | None = None,
    term_months: int | None = None,
    fields: list[str] | None = None,
) -> Application:
    application = get_application(application_id)
    target = ACTIONS[action]
    if application.status is target:
        return application  # решение уже применено: повтор идемпотентен
    check_transition(application.status, target, Actor.ANALYST, comment=comment)
    comment = (comment or "").strip()
    product = application.product

    if action == "approve":
        recommendation = _engine_recommendation(application)
        offer_amount = recommendation.amount if recommendation else application.amount
        offer_term = recommendation.term_months if recommendation else application.term_months
        assert offer_amount is not None and offer_term is not None
        decision = _offer_decision(
            application, analyst, comment, offer_amount, offer_term, "analyst_approved"
        )
        body = None
    elif action == "change_terms":
        errors: dict[str, list[str]] = {}
        if amount is None or not product.min_amount <= amount <= product.max_amount:
            errors["amount"] = [f"От {product.min_amount} до {product.max_amount} ₽"]
        if (
            term_months is None
            or not product.min_term_months <= term_months <= product.max_term_months
        ):
            errors["term_months"] = [
                f"От {product.min_term_months} до {product.max_term_months} мес."
            ]
        if errors:
            raise ValidationFailed("Проверьте новые условия", errors=errors)
        assert amount is not None and term_months is not None
        decision = _offer_decision(
            application, analyst, comment, amount, term_months, "analyst_changed_terms"
        )
        body = (
            f"По заявке №{application.id} кредитный аналитик предложил другие условия. "
            "Посмотрите предложение."
        )
    elif action == "request_info":
        unknown = [f for f in (fields or []) if f not in FIELD_LABELS]
        if unknown:
            raise ValidationFailed(
                "Неизвестные поля анкеты", errors={"fields": [f"Нет поля «{f}»" for f in unknown]}
            )
        db.session.add(
            InfoRequest(
                application_id=application.id,
                requested_by="analyst",
                analyst_id=analyst.id,
                fields=list(fields or []),
                message=comment,
            )
        )
        decision = Decision(
            application_id=application.id,
            outcome="info_requested",
            decided_by="analyst",
            analyst_id=analyst.id,
            reasons=[{"code": "analyst_requested_info", "text": comment}],
            comment=comment,
        )
        labels = ", ".join(field_label(f) for f in fields or [])
        body = f"Банку нужна информация по заявке №{application.id}: {comment}" + (
            f" Поля: {labels}." if labels else ""
        )
    else:
        decision = Decision(
            application_id=application.id,
            outcome="rejected",
            decided_by="analyst",
            analyst_id=analyst.id,
            reasons=[{"code": "analyst_rejected", "text": "Кредитный аналитик отказал по заявке."}],
            comment=comment,
        )
        body = f"Банк не может выдать кредит по заявке №{application.id}. Комментарий: {comment}"

    db.session.add(decision)
    transition(
        application,
        target,
        actor=Actor.ANALYST,
        actor_user=analyst,
        reason=action,
        comment=comment,
        notification_body=body,
    )
    db.session.commit()
    return application
