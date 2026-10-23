"""HTTP-адаптеры к внешним системам: таймаут, 2 ретрая с backoff, понятная ошибка."""

import httpx
import pytest

from app.adapters import build_adapters
from app.adapters.base import AdapterError
from app.adapters.http import JsonHttpClient


def _client(handler, retries: int = 2) -> tuple[JsonHttpClient, list[float]]:  # type: ignore[no-untyped-def]
    sleeps: list[float] = []
    client = JsonHttpClient(
        "http://mocks:8001",
        source="bki",
        timeout_s=3.0,
        retries=retries,
        backoff_s=0.2,
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
    )
    return client, sleeps


def test_returns_json_on_success() -> None:
    client, sleeps = _client(lambda request: httpx.Response(200, json={"ok": True}))
    assert client.request("GET", "/bki/report", params={"inn": "0044385397"}) == {"ok": True}
    assert sleeps == []


def test_retries_server_errors_with_backoff_then_succeeds() -> None:
    responses = iter([httpx.Response(503), httpx.Response(502), httpx.Response(200, json={"n": 3})])
    client, sleeps = _client(lambda request: next(responses))

    assert client.request("GET", "/x") == {"n": 3}
    assert sleeps == [0.2, 0.4]


def test_raises_adapter_error_after_all_retries() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ConnectTimeout("timeout", request=request)

    client, _ = _client(handler)
    with pytest.raises(AdapterError) as error:
        client.request("GET", "/x")

    assert len(calls) == 3  # 1 попытка + 2 ретрая
    assert error.value.source == "bki"


def test_client_errors_are_not_retried() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(400, json={"error": "bad inn"})

    client, _ = _client(handler)
    with pytest.raises(AdapterError):
        client.request("GET", "/x")
    assert len(calls) == 1


def test_invalid_json_is_adapter_error() -> None:
    client, _ = _client(lambda request: httpx.Response(200, text="not json"))
    with pytest.raises(AdapterError):
        client.request("GET", "/x")


def test_adapters_call_mock_endpoints() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(
            (
                request.method,
                request.url.path + ("?" + request.url.query.decode() if request.url.query else ""),
            )
        )
        return httpx.Response(200, json={})

    config = {"MOCKS_BASE_URL": "http://mocks:8001", "ADAPTER_TIMEOUT_S": 3.0, "ADAPTER_RETRIES": 2}
    adapters = build_adapters(config, transport=httpx.MockTransport(handler))
    adapters.bki.get_report("0044385397")
    adapters.egrul.get_company("0044385397")
    adapters.fns.get_transparent_business("0044385397")
    adapters.abs.create_disbursement(
        idempotency_key="application-1", application_id=1, inn="0044385397", amount=100
    )
    adapters.esign.sign(application_id=1, document_hash="abc", signer="client")

    assert seen == [
        ("GET", "/bki/report?inn=0044385397"),
        ("GET", "/egrul/0044385397"),
        ("GET", "/fns/transparent-business/0044385397"),
        ("POST", "/abs/disbursements"),
        ("POST", "/esign/sign"),
    ]
