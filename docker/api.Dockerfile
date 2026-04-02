FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AUTO_INIT_DB=true \
    USERS_FILE=/app/users.json

WORKDIR /app

COPY pyproject.toml README.md users.json ./
COPY apps ./apps
COPY domain ./domain
COPY infrastructure ./infrastructure
COPY pipelines ./pipelines

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
