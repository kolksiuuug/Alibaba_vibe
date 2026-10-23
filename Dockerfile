# Образ backend: сервисы app (Gunicorn) и worker (flask pipeline-worker)
FROM python:3.12.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_APP=wsgi.py

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY requirements.txt .
RUN pip install --require-hashes --no-deps -r requirements.txt

COPY . .
# Страховка от CRLF, если репозиторий скачан архивом на Windows
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

USER app
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["serve"]
