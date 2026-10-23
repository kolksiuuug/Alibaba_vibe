from decimal import Decimal

import pytest

from app.domain.loan_math import annuity_payment, max_principal, payment_schedule


@pytest.mark.parametrize(
    ("principal", "term", "rate", "expected"),
    [
        (1_000_000, 12, "18.5", "91918.12"),
        (3_000_000, 24, "18.5", "150498.08"),
        (500_000, 6, "0", "83333.33"),
    ],
)
def test_annuity_payment(principal: int, term: int, rate: str, expected: str) -> None:
    assert annuity_payment(principal, term, Decimal(rate)) == Decimal(expected)


def test_max_principal_is_inverse_of_payment() -> None:
    payment = annuity_payment(2_500_000, 36, Decimal("17.0"))
    assert abs(max_principal(payment, 36, Decimal("17.0")) - 2_500_000) < 1


def test_max_principal_for_non_positive_payment_is_zero() -> None:
    assert max_principal(Decimal("-10"), 12, Decimal("20")) == 0
    assert max_principal(Decimal("0"), 12, Decimal("20")) == 0


@pytest.mark.parametrize(
    ("principal", "term", "rate"), [(1_000_000, 12, "18.5"), (750_000, 7, "0")]
)
def test_schedule_repays_principal_exactly(principal: int, term: int, rate: str) -> None:
    rows = payment_schedule(principal, term, Decimal(rate))

    assert [row.number for row in rows] == list(range(1, term + 1))
    assert sum(row.principal for row in rows) == principal
    assert rows[-1].balance == 0
    assert all(row.payment == row.principal + row.interest for row in rows)
    assert all(row.payment == rows[0].payment for row in rows[:-1])
