from marshmallow import Schema, fields, validate

from app.api.schemas.applications import (
    STATUS_DESCRIPTION,
    ApplicationDetailSchema,
    EventSchema,
    InfoRequestSchema,
)
from app.api.schemas.common import FactorSchema, ReasonSchema
from app.services.review import ACTIONS


class QueueQuerySchema(Schema):
    status = fields.String(load_default=None, metadata={"description": STATUS_DESCRIPTION})


class QueueItemSchema(Schema):
    id = fields.Integer(required=True)
    status = fields.String(required=True)
    company_name = fields.String(required=True)
    company_inn = fields.String(required=True)
    product_name = fields.String(required=True)
    amount = fields.Integer(required=True)
    term_months = fields.Integer(required=True)
    score = fields.Integer(allow_none=True)
    grade = fields.String(allow_none=True)
    submitted_at = fields.DateTime(allow_none=True)
    status_changed_at = fields.DateTime(required=True)


class CheckSchema(Schema):
    source = fields.String(required=True, metadata={"description": "bki | egrul | fns"})
    status = fields.String(required=True, metadata={"description": "ok | failed"})
    response = fields.Dict(allow_none=True)
    error = fields.String(allow_none=True)
    checked_at = fields.DateTime(required=True)


class ScoringSchema(Schema):
    score = fields.Integer(allow_none=True)
    grade = fields.String(allow_none=True)
    factors = fields.List(fields.Nested(FactorSchema), required=True)
    client_factors = fields.List(fields.String(), required=True)
    stop_factors = fields.List(fields.Nested(ReasonSchema), required=True)
    created_at = fields.DateTime(required=True)


class DecisionSchema(Schema):
    id = fields.Integer(required=True)
    outcome = fields.String(required=True)
    decided_by = fields.String(required=True)
    analyst_id = fields.Integer(allow_none=True)
    is_counter = fields.Boolean(required=True)
    amount = fields.Integer(allow_none=True)
    term_months = fields.Integer(allow_none=True)
    rate = fields.Float(allow_none=True)
    monthly_payment = fields.Float(allow_none=True)
    reasons = fields.List(fields.Nested(ReasonSchema), required=True)
    comment = fields.String(allow_none=True)
    created_at = fields.DateTime(required=True)


class AnalystCardSchema(ApplicationDetailSchema):
    checks = fields.List(fields.Nested(CheckSchema), required=True)
    scoring = fields.Nested(ScoringSchema, allow_none=True)
    decisions = fields.List(fields.Nested(DecisionSchema), required=True)
    info_requests = fields.List(fields.Nested(InfoRequestSchema), required=True)
    events = fields.List(fields.Nested(EventSchema), required=True)


class AnalystDecisionSchema(Schema):
    action = fields.String(
        required=True,
        validate=validate.OneOf(list(ACTIONS)),
        metadata={"description": "approve | change_terms | request_info | reject"},
    )
    comment = fields.String(
        allow_none=True,
        load_default=None,
        metadata={"description": "Обязателен для любого решения"},
    )
    amount = fields.Integer(
        validate=validate.Range(min=1), metadata={"description": "change_terms"}
    )
    term_months = fields.Integer(
        validate=validate.Range(min=1, max=120), metadata={"description": "change_terms"}
    )
    fields_ = fields.List(
        fields.String(),
        load_default=list,
        data_key="fields",
        metadata={"description": "request_info: коды полей анкеты"},
    )
