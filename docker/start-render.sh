#!/bin/sh
set -eu

cd /app

# Production reliability: always ensure migrations applied on boot (Render/AUTO_INIT_DB).
# Alembic upgrade is idempotent; failures are logged but do not crash the API (defensive).
alembic -c infrastructure/db/migrations/alembic.ini upgrade head 2>&1 || echo "[boot] alembic upgrade non-fatal or already current"

python -c "from infrastructure.db.session import init_db; init_db()" 2>&1 || echo "[boot] init_db non-fatal"

# Start API in bg, then web (monolithic container per render.yaml)
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 &

cd /app/apps/web
exec node_modules/.bin/next start --hostname 0.0.0.0 --port "${PORT:-10000}"
