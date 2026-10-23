"""Сборка адаптеров к внешним системам из конфигурации приложения."""

from collections.abc import Mapping
from typing import Any

import httpx
from flask import current_app

from app.adapters.abs import HttpAbsAdapter
from app.adapters.base import Adapters
from app.adapters.bki import HttpBkiAdapter
from app.adapters.egrul import HttpEgrulAdapter
from app.adapters.esign import HttpEsignAdapter
from app.adapters.fns import HttpFnsAdapter
from app.adapters.http import JsonHttpClient


def build_adapters(
    config: Mapping[str, Any], transport: httpx.BaseTransport | None = None
) -> Adapters:
    def http(source: str) -> JsonHttpClient:
        return JsonHttpClient(
            config["MOCKS_BASE_URL"],
            source=source,
            timeout_s=float(config["ADAPTER_TIMEOUT_S"]),
            retries=int(config["ADAPTER_RETRIES"]),
            transport=transport,
        )

    return Adapters(
        bki=HttpBkiAdapter(http("bki")),
        egrul=HttpEgrulAdapter(http("egrul")),
        fns=HttpFnsAdapter(http("fns")),
        abs=HttpAbsAdapter(http("abs")),
        esign=HttpEsignAdapter(http("esign")),
    )


def get_adapters() -> Adapters:
    """Адаптеры текущего приложения; в тестах подменяются через app.extensions["adapters"]."""
    adapters: Adapters | None = current_app.extensions.get("adapters")
    if adapters is None:
        adapters = build_adapters(current_app.config)
        current_app.extensions["adapters"] = adapters
    return adapters
