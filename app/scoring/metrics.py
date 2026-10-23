"""Производные показатели для скоринга и форматирование чисел в объяснениях."""

import statistics
from collections.abc import Sequence
from datetime import date


def months_between(start: date, end: date) -> int:
    """Полных месяцев между датами."""
    months = (end.year - start.year) * 12 + end.month - start.month
    return months - 1 if end.day < start.day else months


def average(values: Sequence[int]) -> float:
    return float(statistics.fmean(values)) if values else 0.0


def variation(values: Sequence[int]) -> float:
    """Коэффициент вариации: стандартное отклонение / среднее."""
    mean = average(values)
    if mean <= 0:
        return float("inf")
    return statistics.pstdev(values) / mean


def money(amount: float) -> str:
    """3584167 -> «3 584 167»."""
    return f"{round(amount):,}".replace(",", " ")


def percent(ratio: float) -> str:
    return f"{ratio * 100:.0f}%"


def plural(n: int, forms: tuple[str, str, str]) -> str:
    """plural(5, ("год", "года", "лет")) -> «лет»."""
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return forms[1]
    return forms[2]
