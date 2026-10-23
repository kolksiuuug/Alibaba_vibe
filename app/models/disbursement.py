"""Выдача кредита через мок АБС (симуляция). Одна выдача на заявку."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Disbursement(db.Model):  # type: ignore[name-defined]
    __tablename__ = "disbursements"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), unique=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    abs_reference: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
