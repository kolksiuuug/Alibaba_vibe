# Обёртки над docker compose (CLAUDE.md, раздел 14).
# Без make (например, на Windows) выполняйте команды из рецептов как есть.
COMPOSE ?= docker compose
PY_IMAGE := python:3.12.15-slim-bookworm
PIP_TOOLS := pip-tools==7.6.2
PIP_COMPILE := pip-compile -q --generate-hashes --strip-extras --allow-unsafe
PY_DEV := pip install -q --root-user-action=ignore --require-hashes --no-deps -r requirements.txt -r requirements-dev.txt
PY_SOURCES := app tests mocks postman wsgi.py

.PHONY: up down logs test e2e seed openapi lock lint audit llm

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f

test:
	$(COMPOSE) run --rm --build app pytest

# UI-сценарии против поднятого стека (make up). Нужен браузер: npx playwright install chromium
# или установленный Edge/Chrome: E2E_BROWSER_CHANNEL=msedge make e2e
e2e:
	cd frontend && npm ci && npx playwright test

seed:
	$(COMPOSE) run --rm app flask seed --reset

openapi:
	$(COMPOSE) run --rm --build --no-deps -v "$(CURDIR)/docs:/app/docs" app flask export-openapi docs/openapi.yaml
	cd frontend && npm run gen:api

lock:
	docker run --rm -v "$(CURDIR):/w" -w /w $(PY_IMAGE) sh -c "\
		pip install -q --root-user-action=ignore $(PIP_TOOLS) && \
		$(PIP_COMPILE) -o requirements.txt requirements.in && \
		$(PIP_COMPILE) -o requirements-dev.txt requirements-dev.in && \
		$(PIP_COMPILE) -o mocks/requirements.txt mocks/requirements.in"

# ruff + mypy в контейнере python:3.12; eslint + tsc + prettier для фронтенда
lint:
	docker run --rm -v "$(CURDIR):/w" -w /w $(PY_IMAGE) sh -c "$(PY_DEV) && \
		ruff check $(PY_SOURCES) && ruff format --check $(PY_SOURCES) && mypy app mocks wsgi.py"
	cd frontend && npm ci && npm run lint && npx prettier --check src e2e

# Уязвимости зависимостей: pip-audit по lock-файлам и npm audit
audit:
	docker run --rm -v "$(CURDIR):/w" -w /w $(PY_IMAGE) sh -c "$(PY_DEV) && \
		pip-audit --disable-pip --no-deps -r requirements.txt -r mocks/requirements.txt"
	cd frontend && npm audit --audit-level=high
