# Моки внешних систем (БКИ, ЕГРЮЛ/ЕГРИП, ФНС, ЭП, АБС)
FROM python:3.12.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /mocks

RUN groupadd --system mocks && useradd --system --gid mocks --home-dir /mocks mocks

COPY requirements.txt .
RUN pip install --require-hashes --no-deps -r requirements.txt

COPY . .

USER mocks
EXPOSE 8001

CMD ["gunicorn", "--bind", "0.0.0.0:8001", "--workers", "1", "--threads", "4", "--timeout", "30", "app:app"]
