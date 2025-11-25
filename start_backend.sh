#!/bin/bash
# Скрипт для запуска backend

cd "$(dirname "$0")"

# Активировать виртуальное окружение
source venv/bin/activate

# Проверить подключение к БД (опционально, можно пропустить если БД не настроена)
# python -c "from app.core.database import engine; engine.connect()" 2>/dev/null || echo "Warning: Database connection failed"

# Запустить сервер
echo "Starting Daily Digest Backend on http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

