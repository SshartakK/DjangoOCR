# Базовый образ Python
FROM python:3.9-slim

# Установка зависимостей системы
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Создание и настройка рабочей директории
WORKDIR /app

# Копирование зависимостей
COPY requirements.txt .

# Установка зависимостей Python
RUN pip install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Создание директории для статических файлов
RUN mkdir -p /app/static

# Команда запуска
CMD ["gunicorn", "--bind", "0.0.0.0:8001", "core.wsgi:application"]
