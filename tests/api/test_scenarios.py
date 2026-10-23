"""Пять сквозных API-сценариев (CLAUDE.md, раздел 9); воркер вызывается синхронно."""

from flask.testing import FlaskClient

from tests.api.helpers import (
    COLLATERAL_FORM,
    create_application,
    drain,
    login,
    submit_and_process,
    url,
)
from tests.fakes import FakeExternal


def test_scenario_approve_sign_and_issue(client: FlaskClient, external: FakeExternal) -> None:
    headers = login(client, "demo-approve")

    recommended = client.post(
        "/api/v1/products/recommend",
        json={"purpose": "working_capital", "amount": 3_000_000, "term_months": 24},
        headers=headers,
    ).json
    assert 1 <= len(recommended) <= 3
    assert recommended[0]["fits"] is True

    application_id = create_application(client, headers, "turnover", 3_000_000, 24)
    detail = submit_and_process(client, headers, application_id, external)

    assert detail["application"]["status"] == "offer"
    assert [step["state"] for step in detail["application"]["pipeline_steps"]] == ["done"] * 6
    offer = detail["offer"]
    assert (offer["amount"], offer["term_months"], offer["is_counter"]) == (3_000_000, 24, False)
    assert offer["rate"] == 18.5
    assert len(offer["schedule"]) == 24
    assert 3 <= len(detail["factors"]) <= 5

    accepted = client.post(url(application_id, "offer/accept"), headers=headers)
    assert accepted.json["application"]["status"] == "accepted"

    code = client.post(url(application_id, "sign/request-code"), headers=headers).json
    assert code["simulated"] is True
    wrong = "111111" if code["code"] != "111111" else "222222"
    rejected_code = client.post(
        url(application_id, "sign/confirm"), json={"code": wrong}, headers=headers
    )
    assert rejected_code.status_code == 422
    signed = client.post(
        url(application_id, "sign/confirm"), json={"code": code["code"]}, headers=headers
    )
    assert signed.json["application"]["status"] == "signed"
    assert external.calls["esign"] == 1

    assert drain(external) == 1
    final = client.get(url(application_id), headers=headers).json
    assert final["application"]["status"] == "issued"
    assert final["disbursement"]["amount"] == 3_000_000

    timeline = client.get(url(application_id, "events"), headers=headers).json
    assert [event["to_status"] for event in timeline] == [
        "draft",
        "submitted",
        "checking",
        "offer",
        "accepted",
        "signed",
        "issued",
    ]
    notifications = client.get("/api/v1/notifications", headers=headers).json
    assert "Кредит выдан" in {item["title"] for item in notifications["items"]}
    assert notifications["unread_count"] == len(notifications["items"])


def test_scenario_counter_offer_declined(client: FlaskClient, external: FakeExternal) -> None:
    headers = login(client, "demo-counter")
    application_id = create_application(client, headers, "turnover", 12_000_000, 24)

    detail = submit_and_process(client, headers, application_id, external)

    offer = detail["offer"]
    assert detail["application"]["status"] == "offer"
    assert offer["is_counter"] is True
    assert (offer["amount"], offer["term_months"]) == (9_910_000, 36)
    assert (offer["requested_amount"], offer["requested_term_months"]) == (12_000_000, 24)

    declined = client.post(url(application_id, "offer/decline"), headers=headers)
    assert declined.json["application"]["status"] == "declined"
    late_accept = client.post(url(application_id, "offer/accept"), headers=headers)
    assert late_accept.status_code == 409
    assert late_accept.json["code"] == "invalid_transition"


def test_scenario_info_requested_then_offer(client: FlaskClient, external: FakeExternal) -> None:
    headers = login(client, "demo-info")
    application_id = create_application(
        client, headers, "equipment", 2_500_000, 36, purpose="equipment"
    )
    draft = client.get(url(application_id), headers=headers).json
    assert draft["completeness"]["ready_to_submit"] is True
    assert {f["code"] for f in draft["completeness"]["missing_for_product"]} == set(COLLATERAL_FORM)

    detail = submit_and_process(client, headers, application_id, external)

    assert detail["application"]["status"] == "info_requested"
    requested = {field["code"] for field in detail["info_request"]["fields"]}
    assert requested == set(COLLATERAL_FORM)

    partial = client.post(
        url(application_id, "info-response"),
        json={"answers": {"collateral_description": "Станок"}},
        headers=headers,
    )
    assert partial.status_code == 422

    answered = client.post(
        url(application_id, "info-response"), json={"answers": COLLATERAL_FORM}, headers=headers
    )
    assert answered.json["application"]["status"] == "checking"
    assert drain(external) == 1

    final = client.get(url(application_id), headers=headers).json
    assert final["application"]["status"] == "offer"
    assert final["application"]["form_data"]["collateral_value"] == 3_200_000
    assert external.calls["bki"] == 1  # результаты проверок переиспользованы


def test_scenario_manual_review_analyst_changes_terms(
    client: FlaskClient, external: FakeExternal
) -> None:
    client_headers = login(client, "demo-manual")
    application_id = create_application(client, client_headers, "express", 1_500_000, 18)
    detail = submit_and_process(client, client_headers, application_id, external)
    assert detail["application"]["status"] == "manual_review"

    analyst = login(client, "analyst")
    queue = client.get("/api/v1/analyst/applications?status=manual_review", headers=analyst).json
    assert [item["id"] for item in queue] == [application_id]
    assert queue[0]["grade"] == "C"

    card = client.get(f"/api/v1/analyst/applications/{application_id}", headers=analyst).json
    assert len(card["scoring"]["factors"]) == 9
    assert {check["source"] for check in card["checks"]} == {"bki", "egrul", "fns"}
    recommendation = card["decisions"][-1]
    assert (recommendation["outcome"], recommendation["amount"]) == ("manual_review", 1_500_000)

    decision_url = f"/api/v1/analyst/applications/{application_id}/decision"
    terms = {"action": "change_terms", "amount": 1_200_000, "term_months": 18}
    no_comment = client.post(decision_url, json=terms, headers=analyst)
    assert no_comment.status_code == 422
    assert no_comment.json["code"] == "comment_required"

    decided = client.post(
        decision_url,
        json={**terms, "comment": "Обороты неровные: снижаем сумму до 1,2 млн"},
        headers=analyst,
    )
    assert decided.status_code == 200
    assert decided.json["application"]["status"] == "offer"
    assert decided.json["events"][-1]["comment"] == "Обороты неровные: снижаем сумму до 1,2 млн"

    seen_by_client = client.get(url(application_id), headers=client_headers).json
    offer = seen_by_client["offer"]
    assert (offer["amount"], offer["is_counter"], offer["decided_by"]) == (
        1_200_000,
        True,
        "analyst",
    )
    accepted = client.post(url(application_id, "offer/accept"), headers=client_headers)
    assert accepted.json["application"]["status"] == "accepted"


def test_scenario_reject_for_overdue(client: FlaskClient, external: FakeExternal) -> None:
    headers = login(client, "demo-reject")
    application_id = create_application(client, headers, "turnover", 2_000_000, 12)

    detail = submit_and_process(client, headers, application_id, external)

    assert detail["application"]["status"] == "rejected"
    assert detail["offer"] is None
    assert [reason["code"] for reason in detail["reasons"]] == ["current_overdue"]
    accept = client.post(url(application_id, "offer/accept"), headers=headers)
    assert accept.status_code == 409
