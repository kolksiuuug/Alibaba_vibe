# API

REST API под префиксом `/api/v1`. Формат — JSON, поля в `snake_case`. Реализация на flask-smorest, валидация и сериализация через схемы Marshmallow из `app/api/schemas/`.

- **Swagger UI** запущенного приложения: http://localhost:8080/api/docs
- **Схема OpenAPI**: `/api/openapi.json` в приложении и файл [`docs/openapi.yaml`](openapi.yaml). Обновляется командой `make openapi`, она же перегенерирует типы фронтенда `frontend/src/api/schema.d.ts`.
- **Postman-коллекция** пяти сценариев: [`postman/credit-cabinet.postman_collection.json`](../postman/credit-cabinet.postman_collection.json). Пересобирается командой `python postman/build_collection.py`.

## Аутентификация

Вход в демо-профиль выполняется без паролей и кодов:

```http
POST /api/v1/auth/demo-login
{"login": "demo-approve"}

200 {"token": "<токен>", "user": {...}}
```

Дальше токен передаётся в каждом запросе: `Authorization: Bearer <токен>`. Токен подписан `itsdangerous` (ключ `SECRET_KEY`), содержит `user_id` и `role` и живёт `TOKEN_MAX_AGE_S` секунд (по умолчанию сутки). Список профилей для экрана входа отдаёт `GET /api/v1/auth/demo-profiles` без токена.

| Ситуация | Ответ |
| --- | --- |
| Нет токена или токен поддельный | 401 |
| Эндпоинт для другой роли (клиент → аналитик и наоборот) | 403 |
| Заявка другой компании | 403 |

## Ошибки

Все ошибки возвращаются в формате `application/problem+json` (RFC 7807):

```json
{
  "type": "about:blank",
  "title": "Действие недоступно в текущем статусе",
  "status": 409,
  "detail": "Переход declined -> accepted недоступен для client",
  "code": "invalid_transition",
  "instance": "/api/v1/applications/7/offer/accept",
  "request_id": "6f1c…"
}
```

| HTTP | `code` | Когда |
| --- | --- | --- |
| 401 | — | нет токена или он недействителен |
| 403 | `access_denied` | чужая заявка или чужое уведомление |
| 404 | `not_found` | заявка, уведомление или демо-профиль не найдены |
| 409 | `invalid_transition` | действие недоступно в текущем статусе (`docs/state-machine.md`) |
| 422 | `validation_failed` | ошибки в данных; поле `errors` содержит ошибки по полям |
| 422 | `comment_required` | решение аналитика без комментария |
| 503 | `service_unavailable` | недоступен сервис подписи; статус заявки не меняется |

`request_id` совпадает с заголовком ответа `X-Request-ID` и с полем `request_id` в JSON-логах.

## Идемпотентность

Повтор действия, когда заявка уже в целевом статусе, возвращает 200 с текущим состоянием и ничего не меняет. Так работают повторный `submit`, `offer/accept`, `sign/confirm` после подписи, повторное решение аналитика. Повторная отправка не создаёт вторую задачу конвейера: в очереди может ждать только одна задача каждого вида на заявку (частичный уникальный индекс `uq_pipeline_jobs_queued`).

## Эндпоинты

### Вход и профиль

| Метод | Путь | Роль | Назначение |
| --- | --- | --- | --- |
| GET | `/api/v1/auth/demo-profiles` | — | демо-профили: пять компаний и аналитик |
| POST | `/api/v1/auth/demo-login` | — | вход, выдача токена |
| GET | `/api/v1/me` | любая | текущий пользователь и его компания |

### Продукты

| Метод | Путь | Роль | Назначение |
| --- | --- | --- | --- |
| GET | `/api/v1/products` | любая | каталог продуктов со ставкой «от» |
| POST | `/api/v1/products/recommend` | любая | 1–3 продукта под цель, сумму и срок с предварительной ставкой и платежом |
| POST | `/api/v1/calculator` | любая | аннуитетный платёж и график; ставка `annual_rate` или ставка «от» продукта `product_code` |

### Заявки клиента

| Метод | Путь | Переход | Назначение |
| --- | --- | --- | --- |
| GET | `/api/v1/applications` | — | заявки компании |
| POST | `/api/v1/applications` | → `draft` | черновик: продукт, сумма, срок, цель, анкета |
| GET | `/api/v1/applications/{id}` | — | карточка: статус, этапы конвейера, полнота анкеты, предложение с графиком, дозапрос, 3–5 факторов решения |
| PATCH | `/api/v1/applications/{id}` | — | изменить черновик |
| POST | `/api/v1/applications/{id}/submit` | `draft → submitted` | отправить; в той же транзакции создаётся задача конвейера |
| POST | `/api/v1/applications/{id}/cancel` | `draft`/`info_requested → cancelled` | отменить |
| POST | `/api/v1/applications/{id}/info-response` | `info_requested → checking` | ответить на дозапрос (`answers` — поля анкеты, `comment` — свободный ответ) |
| POST | `/api/v1/applications/{id}/offer/accept` | `offer → accepted` | принять предложение |
| POST | `/api/v1/applications/{id}/offer/decline` | `offer → declined` | отклонить предложение |
| POST | `/api/v1/applications/{id}/sign/request-code` | — | получить код подписи; код возвращается в ответе и показывается в интерфейсе (симуляция, SMS нет) |
| POST | `/api/v1/applications/{id}/sign/confirm` | `accepted → signed` | подписать кодом через мок ЭП; затем воркер выдаёт кредит (`signed → issued`) |
| GET | `/api/v1/applications/{id}/events` | — | таймлайн переходов статуса |

Анкета (`form_data`) состоит из известных полей. Обязательные для отправки: `contact_name`, `purpose_description`. Поля продукта (`collateral_description`, `collateral_value`, `equipment_supplier`, `guarantor_full_name`, `guarantor_inn`) можно заполнить сразу или позже, по дозапросу банка. Неизвестные поля дают 422.

### Уведомления

| Метод | Путь | Назначение |
| --- | --- | --- |
| GET | `/api/v1/notifications` | последние 100 уведомлений и число непрочитанных |
| POST | `/api/v1/notifications/{id}/read` | отметить прочитанным |

### Аналитик

| Метод | Путь | Назначение |
| --- | --- | --- |
| GET | `/api/v1/analyst/applications?status=` | очередь с фильтром по статусу, без черновиков |
| GET | `/api/v1/analyst/applications/{id}` | карточка: данные компании, результаты проверок, все факторы скоринга с баллами, стоп-факторы, решения движка и аналитика, дозапросы, журнал с комментариями |
| POST | `/api/v1/analyst/applications/{id}/decision` | решение по ручному рассмотрению |

Тело решения: `action` — `approve` | `change_terms` | `request_info` | `reject`; `comment` обязателен. Для `change_terms` нужны `amount` и `term_months`, для `request_info` можно указать `fields` (коды полей анкеты). `approve` берёт условия из рекомендации движка.

### Служебные

| Метод | Путь | Назначение |
| --- | --- | --- |
| GET | `/api/health` | процесс жив |
| GET | `/api/ready` | база данных доступна (healthcheck `app`) |

## Моки внешних систем

Контейнер `mocks` (`http://mocks:8001` внутри сети, `http://localhost:8001` снаружи). Приложение ходит в него только через адаптеры `app/adapters/`.

| Метод | Путь | Система |
| --- | --- | --- |
| GET | `/bki/report?inn=` | бюро кредитных историй |
| GET | `/egrul/{inn}` | ЕГРЮЛ / ЕГРИП |
| GET | `/fns/transparent-business/{inn}` | ФНС «Прозрачный бизнес» |
| POST | `/esign/sign` | электронная подпись (симуляция) |
| POST | `/abs/disbursements` | выдача через АБС (симуляция, идемпотентна по `idempotency_key`) |
| GET | `/admin/fail?service=bki[&enabled=false]` | включить или выключить сбой сервиса для демонстрации fallback |

Подробности и упрощения — в [`docs/assumptions.md`](assumptions.md).
