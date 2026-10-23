"""Доменные ошибки. API превращает их в problem+json со статусом из атрибута status."""


class DomainError(Exception):
    status = 400
    code = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidTransition(DomainError):
    status = 409
    code = "invalid_transition"


class CommentRequired(DomainError):
    status = 422
    code = "comment_required"
