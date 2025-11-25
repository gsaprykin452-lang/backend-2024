# Daily Digest Backend

FastAPI backend для приложения Daily Digest.

## Установка

```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Копирование .env файла
cp .env.example .env
# Отредактируйте .env и добавьте необходимые ключи API
```

## Настройка базы данных

```bash
# Запуск PostgreSQL и Redis через Docker
docker-compose up -d

# Применение схемы БД
psql -U postgres -h localhost -d daily_digest -f ../database/schema.sql

# Или через Alembic (рекомендуется)
alembic upgrade head
```

## Запуск

```bash
# Разработка
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Структура проекта

```
backend/
├── app/
│   ├── api/              # API endpoints (роутеры)
│   ├── core/             # Конфигурация, безопасность, БД
│   ├── models/           # SQLAlchemy модели
│   ├── schemas/          # Pydantic схемы для валидации
│   ├── services/         # Бизнес-логика
│   │   ├── content/      # Обработка контента
│   │   ├── classification/ # Классификация и ранжирование
│   │   ├── briefing/     # Генерация брифингов
│   │   └── tts/          # Text-to-Speech
│   ├── tasks/            # Celery задачи
│   │   ├── sync/         # Синхронизация источников
│   │   └── briefing/     # Генерация брифингов
│   └── main.py           # Точка входа
├── alembic/              # Миграции БД
└── requirements.txt
```

## API Endpoints

- `/docs` - Swagger документация
- `/redoc` - ReDoc документация
- `/health` - Health check

## Разработка

### Создание миграций

```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Запуск Celery worker

```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

### Запуск Celery beat (планировщик)

```bash
celery -A app.tasks.celery_app beat --loglevel=info
```

