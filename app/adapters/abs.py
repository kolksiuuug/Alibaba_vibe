"""АБС банка (мок): выдача кредита на расчётный счёт. Симуляция."""

from app.adapters.base import JsonDict
from app.adapters.http import JsonHttpClient


class HttpAbsAdapter:
    def __init__(self, http: JsonHttpClient) -> None:
        self._http = http

    def create_disbursement(
        self, *, idempotency_key: str, application_id: int, inn: str, amount: int
    ) -> JsonDict:
        payload = {
            "idempotency_key": idempotency_key,
            "application_id": application_id,
            "inn": inn,
            "amount": amount,
        }
        return self._http.request("POST", "/abs/disbursements", json=payload)
