"""
Incident persistence: takes synthesized incident clusters and upserts them
into the `incidents` table with deterministic `incident_key` values so
incident IDs are stable across page reloads, restarts, and rebuilds.

Also writes the `incident_ticket_links` rows that cluster members reference.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def _incident_key(root_cause: str | None, site: str | None, opened_at: Any) -> str:
    raw = f"{(root_cause or 'unknown').lower()}|{(site or 'global').lower()}|{_date_bucket(opened_at)}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    safe = (root_cause or "unknown").lower().replace(" ", "_")[:30]
    return f"INC-{safe}-{digest}"


def _date_bucket(opened_at: Any) -> str:
    if opened_at is None:
        return datetime.now(timezone.utc).strftime("%Y%m%d")
    if isinstance(opened_at, datetime):
        return opened_at.strftime("%Y%m%d")
    try:
        return datetime.fromisoformat(str(opened_at).replace("Z", "")).strftime("%Y%m%d")
    except ValueError:
        return str(opened_at)[:10].replace("-", "")


def persist_synthesized_incidents(
    db: Session, clusters: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Upsert incidents and their ticket links from synthesized clusters.

    Each cluster must contain a list of `tickets` with their `ticket_id`
    (external string id) and optionally their primary key. Returns the
    list of clusters with `id` set to the persisted incident PK.
    """
    persisted: list[dict[str, Any]] = []
    for cluster in clusters:
        key = _incident_key(
            root_cause=cluster.get("root_cause_hypothesis") or "unknown",
            site=cluster.get("site_scope"),
            opened_at=cluster.get("opened_at"),
        )
        row = db.execute(
            text(
                """
                INSERT INTO incidents (
                    incident_key,
                    title,
                    status,
                    root_cause_hypothesis,
                    site_scope,
                    asset_scope,
                    business_impact_score,
                    confidence,
                    opened_at,
                    last_updated_at
                )
                VALUES (
                    :incident_key, :title, :status, :root_cause_hypothesis,
                    :site_scope, :asset_scope, :business_impact_score,
                    :confidence, :opened_at, NOW()
                )
                ON CONFLICT (incident_key) DO UPDATE SET
                    title = EXCLUDED.title,
                    status = EXCLUDED.status,
                    root_cause_hypothesis = EXCLUDED.root_cause_hypothesis,
                    site_scope = EXCLUDED.site_scope,
                    asset_scope = EXCLUDED.asset_scope,
                    business_impact_score = EXCLUDED.business_impact_score,
                    confidence = EXCLUDED.confidence,
                    last_updated_at = NOW()
                RETURNING id, incident_key
                """
            ),
            {
                "incident_key": key,
                "title": cluster.get("title") or key,
                "status": cluster.get("status") or "open",
                "root_cause_hypothesis": cluster.get("root_cause_hypothesis") or "unknown",
                "site_scope": cluster.get("site_scope") or "global",
                "asset_scope": cluster.get("asset_scope"),
                "business_impact_score": float(cluster.get("business_impact_score") or 0.0),
                "confidence": float(cluster.get("confidence") or 0.0),
                "opened_at": cluster.get("opened_at") or datetime.utcnow(),
            },
        ).mappings().first()
        if row is None:
            continue
        incident_id = int(row["id"])
        incident_key = str(row["incident_key"])

        ticket_ids = [
            t["id"] for t in cluster.get("tickets", []) if t.get("id") is not None
        ]
        if ticket_ids:
            db.execute(
                text(
                    """
                    DELETE FROM incident_ticket_links
                    WHERE incident_id = :incident_id
                      AND link_type = 'primary'
                    """
                ),
                {"incident_id": incident_id},
            )
            for ticket_pk in ticket_ids:
                db.execute(
                    text(
                        """
                        INSERT INTO incident_ticket_links (
                            incident_id, ticket_id, link_type, confidence
                        )
                        VALUES (
                            :incident_id, :ticket_id, 'primary', :confidence
                        )
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {
                        "incident_id": incident_id,
                        "ticket_id": int(ticket_pk),
                        "confidence": float(cluster.get("confidence") or 0.0),
                    },
                )

        cluster_copy = dict(cluster)
        cluster_copy["id"] = incident_id
        cluster_copy["incident_key"] = incident_key
        cluster_copy["ticket_count"] = len(ticket_ids) or cluster.get("ticket_count", 0)
        persisted.append(cluster_copy)
    db.commit()
    return persisted


def list_persisted_incidents(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT
                i.id,
                i.incident_key,
                i.title,
                i.status,
                i.root_cause_hypothesis,
                i.site_scope,
                i.business_impact_score,
                i.confidence,
                i.opened_at,
                i.last_updated_at,
                COUNT(DISTINCT l.ticket_id) AS ticket_count
            FROM incidents i
            LEFT JOIN incident_ticket_links l ON l.incident_id = i.id
            GROUP BY i.id
            ORDER BY i.last_updated_at DESC, i.id DESC
            LIMIT 200
            """
        )
    ).mappings()
    result: list[dict[str, Any]] = []
    for r in rows:
        incident_id = int(r["id"])
        evidence = _fetch_graph_evidence(db, incident_id)
        result.append(
            {
                "id": incident_id,
                "incident_key": r["incident_key"],
                "title": r["title"],
                "status": r["status"],
                "root_cause_hypothesis": r["root_cause_hypothesis"],
                "site_scope": r["site_scope"],
                "ticket_count": int(r["ticket_count"] or 0),
                "confidence": float(r["confidence"] or 0.0),
                "business_impact_score": float(r["business_impact_score"] or 0.0),
                "opened_at": _iso(r["opened_at"]),
                "last_updated_at": _iso(r["last_updated_at"]),
                "graph_evidence": evidence,
            }
        )
    return result


def get_persisted_incident_detail(
    db: Session, incident_id: int
) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT
                i.id,
                i.incident_key,
                i.title,
                i.status,
                i.root_cause_hypothesis,
                i.site_scope,
                i.asset_scope,
                i.business_impact_score,
                i.confidence,
                i.opened_at,
                i.last_updated_at
            FROM incidents i
            WHERE i.id = :incident_id
            """
        ),
        {"incident_id": incident_id},
    ).mappings().first()
    if row is None:
        return None

    ticket_rows = db.execute(
        text(
            """
            SELECT
                t.id,
                t.ticket_id,
                t.title,
                t.status,
                t.priority,
                t.request_type,
                t.staff_assigned,
                t.requester,
                t.date_opened,
                t.created_at,
                l.confidence
            FROM incident_ticket_links l
            JOIN tickets t ON t.id = l.ticket_id
            WHERE l.incident_id = :incident_id
            ORDER BY t.date_opened DESC NULLS LAST, t.id DESC
            """
        ),
        {"incident_id": incident_id},
    ).mappings()

    tickets = []
    for t in ticket_rows:
        tickets.append(
            {
                "id": int(t["id"]),
                "ticket_id": t["ticket_id"],
                "title": t["title"],
                "status": t["status"],
                "priority_raw": t["priority"],
                "request_type": t["request_type"],
                "assignee": t["staff_assigned"],
                "requester": t["requester"],
                "date_opened": _iso(t["date_opened"]),
                "created_at": _iso(t["created_at"]),
                "link_confidence": float(t["confidence"] or 0.0),
            }
        )

    return {
        "incident": {
            "id": int(row["id"]),
            "incident_key": row["incident_key"],
            "title": row["title"],
            "status": row["status"],
            "root_cause_hypothesis": row["root_cause_hypothesis"],
            "site_scope": row["site_scope"],
            "asset_scope": row["asset_scope"],
            "business_impact_score": float(row["business_impact_score"] or 0.0),
            "confidence": float(row["confidence"] or 0.0),
            "opened_at": _iso(row["opened_at"]),
            "last_updated_at": _iso(row["last_updated_at"]),
            "ticket_count": len(tickets),
        },
        "tickets": tickets,
        "common_cause": row["root_cause_hypothesis"],
        "recommended_action": (
            f"Coordinate handling for {(row['root_cause_hypothesis'] or 'unknown').replace('_', ' ').lower()} cases."
        ),
        "graph_evidence": _build_graph_evidence(row, tickets),
    }


def _build_graph_evidence(row: Any, tickets: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive a stable graph-evidence summary from the cluster members.

    The graph is not queried here (this is a per-incident read path
    that is called many times); instead we surface the facts the
    cluster already carries and the operator can drill into the
    full graph via `/api/intelligence/health` or the command center.
    """
    site = row["site_scope"] or "global"
    sites = sorted({site})
    requesters = sorted({t["requester"] for t in tickets if t.get("requester")})
    assignees = sorted({t["assignee"] for t in tickets if t.get("assignee")})
    return {
        "shared_site": site,
        "distinct_sites": sites,
        "shared_requester_count": len(requesters),
        "shared_assignee_count": len(assignees),
        "primary_requesters": requesters[:3],
        "primary_assignees": assignees[:3],
        "evidence_basis": "site + requester + assignee + root_cause cluster",
    }


class IncidentPersistence:
    """Thin class wrapper that lets the incident_clustering module call
    persistence without depending on a module-level state.

    Currently exposes `upsert_cluster`, which is the low-level entry
    point used by the `find_or_create_incident` helper. Higher-level
    flows should still go through `persist_synthesized_incidents`.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_cluster(
        self,
        *,
        ticket_ids: list[int],
        root_cause: str,
        site: str | None,
        deterministic_key: str,
    ) -> int:
        """Upsert a cluster of ticket primary keys into `incidents`.

        The function reuses the existing per-cluster logic from
        `persist_synthesized_incidents` so that the resulting incident
        row, its `incident_ticket_links`, and any future metadata are
        written in one place.
        """
        # Build a minimal cluster payload compatible with the existing
        # `persist_synthesized_incidents` flow.
        cluster = {
            "title": f"{root_cause} cluster",
            "status": "open",
            "root_cause_hypothesis": root_cause,
            "site_scope": site or "global",
            "asset_scope": None,
            "business_impact_score": 0.0,
            "confidence": 0.0,
            "opened_at": None,
            "tickets": [{"id": pk} for pk in ticket_ids],
        }
        persisted = persist_synthesized_incidents(self.db, [cluster])
        if not persisted:
            raise RuntimeError("upsert_cluster: persist_synthesized_incidents returned empty")
        return int(persisted[0]["id"])


def _fetch_graph_evidence(db: Session, incident_id: int) -> dict[str, Any]:
    """Read the cluster's ticket links and return a compact graph-evidence
    summary: shared site, requester/assignee counts, and the top members."""
    site_row = db.execute(
        text("SELECT site_scope FROM incidents WHERE id = :iid"),
        {"iid": incident_id},
    ).mappings().first()
    shared_site: str = "global"
    if site_row is not None:
        site_value = site_row["site_scope"]
        if site_value:
            shared_site = str(site_value)

    rows = db.execute(
        text(
            """
            SELECT t.requester, t.staff_assigned
            FROM incident_ticket_links l
            JOIN tickets t ON t.id = l.ticket_id
            WHERE l.incident_id = :iid
            """
        ),
        {"iid": incident_id},
    ).mappings()
    requesters = sorted({r["requester"] for r in rows if r.get("requester")})
    assignees = sorted({r["staff_assigned"] for r in rows if r.get("staff_assigned")})
    return {
        "shared_site": shared_site,
        "distinct_sites": [shared_site] if shared_site else ["global"],
        "shared_requester_count": len(requesters),
        "shared_assignee_count": len(assignees),
        "primary_requesters": requesters[:3],
        "primary_assignees": assignees[:3],
        "evidence_basis": "site + requester + assignee + root_cause cluster",
    }


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        iso = value.isoformat()
        return str(iso) if iso is not None else None
    return str(value)
