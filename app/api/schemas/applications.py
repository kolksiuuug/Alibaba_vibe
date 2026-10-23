from marshmallow import Schema, fields, validate

from app.api.schemas.auth import CompanySchema
from app.api.schemas.common import (
    FactorSchema,
    LabelledFieldSchema,
    ReasonSchema,
    ScheduleRowSchema,
    StepSchema,
)
from app.domain.form_fields import PURPOSES

STATUS_DESCRIPTION = (
    "draft | submitted | checking | info_requested | manual_review | offer | accepted | "
    "signed | issued | rejected | declined | cancelled"
)


class ApplicationCreateSchema(Schema):
    product_code = fields.String(required=True)
    amount = fields.Integer(required=True, validate=validate.Range(min=1))
    term_months = fields.Integer(required=True, validate=validate.Range(min=1, max=120))
    purpose = fields.String(required=True, validate=validate.OneOf(list(PURPOSES)))
    form_data = fields.Dict(keys=fields.String(), load_default=dict)


class ApplicationPatchSchema(Schema):
    product_code = fields.String()
    amount = fields.Integer(validate=validate.Range(min=1))
    term_months = fields.Integer(validate=validate.Range(min=1, max=120))
    purpose = fields.String(validate=validate.OneOf(list(PURPOSES)))
    form_data = fields.Dict(keys=fields.String())


class InfoResponseSchema(Schema):
    answers = fields.Dict(keys=fields.String(), load_default=dict)
    comment = fields.String(allow_none=True, load_default=None)


class SignConfirmSchema(Schema):
    code = fields.String(required=True, validate=validate.Regexp(r"^\s*\d{6}\s*$"))


class SignCodeSchema(Schema):
    code = fields.String(required=True, metadata={"description": "Код показывается в интерфейсе"})
    expires_at = fields.DateTime(required=True)
    document_hash = fields.String(required=True)
    simulated = fields.Boolean(required=True)


class ProductBriefSchema(Schema):
    code = fields.String(required=True)
    name = fields.String(required=True)
    requires_collateral = fields.Boolean(required=True)
    requires_guarantee = fields.Boolean(required=True)


class ApplicationSummarySchema(Schema):
    id = fields.Integer(required=True)
    status = fields.String(required=True, metadata={"description": STATUS_DESCRIPTION})
    product = fields.Nested(ProductBriefSchema, required=True)
    amount = fields.Integer(required=True)
    term_months = fields.Integer(required=True)
    purpose = fields.String(required=True)
    created_at = fields.DateTime(required=True)
    status_changed_at = fields.DateTime(required=True)


class ApplicationSchema(ApplicationSummarySchema):
    company = fields.Nested(CompanySchema, required=True)
    form_data = fields.Dict(keys=fields.String(), required=True)
    pipeline_steps = fields.List(fields.Nested(StepSchema), required=True)
    submitted_at = fields.DateTime(allow_none=True)
    updated_at = fields.DateTime(required=True)


class CompletenessSchema(Schema):
    ready_to_submit = fields.Boolean(required=True)
    missing_required = fields.List(fields.Nested(LabelledFieldSchema), required=True)
    missing_for_product = fields.List(fields.Nested(LabelledFieldSchema), required=True)


class OfferSchema(Schema):
    amount = fields.Integer(required=True)
    term_months = fields.Integer(required=True)
    rate = fields.Float(required=True)
    monthly_payment = fields.Float(required=True)
    is_counter = fields.Boolean(required=True)
    decided_by = fields.String(required=True, metadata={"description": "engine | analyst"})
    requested_amount = fields.Integer(required=True)
    requested_term_months = fields.Integer(required=True)
    total_payment = fields.Float(required=True)
    overpayment = fields.Float(required=True)
    reasons = fields.List(fields.Nested(ReasonSchema), required=True)
    comment = fields.String(allow_none=True)
    schedule = fields.List(fields.Nested(ScheduleRowSchema), required=True)


class InfoRequestSchema(Schema):
    id = fields.Integer(required=True)
    requested_by = fields.String(required=True, metadata={"description": "engine | analyst"})
    message = fields.String(required=True)
    fields_ = fields.List(
        fields.Nested(LabelledFieldSchema), required=True, data_key="fields", attribute="fields"
    )
    response = fields.Dict(allow_none=True)
    responded_at = fields.DateTime(allow_none=True)
    created_at = fields.DateTime(required=True)


class SignatureInfoSchema(Schema):
    signed_at = fields.DateTime(allow_none=True)
    signature_reference = fields.String(allow_none=True)


class DisbursementInfoSchema(Schema):
    amount = fields.Integer(required=True)
    abs_reference = fields.String(required=True)
    created_at = fields.DateTime(required=True)


class ApplicationDetailSchema(Schema):
    application = fields.Nested(ApplicationSchema, required=True)
    completeness = fields.Nested(CompletenessSchema, required=True)
    offer = fields.Nested(OfferSchema, allow_none=True)
    info_request = fields.Nested(InfoRequestSchema, allow_none=True)
    factors = fields.List(fields.Nested(FactorSchema), required=True)
    reasons = fields.List(fields.Nested(ReasonSchema), required=True)
    decision_comment = fields.String(allow_none=True)
    signature = fields.Nested(SignatureInfoSchema, allow_none=True)
    disbursement = fields.Nested(DisbursementInfoSchema, allow_none=True)


class EventSchema(Schema):
    id = fields.Integer(required=True)
    from_status = fields.String(allow_none=True)
    to_status = fields.String(required=True)
    actor = fields.String(required=True, metadata={"description": "client | analyst | system"})
    reason = fields.String(allow_none=True)
    comment = fields.String(allow_none=True)
    at = fields.DateTime(required=True)
