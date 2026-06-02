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
- Reset local auth user store: `make seed-auth`
- Web typecheck: `cd apps/web && npm run typecheck`
- Web production build: `cd apps/web && npm run build`

### Local Auth + Port Flexibility

Default credentials after `make seed-auth`:

- Username: `admin`
- Password: `admin123` (the legacy SHA-256 hash in `users.json` matches this
  plaintext, so the first successful login migrates the record to bcrypt via
  `AuthService`.)

The login page also surfaces a `Demo` badge with a `Fill` action in
non-production builds so mobile browser checks do not require a manual
credential lookup.

The default API port is `8000`. If that port is already taken by another
process (common on developer machines with another Python service running),
the Makefile targets can be overridden:

```bash
# API on a free port
API_PORT=8002 make api

# Web dev with that port wired through
API_INTERNAL_URL=http://127.0.0.1:8002 \
NEXT_PUBLIC_API_URL=http://127.0.0.1:8002/api \
  make web
```

The mobile-screenshot / verification scripts in `scripts/` also accept
`API_BASE_URL` and `BASE_URL` so they can be re-pointed at a non-default
port without code changes.

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
