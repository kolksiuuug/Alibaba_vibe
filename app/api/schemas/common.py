"""Общие схемы: причины, поля анкеты, этапы конвейера, график, факторы скоринга."""

from marshmallow import Schema, fields


class ReasonSchema(Schema):
    code = fields.String(required=True)
    text = fields.String(required=True)


class LabelledFieldSchema(Schema):
    code = fields.String(required=True)
    label = fields.String(required=True)


class StepSchema(Schema):
    code = fields.String(required=True)
    title = fields.String()
    state = fields.String(
        required=True, metadata={"description": "pending | running | done | failed"}
    )
    started_at = fields.String()
    finished_at = fields.String()
    message = fields.String()


class ScheduleRowSchema(Schema):
    number = fields.Integer(required=True)
    payment = fields.Float(required=True)
    principal = fields.Float(required=True)
    interest = fields.Float(required=True)
    balance = fields.Float(required=True)


class FactorSchema(Schema):
    code = fields.String(required=True)
    value = fields.Float(required=True)
    points = fields.Integer(required=True)
    max_points = fields.Integer(required=True)
    explanation_ru = fields.String(required=True)
    impact = fields.String(required=True, metadata={"description": "positive | neutral | negative"})
