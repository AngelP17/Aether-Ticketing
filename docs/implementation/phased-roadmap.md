# Phased Roadmap

## Phase 0: Identity & Docs
- Project repositioned as Aether
- Architecture diagrams in Mermaid
- Decision engine concepts documented
- Portfolio positioning defined

## Phase 1: Backend Foundation
- FastAPI app scaffolded
- PostgreSQL models (11 tables)
- Alembic migrations
- Normalized Excel ingest
- Immutable ticket events on import

## Phase 2: Feature Derivation
- Thread cleaner and summary extraction
- Severity, urgency, business impact, SLA features
- Recurrence and actionability signals

## Phase 3: Decision Engine
- Priority scoring policy implemented
- Root cause rule engine
- Decision records persisted
- Ranked recommendations generated

## Phase 4: Retrieval & Clustering
- Similar-case indexing and lookup
- Duplicate detection heuristics
- Incident clustering logic and linkage

## Phase 5: Frontend Command Center
- Next.js app scaffolded
- Ranked queue and ticket case view
- Recommendation stack and confidence meter
- Incident detail and audit timeline
- Replay view and operator feedback

## Phase 6: Reporting
- 5-tab styled Excel workbook
- Charts, conditional formatting, risk bands
- Report export panel in UI

## Phase 7: Hardening
- Immutable audit snapshots
- WebSocket updates
- Decision determinism tests
- Split CI/CD pipelines (api, web, reports)

## Commit Sequence

1. docs: reposition project as Aether
2. docs: add mermaid architecture diagrams
3. docs: define decision engine concepts
4. backend: scaffold FastAPI app
5. db: add PostgreSQL models
6. db: add Alembic migrations
7. ingest: add normalized Excel loader
8. events: persist immutable ticket events
9. features: add thread cleaner
10. features: add scoring signals
11. features: add recurrence signals
12. decision: add priority scoring
13. decision: add root cause rules
14. decision: persist decision records
15. recommendations: add ranked generation
16. retrieval: add similar-case index
17. retrieval: add duplicate detection
18. incidents: add clustering logic
19. web: scaffold command center
20. web: add ranked queue view
21. web: add recommendations panel
22. web: add incident detail
23. web: add audit replay
24. reports: add styled Excel
25. reports: add charts and formatting
26. web: add report export panel
27. audit: add snapshots and replay
28. realtime: add WebSocket updates
29. tests: add decision coverage
30. ci: split pipelines

## Phase Timeline

```mermaid
gantt
    title Aether Phased Rollout
    dateFormat YYYY-MM-DD
    axisFormat %b
    section Foundation
    Phase 0 Identity & Docs      :done, p0, 2025-01-01, 7d
    Phase 1 Backend Foundation   :done, p1, after p0, 14d
    Phase 2 Feature Derivation   :done, p2, after p1, 10d
    section Intelligence
    Phase 3 Decision Engine      :done, p3, after p2, 14d
    Phase 4 Retrieval & Clustering:done, p4, after p3, 10d
    section Operator UX
    Phase 5 Frontend Command Ctr :done, p5, after p4, 21d
    section Reporting
    Phase 6 Excel + CSV Reports  :done, p6, after p5, 10d
    section Hardening
    Phase 7 Graph + Governance   :active, p7, after p6, 14d
    Phase 8 Endpoint Test Suite  :p8, after p7, 5d
```
