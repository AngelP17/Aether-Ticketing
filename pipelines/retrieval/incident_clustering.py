"""
Incident Clustering: Groups related tickets into incidents.

The high-level cluster generation that powers the API lives in
`apps.api.services.operational_intelligence.synthesize_incidents`,
which now produces graph-evidence payloads alongside the
`recommended_action` for each cluster. This module provides the
low-level helper that takes a list of ticket primary keys and
returns the persisted incident PK via `IncidentPersistence`.
"""
from __future__ import annotations

import hashlib
from typing import Any, Optional

from apps.api.services.incident_persistence import IncidentPersistence


def find_or_create_incident(
    ticket_ids: list[int],
    db: Optional[Any] = None,
    *,
    root_cause_hint: str = "unknown",
    site_hint: str | None = None,
) -> Optional[int]:
    """Given a list of ticket primary keys, find an existing incident
    or create a new one. Returns the persisted incident PK.

    The function builds a deterministic cluster key from the ticket
    ids, root cause, and site hint, then asks `IncidentPersistence` to
    upsert it. When `db` is None, no DB call is made and the function
    returns None so unit tests can run without a live database.
    """
    if not ticket_ids:
        return None
    if db is None:
        return None
    deterministic_key = _deterministic_cluster_key(
        ticket_ids, root_cause=root_cause_hint, site=site_hint
    )
    return IncidentPersistence(db).upsert_cluster(
        ticket_ids=sorted(set(int(t) for t in ticket_ids)),
        root_cause=root_cause_hint,
        site=site_hint,
        deterministic_key=deterministic_key,
    )


def _deterministic_cluster_key(
    ticket_ids: list[int], *, root_cause: str, site: str | None
) -> str:
    payload = "|".join(
        [
            (root_cause or "unknown").lower(),
            (site or "global").lower(),
            ",".join(str(int(t)) for t in sorted(set(ticket_ids))),
        ]
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]
    safe = (root_cause or "unknown").lower().replace(" ", "_")[:30]
    return f"INC-{safe}-{digest}"
