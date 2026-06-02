# Operator Workflows

## Primary Workflow: Triage a Ticket

1. Operator opens Command Center → sees ranked queue
2. Clicks ticket → Ticket Case View loads
3. Reviews: clean summary, score breakdown, root cause hypothesis
4. Reads top 3 recommendations with confidence scores
5. Takes action: accepts top recommendation OR overrides with note
6. System records feedback → updates confidence weights

## Secondary Workflow: Handle Incident Cluster

1. Incident alert appears in Command Center left panel
2. Operator opens Incident Detail View
3. Reviews: common cause hypothesis, linked tickets, business impact
4. Applies coordinated action across all linked tickets
5. Marks incident resolved → system archives with lessons learned

## Tertiary Workflow: Audit Replay

1. Operator or auditor selects ticket in Replay View
2. Timeline shows all events chronologically
3. Point-in-time selector reconstructs exact state at any moment
4. Reviews: what was the score at time T? What recommendation was made?
5. Operator can export audit extract as Excel

## End-to-End Flow (Triage)

```mermaid
flowchart TD
    Start([Open Command Center]) --> CC[Ranked Queue Loaded]
    CC --> Pick{Click ticket}
    Pick -->|yes| Detail[Ticket Case View]
    Detail --> Review{Review score + recommendations}
    Review -->|accept| Accept[POST /api/recommendations/{id}/accept]
    Review -->|reject| Reject[POST /api/recommendations/{id}/reject]
    Review -->|override| Override[POST /api/recommendations/{id}/override]
    Review -->|apply| Apply[POST /api/actions/recommendations/{id}/apply]
    Accept --> Feedback[(operator_feedback)]
    Reject --> Feedback
    Override --> Feedback
    Apply --> Feedback
    Feedback --> Card[Decision Card refreshes]
    Card --> CC
    Pick -->|no| Inc{Open incident}
    Inc -->|yes| IncDetail[Incident Detail]
    IncDetail --> Coord[Apply coordinated action]
    Coord --> CC
```
