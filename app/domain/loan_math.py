"""Аннуитетный платёж, график платежей и обратный расчёт суммы по платежу."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def _monthly_rate(annual_rate_pct: Decimal) -> Decimal:
    return Decimal(annual_rate_pct) / Decimal(1200)


def annuity_payment(
    principal: int | Decimal, term_months: int, annual_rate_pct: Decimal
) -> Decimal:
    p = Decimal(principal)
    r = _monthly_rate(annual_rate_pct)
    if r == 0:
        return (p / term_months).quantize(CENT, ROUND_HALF_UP)
    growth = (1 + r) ** term_months
    return (p * r * growth / (growth - 1)).quantize(CENT, ROUND_HALF_UP)


def max_principal(payment: Decimal, term_months: int, annual_rate_pct: Decimal) -> Decimal:
    """Наибольшая сумма кредита, аннуитетный платёж по которой не больше payment."""
    payment = Decimal(payment)
    if payment <= 0:
        return Decimal(0)
    r = _monthly_rate(annual_rate_pct)
    if r == 0:
        return payment * term_months
    growth = (1 + r) ** term_months
    return payment * (growth - 1) / (r * growth)


@dataclass(frozen=True)
class ScheduleRow:
    number: int
    payment: Decimal
    principal: Decimal
    interest: Decimal
    balance: Decimal


def payment_schedule(
    principal: int | Decimal, term_months: int, annual_rate_pct: Decimal
) -> list[ScheduleRow]:
    """График аннуитетных платежей; последний платёж поглощает копейки округления."""
    payment = annuity_payment(principal, term_months, annual_rate_pct)
    r = _monthly_rate(annual_rate_pct)
    balance = Decimal(principal)
    rows = []
    for number in range(1, term_months + 1):
        interest = (balance * r).quantize(CENT, ROUND_HALF_UP)
        repaid = balance if number == term_months else min(payment - interest, balance)
        balance -= repaid
        rows.append(ScheduleRow(number, repaid + interest, repaid, interest, balance))
    return rows
