"""Рабочее место кредитного аналитика: очередь, карточка заявки, решение."""

from typing import Any

from flask.views import MethodView
from flask_smorest import Blueprint

from app.api.auth import current_user, require_role
from app.api.schemas.analyst import (
    AnalystCardSchema,
    AnalystDecisionSchema,
    QueueItemSchema,
    QueueQuerySchema,
)
from app.services import review

blp = Blueprint(
    "analyst", __name__, url_prefix="/api/v1/analyst/applications", description="Аналитик"
)
ANALYST = "analyst"


@blp.route("")
class Queue(MethodView):
    @require_role(ANALYST)
    @blp.arguments(QueueQuerySchema, location="query")
    @blp.response(200, QueueItemSchema(many=True))
    def get(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        """Очередь заявок с фильтром по статусу (черновики не показываются)."""
        return review.queue(query["status"])


@blp.route("/<int:application_id>")
class Card(MethodView):
    @require_role(ANALYST)
    @blp.response(200, AnalystCardSchema)
    def get(self, application_id: int) -> dict[str, Any]:
        """Карточка: данные, проверки, скоринг по факторам, рекомендация движка, журнал."""
        return review.analyst_card(review.get_application(application_id))


@blp.route("/<int:application_id>/decision")
class DecisionView(MethodView):
    @require_role(ANALYST)
    @blp.arguments(AnalystDecisionSchema)
    @blp.response(200, AnalystCardSchema)
    def post(self, data: dict[str, Any], application_id: int) -> dict[str, Any]:
        """Решение по ручному рассмотрению: одобрить, изменить условия, дозапрос, отказ."""
        application = review.decide(
            current_user(),
            application_id,
            action=data["action"],
            comment=data["comment"],
            amount=data.get("amount"),
            term_months=data.get("term_months"),
            fields=data["fields_"],
        )
        return review.analyst_card(application)
