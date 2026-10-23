from marshmallow import Schema, fields


class NotificationSchema(Schema):
    id = fields.Integer(required=True)
    application_id = fields.Integer(allow_none=True)
    kind = fields.String(required=True)
    title = fields.String(required=True)
    body = fields.String(required=True)
    is_read = fields.Boolean(required=True)
    created_at = fields.DateTime(required=True)


class NotificationListSchema(Schema):
    items = fields.List(fields.Nested(NotificationSchema), required=True)
    unread_count = fields.Integer(required=True)
