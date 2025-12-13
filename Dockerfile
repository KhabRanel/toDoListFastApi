# ============== Базовый Python ==============
FROM python:3.11-slim

# ============== Рабочая директория ==============
WORKDIR /app

# ============== Установка зависимостей ==============
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============== Копируем весь проект ==============
COPY . .

# ============== Открываем порт FastAPI ==============
EXPOSE 8000

# ============== Команда запуска ==============
CMD ["sh", "-c", "echo 'Server running at: http://127.0.0.1:8000' && uvicorn app.app_main:app --host 0.0.0.0 --port 8000"]

