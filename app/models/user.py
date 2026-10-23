"""Пользователь демо-профиля: клиент (привязан к компании) или аналитик."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.company import Company


class User(db.Model):  # type: ignore[name-defined]
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('client', 'analyst')", name="role"),
        CheckConstraint("(role = 'client') = (company_id IS NOT NULL)", name="client_has_company"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(64), unique=True)
    role: Mapped[str] = mapped_column(String(16))
    display_name: Mapped[str] = mapped_column(String(255))
    # Подсказка на экране демо-входа: какой сценарий проходит этот профиль
    demo_hint: Mapped[str | None] = mapped_column(String(255))
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped[Company | None] = relationship()
