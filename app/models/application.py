"""Кредитная заявка. Статус меняется только через services/transitions.py."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.elements import ColumnElement

from app.domain.statuses import Status
from app.extensions import db
from app.models.company import Company
from app.models.product import Product
from app.models.user import User

_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in Status)


class Application(db.Model):  # type: ignore[name-defined]
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUS_VALUES})", name="status"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("term_months > 0", name="term_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    amount: Mapped[int] = mapped_column(BigInteger)
    term_months: Mapped[int]
    purpose: Mapped[str] = mapped_column(String(32))
    # Анкета: поля, которые клиент заполняет или подтверждает
    form_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Без сеттера: прямое присваивание application.status запрещено (см. status ниже)
    _status: Mapped[str] = mapped_column(
        "status", String(32), default=Status.DRAFT.value, index=True
    )
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Этапы конвейера для таймлайна в UI: [{"code": "bki", "state": "done", ...}]
    pipeline_steps: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped[Company] = relationship()
    created_by: Mapped[User] = relationship()
    product: Mapped[Product] = relationship()

    @hybrid_property
    def status(self) -> Status:
        return Status(self._status)

    @status.inplace.expression
    @classmethod
    def _status_expression(cls) -> ColumnElement[str]:
        return cls._status  # type: ignore[return-value]
