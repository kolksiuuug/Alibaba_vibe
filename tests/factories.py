"""Тестовые данные: компании, пользователи, продукты и заявки в нужном статусе."""

import itertools
from datetime import date
from typing import Any

from app.domain.roles import Role
from app.domain.statuses import Status
from app.extensions import db
from app.models import Application, Company, Product, User

_seq = itertools.count(1)


def _turnover(amount: int = 2_000_000) -> list[dict[str, Any]]:
    return [{"month": f"2026-{month:02d}", "amount": amount} for month in range(1, 13)]


def make_company(**overrides: Any) -> Company:
    n = next(_seq)
    data: dict[str, Any] = {
        "name": f"ООО «Тестовая компания {n}»",
        "kind": "llc",
        "inn": f"00{n:08d}",
        "ogrn": f"10000{n:08d}",
        "okved": "47.11",
        "okved_name": "Торговля розничная",
        "registered_at": date(2019, 1, 1),
        "region": "Тестовая область",
        "director_name": "Тестов Тест Тестович",
        "monthly_turnover": _turnover(),
    }
    data.update(overrides)
    company = Company(**data)
    db.session.add(company)
    db.session.flush()
    return company


def make_client(company: Company | None = None) -> User:
    company = company or make_company()
    user = User(
        login=f"client-{next(_seq)}",
        role=Role.CLIENT,
        display_name="Тестов Т. Т.",
        company=company,
    )
    db.session.add(user)
    db.session.flush()
    return user


def make_analyst() -> User:
    user = User(login=f"analyst-{next(_seq)}", role=Role.ANALYST, display_name="Аналитик")
    db.session.add(user)
    db.session.flush()
    return user


def make_product(**overrides: Any) -> Product:
    data: dict[str, Any] = {
        "code": f"product-{next(_seq)}",
        "name": "Тестовый кредит",
        "description": "Продукт для тестов",
        "purposes": ["working_capital"],
        "min_amount": 100_000,
        "max_amount": 10_000_000,
        "min_term_months": 3,
        "max_term_months": 36,
        "rate_spread": 5.0,
        "requires_collateral": False,
        "requires_guarantee": False,
        "required_fields": [],
    }
    data.update(overrides)
    product = Product(**data)
    db.session.add(product)
    db.session.flush()
    return product


def make_application(
    *,
    status: Status = Status.DRAFT,
    client: User | None = None,
    product: Product | None = None,
    **overrides: Any,
) -> Application:
    client = client or make_client()
    data: dict[str, Any] = {
        "company": client.company,
        "created_by": client,
        "product": product or make_product(),
        "amount": 1_000_000,
        "term_months": 12,
        "purpose": "working_capital",
    }
    data.update(overrides)
    application = Application(**data)
    # Только в тестах: заявка сразу в нужном статусе, без прохождения переходов
    application._status = status.value
    db.session.add(application)
    db.session.flush()
    return application
