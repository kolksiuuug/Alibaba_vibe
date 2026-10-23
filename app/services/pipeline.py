"""Конвейер проверки заявки и выдачи.

Шаги проверки: валидация -> ЕГРЮЛ/ЕГРИП -> ФНС -> БКИ -> скоринг -> решение. Прогресс пишется
в Application.pipeline_steps и коммитится после каждого шага: UI видит движение статуса, а после
падения воркера задача продолжается с первого незавершённого шага. Если внешняя система
недоступна после ретраев, заявка уходит в manual_review с причиной.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import select

from app.adapters.base import AdapterError, Adapters, JsonDict
from app.domain.state_machine import Actor
from app.domain.statuses import Status
from app.extensions import db
from app.models import (
    Application,
    CheckResult,
    Decision,
    Disbursement,
    InfoRequest,
    Notification,
    PipelineJob,
    ScoringResult,
)
from app.scoring.decision_engine import decide
from app.scoring.metrics import money
from app.scoring.scorecard import client_factors
from app.scoring.types import (
    BkiData,
    EgrulData,
    EngineDecision,
    FnsData,
    ProductTerms,
    ScoringInput,
)
from app.services.transitions import transition

log = logging.getLogger(__name__)


class JobKind(StrEnum):
    SCORING = "scoring"
    DISBURSEMENT = "disbursement"


STEP_TITLES = {
    "validation": "Проверка анкеты",
    "egrul": "ЕГРЮЛ / ЕГРИП",
    "fns": "ФНС «Прозрачный бизнес»",
    "bki": "Бюро кредитных историй",
    "scoring": "Скоринг",
    "decision": "Решение",
}
STEP_CODES = tuple(STEP_TITLES)
CHECK_SOURCES = ("egrul", "fns", "bki")
ACTIVE_JOB_STATES = ("queued", "running")


@dataclass(frozen=True)
class PipelineContext:
    adapters: Adapters
    key_rate: Decimal
    step_delay_ms: int = 0
    today: Callable[[], date] = date.today
    heartbeat: Callable[[], None] = field(default=lambda: None)


class StepFailed(Exception):
    """Шаг не может быть выполнен автоматически: заявка уходит аналитику."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message


def enqueue_job(application: Application, kind: JobKind = JobKind.SCORING) -> PipelineJob:
    """Поставить задачу в очередь в текущей транзакции.

    Активная задача того же вида переиспользуется: повторный submit не создаёт дубль.
    """
    existing = db.session.scalars(
        select(PipelineJob).where(
            PipelineJob.application_id == application.id,
            PipelineJob.kind == kind.value,
            PipelineJob.state.in_(ACTIVE_JOB_STATES),
        )
    ).first()
    if existing is not None:
        return existing
    job = PipelineJob(
        application_id=application.id,
        kind=kind.value,
        state="queued",
        attempts=0,
        run_after=datetime.now(UTC),
    )
    db.session.add(job)
    db.session.flush()
    return job


# --- pipeline_steps -------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _ensure_steps(application: Application, job_id: int) -> None:
    steps = application.pipeline_steps or []
    if steps and all(step.get("job_id") == job_id for step in steps):
        return  # продолжаем прерванный запуск той же задачи
    application.pipeline_steps = [
        {"code": code, "title": title, "state": "pending", "job_id": job_id}
        for code, title in STEP_TITLES.items()
    ]


def _step_state(application: Application, code: str) -> str:
    return next(
        (step["state"] for step in application.pipeline_steps if step["code"] == code), "pending"
    )


def _update_step(application: Application, code: str, **changes: Any) -> None:
    # Новый список, а не мутация: SQLAlchemy видит изменение JSONB
    application.pipeline_steps = [
        {**step, **changes} if step["code"] == code else step for step in application.pipeline_steps
    ]


# --- шаги -----------------------------------------------------------------------------------


def _validate(application: Application) -> str:
    product = application.product
    if not product.min_amount <= application.amount <= product.max_amount:
        raise StepFailed("validation_failed", "Сумма вне диапазона продукта")
    if not product.min_term_months <= application.term_months <= product.max_term_months:
        raise StepFailed("validation_failed", "Срок вне диапазона продукта")
    return "Анкета заполнена"


def _call_source(adapters: Adapters, source: str, inn: str) -> JsonDict:
    if source == "egrul":
        return adapters.egrul.get_company(inn)
    if source == "fns":
        return adapters.fns.get_transparent_business(inn)
    return adapters.bki.get_report(inn)


def _check_row(application: Application, source: str) -> CheckResult | None:
    return db.session.scalars(
        select(CheckResult).where(
            CheckResult.application_id == application.id, CheckResult.source == source
        )
    ).first()


def _run_check(application: Application, source: str, ctx: PipelineContext) -> str:
    row = _check_row(application, source)
    if row is not None and row.status == "ok":
        return "Данные получены ранее"
    if row is None:
        row = CheckResult(application_id=application.id, source=source, status="failed")
        db.session.add(row)
    try:
        response = _call_source(ctx.adapters, source, application.company.inn)
    except AdapterError as exc:
        row.status, row.error, row.response = "failed", exc.message, None
        raise StepFailed(f"{source}_unavailable", f"{STEP_TITLES[source]}: нет ответа") from exc
    row.status, row.error, row.response = "ok", None, response
    row.checked_at = datetime.now(UTC)
    return "Данные получены"


def _check_data(application: Application, source: str) -> JsonDict:
    row = _check_row(application, source)
    return (row.response if row else None) or {}


def _scoring_input(application: Application) -> ScoringInput:
    egrul, fns, bki = (_check_data(application, source) for source in CHECK_SOURCES)
    company = application.company
    try:
        return ScoringInput(
            okved=str(egrul.get("okved") or company.okved),
            monthly_turnover=tuple(int(month["amount"]) for month in company.monthly_turnover),
            requested_amount=application.amount,
            term_months=application.term_months,
            egrul=EgrulData(
                status=str(egrul["status"]),
                registered_at=date.fromisoformat(str(egrul["registered_at"])),
            ),
            fns=FnsData(
                tax_debt=int(fns.get("tax_debt", 0)),
                late_payments_12m=int(fns.get("late_payments_12m", 0)),
            ),
            bki=BkiData(
                current_overdue_days=int(bki.get("current_overdue_days", 0)),
                max_overdue_days_24m=int(bki.get("max_overdue_days_24m", 0)),
                overdue_count_24m=int(bki.get("overdue_count_24m", 0)),
                monthly_payments=int(bki.get("monthly_payments", 0)),
            ),
            form_data=application.form_data or {},
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise StepFailed("invalid_source_data", f"Некорректные данные проверок: {exc}") from exc


def _decide(application: Application, ctx: PipelineContext) -> EngineDecision:
    return decide(
        _scoring_input(application),
        ProductTerms.from_model(application.product),
        key_rate=ctx.key_rate,
        today=ctx.today(),
    )


def _save_scoring(application: Application, decision: EngineDecision) -> str:
    scoring = decision.scoring
    db.session.add(
        ScoringResult(
            application_id=application.id,
            score=scoring.score if scoring else None,
            grade=scoring.grade if scoring else None,
            factors=[
                {
                    "code": f.code,
                    "value": f.value,
                    "points": f.points,
                    "max_points": f.max_points,
                    "explanation_ru": f.explanation_ru,
                    "impact": f.impact,
                }
                for f in (scoring.factors if scoring else ())
            ],
            client_factors=[f.code for f in client_factors(scoring)] if scoring else [],
            stop_factors=[{"code": r.code, "text": r.text} for r in decision.stop_factors],
        )
    )
    if scoring is None:
        return "Сработал стоп-фактор"
    return f"Оценка {scoring.score} баллов, грейд {scoring.grade}"


def _notification_body(application: Application, decision: EngineDecision) -> str | None:
    offer = decision.offer
    if decision.outcome is Status.OFFER and offer is not None and offer.is_counter:
        return (
            f"По заявке №{application.id} банк предлагает другие условия: "
            f"{money(offer.amount)} ₽ на {offer.term_months} мес. Посмотрите предложение."
        )
    return None


def _save_decision(application: Application, decision: EngineDecision) -> str:
    offer = decision.offer
    db.session.add(
        Decision(
            application_id=application.id,
            outcome=decision.outcome.value,
            decided_by="engine",
            is_counter=bool(offer and offer.is_counter),
            amount=offer.amount if offer else None,
            term_months=offer.term_months if offer else None,
            rate=offer.rate if offer else None,
            monthly_payment=offer.monthly_payment if offer else None,
            reasons=[{"code": r.code, "text": r.text} for r in decision.reasons],
        )
    )
    if decision.outcome is Status.INFO_REQUESTED:
        db.session.add(
            InfoRequest(
                application_id=application.id,
                requested_by="engine",
                fields=list(decision.missing_fields),
                message=decision.reasons[0].text,
            )
        )
    transition(
        application,
        decision.outcome,
        actor=Actor.SYSTEM,
        reason=decision.reasons[0].code if decision.reasons else None,
        notification_body=_notification_body(application, decision),
    )
    return "Решение принято"


def _run_step(application: Application, code: str, ctx: PipelineContext) -> str:
    if code == "validation":
        return _validate(application)
    if code in CHECK_SOURCES:
        return _run_check(application, code, ctx)
    if code == "scoring":
        return _save_scoring(application, _decide(application, ctx))
    return _save_decision(application, _decide(application, ctx))


def _pause(ctx: PipelineContext) -> None:
    if ctx.step_delay_ms > 0:
        time.sleep(ctx.step_delay_ms / 1000)


def run_scoring(job: PipelineJob, ctx: PipelineContext) -> None:
    application = job.application
    if application.status is Status.SUBMITTED:
        transition(application, Status.CHECKING, actor=Actor.SYSTEM)
    if application.status is not Status.CHECKING:
        db.session.commit()
        return  # заявка уже решена: повтор задачи ничего не меняет

    _ensure_steps(application, job.id)
    db.session.commit()

    for code in STEP_CODES:
        if _step_state(application, code) == "done":
            continue
        _update_step(application, code, state="running", started_at=_now_iso())
        ctx.heartbeat()
        db.session.commit()
        try:
            message = _run_step(application, code, ctx)
        except StepFailed as failure:
            _update_step(
                application, code, state="failed", finished_at=_now_iso(), message=failure.message
            )
            transition(
                application,
                Status.MANUAL_REVIEW,
                actor=Actor.SYSTEM,
                reason=failure.reason,
                notification_body=(
                    f"Автоматическая проверка заявки №{application.id} не завершилась "
                    f"({failure.message}). Заявку рассмотрит кредитный аналитик."
                ),
            )
            db.session.commit()
            log.warning(
                "pipeline step failed",
                extra={"application_id": application.id, "step": code, "reason": failure.reason},
            )
            return
        _update_step(application, code, state="done", finished_at=_now_iso(), message=message)
        db.session.commit()
        _pause(ctx)


def current_offer(application: Application) -> Decision | None:
    return db.session.scalars(
        select(Decision)
        .where(Decision.application_id == application.id, Decision.outcome == "offer")
        .order_by(Decision.id.desc())
    ).first()


def run_disbursement(job: PipelineJob, ctx: PipelineContext) -> None:
    """signed -> issued через мок АБС. Ошибка АБС поднимается: воркер повторит задачу."""
    application = job.application
    if application.status is not Status.SIGNED:
        return  # уже выдано (или ещё не подписано): повтор ничего не делает

    exists = db.session.scalars(
        select(Disbursement).where(Disbursement.application_id == application.id)
    ).first()
    if exists is None:
        offer = current_offer(application)
        if offer is None or offer.amount is None:
            raise RuntimeError(f"application {application.id} has no offer to disburse")
        response = ctx.adapters.abs.create_disbursement(
            idempotency_key=f"application-{application.id}",
            application_id=application.id,
            inn=application.company.inn,
            amount=offer.amount,
        )
        db.session.add(
            Disbursement(
                application_id=application.id,
                amount=offer.amount,
                abs_reference=str(response["disbursement_id"]),
                status=str(response.get("status", "completed")),
            )
        )
    ctx.heartbeat()
    transition(application, Status.ISSUED, actor=Actor.SYSTEM)
    db.session.commit()


def give_up(job: PipelineJob, reason: str = "pipeline_failed") -> None:
    """Попытки исчерпаны: задача failed, заявка — аналитику (или клиенту сообщаем о задержке)."""
    job.state = "failed"
    application = job.application
    if job.kind == JobKind.SCORING:
        if application.status is Status.SUBMITTED:
            transition(application, Status.CHECKING, actor=Actor.SYSTEM)
        if application.status is Status.CHECKING:
            transition(
                application,
                Status.MANUAL_REVIEW,
                actor=Actor.SYSTEM,
                reason=reason,
                notification_body=(
                    f"Автоматическая проверка заявки №{application.id} не завершилась. "
                    "Заявку рассмотрит кредитный аналитик."
                ),
            )
    else:
        db.session.add(
            Notification(
                user_id=application.created_by_id,
                application_id=application.id,
                kind="info",
                title="Выдача задерживается",
                body=(
                    f"Не удалось перечислить деньги по заявке №{application.id}. "
                    "Мы уже разбираемся (симуляция)."
                ),
            )
        )
    log.error(
        "pipeline job failed",
        extra={"job_id": job.id, "application_id": application.id, "kind": job.kind},
    )
