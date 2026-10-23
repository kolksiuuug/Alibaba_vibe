"""Регистрация API: blueprints smorest и ошибки problem+json.

Модули с blueprints импортируются внутри register_api(), чтобы app.extensions
мог импортировать ProblemApi без циклических импортов.
"""

import logging

from flask import Flask, Response

from app.api.problem import PROBLEM_MIMETYPE, ProblemApi, problem_response

__all__ = ["PROBLEM_MIMETYPE", "ProblemApi", "problem_response", "register_api"]

log = logging.getLogger(__name__)


def register_api(app: Flask) -> None:
    from app.api.health import blp as health_blp
    from app.extensions import api

    api.init_app(app)
    api.register_blueprint(health_blp)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> Response:
        log.exception("unhandled error")
        return problem_response(500)
