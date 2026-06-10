.PHONY: dev test lint lint-py lint-web migrate rollback clean deps api web typecheck build-docker run-docker seed-auth verify-mobile

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

dev:
	uvicorn apps.api.main:app --reload --port 8000

api:
	uvicorn apps.api.main:app --reload --port 8000

web:
	cd apps/web && npm run dev

test:
	PYTHONPATH=. $(PYTHON) -m pytest tests/ -v --tb=short

lint: lint-py lint-web

lint-py:
	ruff check apps/ infrastructure/ pipelines/ domain/ scripts/ tests/

lint-web:
	cd apps/web && npm run lint

typecheck:
	$(PYTHON) -m mypy --namespace-packages --explicit-package-bases apps/ infrastructure/ pipelines/ domain/ tests/ scripts/ --ignore-missing-imports

migrate:
	alembic -c infrastructure/db/migrations/alembic.ini upgrade head
	python -c "from infrastructure.db.session import init_db; init_db()"
	python -c "from sqlalchemy import text; from infrastructure.db.session import engine; conn = engine.connect(); trans = conn.begin(); conn.execute(text(\"CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)\")); conn.execute(text(\"DELETE FROM alembic_version\")); conn.execute(text(\"INSERT INTO alembic_version (version_num) VALUES ('20260401_120000')\")); trans.commit(); conn.close()"

rollback:
	alembic -c infrastructure/db/migrations/alembic.ini downgrade -1

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	cd apps/web && rm -rf .next node_modules/.cache

deps:
	pip install -e ".[dev]"
	cd apps/web && npm install

build-docker:
	docker compose -f docker/docker-compose.yml build

run-docker:
	docker compose -f docker/docker-compose.yml up -d

seed-auth:
	PYTHONPATH=. $(PYTHON) scripts/seed_auth.py

verify-mobile:
	BASE_URL=$${BASE_URL:-http://localhost:3000} \
	API_BASE_URL=$${API_BASE_URL:-http://localhost:8002/api} \
	node scripts/verify-mobile.mjs
