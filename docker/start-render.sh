#!/bin/sh
set -eu

cd /app
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 &

cd /app/apps/web
exec node_modules/.bin/next start --hostname 0.0.0.0 --port "${PORT:-10000}"
