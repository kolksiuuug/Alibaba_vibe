from flask.testing import FlaskClient
from flask_sqlalchemy import SQLAlchemy

from app.api import PROBLEM_MIMETYPE


def test_health_is_ok(client: FlaskClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_ready_checks_database(client: FlaskClient, db: SQLAlchemy) -> None:
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_unknown_route_returns_problem_json(client: FlaskClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.mimetype == PROBLEM_MIMETYPE
    body = response.json
    assert body["status"] == 404
    assert body["title"] == "Не найдено"
    assert body["instance"] == "/api/v1/does-not-exist"
    assert body["request_id"]


def test_request_id_is_echoed(client: FlaskClient) -> None:
    response = client.get("/api/health", headers={"X-Request-ID": "test-req-1"})
    assert response.headers["X-Request-ID"] == "test-req-1"


def test_invalid_request_id_is_replaced(client: FlaskClient) -> None:
    response = client.get("/api/health", headers={"X-Request-ID": "bad id with spaces"})
    assert response.headers["X-Request-ID"] != "bad id with spaces"


def test_openapi_spec_is_served(client: FlaskClient) -> None:
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    assert "/api/health" in response.json["paths"]


def test_swagger_ui_page_uses_local_assets(client: FlaskClient) -> None:
    response = client.get("/api/docs")
    assert response.status_code == 200
    assert b"/swagger-ui/" in response.data
    assert b"cdn.jsdelivr.net" not in response.data
