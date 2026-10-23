from typing import Any

from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from app.api.schemas.common import LabelledFieldSchema, ScheduleRowSchema
from app.domain.form_fields import PURPOSES


class ProductSchema(Schema):
    code = fields.String(required=True)
    name = fields.String(required=True)
    description = fields.String(required=True)
    purposes = fields.List(fields.String(), required=True)
    min_amount = fields.Integer(required=True)
    max_amount = fields.Integer(required=True)
    min_term_months = fields.Integer(required=True)
    max_term_months = fields.Integer(required=True)
    rate_spread = fields.Float(required=True)
    base_rate = fields.Float(
        required=True, metadata={"description": "Ставка «от»: ключевая ставка + спред продукта"}
    )
    requires_collateral = fields.Boolean(required=True)
    requires_guarantee = fields.Boolean(required=True)
    required_fields = fields.List(fields.Nested(LabelledFieldSchema), required=True)


class RecommendRequestSchema(Schema):
    purpose = fields.String(required=True, validate=validate.OneOf(list(PURPOSES)))
    amount = fields.Integer(required=True, validate=validate.Range(min=1))
    term_months = fields.Integer(required=True, validate=validate.Range(min=1, max=120))


class RecommendationSchema(Schema):
    product = fields.Nested(ProductSchema, required=True)
    amount = fields.Integer(required=True)
    term_months = fields.Integer(required=True)
    rate = fields.Float(required=True)
    monthly_payment = fields.Float(required=True)
    fits = fields.Boolean(required=True, metadata={"description": "Сумма и срок подходят продукту"})
    notes = fields.List(fields.String(), required=True)


class CalculatorRequestSchema(Schema):
    amount = fields.Integer(required=True, validate=validate.Range(min=1))
    term_months = fields.Integer(required=True, validate=validate.Range(min=1, max=120))
    product_code = fields.String()
    annual_rate = fields.Float(validate=validate.Range(min=0, max=100))

    @validates_schema
    def rate_source(self, data: dict[str, Any], **kwargs: Any) -> None:
        if "product_code" not in data and "annual_rate" not in data:
            raise ValidationError("Укажите product_code или annual_rate", "annual_rate")


class CalculatorResponseSchema(Schema):
    amount = fields.Integer(required=True)
    term_months = fields.Integer(required=True)
    annual_rate = fields.Float(required=True)
    monthly_payment = fields.Float(required=True)
    total_payment = fields.Float(required=True)
    overpayment = fields.Float(required=True)
    schedule = fields.List(fields.Nested(ScheduleRowSchema), required=True)
