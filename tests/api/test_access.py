"""Роли, чужие заявки, валидация, идемпотентность и прочие ветки API."""

from flask.testing import FlaskClient

from app.api import PROBLEM_MIMETYPE
from tests.api.helpers import FORM, create_application, drain, login, submit_and_process, url
from tests.fakes import FakeExternal


def test_demo_profiles_are_public(client: FlaskClient, external: FakeExternal) -> None:
    profiles = client.get("/api/v1/auth/demo-profiles").json
    assert {p["login"] for p in profiles} >= {"analyst", "demo-approve", "demo-reject"}
    assert all("token" not in p for p in profiles)


def test_unknown_profile_is_404(client: FlaskClient, external: FakeExternal) -> None:
    response = client.post("/api/v1/auth/demo-login", json={"login": "nobody"})
    assert response.status_code == 404
    assert response.mimetype == PROBLEM_MIMETYPE


def test_requests_without_or_with_bad_token_are_401(
    client: FlaskClient, external: FakeExternal
) -> None:
    assert client.get("/api/v1/me").status_code == 401
    bad = client.get("/api/v1/me", headers={"Authorization": "Bearer forged.token"})
    assert bad.status_code == 401
    assert bad.mimetype == PROBLEM_MIMETYPE


def test_me_returns_company_for_client(client: FlaskClient, external: FakeExternal) -> None:
    me = client.get("/api/v1/me", headers=login(client, "demo-approve")).json
    assert me["role"] == "client"
    assert me["company"]["inn"] == "0044385397"


def test_roles_are_enforced(client: FlaskClient, external: FakeExternal) -> None:
    client_headers = login(client, "demo-approve")
    analyst_headers = login(client, "analyst")
    assert client.get("/api/v1/analyst/applications", headers=client_headers).status_code == 403
    assert client.get("/api/v1/applications", headers=analyst_headers).status_code == 403


def test_client_cannot_see_other_company_application(
    client: FlaskClient, external: FakeExternal
) -> None:
    owner = login(client, "demo-approve")
    stranger = login(client, "demo-counter")
    application_id = create_application(client, owner, "turnover", 1_000_000, 12)

    response = client.get(url(application_id), headers=stranger)

    assert response.status_code == 403
    assert response.json["code"] == "access_denied"
    assert client.get("/api/v1/applications", headers=stranger).json == []
    assert client.get(url(999_999), headers=owner).status_code == 404


def test_create_validates_product_terms(client: FlaskClient, external: FakeExternal) -> None:
    headers = login(client, "demo-approve")
    response = client.post(
        "/api/v1/applications",
        json={
            "product_code": "express",
            "amount": 50_000_000,
            "term_months": 12,
            "purpose": "working_capital",
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert "amount" in response.json["errors"]

    unknown_field = client.post(
        "/api/v1/applications",
        json={
            "product_code": "express",
            "amount": 500_000,
            "term_months": 12,
            "purpose": "working_capital",
            "form_data": {"passport": "1234"},
        },
        headers=headers,
    )
    assert unknown_field.status_code == 422


def test_submit_requires_complete_form_and_is_idempotent(
    client: FlaskClient, external: FakeExternal
) -> None:
    headers = login(client, "demo-approve")
    application_id = create_application(client, headers, "turnover", 1_000_000, 12, form={})

    incomplete = client.post(url(application_id, "submit"), headers=headers)
    assert incomplete.status_code == 422
    assert set(incomplete.json["errors"]["form_data"]) == {"contact_name", "purpose_description"}

    client.patch(url(application_id), json={"form_data": FORM}, headers=headers)
    first = client.post(url(application_id, "submit"), headers=headers)
    second = client.post(url(application_id, "submit"), headers=headers)
    assert first.status_code == second.status_code == 200
    assert second.json["application"]["status"] == "submitted"
    assert drain(external) == 1  # повторный submit не создал вторую задачу

    edit_after_submit = client.patch(url(application_id), json={"amount": 900_000}, headers=headers)
    assert edit_after_submit.status_code == 409


def test_cancel_draft(client: FlaskClient, external: FakeExternal) -> None:
    headers = login(client, "demo-approve")
    application_id = create_application(client, headers, "turnover", 1_000_000, 12)
    response = client.post(url(application_id, "cancel"), headers=headers)
    assert response.json["application"]["status"] == "cancelled"


def test_calculator_and_products(client: FlaskClient, external: FakeExternal) -> None:
    headers = login(client, "demo-approve")
    products = client.get("/api/v1/products", headers=headers).json
    assert {p["code"] for p in products} == {"turnover", "equipment", "express", "credit_line"}
    equipment = next(p for p in products if p["code"] == "equipment")
    assert equipment["base_rate"] == 17.0
    assert {f["code"] for f in equipment["required_fields"]} >= {"collateral_value"}

    calc = client.post(
        "/api/v1/calculator",
        json={"amount": 1_000_000, "term_months": 12, "annual_rate": 18.5},
        headers=headers,
    ).json
    assert calc["monthly_payment"] == 91918.12
    assert len(calc["schedule"]) == 12
    by_product = client.post(
        "/api/v1/calculator",
        json={"amount": 1_000_000, "term_months": 12, "product_code": "turnover"},
        headers=headers,
    ).json
    assert by_product["annual_rate"] == 18.5
    missing_rate = client.post(
        "/api/v1/calculator", json={"amount": 1_000_000, "term_months": 12}, headers=headers
    )
    assert missing_rate.status_code == 422


def test_recommend_rejects_unknown_purpose(client: FlaskClient, external: FakeExternal) -> None:
    response = client.post(
        "/api/v1/products/recommend",
        json={"purpose": "casino", "amount": 1_000_000, "term_months": 12},
        headers=login(client, "demo-approve"),
    )
    assert response.status_code == 422
    assert response.mimetype == PROBLEM_MIMETYPE


def test_analyst_requests_info_then_approves(client: FlaskClient, external: FakeExternal) -> None:
    client_headers = login(client, "demo-manual")
    analyst = login(client, "analyst")
    application_id = create_application(client, client_headers, "express", 1_500_000, 18)
    submit_and_process(client, client_headers, application_id, external)
    decision_url = f"/api/v1/analyst/applications/{application_id}/decision"

    asked = client.post(
        decision_url,
        json={
            "action": "request_info",
            "comment": "Пришлите пояснение по падению оборотов в феврале",
        },
        headers=analyst,
    )
    assert asked.json["application"]["status"] == "info_requested"
    detail = client.get(url(application_id), headers=client_headers).json
    assert detail["info_request"]["requested_by"] == "analyst"
    assert detail["info_request"]["fields"] == []
    empty = client.post(url(application_id, "info-response"), json={}, headers=client_headers)
    assert empty.status_code == 422

    client.post(
        url(application_id, "info-response"),
        json={"comment": "В феврале был плановый ремонт зала"},
        headers=client_headers,
    )
    assert drain(external) == 1
    assert client.get(url(application_id), headers=client_headers).json["application"][
        "status"
    ] == ("manual_review")

    approved = client.post(
        decision_url, json={"action": "approve", "comment": "Пояснение принято"}, headers=analyst
    )
    assert approved.json["application"]["status"] == "offer"
    repeat = client.post(
        decision_url, json={"action": "approve", "comment": "Повтор"}, headers=analyst
    )
    assert repeat.status_code == 200  # идемпотентно
    offer = client.get(url(application_id), headers=client_headers).json["offer"]
    assert (offer["amount"], offer["decided_by"]) == (1_500_000, "analyst")


def test_analyst_rejects_with_comment_visible_to_client(
    client: FlaskClient, external: FakeExternal
) -> None:
    client_headers = login(client, "demo-manual")
    analyst = login(client, "analyst")
    application_id = create_application(client, client_headers, "express", 1_500_000, 18)
    submit_and_process(client, client_headers, application_id, external)

    client.post(
        f"/api/v1/analyst/applications/{application_id}/decision",
        json={"action": "reject", "comment": "Нагрузка по кредитам слишком высокая"},
        headers=analyst,
    )

    detail = client.get(url(application_id), headers=client_headers).json
    assert detail["application"]["status"] == "rejected"
    assert detail["decision_comment"] == "Нагрузка по кредитам слишком высокая"


def test_esign_outage_keeps_offer_accepted(client: FlaskClient, external: FakeExternal) -> None:
    headers = login(client, "demo-approve")
    application_id = create_application(client, headers, "turnover", 3_000_000, 24)
    submit_and_process(client, headers, application_id, external)
    client.post(url(application_id, "offer/accept"), headers=headers)
    code = client.post(url(application_id, "sign/request-code"), headers=headers).json["code"]
    external.fail.add("esign")

    response = client.post(
        url(application_id, "sign/confirm"), json={"code": code}, headers=headers
    )

    assert response.status_code == 503
    assert response.json["code"] == "service_unavailable"
    assert (
        client.get(url(application_id), headers=headers).json["application"]["status"] == "accepted"
    )


def test_notification_can_be_marked_read_only_by_owner(
    client: FlaskClient, external: FakeExternal
) -> None:
    owner = login(client, "demo-approve")
    application_id = create_application(client, owner, "turnover", 1_000_000, 12)
    client.post(url(application_id, "submit"), headers=owner)
    notification = client.get("/api/v1/notifications", headers=owner).json["items"][0]

    stranger = client.post(
        f"/api/v1/notifications/{notification['id']}/read", headers=login(client, "demo-counter")
    )
    assert stranger.status_code == 403
    read = client.post(f"/api/v1/notifications/{notification['id']}/read", headers=owner)
    assert read.json["is_read"] is True
    assert client.get("/api/v1/notifications", headers=owner).json["unread_count"] == 0
