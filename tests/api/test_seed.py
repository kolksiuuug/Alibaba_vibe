from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, select

from app.models import Company, Product, User
from app.services.seed import load_seed, seed_is_loaded

DEMO_LOGINS = {"analyst", "demo-approve", "demo-counter", "demo-info", "demo-manual", "demo-reject"}


def test_seed_loads_demo_profiles(app: Flask, db: SQLAlchemy) -> None:
    assert not seed_is_loaded()
    summary = load_seed(app.config["SEED_DIR"])
    assert summary == {"products": 4, "companies": 5, "users": 6}
    assert set(db.session.scalars(select(User.login))) == DEMO_LOGINS


def test_seed_reset_is_repeatable(app: Flask, db: SQLAlchemy) -> None:
    load_seed(app.config["SEED_DIR"])
    load_seed(app.config["SEED_DIR"], reset=True)
    assert db.session.scalar(select(func.count(Company.id))) == 5
    assert db.session.scalar(select(func.count(Product.id))) == 4


def test_demo_companies_use_synthetic_inn(app: Flask, db: SQLAlchemy) -> None:
    load_seed(app.config["SEED_DIR"])
    for company in db.session.scalars(select(Company)):
        # Код региона 00 не существует: ИНН не совпадёт с реальной организацией
        assert company.inn.startswith("00")
        assert len(company.monthly_turnover) == 12


def test_seed_cli_if_empty_runs_once(app: Flask, db: SQLAlchemy) -> None:
    runner = app.test_cli_runner()
    first = runner.invoke(args=["seed", "--if-empty"])
    second = runner.invoke(args=["seed", "--if-empty"])
    assert "loaded" in first.output
    assert "skipping" in second.output


def test_generator_is_deterministic_and_synthetic() -> None:
    from seed.generate import generate_companies

    first, second = generate_companies(10, 42), generate_companies(10, 42)

    assert first == second
    assert len({item["company"]["inn"] for item in first}) == 10
    assert all(item["company"]["inn"].startswith("00") for item in first)
    assert all(len(item["company"]["monthly_turnover"]) == 12 for item in first)
    assert generate_companies(5, 7) != generate_companies(5, 42)


def test_seed_cli_generate_adds_companies_once(app: Flask, db: SQLAlchemy) -> None:
    runner = app.test_cli_runner()
    runner.invoke(args=["seed"])

    added = runner.invoke(args=["seed", "--generate", "5", "--gen-seed", "1"])
    repeated = runner.invoke(args=["seed", "--generate", "5", "--gen-seed", "1"])

    assert "added 5" in added.output
    assert "added 0" in repeated.output
    assert db.session.scalar(select(func.count(Company.id))) == 10
