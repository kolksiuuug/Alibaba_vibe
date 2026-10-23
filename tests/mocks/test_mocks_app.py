"""Контейнер mocks: ответы по ИНН из mocks/data, детерминированные ответы для неизвестных ИНН."""

from collections.abc import Iterator

import pytest
from flask.testing import FlaskClient

from mocks import app as mocks_module


@pytest.fixture
def mocks() -> Iterator[FlaskClient]:
    mocks_module.FAILING.clear()
    yield mocks_module.app.test_client()
    mocks_module.FAILING.clear()


def test_known_inn_returns_fixture_data(mocks: FlaskClient) -> None:
    bki = mocks.get("/bki/report?inn=0031059928").json
    assert bki["current_overdue_days"] == 120
    egrul = mocks.get("/egrul/0044385397").json
    assert (egrul["status"], egrul["registered_at"]) == ("active", "2019-03-14")
    fns = mocks.get("/fns/transparent-business/0089935844").json
    assert fns["late_payments_12m"] == 1


@pytest.mark.parametrize("inn", ["0012345678", "001234567890", "7701234567"])
def test_unknown_inn_gets_deterministic_answer(mocks: FlaskClient, inn: str) -> None:
    for path in (f"/bki/report?inn={inn}", f"/egrul/{inn}", f"/fns/transparent-business/{inn}"):
        first, second = mocks.get(path), mocks.get(path)
        assert first.status_code == 200
        assert first.json == second.json
    egrul = mocks.get(f"/egrul/{inn}").json
    assert egrul["kind"] == ("ip" if len(inn) == 12 else "llc")
    assert egrul["status"] in {"active", "liquidating"}


@pytest.mark.parametrize("path", ["/bki/report?inn=12ab", "/egrul/123", "/fns/transparent-business/1"])
def test_invalid_inn_is_400(mocks: FlaskClient, path: str) -> None:
    assert mocks.get(path).status_code == 400


def test_admin_fail_switches_service_off_and_on(mocks: FlaskClient) -> None:
    assert mocks.get("/admin/fail?service=bki").json == {"service": "bki", "failing": True}
    assert mocks.get("/bki/report?inn=0044385397").status_code == 503
    assert mocks.get("/egrul/0044385397").status_code == 200

    mocks.get("/admin/fail?service=bki&enabled=false")
    assert mocks.get("/bki/report?inn=0044385397").status_code == 200


def test_admin_fail_rejects_unknown_service(mocks: FlaskClient) -> None:
    assert mocks.get("/admin/fail?service=nope").status_code == 400


def test_disbursement_is_idempotent(mocks: FlaskClient) -> None:
    body = {"idempotency_key": "application-7", "application_id": 7, "inn": "0044385397", "amount": 500000}
    first = mocks.post("/abs/disbursements", json=body).json
    second = mocks.post("/abs/disbursements", json=body).json

    assert first == second
    assert first["status"] == "completed"
    assert first["amount"] == 500000


def test_esign_returns_signature(mocks: FlaskClient) -> None:
    response = mocks.post(
        "/esign/sign", json={"application_id": 7, "document_hash": "abc123", "signer": "client"}
    )
    assert response.status_code == 200
    assert response.json["document_hash"] == "abc123"
    assert response.json["signature_id"].startswith("SIG-")
