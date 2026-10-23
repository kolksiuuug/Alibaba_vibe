"""Кредитное решение движка или аналитика. Актуальное решение — последнее по id."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Decision(db.Model):  # type: ignore[name-defined]
    __tablename__ = "decisions"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('offer', 'manual_review', 'info_requested', 'rejected')", name="outcome"
        ),
        CheckConstraint("decided_by IN ('engine', 'analyst')", name="decided_by"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    outcome: Mapped[str] = mapped_column(String(32))
    decided_by: Mapped[str] = mapped_column(String(16))
    analyst_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    is_counter: Mapped[bool] = mapped_column(Boolean, default=False)
    # Условия предложения; у manual_review — рекомендация движка аналитику
    amount: Mapped[int | None] = mapped_column(BigInteger)
    term_months: Mapped[int | None]
    rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    monthly_payment: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    # [{"code", "text"}]
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
