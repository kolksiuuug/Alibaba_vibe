"""Загрузка параметров скоринга из app/scoring/config.yaml."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path(__file__).with_name("config.yaml")


@lru_cache(maxsize=4)
def load_config(path: str | None = None) -> dict[str, Any]:
    """Конфиг кешируется и общий для всех вызовов: не изменяйте возвращённый словарь."""
    with open(path or CONFIG_PATH, encoding="utf-8") as config_file:
        config: dict[str, Any] = yaml.safe_load(config_file)
    return config
