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
- `tickets.xlsx` is the tracked sanitized demo ticket workbook. It must contain
  fake demo records only. Never replace it with real workplace data.

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
- Mobile layout smoke check: `make verify-mobile` (requires API and web dev servers)

### Render Verification

Render deploys from `render.yaml` with `AUTO_INIT_DB=true`. When production
shows schema-related intelligence errors (for example missing
`decision_records.decision_band`), inspect the live service with the Render CLI
if it is installed and authenticated, then run the repo migration command in
the Render service shell/job context:

```bash
render --version
render services
alembic -c infrastructure/db/migrations/alembic.ini upgrade head
python -c "from infrastructure.db.session import init_db; init_db()"
```

After a Render deploy or migration, verify with a fresh login and these live
endpoints through the deployed host: `/api/auth/me`,
`/api/intelligence/health`, `/api/governance/summary`, and
`/api/replay/{ticket_id}`. Do not mark production fixed until unexpected 500s
are gone in the browser network/console checks.

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

### Direct Postgres Inspection

`127.0.0.1:5432` on a developer machine may point at a different local
Postgres (not the Docker DB), which can mislead anyone trying to verify
data the app is using. The Docker app talks to Postgres on the internal
`db:5432` network alias. For source-of-truth inspection, run psql
inside the container:

```bash
docker compose -f docker/docker-compose.yml exec -T db psql -U aether -d aether
```

The tracked `tickets.xlsx` workbook is the Excel import seed for public demos.
It must stay sanitized and safe for GitHub. Keep private workplace exports under
ignored names such as `tickets.private.xlsx` or in `private-data/`; never stage
those files.

## Conventions And Constraints

- Backend auth uses JWT access tokens. Logout clears the client session only; without a server-side denylist, issued tokens remain valid until expiry.
- Password hashes should be created through `AuthService`; legacy SHA-256 hashes are only accepted for migration on successful login.
- Login throttling is in-memory and suitable for local/demo use. Use a shared store such as Redis before relying on it in multi-process production.
- Production config must not use the default `SECRET_KEY` or wildcard CORS with credentials.
- Do not commit live deployment hostnames, including Render URLs. Use
  placeholders such as `<deployed-host>` in docs and final notes unless the user
  explicitly asks to publish the URL.
- Frontend is a dense B2B operations UI. Preserve the dark operations theme, existing routes, and Lucide icon family.
- Keep motion restrained and respect reduced-motion behavior. Prefer stable app UI over landing-page flourish.

## Frontend Design Principles (OpsCenter-specific)

These are the rules every frontend change in `apps/web/` must follow. They
are derived from the `design-taste-frontend` skill, scoped to a B2B operations
console (Cockpit mode: `VARIANCE 6 / MOTION 3 / DENSITY 8`). Landing-page rules
do not apply; do not use them as a justification for redesigning chrome.

- **One accent, locked.** Amber `#f59e0b` is the only accent. Status colors
  (rose/cyan/emerald) are functional, not decorative. No random purple/cyan
  glows, no gradient text, no neon shadows. The home page's multi-accent
  quick-access cards (amber/cyan/emerald/violet) violate this — collapse to
  amber or zebra to neutral.
- **One radius scale, locked project-wide.** Documented in `globals.css`
  (8 / 12 / 16 / 22 / 32px, plus `999px` for pills/circles). Audit every new
  component against this scale — do not introduce new arbitrary radius values.
- **Shape rule for data surfaces.** For high-density data (metrics, counts,
  scores) prefer hairline dividers and mono numbers over generic card
  containers. The command-center metric grid is a known offender.
- **Typography.** Mono for IDs (`IT-20250007`), timestamps, counts, scores,
  IPs. Sans for prose. No serif anywhere. No Inter as the default.
- **Eyebrow ban translated to panels.** Do not stamp an
  `uppercase tracking-[0.18em]` micro-label above every panel header. The
  section's location is the label. Use plain headings for section topics.
  Uppercase mono labels are allowed only for compact data labels, table
  headers, IDs, timestamps, counts, hashes, status badges, and short metadata
  fields where the casing improves scanability.
- **No AI-fluff copy.** Audit every visible string before ship. No cute
  metaphors, no fake-precise numbers (`92%`, `4.1×`), no passive-aggressive
  humility, no mock-poetic micro-meta. Plain ops register.
- **No fake ML claims.** The current decision layer is deterministic graph +
  rules. Do not call it ML/RIFT unless a versioned model artifact and backend
  contract exist. See `docs/implementation/rift-ml-integration.md`.
- **Full UI state cycles on every list/detail.** Skeleton matching the final
  shape, composed empty state, inline error, tactile `:active` press.
- **Contrast.** WCAG AA on every status badge, button, input, table cell.
- **Motion restraint.** Animated only where it communicates (status pulse on
  live feeds, row enter/exit on board DnD). Spring physics, transform +
  opacity only, honor `prefers-reduced-motion`. No `window.addEventListener(
  scroll)`, no `useState` for pointer/scroll physics.
- **Layout variety.** The board, command center, incidents, reports, admin,
  ticket workspace should not all be the same panel grid. Vary the surface —
  table, kanban, graph, density table, split-pane.
- **Z-index restraint.** Documented scale: `z-0` (decorations) → `z-10`
  (content) → `z-20` (rail) → `z-40/45/46` (nav/sheet/export) → `z-50`
  (modals/errors) → `z-[100]` (toasts). No off-scale values without a
  comment.
- **Mobile grid discipline.** `ops-shell` root must set `grid-cols-1` so
  single-column mobile layout is constrained to the viewport. The previous
  build was 633–956px wide on a 390px viewport because the grid defaulted
  to `auto` columns. Do not remove `grid-cols-1` from `ops-shell`.

## Mobile (390×844) Layout Discipline

- Bottom mobile nav uses **short labels** (`Home / Board / Incidents /
  Reports / More`) and the bell — full-width labels wrap on 390px.
- `ops-floating-export` shrinks to `scale(0.82)` below `md` so it does not
  dominate the right edge of the viewport.
- The topbar route shortcut nav uses `overflow-x-auto` and is the only
  horizontally scrollable surface. Do not wrap.
- The eyebrow / status / sync row in the topbar is `flex-wrap`; pill rows
  drop to the next line cleanly at 390px.

## Files To Avoid Unless Asked

- Do not edit generated or local cache output: `.next/`, `node_modules/`, `.pytest_cache/`, `__pycache__/`, coverage artifacts, or temporary report outputs.
- Do not stage or commit real/local data files such as `tickets.private.xlsx`,
  `tickets*.xlsx` other than the sanitized root `tickets.xlsx`, files under
  `private-data/`, or `local_infra.db`.
- Do not regenerate or replace `docs/screenshots/*.png` unless the task is specifically about screenshots.
- Do not alter lockfiles unless dependency changes require it.

## Done When

- Relevant tests, lint, typecheck, or builds have been run, or the blocker is listed explicitly.
- Security/auth changes include targeted tests.
- Documentation is updated when behavior, setup, commands, or limitations change.
- Frontend changes are checked in the browser for affected routes when a dev server can run.
- Final responses list files changed, verification run, results, blockers, and recommended follow-up.
