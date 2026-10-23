"""Воркер: очередь в PostgreSQL, SKIP LOCKED, heartbeat, ограниченные попытки, выдача."""

from datetime import UTC, datetime, timedelta

import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select, text

from app import worker
from app.domain.statuses import Status
from app.models import AuditEvent, Decision, Disbursement, Notification, PipelineJob
from app.services.pipeline import JobKind, enqueue_job
from app.worker import claim_next_job, process_job, requeue_stale_jobs, run_until_idle
from tests.factories import make_application
from tests.fakes import FakeExternal, fake_context

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)


def _queued(db: SQLAlchemy, status: Status = Status.SUBMITTED, **job_fields: object) -> PipelineJob:
    application = make_application(status=status)
    job = enqueue_job(application)
    for name, value in job_fields.items():
        setattr(job, name, value)
    db.session.commit()
    return job


def test_claim_takes_oldest_ready_job_and_marks_it_running(db: SQLAlchemy) -> None:
    first = _queued(db, run_after=NOW - timedelta(minutes=2))
    _queued(db, run_after=NOW - timedelta(minutes=1))

    job = claim_next_job(now=NOW)

    assert job is not None and job.id == first.id
    assert (job.state, job.attempts, job.heartbeat_at) == ("running", 1, NOW)


def test_claim_ignores_future_and_running_jobs(db: SQLAlchemy) -> None:
    _queued(db, run_after=NOW + timedelta(minutes=5))
    _queued(db, state="running", heartbeat_at=NOW)

    assert claim_next_job(now=NOW) is None


def test_claim_skips_rows_locked_by_another_worker(db: SQLAlchemy) -> None:
    job = _queued(db, run_after=NOW - timedelta(minutes=1))
    with db.engine.connect() as other_worker:
        other_worker.begin()
        other_worker.execute(
            text("SELECT id FROM pipeline_jobs WHERE id = :id FOR UPDATE"), {"id": job.id}
        )
        assert claim_next_job(now=NOW) is None
        other_worker.rollback()

    assert claim_next_job(now=NOW) is not None


def test_stale_running_job_returns_to_queue(db: SQLAlchemy) -> None:
    stale = _queued(db, state="running", attempts=1, heartbeat_at=NOW - timedelta(seconds=61))
    fresh = _queued(db, state="running", attempts=1, heartbeat_at=NOW - timedelta(seconds=30))

    assert requeue_stale_jobs(now=NOW, timeout_s=60, max_attempts=3) == 1

    db.session.refresh(stale)
    db.session.refresh(fresh)
    assert stale.state == "queued"
    assert "heartbeat" in (stale.last_error or "")
    assert fresh.state == "running"


def test_stale_job_after_last_attempt_fails_to_manual_review(db: SQLAlchemy) -> None:
    job = _queued(db, state="running", attempts=3, heartbeat_at=NOW - timedelta(seconds=90))

    requeue_stale_jobs(now=NOW, timeout_s=60, max_attempts=3)

    db.session.refresh(job)
    assert job.state == "failed"
    assert job.application.status is Status.MANUAL_REVIEW
    last = db.session.scalars(select(AuditEvent).order_by(AuditEvent.id.desc())).first()
    assert last is not None and last.reason == "pipeline_failed"


def test_unexpected_error_is_retried_then_fails_to_manual_review(
    db: SQLAlchemy, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(job: PipelineJob, ctx: object) -> None:
        raise RuntimeError("database hiccup")

    monkeypatch.setitem(worker.HANDLERS, JobKind.SCORING, boom)
    job = _queued(db, run_after=NOW - timedelta(seconds=1))
    ctx = fake_context()

    now = NOW
    for attempt in (1, 2):
        claimed = claim_next_job(now=now)
        assert claimed is not None
        process_job(claimed, ctx, now=now, max_attempts=3)
        db.session.refresh(job)
        assert (job.state, job.attempts) == ("queued", attempt)
        assert job.run_after > now
        assert "database hiccup" in (job.last_error or "")
        now = job.run_after

    claimed = claim_next_job(now=now)
    assert claimed is not None
    process_job(claimed, ctx, now=now, max_attempts=3)

    db.session.refresh(job)
    assert job.state == "failed"
    assert job.application.status is Status.MANUAL_REVIEW


def _signed_with_offer(db: SQLAlchemy) -> PipelineJob:
    application = make_application(status=Status.SIGNED)
    db.session.add(
        Decision(
            application_id=application.id,
            outcome="offer",
            decided_by="engine",
            amount=1_000_000,
            term_months=12,
            rate=19,
            monthly_payment=92_000,
        )
    )
    job = enqueue_job(application, JobKind.DISBURSEMENT)
    db.session.commit()
    return job


def test_disbursement_issues_loan(db: SQLAlchemy) -> None:
    job = _signed_with_offer(db)

    processed = run_until_idle(fake_context())

    assert processed == 1
    db.session.refresh(job)
    assert job.state == "done"
    assert job.application.status is Status.ISSUED
    disbursement = db.session.scalars(select(Disbursement)).one()
    assert (disbursement.amount, disbursement.abs_reference) == (1_000_000, f"ABS-{job.application_id}")
    titles = {n.title for n in db.session.scalars(select(Notification))}
    assert "Кредит выдан" in titles


def test_disbursement_retries_when_abs_is_down(db: SQLAlchemy) -> None:
    job = _signed_with_offer(db)

    run_until_idle(fake_context(FakeExternal(fail={"abs"})))

    db.session.refresh(job)
    assert (job.state, job.attempts) == ("queued", 1)
    assert job.application.status is Status.SIGNED


def test_run_until_idle_processes_scoring_job(app: Flask, db: SQLAlchemy) -> None:
    from app.services.seed import load_seed

    load_seed(app.config["SEED_DIR"])
    from app.models import Product, User

    user = db.session.scalars(select(User).where(User.login == "demo-approve")).one()
    product = db.session.scalars(select(Product).where(Product.code == "turnover")).one()
    application = make_application(
        status=Status.SUBMITTED, client=user, product=product, amount=3_000_000, term_months=24
    )
    enqueue_job(application)
    db.session.commit()

    assert run_until_idle(fake_context()) == 1
    assert application.status is Status.OFFER
    assert run_until_idle(fake_context()) == 0


def test_only_one_active_job_per_application_and_kind(db: SQLAlchemy) -> None:
    job = _queued(db)
    again = enqueue_job(job.application)

    assert again.id == job.id
