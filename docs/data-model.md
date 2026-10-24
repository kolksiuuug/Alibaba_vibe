# Модель данных

PostgreSQL 16, схема создаётся миграциями Alembic (`migrations/versions/`), ORM — SQLAlchemy 2 (`app/models/`). Все данные синтетические.

```mermaid
erDiagram
    COMPANY ||--o{ USER : "клиенты компании"
    COMPANY ||--o{ APPLICATION : "подаёт"
    USER ||--o{ APPLICATION : "создал"
    PRODUCT ||--o{ APPLICATION : "по продукту"
    APPLICATION ||--o{ AUDIT_EVENT : "журнал переходов"
    APPLICATION ||--o{ NOTIFICATION : "уведомления"
    USER ||--o{ NOTIFICATION : "получатель"
    APPLICATION ||--o{ PIPELINE_JOB : "задачи конвейера"
    APPLICATION ||--o{ CHECK_RESULT : "проверки"
    APPLICATION ||--o{ SCORING_RESULT : "скоринг"
    APPLICATION ||--o{ DECISION : "решения"
    APPLICATION ||--o{ INFO_REQUEST : "дозапросы"
    APPLICATION ||--o| SIGNATURE : "подпись"
    APPLICATION ||--o| DISBURSEMENT : "выдача"

    COMPANY {
        int id PK
        string name
        string kind "ip | llc"
        string inn UK "синтетический, регион 00"
        string ogrn UK
        string okved
        date registered_at
        jsonb monthly_turnover "12 месяцев оборотов"
    }
    USER {
        int id PK
        string login UK "demo-approve, analyst..."
        string role "client | analyst"
        int company_id FK "только у клиента"
        string demo_hint
    }
    PRODUCT {
        int id PK
        string code UK
        jsonb purposes
        bigint min_amount
        bigint max_amount
        int min_term_months
        int max_term_months
        numeric rate_spread "к ключевой ставке"
        bool requires_collateral
        bool requires_guarantee
        jsonb required_fields
    }
    APPLICATION {
        int id PK
        int company_id FK
        int created_by_id FK
        int product_id FK
        bigint amount
        int term_months
        string purpose
        jsonb form_data "анкета"
        string status "12 кодов, только через transitions"
        jsonb pipeline_steps "этапы для таймлайна"
        timestamptz status_changed_at
        timestamptz submitted_at
    }
    AUDIT_EVENT {
        int id PK
        int application_id FK
        string from_status "NULL — создание черновика"
        string to_status
        string actor "client | analyst | system"
        int actor_user_id FK
        string reason
        text comment
        timestamptz at
    }
    NOTIFICATION {
        int id PK
        int user_id FK
        int application_id FK
        string kind
        string title
        text body
        bool is_read
    }
    PIPELINE_JOB {
        int id PK
        int application_id FK
        string kind "scoring | disbursement"
        string state "queued | running | done | failed"
        int attempts
        timestamptz run_after
        timestamptz heartbeat_at
        text last_error
    }
    CHECK_RESULT {
        int id PK
        int application_id FK
        string source "bki | egrul | fns"
        string status "ok | failed"
        jsonb response
        text error
    }
    SCORING_RESULT {
        int id PK
        int application_id FK
        int score
        string grade "A-E"
        jsonb factors "code, value, points, explanation_ru"
        jsonb client_factors "3-5 кодов для клиента"
        jsonb stop_factors
    }
    DECISION {
        int id PK
        int application_id FK
        string outcome "offer | manual_review | info_requested | rejected"
        string decided_by "engine | analyst"
        int analyst_id FK
        bool is_counter
        bigint amount
        int term_months
        numeric rate
        numeric monthly_payment
        jsonb reasons
        text comment
    }
    INFO_REQUEST {
        int id PK
        int application_id FK
        string requested_by "engine | analyst"
        jsonb fields
        text message
        jsonb response
        timestamptz responded_at
    }
    SIGNATURE {
        int id PK
        int application_id FK "unique"
        string status "pending | signed"
        string code_hash "код только в виде хеша"
        int attempts
        timestamptz expires_at
        string document_hash
        string signature_reference
    }
    DISBURSEMENT {
        int id PK
        int application_id FK "unique"
        bigint amount
        string abs_reference
        string status
    }
```

## Ключевые ограничения

| Таблица | Ограничение | Зачем |
| --- | --- | --- |
| `applications` | `CHECK status IN (12 кодов)`, `amount > 0`, `term_months > 0` | только известные статусы |
| `applications.status` | у ORM-модели нет сеттера | статус меняется только через `services/transitions.py` |
| `users` | `CHECK (role = 'client') = (company_id IS NOT NULL)` | у клиента всегда есть компания, у аналитика нет |
| `pipeline_jobs` | частичный уникальный индекс `(application_id, kind) WHERE state = 'queued'` | повторная отправка не создаёт вторую задачу |
| `pipeline_jobs` | индекс `(state, run_after)` | быстрый выбор следующей задачи воркером |
| `check_results` | `UNIQUE (application_id, source)` | одна строка на источник, результаты переиспользуются |
| `signatures`, `disbursements` | `UNIQUE (application_id)` | одна подпись и одна выдача на заявку |
| `audit_events.actor` | `CHECK actor IN ('client', 'analyst', 'system')` | журнал только с известными акторами |

Актуальное решение по заявке — последняя строка `decisions` по `id`. Рекомендация движка для аналитика — последнее решение с `decided_by = 'engine'` и заполненной суммой.
