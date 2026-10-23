"""Скоринговая карта: 9 факторов с баллами и объяснением на русском (CLAUDE.md, раздел 8.3)."""

from datetime import date
from typing import Any

from app.scoring.metrics import average, money, months_between, percent, plural, variation
from app.scoring.types import BkiData, FactorResult, FnsData, ScoringInput, ScoringOutcome

Bands = list[list[Any]]


def _lower_bound_points(value: float, bands: Bands) -> int:
    """Последняя полоса, порог которой <= значения."""
    points = int(bands[0][1])
    for threshold, band_points in bands:
        if value >= threshold:
            points = int(band_points)
    return points


def _upper_bound_points(value: float, bands: Bands) -> int:
    """Первая полоса, порог которой >= значения; порог null — без ограничения."""
    for threshold, band_points in bands:
        if threshold is None or value <= threshold:
            return int(band_points)
    return int(bands[-1][1])


def _business_age(months: int, cfg: dict[str, Any]) -> FactorResult:
    points = _lower_bound_points(months, cfg["bands"])
    years = months // 12
    if months < 12:
        text = f"Бизнесу {months} мес. — истории пока мало, поэтому риск выше."
    elif points >= 30:
        text = f"Бизнес работает {years} {plural(years, ('год', 'года', 'лет'))} — надёжный срок."
    else:
        text = f"Бизнес работает {years} {plural(years, ('год', 'года', 'лет'))}."
    return FactorResult("business_age", months, points, cfg["max_points"], text)


def _avg_turnover(avg: float, cfg: dict[str, Any]) -> FactorResult:
    points = _lower_bound_points(avg, cfg["bands"])
    text = f"Среднемесячный оборот по счёту — {money(avg)} ₽."
    if points >= 40:
        text += " Это высокий уровень."
    elif points <= 10:
        text += " Оборот небольшой, поэтому доступная сумма ниже."
    return FactorResult("avg_turnover", round(avg), points, cfg["max_points"], text)


def _turnover_stability(cv: float, cfg: dict[str, Any]) -> FactorResult:
    points = _upper_bound_points(cv, cfg["bands"])
    if cv <= 0.10:
        text = "Обороты стабильные: от месяца к месяцу почти не меняются."
    elif cv <= 0.20:
        text = "Обороты в целом стабильные."
    elif cv <= 0.35:
        text = "Обороты заметно колеблются от месяца к месяцу."
    else:
        text = "Обороты сильно скачут — это повышает риск."
    return FactorResult("turnover_stability", round(cv, 3), points, cfg["max_points"], text)


def _debt_load(payments: int, avg: float, cfg: dict[str, Any]) -> FactorResult:
    ratio = payments / avg if avg > 0 else float("inf")
    points = _upper_bound_points(ratio, cfg["bands"])
    if payments == 0:
        text = "Других кредитов нет — текущая долговая нагрузка нулевая."
    else:
        level = "низкая" if points >= 30 else "умеренная" if points >= 15 else "высокая"
        text = f"Платежи по текущим кредитам — {percent(ratio)} от оборота, нагрузка {level}."
    return FactorResult("debt_load", round(ratio, 3), points, cfg["max_points"], text)


def _credit_history(bki: BkiData, cfg: dict[str, Any]) -> FactorResult:
    worst = bki.max_overdue_days_24m
    if bki.current_overdue_days > 0:
        points, text = (
            cfg["severe"],
            "Сейчас есть просрочка по кредиту — это сильно снижает оценку.",
        )
    elif worst == 0:
        points, text = cfg["clean"], "За 2 года просрочек по кредитам не было."
    elif worst <= cfg["minor_max_days"] and bki.overdue_count_24m <= cfg["minor_max_count"]:
        points = cfg["minor"]
        text = f"За 2 года были короткие просрочки (до {worst} дн.) — это допустимо."
    elif worst <= cfg["moderate_max_days"]:
        points = cfg["moderate"]
        text = f"За 2 года были просрочки до {worst} дн. — это снижает оценку."
    else:
        points, text = cfg["severe"], f"За 2 года были серьёзные просрочки — до {worst} дн."
    return FactorResult("credit_history", worst, points, cfg["max_points"], text)


def _tax_discipline(fns: FnsData, cfg: dict[str, Any]) -> FactorResult:
    late = fns.late_payments_12m
    points = _upper_bound_points(late, cfg["bands"])
    if late == 0:
        text = "Налоги платятся вовремя."
    else:
        text = (
            f"За год налоги {late} {plural(late, ('раз', 'раза', 'раз'))} заплачены с опозданием."
        )
    if fns.tax_debt > 0:
        points += cfg["debt_penalty"]
        text += f" Есть налоговая задолженность — {money(fns.tax_debt)} ₽."
    elif late == 0:
        text += " Задолженности нет."
    return FactorResult("tax_discipline", late, points, cfg["max_points"], text)


def _amount_to_turnover(amount: int, avg: float, cfg: dict[str, Any]) -> FactorResult:
    annual = avg * 12
    ratio = amount / annual if annual > 0 else float("inf")
    points = _upper_bound_points(ratio, cfg["bands"])
    text = f"Запрошенная сумма — {percent(ratio)} годового оборота."
    if points >= 20:
        text += " Это комфортно для бизнеса такого размера."
    else:
        text += " Сумма большая относительно оборота."
    return FactorResult("amount_to_turnover", round(ratio, 3), points, cfg["max_points"], text)


def _security(has_collateral: bool, has_guarantee: bool, cfg: dict[str, Any]) -> FactorResult:
    if has_collateral and has_guarantee:
        points, text = cfg["both"], "Есть залог и поручительство — риск для банка ниже."
    elif has_collateral:
        points, text = cfg["collateral"], "Кредит обеспечен залогом."
    elif has_guarantee:
        points, text = cfg["guarantee"], "Есть поручитель."
    else:
        points, text = 0, "Кредит без залога и поручительства."
    # value: 0 — нет обеспечения, 1 — залог, 2 — поручительство, 3 — оба
    value = int(has_collateral) + 2 * int(has_guarantee)
    return FactorResult("security", value, points, cfg["max_points"], text)


def _industry_risk(okved: str, cfg: dict[str, Any]) -> FactorResult:
    okved_class = okved.split(".")[0][:2]
    if okved_class in cfg["low_classes"]:
        points, text = cfg["low_points"], "Отрасль с низким кредитным риском."
    elif okved_class in cfg["high_classes"]:
        points = cfg["high_points"]
        text = "Отрасль с повышенным риском: сезонность и высокая конкуренция."
    else:
        points, text = cfg["default_points"], "Отрасль со средним кредитным риском."
    return FactorResult("industry_risk", points, points, cfg["max_points"], text)


def grade_for(total: int, config: dict[str, Any]) -> str:
    for grade in ("A", "B", "C", "D"):
        if total >= config["grades"][grade]:
            return grade
    return "E"


def score(inp: ScoringInput, config: dict[str, Any], *, today: date) -> ScoringOutcome:
    cfg = config["factors"]
    avg = average(inp.monthly_turnover)
    factors = (
        _business_age(months_between(inp.egrul.registered_at, today), cfg["business_age"]),
        _avg_turnover(avg, cfg["avg_turnover"]),
        _turnover_stability(variation(inp.monthly_turnover), cfg["turnover_stability"]),
        _debt_load(inp.bki.monthly_payments, avg, cfg["debt_load"]),
        _credit_history(inp.bki, cfg["credit_history"]),
        _tax_discipline(inp.fns, cfg["tax_discipline"]),
        _amount_to_turnover(inp.requested_amount, avg, cfg["amount_to_turnover"]),
        _security(inp.has_collateral, inp.has_guarantee, cfg["security"]),
        _industry_risk(inp.okved, cfg["industry_risk"]),
    )
    total = sum(factor.points for factor in factors)
    return ScoringOutcome(score=total, grade=grade_for(total, config), factors=factors)


def client_factors(outcome: ScoringOutcome, limit: int = 4) -> list[FactorResult]:
    """3–5 главных факторов для клиента: сначала то, что снизило оценку, затем сильные стороны."""

    def ratio(factor: FactorResult) -> float:
        return factor.points / factor.max_points

    negatives = sorted((f for f in outcome.factors if f.impact == "negative"), key=ratio)
    positives = sorted(
        (f for f in outcome.factors if f.impact == "positive"), key=ratio, reverse=True
    )
    neutrals = [f for f in outcome.factors if f.impact == "neutral"]
    chosen = (negatives[:3] + positives + neutrals)[: max(limit, 3)]
    return chosen
