#FROM python:3.11-slim
# Для разработки на МАК (чтобы быстро собрать сборку)
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Установка системных зависимостей включая netcat для проверки MongoDB
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    netcat-traditional \
    ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Установка пакетов
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
