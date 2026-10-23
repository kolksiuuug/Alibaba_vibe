"""Демо-вход: выбор профиля без паролей и кодов. Токен подписан itsdangerous."""

from typing import Any

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select

from app.domain.errors import NotFound
from app.extensions import db
from app.models import User

_SALT = "demo-login"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=_SALT)


def issue_token(user: User) -> str:
    return str(_serializer().dumps({"user_id": user.id, "role": user.role}))


def user_from_token(token: str) -> User | None:
    try:
        data: dict[str, Any] = _serializer().loads(
            token, max_age=current_app.config["TOKEN_MAX_AGE_S"]
        )
    except (BadSignature, SignatureExpired):
        return None
    user = db.session.get(User, data.get("user_id"))
    if user is None or user.role != data.get("role"):
        return None
    return user


def demo_profiles() -> list[User]:
    return list(db.session.scalars(select(User).order_by(User.id)))


def demo_login(login: str) -> tuple[User, str]:
    user = db.session.scalars(select(User).where(User.login == login)).first()
    if user is None:
        raise NotFound(f"Демо-профиль «{login}» не найден")
    return user, issue_token(user)
