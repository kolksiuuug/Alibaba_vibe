"""ФНС «Прозрачный бизнес» (мок): налоговая задолженность и дисциплина."""

from app.adapters.base import JsonDict
from app.adapters.http import JsonHttpClient


class HttpFnsAdapter:
    def __init__(self, http: JsonHttpClient) -> None:
        self._http = http

    def get_transparent_business(self, inn: str) -> JsonDict:
        return self._http.request("GET", f"/fns/transparent-business/{inn}")
