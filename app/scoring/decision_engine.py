"""Кредитное решение: стоп-факторы -> полнота данных -> грейд -> условия (CLAUDE.md, раздел 8).

Скоринг даёт оценку риска, а итог и условия определяются здесь с учётом продукта,
суммы, срока и долговой нагрузки.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from app.domain.form_fields import COLLATERAL_FIELDS, FIELD_LABELS, GUARANTEE_FIELDS
from app.domain.loan_math import annuity_payment, max_principal
from app.domain.statuses import Status
from app.scoring.config import load_config
from app.scoring.metrics import average, money
from app.scoring.scorecard import score
from app.scoring.stop_factors import find_stop_factors
from app.scoring.types import (
    EngineDecision,
    OfferTerms,
    ProductTerms,
    Reason,
    ScoringInput,
    ScoringOutcome,
)


@dataclass(frozen=True)
class _Pricing:
    inp: ScoringInput
    product: ProductTerms
    grade: str
    rate: Decimal
    avg_turnover: float
    cfg: dict[str, Any]

    def max_payment(self) -> float:
        """Сколько ещё можно платить в месяц, не превысив допустимую долговую нагрузку."""
        return self.cfg["max_debt_load"] * self.avg_turnover - self.inp.bki.monthly_payments

    def debt_load_cap(self, term: int) -> float:
        return float(max_principal(Decimal(str(self.max_payment())), term, self.rate))

    def limit(self, term: int) -> int:
        """min(макс. сумма продукта, k(грейд) × оборот × f(срок), сумма по долговой нагрузке)."""
        k = self.cfg["limit_multiplier"][self.grade]
        term_factor = min(term, self.cfg["term_factor_cap_months"]) / 12
        turnover_cap = k * self.avg_turnover * term_factor
        raw = min(self.product.max_amount, turnover_cap, self.debt_load_cap(term))
        step = self.cfg["amount_rounding"]
        return max(0, int(raw // step) * step)

    def offer(self, amount: int, term: int, *, is_counter: bool) -> OfferTerms:
        payment = annuity_payment(amount, term, self.rate)
        return OfferTerms(amount, term, self.rate, payment, is_counter)


def missing_fields(inp: ScoringInput, product: ProductTerms) -> tuple[str, ...]:
    required = list(product.required_fields)
    if product.requires_collateral:
        required += [f for f in COLLATERAL_FIELDS if f not in required]
    if product.requires_guarantee:
        required += [f for f in GUARANTEE_FIELDS if f not in required]
    return tuple(f for f in required if not str(inp.form_data.get(f) or "").strip())


def _term_extended(term: int, requested: int) -> Reason:
    return Reason(
        "term_extended",
        f"Чтобы платёж был посильным для бизнеса, предлагаем срок {term} мес. вместо {requested}.",
    )


def _best_offer(pricing: _Pricing) -> tuple[OfferTerms | None, list[Reason]]:
    """Запрошенные условия; иначе та же сумма на более длинный срок; иначе сумма = лимит."""
    amount, term = pricing.inp.requested_amount, pricing.inp.term_months
    terms = range(term, max(term, pricing.product.max_term_months) + 1)

    if amount <= pricing.limit(term):
        return pricing.offer(amount, term, is_counter=False), []
    for longer in terms[1:]:
        if amount <= pricing.limit(longer):
            return pricing.offer(amount, longer, is_counter=True), [_term_extended(longer, term)]

    best_term = max(terms, key=lambda t: (pricing.limit(t), -t))
    best_amount = pricing.limit(best_term)
    if best_amount < pricing.product.min_amount:
        return None, [
            Reason(
                "limit_below_minimum",
                "Доступная сумма по оборотам и долговой нагрузке "
                "меньше минимальной суммы продукта.",
            )
        ]
    reasons = [
        Reason(
            "amount_above_limit",
            f"Сейчас можем предложить {money(best_amount)} ₽: запрошенная сумма больше лимита "
            "по оборотам и текущей долговой нагрузке.",
        )
    ]
    if best_term > term:
        reasons.append(_term_extended(best_term, term))
    return pricing.offer(best_amount, best_term, is_counter=True), reasons


def _reduced_counter(pricing: _Pricing, scoring: ScoringOutcome) -> EngineDecision:
    """Грейд D: меньшая сумма на запрошенный срок, если платёж проходит по долговой нагрузке."""
    term = pricing.inp.term_months
    step = pricing.cfg["amount_rounding"]
    share = pricing.cfg["d_grade_amount_share"]
    reduced = int(pricing.inp.requested_amount * share) // step * step
    amount = min(reduced, pricing.limit(term))
    product = pricing.product

    if amount < product.min_amount:
        if pricing.debt_load_cap(term) < product.min_amount:
            reason = Reason(
                "debt_load_exceeded",
                "С новым кредитом платежи были бы слишком большими относительно оборота.",
            )
        else:
            reason = Reason(
                "limit_below_minimum",
                "Доступная сумма меньше минимальной суммы продукта.",
            )
        return EngineDecision(Status.REJECTED, (reason,), scoring=scoring)

    reason = Reason(
        "reduced_amount",
        f"Риск по заявке повышенный, поэтому можем предложить меньшую сумму — {money(amount)} ₽.",
    )
    offer = pricing.offer(amount, term, is_counter=True)
    return EngineDecision(Status.OFFER, (reason,), offer=offer, scoring=scoring)


def decide(
    inp: ScoringInput,
    product: ProductTerms,
    *,
    key_rate: Decimal,
    today: date,
    config: dict[str, Any] | None = None,
) -> EngineDecision:
    config = config or load_config()

    stops = find_stop_factors(inp, config, today=today)
    if stops:
        return EngineDecision(Status.REJECTED, tuple(stops), stop_factors=tuple(stops))

    missing = missing_fields(inp, product)
    if missing:
        labels = ", ".join(FIELD_LABELS.get(field, field) for field in missing)
        reason = Reason(
            "missing_fields", f"Для продукта «{product.name}» не хватает данных: {labels}."
        )
        return EngineDecision(Status.INFO_REQUESTED, (reason,), missing_fields=missing)

    scoring = score(inp, config, today=today)
    if scoring.grade == "E":
        reason = Reason("low_score", "Оценка риска по заявке слишком низкая для выдачи кредита.")
        return EngineDecision(Status.REJECTED, (reason,), scoring=scoring)

    cfg = config["decision"]
    premium = Decimal(str(cfg["rate_premium"][scoring.grade]))
    pricing = _Pricing(
        inp=inp,
        product=product,
        grade=scoring.grade,
        rate=(Decimal(key_rate) + product.rate_spread + premium).quantize(Decimal("0.01")),
        avg_turnover=average(inp.monthly_turnover),
        cfg=cfg,
    )

    if scoring.grade == "D":
        return _reduced_counter(pricing, scoring)

    offer, reasons = _best_offer(pricing)
    if scoring.grade == "C":
        reason = Reason(
            "borderline_score", "Оценка пограничная: заявку рассмотрит кредитный аналитик."
        )
        return EngineDecision(
            Status.MANUAL_REVIEW, (reason, *reasons), offer=offer, scoring=scoring
        )

    if offer is None:
        return EngineDecision(Status.REJECTED, tuple(reasons), scoring=scoring)
    if not offer.is_counter:
        reasons = [Reason("approved", "Заявка одобрена на запрошенных условиях.")]
    return EngineDecision(Status.OFFER, tuple(reasons), offer=offer, scoring=scoring)
