# Dockerfile для деплоя на Cloud Run / Railway / Render
FROM python:3.11-slim

WORKDIR /app

# Установить системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копировать requirements и установить зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копировать код приложения
COPY . .

# Переменные окружения (можно переопределить)
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Expose порт
EXPOSE 8080

# Команда запуска
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}

