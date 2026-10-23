"""Каталог продуктов, подбор под цель, сумму и срок, калькулятор платежей."""

from decimal import Decimal
from typing import Any

from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint

from app.api.auth import require_role
from app.api.schemas.products import (
    CalculatorRequestSchema,
    CalculatorResponseSchema,
    ProductSchema,
    RecommendationSchema,
    RecommendRequestSchema,
)
from app.services import offers

blp = Blueprint("products", __name__, url_prefix="/api/v1", description="Продукты и калькулятор")


def _key_rate() -> Decimal:
    return Decimal(str(current_app.config["KEY_RATE"]))


@blp.route("/products")
class Products(MethodView):
    @require_role()
    @blp.response(200, ProductSchema(many=True))
    def get(self) -> list[dict[str, Any]]:
        """Кредитные продукты со ставкой «от»."""
        return [offers.product_view(p, _key_rate()) for p in offers.active_products()]


@blp.route("/products/recommend")
class Recommend(MethodView):
    @require_role()
    @blp.arguments(RecommendRequestSchema)
    @blp.response(200, RecommendationSchema(many=True))
    def post(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """1–3 подходящих продукта с предварительной ставкой и ежемесячным платежом."""
        return offers.recommend(
            data["purpose"], data["amount"], data["term_months"], key_rate=_key_rate()
        )


@blp.route("/calculator")
class Calculator(MethodView):
    @require_role()
    @blp.arguments(CalculatorRequestSchema)
    @blp.response(200, CalculatorResponseSchema)
    def post(self, data: dict[str, Any]) -> dict[str, Any]:
        """Аннуитетный платёж и график. Ставка — annual_rate или ставка «от» продукта."""
        return offers.calculate_for(
            data["amount"],
            data["term_months"],
            key_rate=_key_rate(),
            annual_rate=data.get("annual_rate"),
            product_code=data.get("product_code"),
        )
