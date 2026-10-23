"""Входные данные для тестов скоринга: благополучный профиль и точечные изменения."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Any

from app.scoring.types import BkiData, EgrulData, FnsData, ProductTerms, ScoringInput

TODAY = date(2026, 10, 23)
KEY_RATE = Decimal("14.0")


def good_input(**overrides: Any) -> ScoringInput:
    """Профиль на грейд A: 290 баллов из 330."""
    base = ScoringInput(
        okved="10.71",
        monthly_turnover=(3_000_000,) * 12,
        requested_amount=1_000_000,
        term_months=12,
        egrul=EgrulData(status="active", registered_at=date(2015, 1, 1)),
        fns=FnsData(tax_debt=0, late_payments_12m=0),
        bki=BkiData(),
        form_data={},
    )
    return replace(base, **overrides)


def product(**overrides: Any) -> ProductTerms:
    base = ProductTerms(
        code="test",
        name="Тестовый кредит",
        min_amount=100_000,
        max_amount=10_000_000,
        min_term_months=3,
        max_term_months=36,
        rate_spread=Decimal("5.0"),
        requires_collateral=False,
        requires_guarantee=False,
        required_fields=(),
    )
    return replace(base, **overrides)


def d_grade_input(**overrides: Any) -> ScoringInput:
    """Профиль на грейд D: 130 баллов."""
    base = good_input(
        okved="56.10",
        monthly_turnover=(200_000, 600_000) * 6,
        egrul=EgrulData(status="active", registered_at=date(2024, 4, 1)),
        fns=FnsData(tax_debt=0, late_payments_12m=1),
        bki=BkiData(max_overdue_days_24m=20, overdue_count_24m=1, monthly_payments=40_000),
    )
    return replace(base, **overrides)
