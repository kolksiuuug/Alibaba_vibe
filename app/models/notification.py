"""Уведомление в центре уведомлений продукта (email и SMS не используются)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Notification(db.Model):  # type: ignore[name-defined]
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32), default="status_changed")
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
