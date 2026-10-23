"""HTTP-клиент адаптеров: таймаут, ретраи с экспоненциальным backoff, единая ошибка."""

import logging
import time
from collections.abc import Callable
from typing import Any

import httpx

from app.adapters.base import AdapterError, JsonDict

log = logging.getLogger(__name__)


class JsonHttpClient:
    """JSON поверх httpx. 5xx, таймауты и сетевые ошибки повторяются, 4xx — нет."""

    def __init__(
        self,
        base_url: str,
        *,
        source: str,
        timeout_s: float = 3.0,
        retries: int = 2,
        backoff_s: float = 0.2,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.source = source
        self._retries = retries
        self._backoff_s = backoff_s
        self._sleep = sleep
        self._client = httpx.Client(base_url=base_url, timeout=timeout_s, transport=transport)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: JsonDict | None = None,
    ) -> JsonDict:
        attempts = self._retries + 1
        last_error = ""
        for attempt in range(1, attempts + 1):
            try:
                response = self._client.request(method, path, params=params, json=json)
            except httpx.TransportError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code < 500:
                    return self._parse(response)
                last_error = f"HTTP {response.status_code}"
            log.warning(
                "external call failed",
                extra={"source": self.source, "attempt": attempt, "error": last_error},
            )
            if attempt < attempts:
                self._sleep(self._backoff_s * 2 ** (attempt - 1))
        raise AdapterError(self.source, f"unavailable after {attempts} attempts ({last_error})")

    def _parse(self, response: httpx.Response) -> JsonDict:
        if response.is_error:
            raise AdapterError(self.source, f"HTTP {response.status_code}")
        try:
            data = response.json()
        except ValueError as exc:
            raise AdapterError(self.source, "invalid JSON in response") from exc
        if not isinstance(data, dict):
            raise AdapterError(self.source, "unexpected response shape")
        return data
