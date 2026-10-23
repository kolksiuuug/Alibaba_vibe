"""Доменные ошибки превращаются в problem+json с нужным HTTP-статусом."""

from flask import Flask

from app.api import PROBLEM_MIMETYPE
from app.domain.errors import CommentRequired, InvalidTransition


def test_invalid_transition_is_409_problem(app: Flask) -> None:
    error = InvalidTransition("Переход issued -> draft недопустим")
    with app.test_request_context("/api/v1/applications/1/submit", method="POST"):
        response = app.handle_user_exception(error)

    assert response.status_code == 409
    assert response.mimetype == PROBLEM_MIMETYPE
    assert response.json["code"] == "invalid_transition"
    assert response.json["detail"] == "Переход issued -> draft недопустим"


def test_comment_required_is_422_problem(app: Flask) -> None:
    with app.test_request_context("/api/v1/analyst/applications/1/decision", method="POST"):
        response = app.handle_user_exception(CommentRequired("Нужен комментарий"))

    assert response.status_code == 422
    assert response.json["code"] == "comment_required"
