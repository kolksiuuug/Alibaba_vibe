"""Доменные ошибки. API превращает их в problem+json со статусом из атрибута status."""

from typing import Any


class DomainError(Exception):
    status = 400
    code = "domain_error"

    def __init__(self, message: str, *, errors: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors


class InvalidTransition(DomainError):
    status = 409
    code = "invalid_transition"


class CommentRequired(DomainError):
    status = 422
    code = "comment_required"


class ValidationFailed(DomainError):
    status = 422
    code = "validation_failed"


class NotFound(DomainError):
    status = 404
    code = "not_found"


class AccessDenied(DomainError):
    status = 403
    code = "access_denied"


class ServiceUnavailable(DomainError):
    status = 503
    code = "service_unavailable"
