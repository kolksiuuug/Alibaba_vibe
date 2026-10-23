"""Конвейер проверки заявки: шаги, сохранение результатов, fallback в manual_review."""

from typing import Any

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, select

from app.domain.state_machine import Actor
from app.domain.statuses import Status
from app.models import (
    Application,
    AuditEvent,
    CheckResult,
    Decision,
    InfoRequest,
    PipelineJob,
    Product,
    ScoringResult,
    User,
)
from app.services.pipeline import STEP_CODES, enqueue_job, run_scoring
from app.services.seed import load_seed
from app.services.transitions import transition
from tests.factories import make_application
from tests.fakes import FakeExternal, fake_context

COLLATERAL_FORM = {
    "collateral_description": "Токарный станок с ЧПУ, 2024 года выпуска",
    "collateral_value": 3_200_000,
    "equipment_supplier": "ООО «Станкоцентр»",
}


def _submitted(
    app: Flask, db: SQLAlchemy, login: str, product_code: str, amount: int, term: int, **extra: Any
) -> tuple[Application, PipelineJob]:
    load_seed(app.config["SEED_DIR"])
    user = db.session.scalars(select(User).where(User.login == login)).one()
    product = db.session.scalars(select(Product).where(Product.code == product_code)).one()
    application = make_application(
        status=Status.SUBMITTED,
        client=user,
        product=product,
        amount=amount,
        term_months=term,
        **extra,
    )
    job = enqueue_job(application)
    db.session.commit()
    return application, job


def _transitions(
    db: SQLAlchemy, application: Application
) -> list[tuple[str | None, str, str | None]]:
    events = db.session.scalars(
        select(AuditEvent)
        .where(AuditEvent.application_id == application.id)
        .order_by(AuditEvent.id)
    )
    return [(e.from_status, e.to_status, e.reason) for e in events]


def test_demo_approve_gets_offer_and_full_trail(app: Flask, db: SQLAlchemy) -> None:
    application, job = _submitted(app, db, "demo-approve", "turnover", 3_000_000, 24)

    run_scoring(job, fake_context())

    assert application.status is Status.OFFER
    assert [step["state"] for step in application.pipeline_steps] == ["done"] * len(STEP_CODES)
    assert [step["code"] for step in application.pipeline_steps] == list(STEP_CODES)
    checks = db.session.scalars(
        select(CheckResult).where(CheckResult.application_id == application.id)
    )
    assert {c.source: c.status for c in checks} == {"egrul": "ok", "fns": "ok", "bki": "ok"}
    scoring = db.session.scalars(select(ScoringResult)).one()
    assert (scoring.score, scoring.grade) == (290, "A")
    assert len(scoring.factors) == 9
    assert 3 <= len(scoring.client_factors) <= 5
    decision = db.session.scalars(select(Decision)).one()
    assert (decision.outcome, decision.decided_by, decision.is_counter) == (
        "offer",
        "engine",
        False,
    )
    assert (decision.amount, decision.term_months) == (3_000_000, 24)
    assert _transitions(db, application) == [
        ("submitted", "checking", None),
        ("checking", "offer", "approved"),
    ]


def test_demo_counter_saves_counter_offer(app: Flask, db: SQLAlchemy) -> None:
    application, job = _submitted(app, db, "demo-counter", "turnover", 12_000_000, 24)

    run_scoring(job, fake_context())

    decision = db.session.scalars(select(Decision)).one()
    assert application.status is Status.OFFER
    assert decision.is_counter is True
    assert decision.amount < 12_000_000
    assert decision.term_months == 36


def test_demo_info_creates_info_request(app: Flask, db: SQLAlchemy) -> None:
    application, job = _submitted(app, db, "demo-info", "equipment", 2_500_000, 36)

    run_scoring(job, fake_context())

    assert application.status is Status.INFO_REQUESTED
    info = db.session.scalars(select(InfoRequest)).one()
    assert set(info.fields) == set(COLLATERAL_FORM)
    assert info.requested_by == "engine"
    assert info.message
    assert db.session.scalars(select(Decision)).one().outcome == "info_requested"


def test_demo_manual_saves_engine_recommendation(app: Flask, db: SQLAlchemy) -> None:
    application, job = _submitted(app, db, "demo-manual", "express", 1_500_000, 18)

    run_scoring(job, fake_context())

    assert application.status is Status.MANUAL_REVIEW
    decision = db.session.scalars(select(Decision)).one()
    assert decision.outcome == "manual_review"
    assert decision.amount == 1_500_000  # рекомендация движка аналитику


def test_demo_reject_stores_stop_factor(app: Flask, db: SQLAlchemy) -> None:
    application, job = _submitted(app, db, "demo-reject", "turnover", 2_000_000, 12)

    run_scoring(job, fake_context())

    assert application.status is Status.REJECTED
    scoring = db.session.scalars(select(ScoringResult)).one()
    assert [s["code"] for s in scoring.stop_factors] == ["current_overdue"]
    assert scoring.grade is None


def test_unavailable_source_sends_to_manual_review(app: Flask, db: SQLAlchemy) -> None:
    application, job = _submitted(app, db, "demo-approve", "turnover", 3_000_000, 24)

    run_scoring(job, fake_context(FakeExternal(fail={"bki"})))

    assert application.status is Status.MANUAL_REVIEW
    assert _transitions(db, application)[-1] == ("checking", "manual_review", "bki_unavailable")
    states = {step["code"]: step["state"] for step in application.pipeline_steps}
    assert states["bki"] == "failed"
    assert states["scoring"] == "pending"


def test_info_response_rerun_reuses_checks(app: Flask, db: SQLAlchemy) -> None:
    external = FakeExternal()
    application, job = _submitted(app, db, "demo-info", "equipment", 2_500_000, 36)
    run_scoring(job, fake_context(external))
    job.state = "done"  # так задачу закрывает воркер

    application.form_data = {**application.form_data, **COLLATERAL_FORM}
    transition(application, Status.CHECKING, actor=Actor.CLIENT)
    second = enqueue_job(application)
    db.session.commit()
    run_scoring(second, fake_context(external))

    assert application.status is Status.OFFER
    assert external.calls == {"egrul": 1, "fns": 1, "bki": 1}
    assert db.session.scalar(select(func.count()).select_from(Decision)) == 2


def test_resume_skips_completed_steps(app: Flask, db: SQLAlchemy) -> None:
    external = FakeExternal(fail={"egrul"})
    application, job = _submitted(app, db, "demo-approve", "turnover", 3_000_000, 24)
    ok = FakeExternal()
    db.session.add(
        CheckResult(
            application_id=application.id,
            source="egrul",
            status="ok",
            response=ok.get_company(application.company.inn),
        )
    )
    transition(application, Status.CHECKING, actor=Actor.SYSTEM)
    application.pipeline_steps = [
        {
            "code": code,
            "state": "done" if code in ("validation", "egrul") else "pending",
            "job_id": job.id,
        }
        for code in STEP_CODES
    ]
    db.session.commit()

    run_scoring(job, fake_context(external))

    assert application.status is Status.OFFER
    assert external.calls["egrul"] == 0


def test_repeated_job_after_decision_changes_nothing(app: Flask, db: SQLAlchemy) -> None:
    application, job = _submitted(app, db, "demo-approve", "turnover", 3_000_000, 24)
    run_scoring(job, fake_context())
    events_before = len(_transitions(db, application))

    run_scoring(job, fake_context())

    assert application.status is Status.OFFER
    assert len(_transitions(db, application)) == events_before
    assert db.session.scalar(select(func.count()).select_from(Decision)) == 1
