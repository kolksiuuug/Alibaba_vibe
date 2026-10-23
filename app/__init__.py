"""Фабрика приложения: конфигурация, расширения, API, CLI."""

import logging

from flask import Flask

from app.config import DEFAULT_SECRET_KEY, ProdConfig, get_config
from app.extensions import db, migrate
from app.log import configure_logging, init_request_logging


def create_app(config_name: str | None = None) -> Flask:
    config = get_config(config_name)
    if not config.TESTING:
        configure_logging(config.LOG_LEVEL)

    app = Flask(__name__)
    app.config.from_object(config)
    app.json.ensure_ascii = False  # type: ignore[attr-defined]
    app.json.sort_keys = False  # type: ignore[attr-defined]

    db.init_app(app)
    migrate.init_app(app, db)

    from app import models  # noqa: F401  # регистрирует модели в metadata для Alembic
    from app.api import register_api
    from app.cli import register_cli

    init_request_logging(app)
    register_api(app)
    register_cli(app)

    if issubclass(config, ProdConfig) and app.config["SECRET_KEY"] == DEFAULT_SECRET_KEY:
        logging.getLogger(__name__).warning("default SECRET_KEY in use: acceptable for demo only")
    return app
