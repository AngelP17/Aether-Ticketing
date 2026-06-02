# Incident Clustering

## Overview

Incident clustering groups related tickets into a higher-order "incident" entity, enabling coordinated handling and common-cause analysis.

## Clustering Dimensions

Tickets are candidate clusters when they share:
- Text similarity (title + description keywords)
- Same or related asset
- Same site/location
- Same root cause class
- Time window (created within 24 hours)

## First-Pass Clustering Rule

```mermaid
flowchart TD
    A[Incoming Ticket] --> B{text_similarity > 0.78\nAND site_match = true\nAND created_within_24h?}
    B -->|Yes| C[Link to existing incident]
    B -->|No| D{Create new incident?}
    D -->|Yes| E[Create incident]
    E --> F[Link ticket as primary]
    D -->|No| G[Standalone ticket]
    C --> H{Confidence boost?}
    H -->|same asset| I[Increase confidence]
    H -->|same team| I
    H -->|same category| I
    H -->|same rec profile| I
    I --> J[Update incident confidence]
```

## Threshold Constants

| Parameter | Value |
|---|---|
| text_similarity_threshold | 0.78 |
| time_window_hours | 24 |
| min_confidence_to_link | 0.60 |
| min_confidence_to_create | 0.75 |

## Link Types

| Type | Description |
|---|---|
| primary | Core ticket defining the incident |
| related | Related but not core |
| duplicate | Likely same root cause |
| inferred | System-suggested link |

## Confidence Scoring

```
cluster_confidence = base_similarity
  + (same_asset × 0.10)
  + (same_team × 0.08)
  + (same_category × 0.07)
  + (same_root_cause × 0.10)
  + (time_proximity_bonus × 0.05)
```

## Incident Lifecycle

1. **Created** — first ticket triggers cluster creation
2. **Updated** — new tickets linked as incident grows
3. **Root cause identified** — hypothesis set by operator or rules
4. **Resolved** — coordinated resolution applied
5. **Closed** — incident archived with lessons learned

## Incident + Graph Data Model

```mermaid
erDiagram
    incidents {
        string incident_id PK
        string title
        string status
        string root_cause_hypothesis
        float confidence
        int business_impact_score
        datetime opened_at
        datetime closed_at
    }
    incident_ticket_links {
        int incident_id FK
        string ticket_id FK
        string link_type
        float contribution_score
    }
    tickets {
        string ticket_id PK
        string status
        string site
    }
    graph_nodes {
        int id PK
        string node_type
        string ref_id
    }
    graph_edges {
        int id PK
        int source_node_id FK
        int target_node_id FK
        string edge_type
        float weight
    }
    incidents ||--o{ incident_ticket_links : contains
    tickets ||--o{ incident_ticket_links : linked_from
    incidents ||--o{ graph_nodes : "cluster_anchor"
    tickets ||--o{ graph_nodes : "ticket_anchor"
    graph_nodes ||--o{ graph_edges : "from"
    graph_nodes ||--o{ graph_edges : "to"
```
