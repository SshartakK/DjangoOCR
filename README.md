# Django OCR Application

Это веб-приложение для распознавания текста с изображений с использованием Django и Tesseract OCR.

## Требования

- Docker и Docker Compose
- Python 3.9+
- Tesseract OCR (устанавливается автоматически в контейнере)
- Проект с FastAPI (https://github.com/SshartakK/OCR_fast)

## Установка

1. Клонируйте репозиторий:
   ```bash
   git clone <repository-url>
   cd DjangoOCR
   ```

2. Создайте файл `.env` на основе примера:
   ```bash
   cp .env .env
   ```

3. Отредактируйте файл `.env` и настройте переменные окружения:
   ```
   DEBUG=True
   SECRET_KEY=your-secret-key
   ALLOWED_HOSTS=localhost,127.0.0.1
   
   # Настройки базы данных
   POSTGRES_DB=djangodb
   POSTGRES_USER=djangouser
   POSTGRES_PASSWORD=your-strong-password
   POSTGRES_HOST=db
   POSTGRES_PORT=5432
   ```

## Запуск с помощью Docker

1. Соберите и запустите контейнеры:
   ```bash
   docker-compose up --build -d
   ```

2. При первом запуске выполните миграции (если она не выполнилась автоматически) и создайте суперпользователя:
   ```bash
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py createsuperuser
   ```

3. Соберите статические файлы:
   ```bash
   docker-compose exec web python manage.py collectstatic --noinput
   ```

4. Приложение будет доступно по адресу: http://localhost:8001

## Запуск без Docker

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Установите Tesseract OCR:
   - Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
   - macOS: `brew install tesseract`
   - Windows: Скачайте с [официального сайта](https://github.com/UB-Mannheim/tesseract/wiki)

3. Запустите миграции:
   ```bash
   python manage.py migrate
   ```

4. Создайте суперпользователя:
   ```bash
   python manage.py createsuperuser
   ```

5. Запустите сервер разработки:
   ```bash
   python manage.py runserver 0.0.0.0:8001
   ```

6. Приложение будет доступно по адресу: http://127.0.0.1:8001

## Использование

1. Зарегистрируйтесь или войдите в систему
2. Загрузите изображение с текстом
3. Дождитесь обработки
4. Просмотрите распознанный текст

## Лицензия
...
