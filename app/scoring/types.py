"""Входные и выходные структуры скоринга: чистые данные, без БД и HTTP."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from app.domain.form_fields import COLLATERAL_FIELDS, GUARANTEE_FIELDS
from app.domain.statuses import Status


def _filled(form: Mapping[str, Any], keys: tuple[str, ...]) -> bool:
    return all(str(form.get(key) or "").strip() for key in keys)


@dataclass(frozen=True)
class EgrulData:
    status: str
    registered_at: date


@dataclass(frozen=True)
class FnsData:
    tax_debt: int = 0
    late_payments_12m: int = 0


@dataclass(frozen=True)
class BkiData:
    current_overdue_days: int = 0
    max_overdue_days_24m: int = 0
    overdue_count_24m: int = 0
    monthly_payments: int = 0


@dataclass(frozen=True)
class ProductTerms:
    code: str
    name: str
    min_amount: int
    max_amount: int
    min_term_months: int
    max_term_months: int
    rate_spread: Decimal
    requires_collateral: bool = False
    requires_guarantee: bool = False
    required_fields: tuple[str, ...] = ()

    @classmethod
    def from_model(cls, product: Any) -> "ProductTerms":
        return cls(
            code=product.code,
            name=product.name,
            min_amount=product.min_amount,
            max_amount=product.max_amount,
            min_term_months=product.min_term_months,
            max_term_months=product.max_term_months,
            rate_spread=Decimal(str(product.rate_spread)),
            requires_collateral=product.requires_collateral,
            requires_guarantee=product.requires_guarantee,
            required_fields=tuple(product.required_fields or ()),
        )


@dataclass(frozen=True)
class ScoringInput:
    okved: str
    monthly_turnover: tuple[int, ...]
    requested_amount: int
    term_months: int
    egrul: EgrulData
    fns: FnsData
    bki: BkiData
    form_data: Mapping[str, Any] = field(default_factory=dict)

    @property
    def has_collateral(self) -> bool:
        return _filled(self.form_data, COLLATERAL_FIELDS)

    @property
    def has_guarantee(self) -> bool:
        return _filled(self.form_data, GUARANTEE_FIELDS)


@dataclass(frozen=True)
class Reason:
    code: str
    text: str


@dataclass(frozen=True)
class FactorResult:
    code: str
    value: float
    points: int
    max_points: int
    explanation_ru: str

    @property
    def impact(self) -> str:
        """positive / neutral / negative — для выбора главных факторов клиенту."""
        if self.code == "security" and self.points == 0:
            return "neutral"  # отсутствие залога — не минус, а просто факт
        ratio = self.points / self.max_points
        if ratio < 0.4:
            return "negative"
        if ratio >= 0.75:
            return "positive"
        return "neutral"


@dataclass(frozen=True)
class ScoringOutcome:
    score: int
    grade: str
    factors: tuple[FactorResult, ...]


@dataclass(frozen=True)
class OfferTerms:
    amount: int
    term_months: int
    rate: Decimal
    monthly_payment: Decimal
    is_counter: bool


@dataclass(frozen=True)
class EngineDecision:
    outcome: Status
    reasons: tuple[Reason, ...]
    # Для manual_review — рекомендация движка аналитику
    offer: OfferTerms | None = None
    scoring: ScoringOutcome | None = None
    stop_factors: tuple[Reason, ...] = ()
    missing_fields: tuple[str, ...] = ()
