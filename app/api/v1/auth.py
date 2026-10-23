"""Демо-вход без паролей и кодов, текущий пользователь."""

from typing import Any

from flask.views import MethodView
from flask_smorest import Blueprint

from app.api.auth import current_user, require_role
from app.api.schemas.auth import DemoLoginSchema, DemoProfileSchema, TokenSchema, UserSchema
from app.models import User
from app.services.auth import demo_login, demo_profiles

blp = Blueprint("auth", __name__, url_prefix="/api/v1", description="Демо-вход и профиль")


@blp.route("/auth/demo-profiles")
class DemoProfiles(MethodView):
    @blp.doc(security=[])
    @blp.response(200, DemoProfileSchema(many=True))
    def get(self) -> list[User]:
        """Демо-профили для экрана входа: пять компаний и аналитик."""
        return demo_profiles()


@blp.route("/auth/demo-login")
class DemoLogin(MethodView):
    @blp.doc(security=[])
    @blp.arguments(DemoLoginSchema)
    @blp.response(200, TokenSchema)
    def post(self, data: dict[str, Any]) -> dict[str, Any]:
        """Войти в демо-профиль и получить Bearer-токен."""
        user, token = demo_login(data["login"])
        return {"token": token, "user": user}


@blp.route("/me")
class Me(MethodView):
    @require_role()
    @blp.response(200, UserSchema)
    def get(self) -> User:
        """Текущий пользователь и его компания."""
        return current_user()
