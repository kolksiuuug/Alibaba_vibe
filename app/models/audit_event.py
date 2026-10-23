"""Журнал переходов статуса заявки. Пишется при каждом переходе."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class AuditEvent(db.Model):  # type: ignore[name-defined]
    __tablename__ = "audit_events"
    __table_args__ = (CheckConstraint("actor IN ('client', 'analyst', 'system')", name="actor"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    # NULL — событие создания черновика
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32))
    actor: Mapped[str] = mapped_column(String(16))
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    # Машинный код причины, например bki_unavailable
    reason: Mapped[str | None] = mapped_column(String(255))
    comment: Mapped[str | None] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
