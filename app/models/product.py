"""Кредитный продукт. Названия и параметры вымышленные."""

from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Product(db.Model):  # type: ignore[name-defined]
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("min_amount > 0 AND min_amount <= max_amount", name="amount_range"),
        CheckConstraint(
            "min_term_months > 0 AND min_term_months <= max_term_months", name="term_range"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    # Коды целей кредита, под которые подходит продукт
    purposes: Mapped[list[str]] = mapped_column(JSONB)
    min_amount: Mapped[int] = mapped_column(BigInteger)
    max_amount: Mapped[int] = mapped_column(BigInteger)
    min_term_months: Mapped[int]
    max_term_months: Mapped[int]
    # Спред к ключевой ставке, п. п.
    rate_spread: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    requires_collateral: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_guarantee: Mapped[bool] = mapped_column(Boolean, default=False)
    # Поля анкеты, обязательные именно для этого продукта (сверх общих)
    required_fields: Mapped[list[str]] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
