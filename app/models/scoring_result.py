"""Результат скоринга: баллы, грейд, факторы с объяснениями, сработавшие стоп-факторы."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class ScoringResult(db.Model):  # type: ignore[name-defined]
    __tablename__ = "scoring_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    # NULL, если сработал стоп-фактор и карта не считалась
    score: Mapped[int | None]
    grade: Mapped[str | None] = mapped_column(String(1))
    # [{"code", "value", "points", "max_points", "explanation_ru", "impact"}]
    factors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    # Коды 3–5 главных факторов, которые видит клиент
    client_factors: Mapped[list[str]] = mapped_column(JSONB, default=list)
    # [{"code", "text"}]
    stop_factors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
