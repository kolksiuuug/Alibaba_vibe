# Сторонние компоненты и лицензии

Все компоненты бесплатны и распространяются под открытыми лицензиями. Платных API, подписок, закрытых моделей и покупных данных в проекте нет. Точные версии и хеши зафиксированы в `requirements.txt`, `requirements-dev.txt`, `mocks/requirements.txt` и `frontend/package-lock.json`.

## Backend: образ `app` и `worker` (Python 3.12)

Прямые зависимости (`requirements.in`):

| Пакет | Версия | Лицензия | Назначение |
| --- | --- | --- | --- |
| Flask | 3.1.2 | BSD-3-Clause | веб-фреймворк |
| gunicorn | 23.0.0 | MIT | WSGI-сервер |
| Flask-SQLAlchemy | 3.1.1 | BSD-3-Clause | интеграция SQLAlchemy |
| SQLAlchemy | 2.0.32 | MIT | ORM |
| Flask-Migrate | 4.1.0 | MIT | миграции (Alembic) |
| psycopg2-binary | 2.9.9 | LGPL-3.0 с исключениями | драйвер PostgreSQL |
| flask-smorest | 0.47.0 | MIT | REST API, OpenAPI, Swagger UI |
| marshmallow | 3.26.2 | MIT | схемы и валидация |
| apispec | 6.6.1 | MIT | генерация OpenAPI |
| httpx | 0.27.0 | BSD-3-Clause | HTTP-клиент адаптеров |
| python-dotenv | 1.0.1 | BSD-3-Clause | загрузка `.env` |
| PyYAML | 6.0.2 | MIT | конфиг скоринга, экспорт OpenAPI в YAML |
| pytest | 8.3.3 | MIT | тесты |
| pytest-flask | 1.3.0 | MIT | фикстуры Flask для тестов |

Транзитивные зависимости: alembic (MIT), anyio (MIT), blinker (MIT), certifi (MPL-2.0), click (BSD-3-Clause), greenlet (MIT AND PSF-2.0), h11 (MIT), httpcore (BSD-3-Clause), idna (BSD-3-Clause), iniconfig (MIT), itsdangerous (BSD-3-Clause, подпись токенов демо-входа), Jinja2 (BSD-3-Clause), Mako (MIT), MarkupSafe (BSD-3-Clause), packaging (Apache-2.0 OR BSD-2-Clause), pluggy (MIT), sniffio (MIT OR Apache-2.0), typing_extensions (PSF-2.0), webargs (MIT), Werkzeug (BSD-3-Clause).

## Моки: образ `mocks`

Flask 3.1.2 (BSD-3-Clause) и gunicorn 23.0.0 (MIT) с теми же транзитивными зависимостями Flask.

## Инструменты разработки (в образы не попадают)

| Пакет | Лицензия | Назначение |
| --- | --- | --- |
| pip-tools 7.6.2 | BSD-3-Clause | `make lock`: сборка lock-файлов с хешами |
| ruff | MIT | линтер и форматтер Python |
| mypy | MIT | проверка типов |
| pip-audit | Apache-2.0 | аудит уязвимостей зависимостей |
| types-PyYAML | Apache-2.0 | типы для mypy |

## Frontend (npm)

| Пакет | Версия | Лицензия | Где используется |
| --- | --- | --- | --- |
| react, react-dom | 18.3.1 | MIT | SPA в браузере |
| react-router-dom | 6.30.6 | MIT | маршрутизация SPA |
| @tanstack/react-query | 5.104.5 | MIT | запросы к API, опрос статуса |
| swagger-ui-dist | 5.34.0 | Apache-2.0 | ассеты Swagger UI на `/api/docs`, отдаются nginx без внешних CDN |
| vite | 8.3.5 | MIT | сборка (только стадия сборки образа) |
| @vitejs/plugin-react | 6.1.2 | MIT | сборка |
| typescript | 5.9.3 | Apache-2.0 | проверка типов |
| openapi-typescript | 7.13.0 | MIT | генерация типов API из `docs/openapi.yaml` |
| prettier | 3.9.10 | MIT | форматирование |
| @types/react, @types/react-dom | 18.3.x | MIT | типы |

Транзитивные пакеты сборки: MIT (большинство), MPL-2.0 (lightningcss — минификация CSS в Vite), Apache-2.0 (detect-libc, yaml-ast-parser, @scarf/scarf), ISC (minimatch, picocolors, yargs-parser), BSD-3-Clause (source-map-js), Python-2.0 (argparse), MIT OR CC0-1.0 (type-fest). Пакет `@scarf/scarf` приходит вместе с swagger-ui-dist и собирает телеметрию установки; она отключена (`scarfSettings` в `package.json` и `SCARF_ANALYTICS=false` в `nginx/Dockerfile`).

## Docker-образы

| Образ | Лицензия | Назначение |
| --- | --- | --- |
| `python:3.12.15-slim-bookworm` | PSF-2.0, пакеты Debian под своими лицензиями | база для `app`, `worker`, `mocks` |
| `postgres:16.15-alpine3.24` | PostgreSQL License | БД |
| `nginx:1.26.3-alpine3.20` | BSD-2-Clause | входная точка, SPA, прокси `/api` |
| `node:22.23.4-alpine3.24` | MIT | только стадия сборки фронтенда |

## Смоделированные интеграции

Внешние системы не вызываются. Вместо них работает контейнер `mocks` с синтетическими ответами:

| Система | Что моделируется |
| --- | --- |
| Бюро кредитных историй (БКИ) | кредитный отчёт: действующие кредиты, просрочки |
| ЕГРЮЛ / ЕГРИП | статус компании или ИП, дата регистрации |
| ФНС «Прозрачный бизнес» | налоговая задолженность, сведения о деятельности |
| Электронная подпись (ЭП) | подписание кодом в интерфейсе (симуляция) |
| АБС банка | выдача кредита (симуляция) |

## Данные и модели

- Демо-данные (`seed/*.json`) созданы командой вручную и полностью синтетические: названия компаний, ФИО и ИНН вымышлены, ИНН и ОГРН используют несуществующий код региона `00`.
- Модели машинного обучения и LLM в основном сценарии не используются. LLM-ассистент необязателен и по умолчанию выключен (`LLM_ENABLED=false`).
