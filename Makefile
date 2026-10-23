# Обёртки над docker compose (CLAUDE.md, раздел 14).
# Без make (например, на Windows) выполняйте команды из рецептов как есть.
COMPOSE ?= docker compose
PY_IMAGE := python:3.12.15-slim-bookworm
PIP_TOOLS := pip-tools==7.6.2
PIP_COMPILE := pip-compile -q --generate-hashes --strip-extras --allow-unsafe

.PHONY: up down logs test seed openapi lock

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f

test:
	$(COMPOSE) run --rm --build app pytest

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
