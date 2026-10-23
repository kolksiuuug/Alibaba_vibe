from marshmallow import Schema, fields, validate


class TurnoverMonthSchema(Schema):
    month = fields.String(required=True, metadata={"example": "2026-09"})
    amount = fields.Integer(required=True)


class CompanySchema(Schema):
    id = fields.Integer(required=True)
    name = fields.String(required=True)
    kind = fields.String(required=True, metadata={"description": "ip | llc"})
    inn = fields.String(required=True)
    ogrn = fields.String(required=True)
    okved = fields.String(required=True)
    okved_name = fields.String(required=True)
    registered_at = fields.Date(required=True)
    region = fields.String(required=True)
    director_name = fields.String(required=True)
    monthly_turnover = fields.List(fields.Nested(TurnoverMonthSchema), required=True)


class UserSchema(Schema):
    id = fields.Integer(required=True)
    login = fields.String(required=True)
    role = fields.String(required=True, metadata={"description": "client | analyst"})
    display_name = fields.String(required=True)
    demo_hint = fields.String(allow_none=True)
    company = fields.Nested(CompanySchema, allow_none=True)


class DemoProfileSchema(Schema):
    login = fields.String(required=True)
    role = fields.String(required=True)
    display_name = fields.String(required=True)
    demo_hint = fields.String(allow_none=True)
    company_name = fields.String(attribute="company.name", allow_none=True)


class DemoLoginSchema(Schema):
    login = fields.String(required=True, validate=validate.Length(min=1, max=64))


class TokenSchema(Schema):
    token = fields.String(required=True)
    user = fields.Nested(UserSchema, required=True)
