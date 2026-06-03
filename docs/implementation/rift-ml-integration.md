# RIFT / ML Integration Placeholder

## Current State

Aether OpsCenter currently exposes deterministic intelligence:

- Weighted rules scoring in `domain/policies.py` and `apps/api/services/decision_service.py`
- Root-cause rules in `pipelines/decisions/root_cause_rules.py`
- Ticket graph features in `apps/api/services/graph_intelligence_service.py`
- Similar-case retrieval in `pipelines/retrieval/`
- Drift and engine-card governance in `pipelines/governance/`

The current engine is not a trained ML model. UI copy should call it
`deterministic graph + rules` unless a real model artifact is added.

## Required Contract For Real ML/RIFT

Before wiring a model into the product, define and version these fields:

- Model artifact location and load path
- Input schema: ticket fields, graph features, historical decision fields,
  feedback fields, and any embeddings
- Output schema: priority score, decision band, confidence, root-cause
  candidates, recommended action, explanation, and model version
- Fallback behavior when the model is unavailable
- Audit fields persisted on `decision_records`: model version, feature
  snapshot, decision hash, confidence, and explanation payload
- Human-review thresholds for low confidence, drift, or conflicting signals

## UI Placement

Expose ML/RIFT only after the backend contract exists:

- Command Center: compact intelligence panel beside the selected ticket
- Ticket Detail: decision metadata, recommendation evidence, and similar cases
- Replay: model/rules decision history and operator feedback timeline
- Admin: model version, drift status, graph health, action-run status, and
  feedback volume

Until then, the UI should show graph/drift/recommendation health honestly and
avoid labeling deterministic signals as ML.
