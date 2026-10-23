"""Бюро кредитных историй (мок): кредитный отчёт по ИНН."""

from app.adapters.base import JsonDict
from app.adapters.http import JsonHttpClient


class HttpBkiAdapter:
    def __init__(self, http: JsonHttpClient) -> None:
        self._http = http

    def get_report(self, inn: str) -> JsonDict:
        return self._http.request("GET", "/bki/report", params={"inn": inn})
