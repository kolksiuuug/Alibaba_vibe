"""Пять демо-сценариев из README дают заявленные исходы на данных seed/ и mocks/data/."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.domain.statuses import Status
from app.scoring.decision_engine import decide
from app.scoring.types import BkiData, EgrulData, EngineDecision, FnsData, ProductTerms, ScoringInput
from tests.scoring_builders import KEY_RATE, TODAY

ROOT = Path(__file__).resolve().parents[2]
BKI_FIELDS = ("current_overdue_days", "max_overdue_days_24m", "overdue_count_24m", "monthly_payments")
COLLATERAL_FORM = {
    "collateral_description": "Токарный станок с ЧПУ, 2024 года выпуска",
    "collateral_value": 3_200_000,
    "equipment_supplier": "ООО «Станкоцентр» (вымышленный поставщик)",
}


def _load(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


COMPANIES = {item["login"]: item["company"] for item in _load("seed/demo_companies.json")}
PRODUCTS = {item["code"]: item for item in _load("seed/products.json")}
EGRUL = _load("mocks/data/egrul.json")
FNS = _load("mocks/data/fns.json")
BKI = _load("mocks/data/bki.json")


def _product(code: str) -> ProductTerms:
    p = PRODUCTS[code]
    return ProductTerms(
        code=p["code"],
        name=p["name"],
        min_amount=p["min_amount"],
        max_amount=p["max_amount"],
        min_term_months=p["min_term_months"],
        max_term_months=p["max_term_months"],
        rate_spread=Decimal(str(p["rate_spread"])),
        requires_collateral=p["requires_collateral"],
        requires_guarantee=p["requires_guarantee"],
        required_fields=tuple(p["required_fields"]),
    )


def _decide(
    login: str, product_code: str, amount: int, term: int, form: dict[str, Any] | None = None
) -> EngineDecision:
    company = COMPANIES[login]
    inn = company["inn"]
    inp = ScoringInput(
        okved=company["okved"],
        monthly_turnover=tuple(month["amount"] for month in company["monthly_turnover"]),
        requested_amount=amount,
        term_months=term,
        egrul=EgrulData(
            status=EGRUL[inn]["status"],
            registered_at=date.fromisoformat(EGRUL[inn]["registered_at"]),
        ),
        fns=FnsData(tax_debt=FNS[inn]["tax_debt"], late_payments_12m=FNS[inn]["late_payments_12m"]),
        bki=BkiData(**{field: BKI[inn][field] for field in BKI_FIELDS}),
        form_data=form or {},
    )
    return decide(inp, _product(product_code), key_rate=KEY_RATE, today=TODAY)


def test_mock_data_covers_every_demo_company() -> None:
    inns = {company["inn"] for company in COMPANIES.values()}
    assert inns <= set(EGRUL) and inns <= set(FNS) and inns <= set(BKI)


def test_demo_approve_gets_offer() -> None:
    decision = _decide("demo-approve", "turnover", 3_000_000, 24)
    assert decision.outcome is Status.OFFER
    assert decision.offer is not None and not decision.offer.is_counter


def test_demo_counter_gets_counter_offer() -> None:
    decision = _decide("demo-counter", "turnover", 12_000_000, 24)
    assert decision.outcome is Status.OFFER
    offer = decision.offer
    assert offer is not None and offer.is_counter
    assert offer.amount < 12_000_000
    assert offer.term_months >= 24


def test_demo_info_requests_collateral_then_gets_offer() -> None:
    first = _decide("demo-info", "equipment", 2_500_000, 36)
    assert first.outcome is Status.INFO_REQUESTED
    assert set(first.missing_fields) == set(COLLATERAL_FORM)

    second = _decide("demo-info", "equipment", 2_500_000, 36, COLLATERAL_FORM)
    assert second.outcome is Status.OFFER


def test_demo_manual_goes_to_manual_review() -> None:
    decision = _decide("demo-manual", "express", 1_500_000, 18)
    assert decision.scoring is not None and decision.scoring.grade == "C"
    assert decision.outcome is Status.MANUAL_REVIEW


def test_demo_reject_is_rejected_for_overdue() -> None:
    decision = _decide("demo-reject", "turnover", 2_000_000, 12)
    assert decision.outcome is Status.REJECTED
    assert [reason.code for reason in decision.stop_factors] == ["current_overdue"]
