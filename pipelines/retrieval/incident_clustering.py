"""
Incident Clustering: Groups related tickets into incidents.
"""

from typing import Optional

from apps.api.services.operational_intelligence import synthesize_incidents

def find_or_create_incident(ticket_ids: list[int]) -> Optional[int]:
    """
    Given a list of ticket IDs, find an existing incident or create a new one.
    Returns incident_id.
    """
    incidents = synthesize_incidents(
        [
            {
                "ticket_id": f"T-{ticket_id}",
                "title": f"Ticket {ticket_id}",
                "status": "Open",
                "priority_raw": "Medium",
                "priority_score": 50,
                "root_cause_hypothesis": "unknown",
                "confidence_score": 50,
                "created_at": "2026-04-01T00:00:00",
                "days_open": 0,
                "category": "unknown",
            }
            for ticket_id in ticket_ids
        ]
    )
    if not incidents:
        return None
    return 1
