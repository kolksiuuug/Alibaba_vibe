"""Заявки клиента: черновик, отправка, дозапрос, предложение, подпись, таймлайн."""

from typing import Any

from flask.views import MethodView
from flask_smorest import Blueprint

from app.adapters import get_adapters
from app.api.auth import current_user, require_role
from app.api.schemas.applications import (
    ApplicationCreateSchema,
    ApplicationDetailSchema,
    ApplicationPatchSchema,
    ApplicationSummarySchema,
    EventSchema,
    InfoResponseSchema,
    SignCodeSchema,
    SignConfirmSchema,
)
from app.models import Application
from app.services import applications as service
from app.services import signing

blp = Blueprint(
    "applications", __name__, url_prefix="/api/v1/applications", description="Заявки клиента"
)
CLIENT = "client"


@blp.route("")
class ApplicationList(MethodView):
    @require_role(CLIENT)
    @blp.response(200, ApplicationSummarySchema(many=True))
    def get(self) -> list[Application]:
        """Заявки компании текущего клиента."""
        return service.list_company_applications(current_user())

    @require_role(CLIENT)
    @blp.arguments(ApplicationCreateSchema)
    @blp.response(201, ApplicationDetailSchema)
    def post(self, data: dict[str, Any]) -> dict[str, Any]:
        """Создать черновик. Данные компании подставляются автоматически."""
        application = service.create_draft(current_user(), **data)
        return service.client_view(application)


@blp.route("/<int:application_id>")
class ApplicationItem(MethodView):
    @require_role(CLIENT)
    @blp.response(200, ApplicationDetailSchema)
    def get(self, application_id: int) -> dict[str, Any]:
        """Карточка заявки: статус, этапы проверки, предложение, дозапрос, факторы решения."""
        return service.client_view(service.get_client_application(current_user(), application_id))

    @require_role(CLIENT)
    @blp.arguments(ApplicationPatchSchema)
    @blp.response(200, ApplicationDetailSchema)
    def patch(self, data: dict[str, Any], application_id: int) -> dict[str, Any]:
        """Изменить черновик (условия и поля анкеты)."""
        return service.client_view(service.update_draft(current_user(), application_id, data))


@blp.route("/<int:application_id>/submit")
class Submit(MethodView):
    @require_role(CLIENT)
    @blp.response(200, ApplicationDetailSchema)
    def post(self, application_id: int) -> dict[str, Any]:
        """Отправить заявку на проверку. Повтор идемпотентен."""
        return service.client_view(service.submit(current_user(), application_id))


@blp.route("/<int:application_id>/cancel")
class Cancel(MethodView):
    @require_role(CLIENT)
    @blp.response(200, ApplicationDetailSchema)
    def post(self, application_id: int) -> dict[str, Any]:
        """Отменить черновик или заявку, по которой банк ждёт ответа."""
        return service.client_view(service.cancel(current_user(), application_id))


@blp.route("/<int:application_id>/info-response")
class InfoResponse(MethodView):
    @require_role(CLIENT)
    @blp.arguments(InfoResponseSchema)
    @blp.response(200, ApplicationDetailSchema)
    def post(self, data: dict[str, Any], application_id: int) -> dict[str, Any]:
        """Ответить на дозапрос банка: заявка снова уходит на проверку."""
        application = service.respond_to_info_request(
            current_user(), application_id, data["answers"], data["comment"]
        )
        return service.client_view(application)


@blp.route("/<int:application_id>/offer/accept")
class AcceptOffer(MethodView):
    @require_role(CLIENT)
    @blp.response(200, ApplicationDetailSchema)
    def post(self, application_id: int) -> dict[str, Any]:
        """Принять предложение банка."""
        return service.client_view(service.accept_offer(current_user(), application_id))


@blp.route("/<int:application_id>/offer/decline")
class DeclineOffer(MethodView):
    @require_role(CLIENT)
    @blp.response(200, ApplicationDetailSchema)
    def post(self, application_id: int) -> dict[str, Any]:
        """Отклонить предложение банка."""
        return service.client_view(service.decline_offer(current_user(), application_id))


@blp.route("/<int:application_id>/sign/request-code")
class RequestSignCode(MethodView):
    @require_role(CLIENT)
    @blp.response(200, SignCodeSchema)
    def post(self, application_id: int) -> dict[str, Any]:
        """Получить код подписи. Симуляция: код показывается в интерфейсе, SMS не отправляется."""
        return signing.request_code(current_user(), application_id)


@blp.route("/<int:application_id>/sign/confirm")
class ConfirmSign(MethodView):
    @require_role(CLIENT)
    @blp.arguments(SignConfirmSchema)
    @blp.response(200, ApplicationDetailSchema)
    def post(self, data: dict[str, Any], application_id: int) -> dict[str, Any]:
        """Подписать договор кодом (симуляция ЭП). Дальше воркер выдаёт кредит."""
        application = signing.confirm(current_user(), application_id, data["code"], get_adapters())
        return service.client_view(application)


@blp.route("/<int:application_id>/events")
class Events(MethodView):
    @require_role(CLIENT)
    @blp.response(200, EventSchema(many=True))
    def get(self, application_id: int) -> list[dict[str, Any]]:
        """Таймлайн переходов статуса."""
        application = service.get_client_application(current_user(), application_id)
        return service.events(application, with_comments=False)
