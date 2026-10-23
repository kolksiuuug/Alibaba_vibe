"""Центр уведомлений в продукте (email и SMS не используются)."""

from typing import Any

from flask.views import MethodView
from flask_smorest import Blueprint

from app.api.auth import current_user, require_role
from app.api.schemas.notifications import NotificationListSchema, NotificationSchema
from app.models import Notification
from app.services import notifications as service

blp = Blueprint(
    "notifications", __name__, url_prefix="/api/v1/notifications", description="Уведомления"
)


@blp.route("")
class NotificationList(MethodView):
    @require_role()
    @blp.response(200, NotificationListSchema)
    def get(self) -> dict[str, Any]:
        """Последние уведомления пользователя и число непрочитанных."""
        items, unread = service.list_for_user(current_user())
        return {"items": items, "unread_count": unread}


@blp.route("/<int:notification_id>/read")
class NotificationRead(MethodView):
    @require_role()
    @blp.response(200, NotificationSchema)
    def post(self, notification_id: int) -> Notification:
        """Отметить уведомление прочитанным."""
        return service.mark_read(current_user(), notification_id)
