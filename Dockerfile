FROM node:20-slim AS web-builder

WORKDIR /app/apps/web

COPY apps/web/package*.json ./
RUN npm ci

COPY apps/web/ ./
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NEXT_TELEMETRY_DISABLED=1 \
    API_INTERNAL_URL=http://127.0.0.1:8000 \
    PORT=10000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md users.json ./
COPY apps ./apps
COPY domain ./domain
COPY infrastructure ./infrastructure
COPY pipelines ./pipelines
COPY docker/start-render.sh ./docker/start-render.sh

RUN pip install --no-cache-dir .

COPY --from=web-builder /app/apps/web/.next ./apps/web/.next
COPY --from=web-builder /app/apps/web/node_modules ./apps/web/node_modules
COPY --from=web-builder /app/apps/web/package.json ./apps/web/package.json
COPY --from=web-builder /app/apps/web/next.config.js ./apps/web/next.config.js

RUN chmod +x ./docker/start-render.sh

EXPOSE 8000 10000

CMD ["./docker/start-render.sh"]
