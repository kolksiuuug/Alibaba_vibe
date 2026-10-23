"""CLI-команды: flask seed, flask pipeline-worker."""

from pathlib import Path

import click
from flask import Flask, current_app
from flask.cli import with_appcontext


@click.command("seed")
@click.option("--reset", is_flag=True, help="Очистить все таблицы и загрузить демо-данные заново.")
@click.option("--if-empty", is_flag=True, help="Загрузить демо-данные, только если БД пустая.")
@with_appcontext
def seed_command(reset: bool, if_empty: bool) -> None:
    """Загрузить синтетические демо-данные из каталога seed/."""
    from app.services.seed import load_seed, seed_is_loaded

    if if_empty and not reset and seed_is_loaded():
        click.echo("seed: data already present, skipping")
        return
    summary = load_seed(current_app.config["SEED_DIR"], reset=reset)
    click.echo(f"seed: loaded {summary}")


@click.command("pipeline-worker")
@click.option("--once", is_flag=True, help="Один проход цикла и выход (для отладки).")
@with_appcontext
def pipeline_worker_command(once: bool) -> None:
    """Запустить воркер конвейера заявок."""
    from app.worker import run_worker

    run_worker(once=once)


@click.command("export-openapi")
@click.argument("path", default="docs/openapi.yaml")
@with_appcontext
def export_openapi_command(path: str) -> None:
    """Записать OpenAPI в YAML: как flask openapi write, но кириллица без экранирования."""
    import yaml

    from app.extensions import api

    raw = api.spec.to_dict()
    head = ("openapi", "info", "tags", "security", "paths", "components")
    ordered = {key: raw[key] for key in head if key in raw} | raw
    spec = yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False)
    Path(path).write_text(spec, encoding="utf-8")
    click.echo(f"openapi: written to {path}")


def register_cli(app: Flask) -> None:
    app.cli.add_command(seed_command)
    app.cli.add_command(pipeline_worker_command)
    app.cli.add_command(export_openapi_command)
