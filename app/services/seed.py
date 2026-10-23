"""Загрузка синтетических демо-данных из seed/*.json."""

import json
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.domain.roles import Role
from app.extensions import db
from app.models import Company, Product, User

DEMO_ANALYST = {
    "login": "analyst",
    "display_name": "Демо-аналитик",
    "demo_hint": "Очередь заявок, карточка и решения по ручному рассмотрению",
}


def _read_json(seed_dir: str, name: str) -> Any:
    return json.loads((Path(seed_dir) / name).read_text(encoding="utf-8"))


def seed_is_loaded() -> bool:
    return db.session.query(User.id).limit(1).first() is not None


def clear_all() -> None:
    tables = ", ".join(f'"{table.name}"' for table in db.metadata.sorted_tables)
    db.session.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    # id начинаются заново: старые объекты в сессии иначе конфликтуют с новыми
    db.session.expunge_all()


def load_seed(seed_dir: str, *, reset: bool = False) -> dict[str, int]:
    if reset:
        clear_all()

    products = [Product(**item) for item in _read_json(seed_dir, "products.json")]
    db.session.add_all(products)

    users = [User(role=Role.ANALYST, **DEMO_ANALYST)]
    companies = []
    for item in _read_json(seed_dir, "demo_companies.json"):
        company_data = dict(item["company"])
        company_data["registered_at"] = date.fromisoformat(company_data["registered_at"])
        company = Company(**company_data)
        companies.append(company)
        users.append(
            User(
                role=Role.CLIENT,
                company=company,
                login=item["login"],
                display_name=item["display_name"],
                demo_hint=item.get("demo_hint"),
            )
        )
    db.session.add_all(companies + users)
    db.session.commit()
    return {"products": len(products), "companies": len(companies), "users": len(users)}
