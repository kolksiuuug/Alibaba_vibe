"""Результат проверки во внешней системе: одна строка на заявку и источник."""

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class CheckResult(db.Model):  # type: ignore[name-defined]
    __tablename__ = "check_results"
    __table_args__ = (
        UniqueConstraint("application_id", "source", name="uq_check_results_application_source"),
        CheckConstraint("source IN ('bki', 'egrul', 'fns')", name="source"),
        CheckConstraint("status IN ('ok', 'failed')", name="status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    source: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
