"""CLI-команды: flask seed, flask pipeline-worker."""

from pathlib import Path

import click
from flask import Flask, current_app
from flask.cli import with_appcontext


@click.command("seed")
@click.option("--reset", is_flag=True, help="Очистить все таблицы и загрузить демо-данные заново.")
@click.option("--if-empty", is_flag=True, help="Загрузить демо-данные, только если БД пустая.")
@click.option(
    "--generate", "generate", type=int, default=0, help="Добавить N сгенерированных компаний."
)
@click.option("--gen-seed", type=int, default=42, help="Seed генератора (данные воспроизводимы).")
@with_appcontext
def seed_command(reset: bool, if_empty: bool, generate: int, gen_seed: int) -> None:
    """Загрузить синтетические демо-данные из каталога seed/ (и сгенерированные компании)."""
    from app.services.seed import load_extra_companies, load_seed, seed_is_loaded

    if reset or not seed_is_loaded():
        summary = load_seed(current_app.config["SEED_DIR"], reset=reset)
        click.echo(f"seed: loaded {summary}")
    elif not generate:
        hint = "" if if_empty else " (use --reset to reload)"
        click.echo(f"seed: data already present, skipping{hint}")

    if generate > 0:
        from seed.generate import generate_companies

        added = load_extra_companies(generate_companies(generate, gen_seed))
        click.echo(f"seed: added {added} generated companies (seed {gen_seed})")


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
