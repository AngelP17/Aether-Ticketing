# Data Flow

## Ingest Pipeline

```mermaid
flowchart LR
    A[tickets.xlsx] --> B[excel_loader.py]
    B --> C[delta_detector.py]
    C --> D{Changes?}
    D -->|New/Changed| E[row_normalizer.py]
    D -->|Unchanged| F[Skip]
    E --> G[thread_cleaner.py]
    G --> H[ticket_events\nappend-only stream]
    H --> I[tickets\ncurrent-state table]
    I --> J[ticket_features.py]
    J --> K[scoring.py]
    J --> L[root_cause_rules.py]
    K --> M[decision_record\nper ticket]
    L --> M
    K --> N[recommendation_engine.py]
    N --> O[recommendations\nper decision]
    J --> P[incident_clustering.py]
    P --> Q[incidents\n+ links]
    M --> R[similar_cases.py]
    R --> S[similar_case_links]
    S --> T[excel_report.py]
    Q --> T
    O --> T
```

## Delta Detection

1. Read source rows with last-modified hash
2. Compare against stored hash in DB
3. Only process rows where hash changed
4. On new row → emit `ticket_created` event
5. On changed row → emit appropriate status/priority/description event

## Feature Derivation

Each ticket is processed through:
1. **Text cleaning** — remove email threading artifacts, normalize whitespace
2. **Keyword extraction** — TF-IDF top terms per title + description
3. **SLA computation** — elapsed time vs category target
4. **Recurrence lookup** — count same asset/category/site in last 90 days
5. **Business impact** — site weight + asset criticality lookup
