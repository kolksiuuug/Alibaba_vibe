"""Стоп-факторы: любой из них ведёт к отказу (CLAUDE.md, раздел 8.1)."""

from datetime import date
from typing import Any

from app.scoring.metrics import money, months_between
from app.scoring.types import Reason, ScoringInput


def find_stop_factors(inp: ScoringInput, config: dict[str, Any], *, today: date) -> list[Reason]:
    cfg = config["stop_factors"]
    reasons = []

    if inp.egrul.status in cfg["inactive_company_statuses"]:
        reasons.append(
            Reason(
                "company_inactive",
                "По данным ЕГРЮЛ/ЕГРИП компания не действует: ликвидация или банкротство.",
            )
        )

    max_overdue = cfg["max_current_overdue_days"]
    if inp.bki.current_overdue_days > max_overdue:
        reasons.append(
            Reason(
                "current_overdue",
                f"В кредитной истории есть текущая просрочка {inp.bki.current_overdue_days} дн. "
                f"— больше {max_overdue} дней.",
            )
        )

    max_debt = cfg["max_tax_debt"]
    if inp.fns.tax_debt > max_debt:
        reasons.append(
            Reason(
                "tax_debt",
                f"Налоговая задолженность {money(inp.fns.tax_debt)} ₽ "
                f"— больше допустимых {money(max_debt)} ₽.",
            )
        )

    age = months_between(inp.egrul.registered_at, today)
    min_age = cfg["min_business_age_months"]
    if age < min_age:
        reasons.append(
            Reason(
                "business_too_young",
                f"Бизнес работает {age} мес. — нужно не меньше {min_age} месяцев.",
            )
        )

    return reasons
