# API Contracts

## Endpoint Map

```mermaid
flowchart LR
    subgraph Public
        Login[POST /api/auth/login]
        Logout[POST /api/auth/logout]
        Reports[GET /api/reports/excel|csv]
    end
    subgraph Read
        Tickets[GET /api/tickets]
        Ticket[GET /api/tickets/{id}]
        Events[GET /api/tickets/{id}/events]
        Incidents[GET /api/incidents]
        Incident[GET /api/incidents/{id}]
        Decisions[GET /api/decisions/{id}]
        Recs[GET /api/recommendations]
        Metrics[GET /api/metrics/*]
        Replay[GET /api/replay/{id}]
        Assets[GET /api/assets/*]
        Intelligence[GET /api/intelligence/health]
    end
    subgraph Authenticated
        Me[GET /api/auth/me]
        Change[POST /api/auth/change-password]
        Comments[GET /api/tickets/{id}/comments]
        CatalogR[GET /api/categories|labels|assignees|options]
        Gov[GET /api/governance/summary|card]
    end
    subgraph WriteAgent[Write - admin+agent]
        TicketW[POST/PUT/DELETE /api/tickets/*]
        CommentW[POST/PUT/DELETE comments]
        AttachW[POST/DELETE attachments]
        Apply[POST /api/actions/recommendations/{id}/apply]
        Accept[POST /api/recommendations/{id}/accept|reject|override]
        ChangeStatus[PUT /api/tickets/{id}/move]
    end
    subgraph WriteAdmin[Write - admin only]
        Users[POST/PUT/DELETE /api/auth/users]
        Cat[POST/PUT/DELETE /api/categories|labels|assignees]
    end
    Public --> Read
    Read --> Authenticated
    Authenticated --> WriteAgent
    WriteAgent --> WriteAdmin
```

**Query params**: status, priority, category, assignee, ranking, limit, offset

**Response**: `list[TicketResponse]`
```json
[
  {
    "ticket_id": "IT-20250001",
    "title": "Cannot access shared drive",
    "status": "Open",
    "priority_raw": "High",
    "priority_score": 81.4,
    "root_cause_hypothesis": "file_share_permissions",
    "confidence_score": 0.82,
    "site": "Production-HQ",
    "assignee": "jsmith",
    "category": "Access",
    "description": "User cannot access shared drive",
    "requester": "jsmith@company.com",
    "created_at": "2025-01-15T09:30:00Z",
    "days_open": 3,
    "incident_id": "INC-2025-0012"
  }
]
```

## GET /api/tickets/{ticket_id}

**Response**: `TicketDetailResponse`
```json
{
  "ticket": {
    "ticket_id": "IT-20250001",
    "title": "Cannot access shared drive",
    "status": "Open",
    "priority_raw": "High",
    "priority_score": 81.4,
    "root_cause_hypothesis": "file_share_permissions",
    "confidence_score": 0.82,
    "site": "Production-HQ",
    "assignee": "jsmith",
    "created_at": "2025-01-15T09:30:00Z",
    "days_open": 3,
    "incident_id": "INC-2025-0012"
  },
  "decision": {
    "id": 1,
    "ticket_id": "IT-20250001",
    "priority_score": 81.4,
    "severity_score": 72,
    "urgency_score": 68,
    "business_impact_score": 85,
    "sla_risk_score": 54,
    "recurrence_score": 40,
    "dependency_criticality_score": 50,
    "actionability_score": 78,
    "uncertainty_penalty": 12,
    "root_cause_hypothesis": "file_share_permissions",
    "confidence_score": 0.82,
    "decision_ts": "2025-01-18T14:22:00Z",
    "recommendations": [
      {
        "id": 1,
        "rank": 1,
        "action_type": "apply_runbook",
        "action_label": "Reset NTFS permissions and remap drive",
        "risk_level": "low",
        "confidence": 0.88,
        "expected_benefit": "Resolve within 1h",
        "rationale": "Pattern matches 8 resolved cases"
      }
    ]
  },
  "recommendations": [...],
  "similar_cases": [...],
  "events": [...],
  "linked_incident": {...}
}
```

## GET /api/decisions/{ticket_id}

**Response**: `DecisionResponse` with nested recommendations

## POST /api/decisions/recompute/{ticket_id}

**Response**: `DecisionResponse` - recomputes and returns fresh decision

## POST /api/recommendations/{recommendation_id}/accept

**Body**: `{ "note": "optional operator note" }`

**Response**: `{ "status": "accepted", "feedback_id": "fb_001" }`

## POST /api/recommendations/{recommendation_id}/reject

**Body**: `{ "reason": "wrong_category" }`

**Response**: `{ "status": "rejected", "feedback_id": "fb_002" }`

## POST /api/recommendations/{recommendation_id}/override

**Body**: `{ "override_note": "Customer VIP - elevating manually", "override_priority": 95 }`

**Response**: `{ "status": "recorded", "override_id": "ovr_001" }`

## GET /api/reports/excel

**Query params**: report_type (executive|operational|incident|decision|audit), date_from, date_to

**Response**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

## GET /api/replay/{ticket_id}

**Query params**: `?as_of=2025-01-15T12:00:00Z`

**Response**:
```json
{
  "ticket_id": "IT-20250001",
  "as_of": "2025-01-15T12:00:00Z",
  "snapshot": { ... },
  "events": [
    { "event_type": "ticket_created", "event_ts": "2025-01-12T09:00:00Z", ... },
    { "event_type": "decision_generated", "event_ts": "2025-01-12T09:01:00Z", ... }
  ],
  "decision_at_time": { "priority_score": 65, ... }
}
```

## GET /api/incidents

**Response**: `list[IncidentResponse]`
```json
[
  {
    "id": "INC-2025-0012",
    "title": "File share access issue - Production HQ",
    "status": "open",
    "root_cause_hypothesis": "file_share_permissions",
    "ticket_count": 7,
    "confidence": 0.89,
    "business_impact_score": 82,
    "opened_at": "2025-01-15T08:00:00Z"
  }
]
```

## GET /api/incidents/{incident_id}

**Response**: `IncidentDetailResponse`
```json
{
  "incident": { ... },
  "tickets": [ ... ],
  "common_cause": "NTFS permission corruption on \\\\fileserv-prod",
  "recommended_action": "Run permission repair runbook on all affected servers"
}
```
```
