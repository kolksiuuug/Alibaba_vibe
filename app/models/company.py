"""Компания — действующий клиент банка. Все данные синтетические."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Company(db.Model):  # type: ignore[name-defined]
    __tablename__ = "companies"
    __table_args__ = (CheckConstraint("kind IN ('ip', 'llc')", name="kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(8))
    inn: Mapped[str] = mapped_column(String(12), unique=True)
    ogrn: Mapped[str] = mapped_column(String(15), unique=True)
    okved: Mapped[str] = mapped_column(String(16))
    okved_name: Mapped[str] = mapped_column(String(255))
    registered_at: Mapped[date]
    region: Mapped[str] = mapped_column(String(128))
    director_name: Mapped[str] = mapped_column(String(255))
    # Обороты по расчётному счёту за 12 месяцев: [{"month": "2025-10", "amount": 3420000}, ...]
    monthly_turnover: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
