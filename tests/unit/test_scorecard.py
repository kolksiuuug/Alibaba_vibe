"""Скоринговая карта (CLAUDE.md, раздел 8.3): 9 факторов, сумма баллов -> грейд A–E."""

from datetime import date

import pytest

from app.scoring.config import load_config
from app.scoring.scorecard import client_factors, grade_for, score
from app.scoring.types import BkiData, EgrulData, FnsData, ScoringOutcome
from tests.scoring_builders import TODAY, good_input

CONFIG = load_config()
FACTOR_CODES = {
    "business_age",
    "avg_turnover",
    "turnover_stability",
    "debt_load",
    "credit_history",
    "tax_discipline",
    "amount_to_turnover",
    "security",
    "industry_risk",
}


def _points(outcome: ScoringOutcome, code: str) -> int:
    return next(f.points for f in outcome.factors if f.code == code)


def _score(**overrides: object) -> ScoringOutcome:
    return score(good_input(**overrides), CONFIG, today=TODAY)


def test_good_profile_scores_290_and_grade_a() -> None:
    outcome = _score()
    assert {f.code for f in outcome.factors} == FACTOR_CODES
    assert outcome.score == 290
    assert outcome.score == sum(f.points for f in outcome.factors)
    assert outcome.grade == "A"


def test_every_factor_has_points_within_max_and_explanation() -> None:
    for factor in _score().factors:
        assert factor.points <= factor.max_points
        assert factor.explanation_ru


@pytest.mark.parametrize(
    ("registered_at", "points"),
    [
        (date(2025, 11, 1), 0),
        (date(2025, 10, 23), 10),
        (date(2021, 10, 24), 30),
        (date(2021, 10, 23), 40),
    ],
)
def test_business_age_bands(registered_at: date, points: int) -> None:
    egrul = EgrulData(status="active", registered_at=registered_at)
    assert _points(_score(egrul=egrul), "business_age") == points


@pytest.mark.parametrize(
    ("monthly", "points"),
    [
        (299_999, 0),
        (300_000, 10),
        (999_999, 10),
        (1_000_000, 25),
        (3_000_000, 40),
        (10_000_000, 50),
    ],
)
def test_avg_turnover_bands(monthly: int, points: int) -> None:
    turnover = (monthly,) * 12
    assert (
        _points(_score(monthly_turnover=turnover, requested_amount=100_000), "avg_turnover")
        == points
    )


@pytest.mark.parametrize(
    ("turnover", "points"),
    [
        ((1_000_000,) * 12, 40),  # CV = 0
        ((950_000, 1_050_000) * 6, 40),  # CV = 0.05
        ((850_000, 1_150_000) * 6, 30),  # CV = 0.15
        ((700_000, 1_300_000) * 6, 15),  # CV = 0.30
        ((600_000, 1_400_000) * 6, 5),  # CV = 0.40
        ((200_000, 1_800_000) * 6, 0),  # CV = 0.80
    ],
)
def test_turnover_stability_bands(turnover: tuple[int, ...], points: int) -> None:
    outcome = _score(monthly_turnover=turnover, requested_amount=100_000)
    assert _points(outcome, "turnover_stability") == points


@pytest.mark.parametrize(
    ("payments", "points"),
    [
        (0, 40),
        (150_000, 40),
        (150_001, 30),
        (450_000, 30),
        (900_000, 15),
        (1_350_000, 0),
        (1_500_000, -20),
    ],
)
def test_debt_load_bands(payments: int, points: int) -> None:
    assert _points(_score(bki=BkiData(monthly_payments=payments)), "debt_load") == points


@pytest.mark.parametrize(
    ("bki", "points"),
    [
        (BkiData(), 50),
        (BkiData(max_overdue_days_24m=30, overdue_count_24m=2), 30),
        (BkiData(max_overdue_days_24m=30, overdue_count_24m=3), 10),
        (BkiData(max_overdue_days_24m=60, overdue_count_24m=1), 10),
        (BkiData(max_overdue_days_24m=61, overdue_count_24m=1), -20),
        (BkiData(current_overdue_days=5, max_overdue_days_24m=5, overdue_count_24m=1), -20),
    ],
)
def test_credit_history(bki: BkiData, points: int) -> None:
    assert _points(_score(bki=bki), "credit_history") == points


@pytest.mark.parametrize(
    ("fns", "points"),
    [
        (FnsData(late_payments_12m=0), 30),
        (FnsData(late_payments_12m=2), 15),
        (FnsData(late_payments_12m=3), 0),
        (FnsData(late_payments_12m=0, tax_debt=5_000), 20),
    ],
)
def test_tax_discipline(fns: FnsData, points: int) -> None:
    assert _points(_score(fns=fns), "tax_discipline") == points


@pytest.mark.parametrize(
    ("amount", "points"),
    [(3_600_000, 30), (3_600_001, 20), (9_000_000, 20), (18_000_000, 5), (18_000_001, -15)],
)
def test_amount_to_annual_turnover(amount: int, points: int) -> None:
    assert _points(_score(requested_amount=amount), "amount_to_turnover") == points


@pytest.mark.parametrize(
    ("form", "points"),
    [
        ({}, 0),
        ({"collateral_description": "Станок ЧПУ", "collateral_value": 2_000_000}, 25),
        ({"guarantor_full_name": "Петров Пётр Петрович", "guarantor_inn": "001234567890"}, 15),
        (
            {
                "collateral_description": "Станок ЧПУ",
                "collateral_value": 2_000_000,
                "guarantor_full_name": "Петров Пётр Петрович",
                "guarantor_inn": "001234567890",
            },
            30,
        ),
    ],
)
def test_security(form: dict[str, object], points: int) -> None:
    assert _points(_score(form_data=form), "security") == points


@pytest.mark.parametrize(
    ("okved", "points"), [("10.71", 20), ("49.41", 10), ("56.10", 0), ("41.20", 0)]
)
def test_industry_risk(okved: str, points: int) -> None:
    assert _points(_score(okved=okved), "industry_risk") == points


@pytest.mark.parametrize(
    ("total", "grade"),
    [
        (330, "A"),
        (250, "A"),
        (249, "B"),
        (200, "B"),
        (199, "C"),
        (140, "C"),
        (139, "D"),
        (100, "D"),
        (99, "E"),
        (-50, "E"),
    ],
)
def test_grade_thresholds(total: int, grade: str) -> None:
    assert grade_for(total, CONFIG) == grade


def test_client_sees_three_to_five_main_factors() -> None:
    outcome = _score(
        bki=BkiData(max_overdue_days_24m=45, overdue_count_24m=1),
        fns=FnsData(late_payments_12m=3),
    )
    shown = client_factors(outcome)
    assert 3 <= len(shown) <= 5
    codes = {f.code for f in shown}
    assert {"credit_history", "tax_discipline"} <= codes
