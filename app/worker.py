"""Воркер конвейера: очередь pipeline_jobs в PostgreSQL.

Забирает задачу через SELECT … FOR UPDATE SKIP LOCKED, обновляет heartbeat, возвращает в
очередь задачи с устаревшим heartbeat и делает не больше PIPELINE_MAX_ATTEMPTS попыток.
Переживает рестарт: состояние целиком в БД.
"""

import logging
import signal
import time
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import FrameType
from typing import Any

from flask import current_app
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.adapters import build_adapters
from app.extensions import db
from app.models import PipelineJob
from app.services.pipeline import (
    JobKind,
    PipelineContext,
    give_up,
    run_disbursement,
    run_scoring,
)

log = logging.getLogger(__name__)

HANDLERS: dict[str, Callable[[PipelineJob, PipelineContext], None]] = {
    JobKind.SCORING: run_scoring,
    JobKind.DISBURSEMENT: run_disbursement,
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def claim_next_job(*, now: datetime | None = None) -> PipelineJob | None:
    now = now or _utcnow()
    job = db.session.scalars(
        select(PipelineJob)
        .where(PipelineJob.state == "queued", PipelineJob.run_after <= now)
        .order_by(PipelineJob.run_after, PipelineJob.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).first()
    if job is None:
        db.session.rollback()
        return None
    job.state = "running"
    job.attempts += 1
    job.heartbeat_at = now
    db.session.commit()
    return job


def requeue_stale_jobs(
    *, now: datetime | None = None, timeout_s: int = 60, max_attempts: int = 3
) -> int:
    """Вернуть в очередь задачи, чей воркер перестал подавать heartbeat."""
    now = now or _utcnow()
    stale = db.session.scalars(
        select(PipelineJob)
        .where(
            PipelineJob.state == "running",
            PipelineJob.heartbeat_at < now - timedelta(seconds=timeout_s),
        )
        .with_for_update(skip_locked=True)
    ).all()
    for job in stale:
        job.last_error = f"heartbeat timeout: no heartbeat for more than {timeout_s} s"
        if job.attempts >= max_attempts:
            give_up(job)
        else:
            job.state = "queued"
            job.run_after = now
        log.warning("stale job requeued", extra={"job_id": job.id, "attempts": job.attempts})
    db.session.commit()
    return len(stale)


def process_job(
    job: PipelineJob,
    ctx: PipelineContext,
    *,
    now: datetime | None = None,
    max_attempts: int = 3,
    retry_backoff_s: int = 5,
) -> None:
    job_id = job.id

    def beat() -> None:
        job.heartbeat_at = _utcnow()

    try:
        HANDLERS[job.kind](job, replace(ctx, heartbeat=beat))
        job.state = "done"
        job.last_error = None
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        failed = db.session.get(PipelineJob, job_id)
        if failed is None:
            raise
        failed.last_error = f"{type(exc).__name__}: {exc}"[:2000]
        if failed.attempts >= max_attempts:
            give_up(failed)
        else:
            failed.state = "queued"
            failed.run_after = (now or _utcnow()) + timedelta(
                seconds=retry_backoff_s * failed.attempts
            )
        db.session.commit()
        log.warning(
            "pipeline job error",
            extra={"job_id": job_id, "attempts": failed.attempts, "error": failed.last_error},
        )


def run_until_idle(
    ctx: PipelineContext, *, max_jobs: int = 100, max_attempts: int = 3, retry_backoff_s: int = 5
) -> int:
    """Обработать все готовые задачи синхронно (API-тесты, отладка). Возвращает их число."""
    processed = 0
    while processed < max_jobs:
        job = claim_next_job()
        if job is None:
            break
        process_job(job, ctx, max_attempts=max_attempts, retry_backoff_s=retry_backoff_s)
        processed += 1
    return processed


def build_context(config: Any) -> PipelineContext:
    return PipelineContext(
        adapters=build_adapters(config),
        key_rate=Decimal(str(config["KEY_RATE"])),
        step_delay_ms=int(config["PIPELINE_STEP_DELAY_MS"]),
    )


class StopFlag:
    """Плавная остановка по SIGTERM/SIGINT: текущая задача дорабатывает до конца."""

    def __init__(self) -> None:
        self.stopped = False

    def stop(self, signum: int, frame: FrameType | None) -> None:
        log.info("worker stopping", extra={"signal": signum})
        self.stopped = True


def touch_heartbeat(path: str) -> None:
    Path(path).touch()


def run_worker(*, once: bool = False) -> None:
    stop = StopFlag()
    signal.signal(signal.SIGTERM, stop.stop)
    signal.signal(signal.SIGINT, stop.stop)

    config = current_app.config
    ctx = build_context(config)
    poll_interval_s = config["WORKER_POLL_INTERVAL_MS"] / 1000
    heartbeat_file = config["WORKER_HEARTBEAT_FILE"]
    limits = {
        "max_attempts": config["PIPELINE_MAX_ATTEMPTS"],
        "retry_backoff_s": config["PIPELINE_RETRY_BACKOFF_S"],
    }
    log.info("worker started", extra={"poll_interval_s": poll_interval_s})

    while not stop.stopped:
        touch_heartbeat(heartbeat_file)
        try:
            requeue_stale_jobs(
                timeout_s=config["PIPELINE_HEARTBEAT_TIMEOUT_S"],
                max_attempts=limits["max_attempts"],
            )
            while not stop.stopped and (job := claim_next_job()) is not None:
                process_job(job, ctx, **limits)
                touch_heartbeat(heartbeat_file)
        except SQLAlchemyError:
            db.session.rollback()
            log.exception("worker database error, retrying")
        if once:
            break
        time.sleep(poll_interval_s)

    log.info("worker stopped")
