# 🚀 Система контроля заданий на выпуск продукции

Расширенная веб-платформа для управления производственными сменами, продукцией и асинхронными задачами.

---

## 📖 Описание

Система позволяет:
- Создавать и управлять **партиями** (сменными заданиями)
- Отслеживать **продукцию** в рамках партии
- **Аггрегировать** продукцию (вручную или массово)
- Генерировать **Excel/PDF отчёты** по партиям
- Импортировать/экспортировать данные через **CSV/Excel**
- Интегрироваться с внешними системами через **Webhooks**
- Кэшировать статистику в **Redis**
- Хранить файлы в **MinIO** (S3-совместимое хранилище)

---

## 🛠 Технологический стек

| Компонент           | Технология                             |
|---------------------|----------------------------------------|
| **Backend**         | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| **База данных**     | PostgreSQL 16, Alembic                 |
| **Асинхронные задачи** | Celery 5.3+, RabbitMQ, Redis         |
| **Кэширование**     | Redis 7+                               |
| **Файловое хранилище** | MinIO (S3-совместимое)              |
| **Контейнеризация** | Docker, Docker Compose                 |
| **Линтинг/форматирование** | Ruff (pre-commit)              |

---

## 📦 Установка и запуск

### 1. Клонировать репозиторий

```bash
git clone git@github.com:bagkir/product-control.git
cd product-control
```

### 2. Переменные окружения

## 🔧 Переменные окружения

Создайте файл `.env` в корне проекта на основе `.env.example`.  
Обязательные переменные:

| Переменная               | Описание                                       | Пример значения                                      |
|--------------------------|------------------------------------------------|------------------------------------------------------|
| `POSTGRES_DB`            | Имя базы данных                                | `product-control`                                    |
| `POSTGRES_USER`          | Пользователь PostgreSQL                        | `postgres`                                           |
| `POSTGRES_PASSWORD`      | Пароль PostgreSQL                              | `postgres`                                           |
| `POSTGRES_HOST`          | Хост PostgreSQL (имя сервиса в Docker)         | `db`                                                 |
| `POSTGRES_PORT`          | Внутренний порт PostgreSQL (обычно 5432)       | `5432`                                               |
| `DATABASE_URL`           | URL для подключения (asyncpg)                  | `postgresql+asyncpg://postgres:postgres@db:5432/product-control` |
| `TEST_DATABASE_URL`      | URL для тестовой БД (отдельная БД)             | `postgresql+asyncpg://postgres:postgres@db:5432/product_control_test` |
| `CELERY_BROKER_URL`      | Брокер сообщений (RabbitMQ)                    | `amqp://admin:admin@rabbitmq:5672//`                |
| `CELERY_RESULT_BACKEND`  | Бэкенд для результатов Celery (Redis)          | `redis://redis:6379/1`                               |
| `REDIS_URL`              | URL для кэша (отдельная БД Redis)              | `redis://redis:6379/0`                               |
| `RABBITMQ_USER`          | Пользователь RabbitMQ                          | `admin`                                              |
| `RABBITMQ_PASSWORD`      | Пароль RabbitMQ                                | `admin`                                              |
| `MINIO_ENDPOINT`         | Адрес MinIO (внутри Docker)                    | `minio:9000`                                         |
| `MINIO_ACCESS_KEY`       | Access Key MinIO                               | `minioadmin`                                         |
| `MINIO_SECRET_KEY`       | Secret Key MinIO                               | `minioadmin`                                         |
| `MINIO_SECURE`           | Использовать HTTPS? (false для dev)            | `false`                                              |
| `WEB_PORT`               | Порт, на котором работает API (внешний)        | `8000`                                               |
| `ENVIRONMENT`            | Окружение (`development`, `production`)        | `development`                                        |
| `DEBUG`                  | Режим отладки (`true`/`false`)                 | `true`                                               |
| `API_V1_PREFIX`          | Префикс для API v1                             | `/api/v1`                                            |
| `LOG_LEVEL`              | Уровень логирования                            | `INFO`                                               |
| `API_KEY_HEADER`         | Заголовок для API-ключа                        | `X-API-Key`                                          |
| `API_KEY`                | Значение API-ключа (для защиты эндпоинтов)     | `api_key1234567890` (замените на свой)                |

> **Примечание:** Для тестов используется отдельная база данных `product_control_test` – она создаётся автоматически при запуске тестов (если не существует).

### 3. Запуск через Docker Compose

```bash
docker-compose up -d --build
```

Сервисы будут доступны:

| Сервис      | URL / порт                     |
|-------------|--------------------------------|
| **API**     | http://localhost:8000          |
| **Swagger** | http://localhost:8000/docs     |
| **Flower**  | http://localhost:5555          |
| **MinIO**   | http://localhost:9001 (консоль)|
| **RabbitMQ**| http://localhost:15672         |

### 4. Применение миграций (автоматически при старте)

Миграции применяются через `alembic upgrade head` при запуске контейнера `api`.

---

## 📊 Основные модели данных

### Batch (Партия)
- `id`, `batch_number`, `batch_date`, `is_closed`, `closed_at`
- `task_description`, `shift`, `team`
- `work_center_id` (FK → WorkCenter)
- `nomenclature`, `ekn_code`
- `shift_start`, `shift_end`

### Product (Продукция)
- `id`, `unique_code` (уникальный)
- `batch_id` (FK → Batch)
- `is_aggregated`, `aggregated_at`

### WorkCenter (Рабочий центр)
- `id`, `identifier` (уникальный), `name`

### WebhookSubscription
- `url`, `events` (массив), `secret_key`, `is_active`, `retry_count`, `timeout`

### WebhookDelivery
- `subscription_id`, `event_type`, `payload`, `status`, `attempts`, `response_status`, `error_message`

---

## 🔌 API Endpoints (основные)

Все эндпоинты имеют префикс `/api/v1`.

### Партии
| Метод | Путь                           | Описание                        |
|-------|--------------------------------|---------------------------------|
| POST  | `/batches`                     | Создать партию(и)               |
| GET   | `/batches/{id}`                | Получить партию с продукцией    |
| PATCH | `/batches/{id}`                | Обновить партию (закрыть/открыть)|
| GET   | `/batches`                     | Список с фильтрацией            |
| POST  | `/batches/import`              | Импорт из файла (асинхронно)    |
| POST  | `/batches/export`              | Экспорт в файл (асинхронно)     |

### Продукция
| Метод | Путь                           | Описание                        |
|-------|--------------------------------|---------------------------------|
| POST  | `/products`                    | Добавить продукцию              |
| POST  | `/batches/{id}/aggregate`      | Аггрегация одной продукции      |
| POST  | `/batches/{id}/aggregate-async`| Массовая аггрегация (асинхронно)|

### Отчёты
| Метод | Путь                           | Описание                        |
|-------|--------------------------------|---------------------------------|
| POST  | `/batches/{id}/reports`        | Сгенерировать отчёт (Excel/PDF) |

### Webhooks
| Метод | Путь                           | Описание                        |
|-------|--------------------------------|---------------------------------|
| POST  | `/webhooks`                    | Создать подписку                |
| GET   | `/webhooks`                    | Список подписок                 |
| PATCH | `/webhooks/{id}`               | Обновить подписку               |
| DELETE| `/webhooks/{id}`               | Удалить подписку                |
| GET   | `/webhooks/{id}/deliveries`    | История доставок                |

### Аналитика
| Метод | Путь                           | Описание                        |
|-------|--------------------------------|---------------------------------|
| GET   | `/analytics/dashboard`         | Статистика дашборда (кэш)       |
| GET   | `/batches/{id}/statistics`     | Статистика по партии            |
| POST  | `/analytics/compare-batches`   | Сравнение партий                |

### Задачи (Celery)
| Метод | Путь                           | Описание                        |
|-------|--------------------------------|---------------------------------|
| GET   | `/tasks/{task_id}`             | Статус асинхронной задачи       |

---

## ⚙️ Celery (асинхронные задачи)

| Задача                               | Описание                                    |
|--------------------------------------|---------------------------------------------|
| `aggregate_products_batch`           | Массовая аггрегация продукции (>100 шт.)   |
| `generate_batch_report`              | Генерация Excel/PDF отчёта                  |
| `import_batches_from_file`           | Импорт партий из Excel/CSV                  |
| `export_batches_to_file`             | Экспорт партий в Excel/CSV                  |
| `send_webhook_delivery`              | Отправка webhook с retry                   |

### Celery Beat (расписание)
| Задача                               | Расписание                                   |
|--------------------------------------|----------------------------------------------|
| `auto_close_expired_batches`         | Каждый день в 01:00                          |
| `cleanup_old_files`                  | Каждый день в 02:00                          |
| `update_cached_statistics`           | Каждые 5 минут                               |
| `retry_failed_webhooks`              | Каждые 15 минут                              |

---

## 🔔 Webhooks

Поддерживаются события:
- `batch_created`
- `batch_updated`
- `batch_closed`
- `product_aggregated`
- `report_generated`
- `import_completed`

Вебхуки защищены **HMAC-подписью** (секретный ключ задаётся при создании подписки).  
Неудачные доставки повторяются с экспоненциальной задержкой (до `retry_count` попыток).

---

## 💾 Кэширование (Redis)

Кэшируются:
- **Дашборд статистика** (TTL: 5 минут)
- **Список партий** с фильтрацией (TTL: 1 минута)
- **Детали партии** (TTL: 10 минут)
- **Статистика партии** (TTL: 5 минут)

Инвалидация происходит автоматически при изменениях (создание, обновление, аггрегация).

---

## 📦 MinIO (файловое хранилище)

Создаются бакеты:
- `reports` – для отчётов
- `exports` – для экспортированных данных
- `imports` – для загружаемых файлов

Инициализация бакетов выполняется скриптом `scripts/init_minio.py` (запускается при старте контейнера).

Файлы загружаются с **pre-signed URL** (срок действия – 7 дней).  
Старые файлы (>30 дней) удаляются автоматически задачей `cleanup_old_files`.

---

## 🧪 Тестирование

Запуск тестов (pytest + asyncio):

```bash
docker-compose exec api pytest -v --cache-clear
```

Тесты разделены на **unit** и **integration**.

---

## 🛠 Инструменты разработки

- **Ruff** – линтинг и форматирование (заменяет black и isort)  
  Запуск:
  ```bash
  poetry run ruff check . --fix
  poetry run ruff format .
  ```
- **Pre-commit** – автоматически запускает Ruff при коммите:
  ```bash
  pre-commit install
  ```

---

## 📄 Лицензия

MIT License (если применимо).

---

## 👥 Вклад

Pull Request'ы приветствуются! Для серьёзных изменений откройте issue для обсуждения.

---

## 📞 Контакты

Автор: [Ваше имя/команда]  
Email: your-email@example.com

---

⭐ Если проект полезен – поставьте звёздочку на GitHub!
