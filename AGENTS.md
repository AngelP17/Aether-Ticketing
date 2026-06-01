# Aether OpsCenter Agent Guide

## Start Here

- Inspect the repo before editing. Read `README.md`, this file, the relevant route/service/component files, and the manifests before planning changes.
- Do not change application behavior during documentation-only tasks.
- Keep route slugs and API paths stable unless the user explicitly asks for a product/API change.
- Treat `.snapshots/` as existing untracked local state unless the user says otherwise.

## Project Shape

- `apps/api/` contains the FastAPI backend routes, schemas, security dependencies, and services.
- `apps/web/` contains the Next.js 14 App Router frontend.
- `domain/`, `pipelines/`, and `infrastructure/` contain scoring, ingestion, reporting, SQLAlchemy models, migrations, and support code.
- `infrastructure/db/migrations/` contains Alembic migration config and versions.
- `users.json` is the current local/demo auth user store. It is not a generated cache, but avoid editing real credentials casually.

## Commands

Use commands that are already defined in this repo:

- Install dependencies: `make deps`
- Run API: `make dev` or `make api`
- Run web: `make web`
- Run Python tests: `make test`
- Run all lint: `make lint`
- Run Python lint: `make lint-py`
- Run web lint: `make lint-web`
- Run Python typecheck: `make typecheck`
- Run DB migrations: `make migrate`
- Roll back one migration: `make rollback`
- Build Docker images: `make build-docker`
- Run Docker stack: `make run-docker`
- Web typecheck: `cd apps/web && npm run typecheck`
- Web production build: `cd apps/web && npm run build`

## Conventions And Constraints

- Backend auth uses JWT access tokens. Logout clears the client session only; without a server-side denylist, issued tokens remain valid until expiry.
- Password hashes should be created through `AuthService`; legacy SHA-256 hashes are only accepted for migration on successful login.
- Login throttling is in-memory and suitable for local/demo use. Use a shared store such as Redis before relying on it in multi-process production.
- Production config must not use the default `SECRET_KEY` or wildcard CORS with credentials.
- Frontend is a dense B2B operations UI. Preserve the dark operations theme, existing routes, and Lucide icon family.
- Keep motion restrained and respect reduced-motion behavior. Prefer stable app UI over landing-page flourish.

## Files To Avoid Unless Asked

- Do not edit generated or local cache output: `.next/`, `node_modules/`, `.pytest_cache/`, `__pycache__/`, coverage artifacts, or temporary report outputs.
- Do not regenerate or replace `docs/screenshots/*.png` unless the task is specifically about screenshots.
- Do not alter lockfiles unless dependency changes require it.

## Done When

- Relevant tests, lint, typecheck, or builds have been run, or the blocker is listed explicitly.
- Security/auth changes include targeted tests.
- Documentation is updated when behavior, setup, commands, or limitations change.
- Frontend changes are checked in the browser for affected routes when a dev server can run.
- Final responses list files changed, verification run, results, blockers, and recommended follow-up.
