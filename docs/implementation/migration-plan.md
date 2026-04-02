# Migration Plan: Flask → Aether

## Overview

Migration from the existing Flask monolith to FastAPI + Next.js with zero downtime and backward-compatible data layer.

## Strategy: Side-By-Side Build

The new Aether system is built alongside the existing Flask app, sharing the same Neon PostgreSQL database. The existing `tickets`, `categories`, `labels` tables are preserved. New Aether-specific tables (ticket_events, decision_records, incidents, etc.) are added alongside.

## Migration Phases

### Phase 1: Dual-Write Period
Both Flask app and new FastAPI write to the shared Neon DB. Flask remains source of truth for existing CRUD operations.

### Phase 2: Read Path Migration
Route read operations (ticket list, detail, export) to FastAPI. Flask still handles writes. A/B validate data consistency.

### Phase 3: Full Cutover
All traffic routes to FastAPI + Next.js. Flask app is archived (not deleted — deployment history preserved).

### Phase 4: Legacy Table Cleanup
After validation period, migrate categories/labels to new asset model. Drop legacy columns not needed by new system.

## Backward Compatibility

- Existing `tickets` table schema is preserved during dual-write
- New nullable columns added (feature_snapshot_json, etc.) — no migration required
- Ticket IDs remain stable across cutover
- Auth system upgraded in Phase 7 (JWT); session-based auth remains until then

## Key Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Data divergence during dual-write | Emit events from Flask writes too (add events to existing app.py) |
| Session auth vs JWT | Share secret key; issue session + JWT during transition |
| Excel export format change | Maintain backward-compatible export endpoint until Phase 6 |
| Neon DB connection during migration | Use same DATABASE_URL; no new credentials needed |

## Timeline

- Week 1–2: Phase 0–1 (docs + FastAPI scaffold + models)
- Week 3–4: Phase 2–3 (features + decision engine)
- Week 5: Phase 4 (retrieval + clustering)
- Week 6–7: Phase 5 (frontend)
- Week 8: Phase 6 (reporting)
- Week 9–10: Phase 7 (hardening + cutover)
