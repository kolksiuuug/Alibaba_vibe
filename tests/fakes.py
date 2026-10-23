"""Подмена внешних систем в тестах конвейера: ответы из mocks/data, счётчик вызовов, сбои."""

import json
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.adapters.base import AdapterError, Adapters
from app.services.pipeline import PipelineContext

DATA_DIR = Path(__file__).resolve().parents[1] / "mocks" / "data"
TODAY = date(2026, 10, 23)


def _load(name: str) -> dict[str, dict[str, Any]]:
    return json.loads((DATA_DIR / f"{name}.json").read_text(encoding="utf-8"))


class FakeExternal:
    """Одна заглушка на все внешние системы; fail — источники, которые «не отвечают»."""

    def __init__(self, fail: set[str] | None = None) -> None:
        self.fail = set(fail or ())
        self.calls: Counter[str] = Counter()
        self.data = {name: _load(name) for name in ("bki", "egrul", "fns")}

    def _call(self, source: str, inn: str) -> dict[str, Any]:
        self.calls[source] += 1
        if source in self.fail:
            raise AdapterError(source, "service unavailable")
        return dict(self.data[source][inn], inn=inn)

    def get_report(self, inn: str) -> dict[str, Any]:
        return self._call("bki", inn)

    def get_company(self, inn: str) -> dict[str, Any]:
        return self._call("egrul", inn)

    def get_transparent_business(self, inn: str) -> dict[str, Any]:
        return self._call("fns", inn)

    def create_disbursement(
        self, *, idempotency_key: str, application_id: int, inn: str, amount: int
    ) -> dict[str, Any]:
        self.calls["abs"] += 1
        if "abs" in self.fail:
            raise AdapterError("abs", "service unavailable")
        return {"disbursement_id": f"ABS-{application_id}", "status": "completed", "amount": amount}

    def sign(self, *, application_id: int, document_hash: str, signer: str) -> dict[str, Any]:
        self.calls["esign"] += 1
        if "esign" in self.fail:
            raise AdapterError("esign", "service unavailable")
        return {"signature_id": f"SIG-{application_id}", "document_hash": document_hash}


def fake_context(external: FakeExternal | None = None) -> PipelineContext:
    external = external or FakeExternal()
    adapters = Adapters(bki=external, egrul=external, fns=external, abs=external, esign=external)
    return PipelineContext(
        adapters=adapters,
        key_rate=Decimal("14.0"),
        step_delay_ms=0,
        today=lambda: TODAY,
    )
