"""Задача конвейера в очереди PostgreSQL (вместо Redis): проверка заявки или выдача."""

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.application import Application


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PipelineJob(db.Model):  # type: ignore[name-defined]
    __tablename__ = "pipeline_jobs"
    __table_args__ = (
        CheckConstraint("state IN ('queued', 'running', 'done', 'failed')", name="state"),
        CheckConstraint("kind IN ('scoring', 'disbursement')", name="kind"),
        Index("ix_pipeline_jobs_ready", "state", "run_after"),
        # Не больше одной задачи каждого вида в очереди на заявку: повторный submit не дублирует.
        # Выполняемая задача сюда не входит: пока воркер её закрывает, новая уже может встать в очередь.
        Index(
            "uq_pipeline_jobs_queued",
            "application_id",
            "kind",
            unique=True,
            postgresql_where=text("state = 'queued'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    state: Mapped[str] = mapped_column(String(16), default="queued")
    attempts: Mapped[int] = mapped_column(default=0)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    application: Mapped[Application] = relationship()
