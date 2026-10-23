"""Дозапрос банка: какие данные нужны и что ответил клиент."""

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class InfoRequest(db.Model):  # type: ignore[name-defined]
    __tablename__ = "info_requests"
    __table_args__ = (
        CheckConstraint("requested_by IN ('engine', 'analyst')", name="requested_by"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    requested_by: Mapped[str] = mapped_column(String(16))
    analyst_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    # Коды полей анкеты, которые нужно заполнить
    fields: Mapped[list[str]] = mapped_column(JSONB, default=list)
    message: Mapped[str] = mapped_column(Text)
    response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
