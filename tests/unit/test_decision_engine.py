"""Кредитное решение (CLAUDE.md, раздел 8.1–8.6): каждая ветка покрыта тестом."""

import random
from dataclasses import replace
from datetime import date
from decimal import Decimal

from app.domain.loan_math import annuity_payment
from app.domain.statuses import Status
from app.scoring.decision_engine import decide
from app.scoring.types import BkiData, EgrulData, EngineDecision, FnsData, ScoringInput
from tests.scoring_builders import KEY_RATE, TODAY, d_grade_input, good_input, product

MAX_DEBT_LOAD = 0.25


def _decide(inp: ScoringInput, **product_overrides: object) -> EngineDecision:
    return decide(inp, product(**product_overrides), key_rate=KEY_RATE, today=TODAY)


def _debt_load(inp: ScoringInput, payment: Decimal) -> float:
    avg = sum(inp.monthly_turnover) / len(inp.monthly_turnover)
    return (inp.bki.monthly_payments + float(payment)) / avg


def _reason_codes(decision: EngineDecision) -> set[str]:
    return {reason.code for reason in decision.reasons}


def test_stop_factor_rejects_with_reason() -> None:
    decision = _decide(good_input(bki=BkiData(current_overdue_days=120, max_overdue_days_24m=120)))

    assert decision.outcome is Status.REJECTED
    assert [r.code for r in decision.stop_factors] == ["current_overdue"]
    assert decision.offer is None


def test_stop_factor_wins_over_missing_fields() -> None:
    decision = _decide(
        good_input(egrul=EgrulData(status="liquidated", registered_at=date(2015, 1, 1))),
        required_fields=("collateral_value",),
    )
    assert decision.outcome is Status.REJECTED


def test_missing_product_fields_request_info() -> None:
    decision = _decide(
        good_input(form_data={"collateral_description": "Фрезерный станок"}),
        requires_collateral=True,
        required_fields=("collateral_description", "collateral_value", "equipment_supplier"),
    )

    assert decision.outcome is Status.INFO_REQUESTED
    assert decision.missing_fields == ("collateral_value", "equipment_supplier")
    assert decision.reasons[0].code == "missing_fields"


def test_grade_a_within_limit_gets_offer_on_requested_terms() -> None:
    decision = _decide(good_input())

    assert decision.scoring is not None and decision.scoring.grade == "A"
    assert decision.outcome is Status.OFFER
    offer = decision.offer
    assert offer is not None
    assert (offer.amount, offer.term_months, offer.is_counter) == (1_000_000, 12, False)
    assert offer.rate == Decimal("19.0")  # 14 + 5 + 0
    assert offer.monthly_payment == annuity_payment(1_000_000, 12, Decimal("19.0"))


def test_grade_b_rate_includes_grade_premium() -> None:
    inp = good_input(
        okved="56.10",
        bki=BkiData(max_overdue_days_24m=10, overdue_count_24m=1),
        fns=FnsData(late_payments_12m=1),
    )
    decision = _decide(inp)

    assert decision.scoring is not None and decision.scoring.grade == "B"
    assert decision.outcome is Status.OFFER
    assert decision.offer is not None
    assert decision.offer.rate == Decimal("20.5")  # 14 + 5 + 1.5


def test_grade_a_over_limit_gets_counter_with_longer_term() -> None:
    inp = good_input(requested_amount=9_500_000)
    decision = _decide(inp)

    assert decision.outcome is Status.OFFER
    offer = decision.offer
    assert offer is not None and offer.is_counter
    assert offer.amount == 9_500_000
    assert 12 < offer.term_months <= 36
    assert _debt_load(inp, offer.monthly_payment) <= MAX_DEBT_LOAD
    assert "term_extended" in _reason_codes(decision)


def test_far_over_limit_gets_counter_capped_at_limit() -> None:
    inp = good_input(requested_amount=20_000_000)
    decision = _decide(inp)

    offer = decision.offer
    assert decision.outcome is Status.OFFER
    assert offer is not None and offer.is_counter
    assert offer.amount == 10_000_000  # максимум продукта
    assert _debt_load(inp, offer.monthly_payment) <= MAX_DEBT_LOAD
    assert "amount_above_limit" in _reason_codes(decision)


def test_limit_below_product_minimum_is_rejected() -> None:
    inp = good_input(requested_amount=6_000_000, bki=BkiData(monthly_payments=700_000))
    decision = _decide(inp, min_amount=5_000_000)

    assert decision.scoring is not None and decision.scoring.grade in {"A", "B"}
    assert decision.outcome is Status.REJECTED
    assert "limit_below_minimum" in _reason_codes(decision)


def test_grade_c_goes_to_manual_review_with_recommendation() -> None:
    inp = good_input(
        okved="56.10",
        monthly_turnover=(700_000, 1_300_000) * 6,
        bki=BkiData(max_overdue_days_24m=25, overdue_count_24m=1, monthly_payments=120_000),
        fns=FnsData(late_payments_12m=1),
    )
    decision = _decide(inp)

    assert decision.scoring is not None and decision.scoring.grade == "C"
    assert decision.outcome is Status.MANUAL_REVIEW
    assert decision.offer is not None  # рекомендация движка для аналитика
    assert decision.offer.rate == Decimal("22.0")  # 14 + 5 + 3
    assert "borderline_score" in _reason_codes(decision)


def test_grade_d_gets_reduced_counter_when_payment_fits() -> None:
    inp = d_grade_input()
    decision = _decide(inp)

    assert decision.scoring is not None and decision.scoring.grade == "D"
    assert decision.outcome is Status.OFFER
    offer = decision.offer
    assert offer is not None and offer.is_counter
    assert 100_000 <= offer.amount <= inp.requested_amount // 2
    assert offer.rate == Decimal("24.0")  # 14 + 5 + 5
    assert _debt_load(inp, offer.monthly_payment) <= MAX_DEBT_LOAD


def test_grade_d_rejected_when_debt_load_too_high() -> None:
    inp = d_grade_input(
        bki=BkiData(max_overdue_days_24m=20, overdue_count_24m=1, monthly_payments=120_000)
    )
    decision = _decide(inp)

    assert decision.scoring is not None and decision.scoring.grade == "D"
    assert decision.outcome is Status.REJECTED
    assert "debt_load_exceeded" in _reason_codes(decision)


def test_grade_e_rejected() -> None:
    inp = d_grade_input(
        bki=BkiData(max_overdue_days_24m=80, overdue_count_24m=4, monthly_payments=200_000),
        fns=FnsData(late_payments_12m=5),
    )
    decision = _decide(inp)

    assert decision.scoring is not None and decision.scoring.grade == "E"
    assert decision.outcome is Status.REJECTED
    assert decision.offer is None
    assert "low_score" in _reason_codes(decision)


def test_random_profiles_always_get_consistent_decisions() -> None:
    """Логика не заточена под демо: на любых синтетических данных решение корректно."""
    rng = random.Random(42)
    allowed = {Status.OFFER, Status.MANUAL_REVIEW, Status.REJECTED, Status.INFO_REQUESTED}
    for _ in range(300):
        base = rng.randint(100_000, 8_000_000)
        inp = replace(
            good_input(),
            okved=rng.choice(["10.71", "49.41", "56.10", "41.20", "62.01"]),
            monthly_turnover=tuple(int(base * rng.uniform(0.4, 1.6)) for _ in range(12)),
            requested_amount=rng.randint(100_000, 10_000_000),
            term_months=rng.randint(3, 36),
            egrul=EgrulData(status="active", registered_at=date(rng.randint(2010, 2026), 1, 1)),
            fns=FnsData(
                tax_debt=rng.choice([0, 0, 50_000, 200_000]),
                late_payments_12m=rng.randint(0, 4),
            ),
            bki=BkiData(
                current_overdue_days=rng.choice([0, 0, 0, 30, 120]),
                max_overdue_days_24m=rng.choice([0, 10, 45, 90]),
                overdue_count_24m=rng.randint(0, 4),
                monthly_payments=rng.randint(0, base // 2),
            ),
        )
        decision = _decide(inp)
        assert decision.outcome in allowed
        if decision.outcome is Status.OFFER:
            offer = decision.offer
            assert offer is not None
            assert 100_000 <= offer.amount <= 10_000_000
            assert 3 <= offer.term_months <= 36
            assert Decimal("19.0") <= offer.rate <= Decimal("24.0")
            assert _debt_load(inp, offer.monthly_payment) <= MAX_DEBT_LOAD + 1e-9
            if not offer.is_counter:
                assert offer.amount == inp.requested_amount
