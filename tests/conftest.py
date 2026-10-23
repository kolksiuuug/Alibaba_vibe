"""Общие фикстуры: приложение с TestConfig и отдельная тестовая БД PostgreSQL."""

from collections.abc import Iterator

import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app import create_app
from app.extensions import db as _db


def _ensure_database(url: str) -> None:
    target = make_url(url)
    admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": target.database},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    finally:
        admin.dispose()


@pytest.fixture(scope="session")
def app() -> Iterator[Flask]:
    app = create_app("test")
    _ensure_database(app.config["SQLALCHEMY_DATABASE_URI"])
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app: Flask) -> Iterator[SQLAlchemy]:
    """БД для теста; после теста все таблицы очищаются."""
    yield _db
    _db.session.rollback()
    tables = ", ".join(f'"{table.name}"' for table in _db.metadata.sorted_tables)
    _db.session.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    _db.session.commit()
