#!/bin/sh
# serve: миграции -> сид (если БД пустая) -> Gunicorn.
# Любая другая команда выполняется как есть: flask pipeline-worker, pytest, flask seed --reset.
set -eu

if [ "${1:-serve}" = "serve" ]; then
    flask db upgrade
    flask seed --if-empty
    exec gunicorn \
        --bind 0.0.0.0:8000 \
        --workers "${GUNICORN_WORKERS:-2}" \
        --threads "${GUNICORN_THREADS:-4}" \
        --timeout "${GUNICORN_TIMEOUT:-30}" \
        wsgi:app
fi

exec "$@"
