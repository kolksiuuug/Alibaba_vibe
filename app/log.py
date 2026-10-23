"""Структурные JSON-логи: request_id и маскирование ИНН, ОГРН, телефонов и ФИО."""

import json
import logging
import re
import sys
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from flask import Flask, Response, g, has_request_context, request

# 10–15 цифр подряд: ИНН (10/12), ОГРН (13), ОГРНИП (15)
_LONG_NUMBER_RE = re.compile(r"(?<!\d)\d{10,15}(?!\d)")
_PHONE_RE = re.compile(r"(?:\+7|(?<!\d)8)[\s\-(]*\d{3}[\s\-)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)")
# «Фамилия Имя Отчество» и «Фамилия И. О.»
_FIO_RE = re.compile(
    r"\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:вич|вна|ична|чна|ич|оглы|кызы)\b"
)
_INITIALS_RE = re.compile(r"\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s?[А-ЯЁ]\.")
FIO_MASK = "[ФИО скрыто]"

# Поля extra, значения которых в логах не показываем совсем
SENSITIVE_KEYS = frozenset(
    {
        "inn",
        "ogrn",
        "phone",
        "fio",
        "full_name",
        "director_name",
        "display_name",
        "contact_name",
        "contact_phone",
        "guarantor_full_name",
        "guarantor_inn",
    }
)

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_QUIET_PATHS = frozenset({"/api/health", "/api/ready"})
_STD_RECORD_ATTRS = frozenset(logging.makeLogRecord({}).__dict__) | {
    "message",
    "asctime",
    "request_id",
}


def _mask_number(match: re.Match[str]) -> str:
    digits = match.group()
    return digits[:2] + "*" * (len(digits) - 4) + digits[-2:]


def _mask_phone(match: re.Match[str]) -> str:
    return "+7*******" + re.sub(r"\D", "", match.group())[-2:]


def mask_pii(text: str) -> str:
    text = _PHONE_RE.sub(_mask_phone, text)
    text = _LONG_NUMBER_RE.sub(_mask_number, text)
    text = _FIO_RE.sub(FIO_MASK, text)
    return _INITIALS_RE.sub(FIO_MASK, text)


def _mask_value(key: str, value: Any) -> Any:
    if key in SENSITIVE_KEYS and value is not None:
        return "***"
    if isinstance(value, str):
        return mask_pii(value)
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": mask_pii(record.getMessage()),
            "request_id": getattr(record, "request_id", None),
        }
        for key, value in record.__dict__.items():
            if key not in _STD_RECORD_ATTRS and not key.startswith("_"):
                payload[key] = _mask_value(key, value)
        if record.exc_info:
            payload["exc"] = mask_pii(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = g.get("request_id") if has_request_context() else None
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())


def init_request_logging(app: Flask) -> None:
    access_log = logging.getLogger("app.access")

    @app.before_request
    def start_request() -> None:
        incoming = request.headers.get("X-Request-ID", "")
        g.request_id = incoming if _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
        g.request_started_at = time.perf_counter()

    @app.after_request
    def finish_request(response: Response) -> Response:
        request_id = g.get("request_id")
        if request_id:
            response.headers["X-Request-ID"] = request_id
        if request.path not in _QUIET_PATHS:
            started = g.get("request_started_at")
            duration_ms = round((time.perf_counter() - started) * 1000, 1) if started else None
            access_log.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
        return response
