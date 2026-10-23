"""Стоп-факторы (CLAUDE.md, раздел 8.1): любой из них ведёт к отказу."""

from datetime import date

import pytest

from app.scoring.config import load_config
from app.scoring.stop_factors import find_stop_factors
from app.scoring.types import BkiData, EgrulData, FnsData
from tests.scoring_builders import TODAY, good_input

CONFIG = load_config()


def _codes(**overrides: object) -> list[str]:
    return [reason.code for reason in find_stop_factors(good_input(**overrides), CONFIG, today=TODAY)]


def test_clean_profile_has_no_stop_factors() -> None:
    assert _codes() == []


@pytest.mark.parametrize("status", ["liquidating", "liquidated", "bankrupt"])
def test_inactive_company_is_stopped(status: str) -> None:
    assert _codes(egrul=EgrulData(status=status, registered_at=date(2015, 1, 1))) == [
        "company_inactive"
    ]


@pytest.mark.parametrize(("days", "stopped"), [(90, False), (91, True), (120, True)])
def test_current_overdue_over_90_days(days: int, stopped: bool) -> None:
    codes = _codes(bki=BkiData(current_overdue_days=days, max_overdue_days_24m=days))
    assert ("current_overdue" in codes) is stopped


@pytest.mark.parametrize(("debt", "stopped"), [(100_000, False), (100_001, True)])
def test_tax_debt_above_threshold(debt: int, stopped: bool) -> None:
    assert ("tax_debt" in _codes(fns=FnsData(tax_debt=debt))) is stopped


@pytest.mark.parametrize(
    ("registered_at", "stopped"),
    [(date(2026, 4, 23), False), (date(2026, 4, 24), True), (date(2026, 9, 1), True)],
)
def test_business_younger_than_6_months(registered_at: date, stopped: bool) -> None:
    codes = _codes(egrul=EgrulData(status="active", registered_at=registered_at))
    assert ("business_too_young" in codes) is stopped


def test_all_stop_factors_are_reported_with_russian_text() -> None:
    reasons = find_stop_factors(
        good_input(
            egrul=EgrulData(status="bankrupt", registered_at=date(2026, 9, 1)),
            fns=FnsData(tax_debt=500_000),
            bki=BkiData(current_overdue_days=200, max_overdue_days_24m=200),
        ),
        CONFIG,
        today=TODAY,
    )
    assert {r.code for r in reasons} == {
        "company_inactive",
        "current_overdue",
        "tax_debt",
        "business_too_young",
    }
    assert all(reason.text for reason in reasons)
