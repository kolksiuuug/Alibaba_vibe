"""Ошибки API в формате application/problem+json (RFC 7807)."""

import http
import logging
from http import HTTPStatus
from typing import Any

from flask import Response, g, has_request_context, jsonify, request
from flask_smorest import Api
from flask_smorest.utils import prepare_response
from marshmallow import Schema, fields
from werkzeug.exceptions import HTTPException

PROBLEM_MIMETYPE = "application/problem+json"

log = logging.getLogger(__name__)

TITLES_RU = {
    400: "Некорректный запрос",
    401: "Требуется вход",
    403: "Доступ запрещён",
    404: "Не найдено",
    405: "Метод не поддерживается",
    409: "Действие недоступно в текущем статусе",
    422: "Ошибка в данных запроса",
    500: "Внутренняя ошибка",
    503: "Сервис временно недоступен",
}


class ProblemSchema(Schema):
    type = fields.String(metadata={"description": "URI типа ошибки, по умолчанию about:blank"})
    title = fields.String(metadata={"description": "Краткое описание на русском"})
    status = fields.Integer(metadata={"description": "HTTP-статус"})
    detail = fields.String(metadata={"description": "Подробности для пользователя"})
    instance = fields.String(metadata={"description": "Путь запроса"})
    code = fields.String(metadata={"description": "Машинный код ошибки"})
    errors = fields.Dict(metadata={"description": "Ошибки валидации по полям"})
    request_id = fields.String(metadata={"description": "Идентификатор запроса для поиска в логах"})


def problem_response(
    status: int,
    detail: str | None = None,
    *,
    code: str | None = None,
    errors: Any = None,
) -> Response:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": TITLES_RU.get(status, HTTPStatus(status).phrase),
        "status": status,
    }
    if detail:
        body["detail"] = detail
    if code:
        body["code"] = code
    if errors:
        body["errors"] = errors
    if has_request_context():
        body["instance"] = request.path
        body["request_id"] = g.get("request_id")
    response = jsonify(body)
    response.status_code = status
    response.mimetype = PROBLEM_MIMETYPE
    return response


class ProblemApi(Api):
    """Api smorest, который отдаёт все HTTP-ошибки как problem+json."""

    ERROR_SCHEMA = ProblemSchema

    def _register_responses(self) -> None:
        # Копия метода flask-smorest 0.47.0 (версия закреплена), но ошибки 4xx/5xx
        # описаны в OpenAPI с типом application/problem+json, как их и отдаёт API.
        for status in http.HTTPStatus:
            response: dict[str, Any] = {"description": status.phrase}
            content_type = self.DEFAULT_RESPONSE_CONTENT_TYPE
            if status >= 400:
                response["schema"] = self.ERROR_SCHEMA
                content_type = PROBLEM_MIMETYPE
            prepare_response(response, self.spec, content_type)
            self.spec.components.response(status.name, response, lazy=True)
        default = {"description": "Ошибка в формате problem+json", "schema": self.ERROR_SCHEMA}
        prepare_response(default, self.spec, PROBLEM_MIMETYPE)
        self.spec.components.response("DEFAULT_ERROR", default, lazy=True)

    def handle_http_exception(self, error: HTTPException) -> Response:
        data = getattr(error, "data", None) or {}
        status = error.code or 500
        if status >= 500:
            log.error("http error", extra={"status": status})
        response = problem_response(
            status,
            data.get("message"),
            errors=data.get("messages") or data.get("errors"),
        )
        for name, value in (data.get("headers") or {}).items():
            response.headers[name] = value
        if status == 405 and getattr(error, "valid_methods", None):
            response.headers["Allow"] = ", ".join(error.valid_methods)  # type: ignore[attr-defined]
        return response
