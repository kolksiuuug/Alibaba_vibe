"""Liveness и readiness для healthcheck в docker compose."""

from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.schemas.health import HealthSchema
from app.extensions import db

blp = Blueprint("health", __name__, url_prefix="/api", description="Состояние сервиса")


@blp.route("/health")
class Health(MethodView):
    @blp.response(200, HealthSchema)
    def get(self) -> dict[str, str]:
        """Процесс жив (зависимости не проверяются)."""
        return {"status": "ok"}


@blp.route("/ready")
class Ready(MethodView):
    @blp.response(200, HealthSchema)
    def get(self) -> dict[str, str]:
        """Сервис готов принимать запросы: база данных доступна."""
        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            db.session.rollback()
            abort(503, message="База данных недоступна")
        return {"status": "ok"}
