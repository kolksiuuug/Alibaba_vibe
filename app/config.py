"""Конфигурация из переменных окружения: DevConfig, TestConfig, ProdConfig."""

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

DEFAULT_SECRET_KEY = "demo-only-secret-change-me"
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


class BaseConfig:
    TESTING = False
    SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://credit:credit@localhost:5432/credit"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # OpenAPI и Swagger UI. Ассеты Swagger UI отдаёт nginx, внешние CDN не нужны.
    API_TITLE = "Умный кредитный кабинет предпринимателя"
    API_VERSION = "1.0.0"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/api"
    OPENAPI_JSON_PATH = "openapi.json"
    OPENAPI_SWAGGER_UI_PATH = "/docs"
    OPENAPI_SWAGGER_UI_URL = os.getenv("SWAGGER_UI_URL", "/swagger-ui/")
    # Все операции требуют Bearer-токен, кроме помеченных security=[] (демо-вход, health)
    API_SPEC_OPTIONS: dict[str, Any] = {"security": [{"bearerAuth": []}]}

    # Время жизни токена демо-входа, с
    TOKEN_MAX_AGE_S = env_int("TOKEN_MAX_AGE_S", 86400)

    SEED_DIR = os.getenv("SEED_DIR", os.path.join(_PROJECT_ROOT, "seed"))

    # Кредитные параметры: ключевая ставка ЦБ, % годовых
    KEY_RATE = env_float("KEY_RATE", 14.0)

    PIPELINE_STEP_DELAY_MS = env_int("PIPELINE_STEP_DELAY_MS", 700)
    PIPELINE_HEARTBEAT_TIMEOUT_S = env_int("PIPELINE_HEARTBEAT_TIMEOUT_S", 60)
    PIPELINE_MAX_ATTEMPTS = env_int("PIPELINE_MAX_ATTEMPTS", 3)
    PIPELINE_RETRY_BACKOFF_S = env_int("PIPELINE_RETRY_BACKOFF_S", 5)
    WORKER_POLL_INTERVAL_MS = env_int("WORKER_POLL_INTERVAL_MS", 1000)
    WORKER_HEARTBEAT_FILE = os.getenv("WORKER_HEARTBEAT_FILE", "/tmp/worker-heartbeat")

    # Внешние системы — только моки (CLAUDE.md, раздел 1.3)
    MOCKS_BASE_URL = os.getenv("MOCKS_BASE_URL", "http://mocks:8001")
    ADAPTER_TIMEOUT_S = env_float("ADAPTER_TIMEOUT_S", 3.0)
    ADAPTER_RETRIES = env_int("ADAPTER_RETRIES", 2)
    LLM_ENABLED = env_bool("LLM_ENABLED", False)


class DevConfig(BaseConfig):
    LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")


class TestConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL", "postgresql+psycopg2://credit:credit@localhost:5432/credit_test"
    )
    PIPELINE_STEP_DELAY_MS = 0
    LOG_LEVEL = "WARNING"


class ProdConfig(BaseConfig):
    pass


CONFIGS: dict[str, type[BaseConfig]] = {"dev": DevConfig, "test": TestConfig, "prod": ProdConfig}


def get_config(name: str | None = None) -> type[BaseConfig]:
    key = (name or os.environ.get("APP_CONFIG") or "dev").strip().lower()
    try:
        return CONFIGS[key]
    except KeyError:
        raise ValueError(f"Unknown APP_CONFIG={key!r}, expected one of {sorted(CONFIGS)}") from None
