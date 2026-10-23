"""ЕГРЮЛ / ЕГРИП (мок): статус и дата регистрации компании или ИП."""

from app.adapters.base import JsonDict
from app.adapters.http import JsonHttpClient


class HttpEgrulAdapter:
    def __init__(self, http: JsonHttpClient) -> None:
        self._http = http

    def get_company(self, inn: str) -> JsonDict:
        return self._http.request("GET", f"/egrul/{inn}")
