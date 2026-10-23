"""Сборка Postman-коллекции пяти сценариев проверки.

Запуск: python postman/build_collection.py -> postman/credit-cabinet.postman_collection.json
Импортируйте JSON в Postman и запускайте папки целиком (Runner). Переменная baseUrl —
адрес стенда, по умолчанию http://localhost:8080.
"""

import json
from pathlib import Path
from typing import Any

OUTPUT = Path(__file__).with_name("credit-cabinet.postman_collection.json")
WAIT_MS = 7000  # воркер проходит 6 шагов по ~0,7 с (PIPELINE_STEP_DELAY_MS)
FORM = {
    "contact_name": "Демо Контакт Синтетикович",
    "purpose_description": "Закупка сырья и материалов на сезон",
}
COLLATERAL = {
    "collateral_description": "Токарный станок с ЧПУ, 2024 года выпуска",
    "collateral_value": 3200000,
    "equipment_supplier": "ООО «Станкоцентр» (вымышленный поставщик)",
}


def _script(kind: str, lines: list[str]) -> dict[str, Any]:
    return {"listen": kind, "script": {"type": "text/javascript", "exec": lines}}


def request(
    name: str,
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    token: str | None = "clientToken",
    tests: list[str] | None = None,
    wait: bool = False,
) -> dict[str, Any]:
    req: dict[str, Any] = {
        "method": method,
        "header": [],
        "url": "{{baseUrl}}" + path,
        "auth": (
            {"type": "bearer", "bearer": [{"key": "token", "value": "{{" + token + "}}"}]}
            if token
            else {"type": "noauth"}
        ),
    }
    if body is not None:
        req["header"].append({"key": "Content-Type", "value": "application/json"})
        req["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, ensure_ascii=False, indent=2),
            "options": {"raw": {"language": "json"}},
        }
    events = []
    if wait:
        events.append(
            _script(
                "prerequest",
                ["// ждём воркер конвейера", f"setTimeout(function () {{}}, {WAIT_MS});"],
            )
        )
    if tests:
        events.append(_script("test", tests))
    item: dict[str, Any] = {"name": name, "request": req}
    if events:
        item["event"] = events
    return item


def http_is(code: int) -> str:
    return f'pm.test("HTTP {code}", function () {{ pm.response.to.have.status({code}); }});'


def status_is(status: str) -> str:
    return (
        f'pm.test("status = {status}", function () {{ '
        f'pm.expect(pm.response.json().application.status).to.eql("{status}"); }});'
    )


def save(variable: str, expression: str) -> str:
    return f'pm.collectionVariables.set("{variable}", {expression});'


def login(profile: str, variable: str = "clientToken") -> dict[str, Any]:
    return request(
        f"Вход: {profile}",
        "POST",
        "/api/v1/auth/demo-login",
        body={"login": profile},
        token=None,
        tests=[http_is(200), save(variable, "pm.response.json().token")],
    )


def create(
    product: str, amount: int, term: int, purpose: str = "working_capital"
) -> dict[str, Any]:
    return request(
        "Создать черновик заявки",
        "POST",
        "/api/v1/applications",
        body={
            "product_code": product,
            "amount": amount,
            "term_months": term,
            "purpose": purpose,
            "form_data": FORM,
        },
        tests=[
            http_is(201),
            status_is("draft"),
            save("applicationId", "pm.response.json().application.id"),
        ],
    )


def submit() -> dict[str, Any]:
    return request(
        "Отправить заявку",
        "POST",
        "/api/v1/applications/{{applicationId}}/submit",
        tests=[http_is(200), status_is("submitted")],
    )


def wait_and_get(status: str, extra: list[str] | None = None) -> dict[str, Any]:
    return request(
        f"Подождать конвейер и открыть заявку → {status}",
        "GET",
        "/api/v1/applications/{{applicationId}}",
        wait=True,
        tests=[http_is(200), status_is(status), *(extra or [])],
    )


def action(name: str, path: str, status: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    return request(
        name,
        "POST",
        "/api/v1/applications/{{applicationId}}/" + path,
        body=body,
        tests=[http_is(200), status_is(status)],
    )


def folder(name: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {"name": name, "item": items}


COLLECTION = {
    "info": {
        "name": "Умный кредитный кабинет — 5 сценариев",
        "description": (
            "Пять демо-сценариев проверки (синтетические данные). Запускайте папки Runner'ом "
            "по порядку. baseUrl — адрес стенда. Подробнее: docs/api.md, docs/test-scenarios.md."
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "variable": [
        {"key": "baseUrl", "value": "http://localhost:8080"},
        {"key": "clientToken", "value": ""},
        {"key": "analystToken", "value": ""},
        {"key": "applicationId", "value": ""},
        {"key": "signCode", "value": ""},
    ],
    "item": [
        folder(
            "0. Состояние сервиса и демо-профили",
            [
                request("Health", "GET", "/api/health", token=None, tests=[http_is(200)]),
                request(
                    "Ready (БД доступна)", "GET", "/api/ready", token=None, tests=[http_is(200)]
                ),
                request(
                    "Демо-профили для входа",
                    "GET",
                    "/api/v1/auth/demo-profiles",
                    token=None,
                    tests=[http_is(200)],
                ),
            ],
        ),
        folder(
            "1. Одобрение, подпись и выдача (demo-approve)",
            [
                login("demo-approve"),
                request(
                    "Подбор продукта",
                    "POST",
                    "/api/v1/products/recommend",
                    body={"purpose": "working_capital", "amount": 3000000, "term_months": 24},
                    tests=[http_is(200)],
                ),
                create("turnover", 3000000, 24),
                submit(),
                wait_and_get(
                    "offer",
                    [
                        'pm.test("предложение без изменений", function () { '
                        "pm.expect(pm.response.json().offer.is_counter).to.eql(false); });"
                    ],
                ),
                action("Принять предложение", "offer/accept", "accepted"),
                request(
                    "Получить код подписи (симуляция)",
                    "POST",
                    "/api/v1/applications/{{applicationId}}/sign/request-code",
                    tests=[http_is(200), save("signCode", "pm.response.json().code")],
                ),
                action("Подписать кодом", "sign/confirm", "signed", {"code": "{{signCode}}"}),
                wait_and_get("issued"),
                request("Центр уведомлений", "GET", "/api/v1/notifications", tests=[http_is(200)]),
                request(
                    "Таймлайн заявки",
                    "GET",
                    "/api/v1/applications/{{applicationId}}/events",
                    tests=[http_is(200)],
                ),
            ],
        ),
        folder(
            "2. Контрпредложение (demo-counter)",
            [
                login("demo-counter"),
                create("turnover", 12000000, 24),
                submit(),
                wait_and_get(
                    "offer",
                    [
                        'pm.test("контрпредложение", function () { '
                        "pm.expect(pm.response.json().offer.is_counter).to.eql(true); });"
                    ],
                ),
                action("Отклонить предложение", "offer/decline", "declined"),
            ],
        ),
        folder(
            "3. Дозапрос данных о залоге (demo-info)",
            [
                login("demo-info"),
                create("equipment", 2500000, 36, purpose="equipment"),
                submit(),
                wait_and_get("info_requested"),
                action(
                    "Ответить на дозапрос",
                    "info-response",
                    "checking",
                    {"answers": COLLATERAL},
                ),
                wait_and_get("offer"),
            ],
        ),
        folder(
            "4. Ручное рассмотрение аналитиком (demo-manual)",
            [
                login("demo-manual"),
                create("express", 1500000, 18),
                submit(),
                wait_and_get("manual_review"),
                login("analyst", "analystToken"),
                request(
                    "Очередь: ручное рассмотрение",
                    "GET",
                    "/api/v1/analyst/applications?status=manual_review",
                    token="analystToken",
                    tests=[http_is(200)],
                ),
                request(
                    "Карточка заявки",
                    "GET",
                    "/api/v1/analyst/applications/{{applicationId}}",
                    token="analystToken",
                    tests=[http_is(200)],
                ),
                request(
                    "Решение без комментария → 422",
                    "POST",
                    "/api/v1/analyst/applications/{{applicationId}}/decision",
                    body={"action": "approve"},
                    token="analystToken",
                    tests=[http_is(422)],
                ),
                request(
                    "Изменить условия",
                    "POST",
                    "/api/v1/analyst/applications/{{applicationId}}/decision",
                    body={
                        "action": "change_terms",
                        "amount": 1200000,
                        "term_months": 18,
                        "comment": "Обороты неровные: снижаем сумму до 1,2 млн",
                    },
                    token="analystToken",
                    tests=[http_is(200), status_is("offer")],
                ),
                request(
                    "Клиент видит новое предложение",
                    "GET",
                    "/api/v1/applications/{{applicationId}}",
                    tests=[http_is(200), status_is("offer")],
                ),
            ],
        ),
        folder(
            "5. Отказ: просрочка 90+ (demo-reject)",
            [
                login("demo-reject"),
                create("turnover", 2000000, 12),
                submit(),
                wait_and_get("rejected"),
                request(
                    "Принять предложение после отказа → 409",
                    "POST",
                    "/api/v1/applications/{{applicationId}}/offer/accept",
                    tests=[http_is(409)],
                ),
            ],
        ),
    ],
}


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(COLLECTION, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"written {OUTPUT}")
