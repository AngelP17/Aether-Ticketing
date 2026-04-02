# System Overview

## Context

Aether ingests ticket data from Excel/import sources, transforms it through an event-sourced pipeline, produces ranked decisions and recommendations, and presents an operator command center for action.

```mermaid
flowchart LR
    A[Ticket Sources] --> B[Ingest Pipeline]
    B --> C[Normalization]
    C --> D[Event Store]
    D --> E[Feature Derivation]
    E --> F[Decision Engine]
    F --> G[Recommendations]
    F --> H[Incident Clustering]
    F --> I[Audit Records]
    G --> J[Operator Command Center]
    H --> J
    I --> K[Replay and Audit View]
    J --> L[Operator Feedback]
    L --> D
```

## Core Principles

1. **Event sourcing first** — every ticket change produces an immutable event
2. **Decision quality over dashboard fluff** — every feature must improve decision quality, speed, or trust
3. **Explainability by default** — every score and recommendation has a human-readable rationale
4. **Operator in the loop** — human feedback updates weights and improves future decisions

## Data Flow

```mermaid
flowchart TD
    A[tickets.xlsx / Import] --> B[excel_loader.py]
    B --> C[delta_detector.py]
    C --> D[row_normalizer.py]
    D --> E[thread_cleaner.py]
    E --> F[ticket_events table]
    F --> G[ticket_features.py]
    G --> H{scoring.py}
    H --> I[decision_record + recommendations]
    H --> J[root_cause_rules.py]
    G --> K[incident_clustering.py]
    K --> L[incidents + incident_ticket_links]
    I --> M[similar_cases.py]
    M --> N[similar_case_links]
    I --> O[excel_report.py]
    J --> O
    K --> O
    N --> O
```

## Database Architecture

```mermaid
erDiagram
    tickets ||--o{ ticket_events : produces
    tickets ||--o| decision_records : has
    decision_records ||--o{ recommendations : yields
    tickets ||--o{ similar_case_links : similar_to
    tickets ||--o{ incident_ticket_links : linked_to
    incidents ||--o{ incident_ticket_links : contains
    recommendations ||--o| operator_feedback : receives
    recommendations ||--o| action_runs : triggers
    tickets ||--o| audit_records : snapshotted_as
```

## Key Design Decisions

- **PostgreSQL on Neon** — managed Postgres, connection pooling, branch-based dev
- **Delta detection over full reload** — last-modified hash comparison avoids reprocessing unchanged rows
- **Rules-first root cause** — keyword matching before ML embedding; faster, more explainable
- **BM25 for similarity** — simpler than embeddings, good enough recall for similar-case retrieval
- **Event immutable** — ticket_events table is append-only; audit_records provide point-in-time snapshots
