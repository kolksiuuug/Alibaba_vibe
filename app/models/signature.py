"""Подписание договора кодом из интерфейса (симуляция ЭП). Одна запись на заявку."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Signature(db.Model):  # type: ignore[name-defined]
    __tablename__ = "signatures"
    __table_args__ = (CheckConstraint("status IN ('pending', 'signed')", name="status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    # Код хранится только в виде хеша; сам код показывается клиенту в интерфейсе
    code_hash: Mapped[str] = mapped_column(String(64))
    code_salt: Mapped[str] = mapped_column(String(32))
    attempts: Mapped[int] = mapped_column(default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # SHA-256 условий предложения: что именно подписано
    document_hash: Mapped[str] = mapped_column(String(64))
    signature_reference: Mapped[str | None] = mapped_column(String(64))
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
