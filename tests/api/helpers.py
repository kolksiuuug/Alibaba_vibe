"""Помощники API-тестов: демо-вход, создание и отправка заявки, синхронный воркер."""

from typing import Any

from flask.testing import FlaskClient

from app.worker import run_until_idle
from tests.fakes import FakeExternal, fake_context

FORM = {
    "contact_name": "Тестов Тест Тестович",
    "purpose_description": "Закупка сырья на сезон",
}
COLLATERAL_FORM = {
    "collateral_description": "Токарный станок с ЧПУ, 2024 года выпуска",
    "collateral_value": "3 200 000",
    "equipment_supplier": "ООО «Станкоцентр»",
}


def login(client: FlaskClient, profile: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/demo-login", json={"login": profile})
    assert response.status_code == 200, response.json
    return {"Authorization": f"Bearer {response.json['token']}"}


def drain(external: FakeExternal) -> int:
    """Синхронно выполнить все задачи воркера."""
    return run_until_idle(fake_context(external))


def create_application(
    client: FlaskClient,
    headers: dict[str, str],
    product_code: str,
    amount: int,
    term_months: int,
    *,
    purpose: str = "working_capital",
    form: dict[str, Any] | None = None,
) -> int:
    response = client.post(
        "/api/v1/applications",
        json={
            "product_code": product_code,
            "amount": amount,
            "term_months": term_months,
            "purpose": purpose,
            "form_data": FORM if form is None else form,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.json
    return int(response.json["application"]["id"])


def submit_and_process(
    client: FlaskClient, headers: dict[str, str], application_id: int, external: FakeExternal
) -> dict[str, Any]:
    response = client.post(f"/api/v1/applications/{application_id}/submit", headers=headers)
    assert response.status_code == 200, response.json
    assert response.json["application"]["status"] == "submitted"
    assert drain(external) == 1
    detail = client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert detail.status_code == 200
    return dict(detail.json)


def url(application_id: int, action: str = "") -> str:
    return f"/api/v1/applications/{application_id}" + (f"/{action}" if action else "")
