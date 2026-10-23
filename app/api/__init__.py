"""Регистрация API: blueprints smorest и ошибки problem+json.

Модули с blueprints импортируются внутри register_api(), чтобы app.extensions
мог импортировать ProblemApi без циклических импортов.
"""

import logging

from flask import Flask, Response

from app.api.problem import PROBLEM_MIMETYPE, ProblemApi, problem_response
from app.domain.errors import DomainError

__all__ = ["PROBLEM_MIMETYPE", "ProblemApi", "problem_response", "register_api"]

log = logging.getLogger(__name__)


def register_api(app: Flask) -> None:
    from app.api.health import blp as health_blp
    from app.api.v1 import analyst, applications, auth, notifications, products
    from app.extensions import api

    api.init_app(app)
    api.spec.components.security_scheme("bearerAuth", {"type": "http", "scheme": "bearer"})
    for blueprint in (
        health_blp,
        auth.blp,
        products.blp,
        applications.blp,
        notifications.blp,
        analyst.blp,
    ):
        api.register_blueprint(blueprint)

    @app.errorhandler(DomainError)
    def handle_domain_error(error: DomainError) -> Response:
        return problem_response(error.status, error.message, code=error.code, errors=error.errors)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> Response:
        log.exception("unhandled error")
        return problem_response(500)
