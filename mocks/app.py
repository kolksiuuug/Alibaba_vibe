"""Моки внешних систем: БКИ, ЕГРЮЛ/ЕГРИП, ФНС «Прозрачный бизнес», ЭП, АБС.

Все ответы синтетические, реальные системы не вызываются. Для ИНН из data/*.json
возвращаются подготовленные данные демо-компаний, для любого другого корректного ИНН —
детерминированный ответ, вычисленный из хеша ИНН.

Сбои для демонстрации: MOCKS_FAILURE_RATE (доля случайных ответов 503) и
GET /admin/fail?service=bki (выключить: &enabled=false).
"""

import hashlib
import json
import os
import random
import re
import threading
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, request

DATA_DIR = Path(__file__).parent / "data"
SERVICES = ("bki", "egrul", "fns", "esign", "abs")
INN_RE = re.compile(r"^(\d{10}|\d{12})$")
FAILURE_RATE = float(os.getenv("MOCKS_FAILURE_RATE", "0"))

FAILING: set[str] = set()
_DISBURSEMENTS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()

app = Flask(__name__)
app.json.ensure_ascii = False  # type: ignore[attr-defined]


def _load(name: str) -> dict[str, dict[str, Any]]:
    return json.loads((DATA_DIR / f"{name}.json").read_text(encoding="utf-8"))


DATA = {name: _load(name) for name in ("bki", "egrul", "fns")}


def _error(status: int, code: str, message: str) -> Response:
    response = jsonify({"error": code, "message": message})
    response.status_code = status
    return response


def _unavailable(service: str) -> Response | None:
    if service in FAILING or (FAILURE_RATE > 0 and random.random() < FAILURE_RATE):
        return _error(503, "service_unavailable", f"{service} временно недоступен (симуляция)")
    return None


def _hash(inn: str, salt: str) -> int:
    return int(hashlib.sha256(f"{salt}:{inn}".encode()).hexdigest()[:12], 16)


def _generated_egrul(inn: str) -> dict[str, Any]:
    h = _hash(inn, "egrul")
    kind = "ip" if len(inn) == 12 else "llc"
    okveds = ["10.71", "25.62", "46.90", "47.11", "49.41", "56.10", "62.01", "41.20"]
    digits = str(h).zfill(14)
    return {
        "name": f"{'ИП' if kind == 'ip' else 'ООО'} «Синтетика-{inn[-4:]}»",
        "kind": kind,
        "ogrn": ("3" + digits[:14]) if kind == "ip" else ("1" + digits[:12]),
        "status": "liquidating" if h % 20 == 0 else "active",
        "registered_at": (date(2012, 1, 1) + timedelta(days=h % 4500)).isoformat(),
        "okved": okveds[h % len(okveds)],
        "director_name": "Синтетический руководитель",
    }


def _generated_fns(inn: str) -> dict[str, Any]:
    h = _hash(inn, "fns")
    tax_debt = 150_000 if h % 15 == 0 else 20_000 if h % 7 == 0 else 0
    return {
        "tax_debt": tax_debt,
        "late_payments_12m": h % 4,
        "tax_regime": "УСН" if h % 2 else "ОСН",
        "employees": 3 + h % 60,
    }


def _generated_bki(inn: str) -> dict[str, Any]:
    h = _hash(inn, "bki")
    loans = h % 4
    current = 100 if h % 25 == 0 else 0
    worst = current or [0, 0, 0, 10, 25, 45][h % 6]
    return {
        "active_loans": loans,
        "monthly_payments": loans * (25_000 + (h % 5) * 25_000),
        "current_overdue_days": current,
        "max_overdue_days_24m": worst,
        "overdue_count_24m": 0 if worst == 0 else 1 + h % 3,
    }


GENERATORS: dict[str, Callable[[str], dict[str, Any]]] = {
    "egrul": _generated_egrul,
    "fns": _generated_fns,
    "bki": _generated_bki,
}


def _company_data(service: str, inn: str) -> dict[str, Any] | Response:
    if not INN_RE.match(inn):
        return _error(400, "invalid_inn", "ИНН должен состоять из 10 или 12 цифр")
    failure = _unavailable(service)
    if failure is not None:
        return failure
    known = DATA[service].get(inn)
    data = dict(known) if known else GENERATORS[service](inn)
    return {"inn": inn, **data, "synthetic": True}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/bki/report")
def bki_report() -> dict[str, Any] | Response:
    return _company_data("bki", request.args.get("inn", ""))


@app.get("/egrul/<inn>")
def egrul(inn: str) -> dict[str, Any] | Response:
    return _company_data("egrul", inn)


@app.get("/fns/transparent-business/<inn>")
def fns_transparent_business(inn: str) -> dict[str, Any] | Response:
    return _company_data("fns", inn)


@app.post("/esign/sign")
def esign_sign() -> dict[str, Any] | Response:
    failure = _unavailable("esign")
    if failure is not None:
        return failure
    body = request.get_json(silent=True) or {}
    document_hash = str(body.get("document_hash") or "")
    if not document_hash or "application_id" not in body:
        return _error(400, "invalid_request", "Нужны application_id и document_hash")
    seed = f"{body['application_id']}:{document_hash}"
    return {
        "signature_id": "SIG-" + hashlib.sha256(seed.encode()).hexdigest()[:12].upper(),
        "document_hash": document_hash,
        "signer": body.get("signer", "client"),
        "signed_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "simulated": True,
    }


@app.post("/abs/disbursements")
def abs_disbursements() -> dict[str, Any] | Response:
    failure = _unavailable("abs")
    if failure is not None:
        return failure
    body = request.get_json(silent=True) or {}
    key = str(body.get("idempotency_key") or "")
    amount = body.get("amount")
    if not key or not isinstance(amount, int) or amount <= 0:
        return _error(400, "invalid_request", "Нужны idempotency_key и положительная сумма amount")
    with _LOCK:
        # Повтор с тем же ключом возвращает ту же выдачу: деньги не уходят дважды
        if key not in _DISBURSEMENTS:
            _DISBURSEMENTS[key] = {
                "disbursement_id": "ABS-" + hashlib.sha256(key.encode()).hexdigest()[:10].upper(),
                "status": "completed",
                "amount": amount,
                "credited_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "simulated": True,
            }
        return _DISBURSEMENTS[key]


@app.get("/admin/fail")
def admin_fail() -> dict[str, Any] | Response:
    service = request.args.get("service", "")
    if service not in SERVICES:
        return _error(
            400, "unknown_service", f"service должен быть одним из: {', '.join(SERVICES)}"
        )
    enabled = request.args.get("enabled", "true").lower() not in {"false", "0", "no", "off"}
    with _LOCK:
        if enabled:
            FAILING.add(service)
        else:
            FAILING.discard(service)
    return {"service": service, "failing": enabled}
