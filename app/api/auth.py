"""Аутентификация API: Bearer-токен демо-входа и проверка роли."""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from flask import g, request
from flask_smorest import abort

from app.models import User
from app.services.auth import user_from_token

F = TypeVar("F", bound=Callable[..., Any])


def current_user() -> User:
    return cast(User, g.current_user)


def require_role(*roles: str) -> Callable[[F], F]:
    """Пустой список ролей — нужен только вход. Иначе 403 для других ролей."""

    def decorator(view: F) -> F:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            scheme, _, token = request.headers.get("Authorization", "").partition(" ")
            if scheme.lower() != "bearer" or not token.strip():
                abort(401, message="Войдите в демо-профиль")
            user = user_from_token(token.strip())
            if user is None:
                abort(401, message="Сессия истекла, войдите снова")
            if roles and user.role not in roles:
                abort(403, message="Раздел недоступен для этой роли")
            g.current_user = user
            return view(*args, **kwargs)

        return cast(F, wrapper)

    return decorator
