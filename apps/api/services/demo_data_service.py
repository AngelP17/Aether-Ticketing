from __future__ import annotations

import hashlib
import json
import logging
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


DEMO_ASSETS = [
    {
        "asset_name": "VPN Gateway",
        "asset_type": "Network",
        "site_id": "North Hub",
        "criticality": "high",
        "owner_team": "Infrastructure",
    },
    {
        "asset_name": "Exchange Online",
        "asset_type": "SaaS",
        "site_id": "HQ",
        "criticality": "medium",
        "owner_team": "Collaboration",
    },
    {
        "asset_name": "ERP Portal",
        "asset_type": "Application",
        "site_id": "Remote",
        "criticality": "critical",
        "owner_team": "Business Systems",
    },
    {
        "asset_name": "Directory",
        "asset_type": "Identity",
        "site_id": "HQ",
        "criticality": "high",
        "owner_team": "Identity",
    },
]


DEMO_TICKETS = [
    {
        "ticket_id": "IT-20260001",
        "title": "VPN access fails after password reset",
        "status": "Open",
        "priority": "High",
        "request_type": "Access",
        "staff_assigned": "Maya Chen",
        "requester": "Jordan Lee",
        "date_opened": date(2026, 5, 1),
        "description": "User cannot connect to VPN after a successful password reset.",
        "resolution_notes": "Pending identity sync review.",
        "site_id": "North Hub",
        "asset_name": "VPN Gateway",
    },
    {
        "ticket_id": "IT-20260002",
        "title": "Shared mailbox forwarding rule missing",
        "status": "In Progress",
        "priority": "Medium",
        "request_type": "Email",
        "staff_assigned": "Owen Patel",
        "requester": "Riley Brooks",
        "date_opened": date(2026, 5, 2),
        "description": "Finance shared mailbox stopped forwarding invoices.",
        "resolution_notes": "Forwarding rule recreated in test.",
        "site_id": "HQ",
        "asset_name": "Exchange Online",
    },
    {
        "ticket_id": "IT-20260003",
        "title": "Printer queue stuck on third floor",
        "status": "Open",
        "priority": "Low",
        "request_type": "Hardware",
        "staff_assigned": "Iris Morgan",
        "requester": "Casey Rivera",
        "date_opened": date(2026, 5, 3),
        "description": "Printer jobs remain queued for the third floor copier.",
        "resolution_notes": "Spooler restart scheduled.",
        "site_id": "HQ",
        "asset_name": None,
    },
    {
        "ticket_id": "IT-20260004",
        "title": "ERP approval page timing out",
        "status": "Open",
        "priority": "Critical",
        "request_type": "Application",
        "staff_assigned": "Maya Chen",
        "requester": "Taylor Kim",
        "date_opened": date(2026, 5, 4),
        "description": "Approvers see timeout errors on purchase requests.",
        "resolution_notes": "Escalated to application owner.",
        "site_id": "Remote",
        "asset_name": "ERP Portal",
    },
    {
        "ticket_id": "IT-20260005",
        "title": "Laptop disk encryption recovery prompt",
        "status": "Resolved",
        "priority": "Medium",
        "request_type": "Endpoint",
        "staff_assigned": "Iris Morgan",
        "requester": "Alex Grant",
        "date_opened": date(2026, 5, 5),
        "description": "Laptop requests recovery key after firmware update.",
        "resolution_notes": "Recovery key verified and TPM reset.",
        "site_id": "West Office",
        "asset_name": None,
    },
    {
        "ticket_id": "IT-20260006",
        "title": "New hire account missing groups",
        "status": "In Progress",
        "priority": "High",
        "request_type": "Access",
        "staff_assigned": "Noah Singh",
        "requester": "Morgan Ellis",
        "date_opened": date(2026, 5, 6),
        "description": "New hire can log in but lacks required operations groups.",
        "resolution_notes": "Access package approval pending.",
        "site_id": "HQ",
        "asset_name": "Directory",
    },
    {
        "ticket_id": "IT-20260007",
        "title": "Phishing report needs review",
        "status": "Open",
        "priority": "Medium",
        "request_type": "Security",
        "staff_assigned": "Owen Patel",
        "requester": "Jamie Stone",
        "date_opened": date(2026, 5, 7),
        "description": "Suspicious email reported by multiple users.",
        "resolution_notes": "Headers collected for review.",
        "site_id": "Remote",
        "asset_name": None,
    },
    {
        "ticket_id": "IT-20260008",
        "title": "Warehouse scanner cannot sync inventory",
        "status": "Open",
        "priority": "High",
        "request_type": "Endpoint",
        "staff_assigned": "Noah Singh",
        "requester": "Sam Rivera",
        "date_opened": date(2026, 5, 8),
        "description": "Scanner batch uploads fail after the latest app update.",
        "resolution_notes": "Rollback package staged.",
        "site_id": "South Warehouse",
        "asset_name": None,
    },
]


def reset_demo_dataset(db: Session) -> None:
    """Replace ticket-derived state with synthetic records for public demos."""
    _truncate_demo_owned_tables(db)
    asset_ids = _seed_assets(db)
    _seed_assignees(db)
    _seed_categories(db)
    _seed_labels(db)
    ticket_pks = _seed_tickets(db, asset_ids)
    _seed_incident(db, ticket_pks)
    db.commit()
    logger.info("demo dataset reset completed: tickets=%s", len(DEMO_TICKETS))


def _truncate_demo_owned_tables(db: Session) -> None:
    db.execute(
        text(
            """
            TRUNCATE TABLE
                action_runs,
                operator_feedback,
                recommendations,
                decision_records,
                similar_case_links,
                incident_ticket_links,
                incidents,
                ticket_events,
                ticket_comments,
                ticket_attachments,
                ticket_labels,
                ticket_sla_tracking,
                tickets,
                assets,
                assignees,
                labels,
                categories
            RESTART IDENTITY CASCADE
            """
        )
    )


def _seed_assets(db: Session) -> dict[str, int]:
    asset_ids: dict[str, int] = {}
    for asset in DEMO_ASSETS:
        row = db.execute(
            text(
                """
                INSERT INTO assets (
                    asset_name, asset_type, site_id, criticality, owner_team, dependency_json
                )
                VALUES (
                    :asset_name, :asset_type, :site_id, :criticality, :owner_team,
                    CAST(:dependency_json AS JSON)
                )
                RETURNING id
                """
            ),
            {**asset, "dependency_json": json.dumps({"demo": True})},
        ).mappings().one()
        asset_ids[asset["asset_name"]] = int(row["id"])
    return asset_ids


def _seed_assignees(db: Session) -> None:
    columns = {
        row["column_name"]
        for row in db.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'assignees'
                """
            )
        ).mappings()
    }
    for display_name in sorted({str(ticket["staff_assigned"]) for ticket in DEMO_TICKETS}):
        if "name" in columns:
            db.execute(
                text(
                    """
                    INSERT INTO assignees (name, display_name, is_active, created_at)
                    VALUES (:display_name, :display_name, TRUE, NOW())
                    """
                ),
                {"display_name": display_name},
            )
        else:
            db.execute(
                text(
                    """
                    INSERT INTO assignees (display_name, is_active, created_at)
                    VALUES (:display_name, TRUE, NOW())
                    """
                ),
                {"display_name": display_name},
            )


def _seed_categories(db: Session) -> None:
    categories = [
        ("Access", "#f59e0b", "key-round", 10),
        ("Application", "#38bdf8", "layout-dashboard", 20),
        ("Endpoint", "#34d399", "laptop", 30),
        ("Email", "#a78bfa", "mail", 40),
        ("Hardware", "#94a3b8", "printer", 50),
        ("Security", "#fb7185", "shield-alert", 60),
    ]
    for name, color, icon, sort_order in categories:
        db.execute(
            text(
                """
                INSERT INTO categories (name, color, icon, is_custom, is_active, sort_order)
                VALUES (:name, :color, :icon, FALSE, TRUE, :sort_order)
                """
            ),
            {"name": name, "color": color, "icon": icon, "sort_order": sort_order},
        )


def _seed_labels(db: Session) -> None:
    for name, color in [
        ("demo", "#f59e0b"),
        ("customer-impact", "#fb7185"),
        ("needs-triage", "#38bdf8"),
        ("workflow", "#34d399"),
    ]:
        db.execute(
            text("INSERT INTO labels (name, color, created_at) VALUES (:name, :color, NOW())"),
            {"name": name, "color": color},
        )


def _seed_tickets(db: Session, asset_ids: dict[str, int]) -> dict[str, int]:
    ticket_pks: dict[str, int] = {}
    for ticket in DEMO_TICKETS:
        source_hash = _source_hash(ticket)
        custom_fields = {
            "demo": True,
            "sanitized": True,
            "source": "synthetic_seed",
        }
        row = db.execute(
            text(
                """
                INSERT INTO tickets (
                    ticket_id,
                    title,
                    clean_summary,
                    status,
                    priority,
                    request_type,
                    staff_assigned,
                    requester,
                    date_opened,
                    description,
                    resolution_notes,
                    source_hash,
                    site_id,
                    asset_id,
                    source_system,
                    is_active,
                    custom_fields,
                    created_at,
                    updated_at
                )
                VALUES (
                    :ticket_id,
                    :title,
                    :clean_summary,
                    :status,
                    :priority,
                    :request_type,
                    :staff_assigned,
                    :requester,
                    :date_opened,
                    :description,
                    :resolution_notes,
                    :source_hash,
                    :site_id,
                    :asset_id,
                    'demo_seed',
                    TRUE,
                    CAST(:custom_fields AS JSONB),
                    NOW(),
                    NOW()
                )
                RETURNING id
                """
            ),
            {
                **ticket,
                "clean_summary": ticket["description"],
                "source_hash": source_hash,
                "asset_id": asset_ids.get(str(ticket["asset_name"])),
                "custom_fields": json.dumps(custom_fields),
            },
        ).mappings().one()
        ticket_pk = int(row["id"])
        ticket_pks[str(ticket["ticket_id"])] = ticket_pk
        db.execute(
            text(
                """
                INSERT INTO ticket_events (
                    ticket_id, event_type, event_ts, actor_type, actor_id, payload_json, source_hash
                )
                VALUES (
                    :ticket_pk, 'demo_seeded', NOW(), 'system', 'demo-seed',
                    CAST(:payload_json AS JSON), :source_hash
                )
                """
            ),
            {
                "ticket_pk": ticket_pk,
                "payload_json": json.dumps({"demo": True, "status": ticket["status"]}),
                "source_hash": source_hash,
            },
        )
    return ticket_pks


def _seed_incident(db: Session, ticket_pks: dict[str, int]) -> None:
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
                'INC-DEMO-001',
                'Identity sync disruption affecting access requests',
                'investigating',
                'Identity propagation delay',
                'HQ, North Hub',
                'Directory, VPN Gateway',
                72,
                0.84,
                NOW(),
                NOW()
            )
            RETURNING id
            """
        )
    ).mappings().one()
    incident_id = int(row["id"])
    for ticket_id in ["IT-20260001", "IT-20260006"]:
        db.execute(
            text(
                """
                INSERT INTO incident_ticket_links (
                    incident_id, ticket_id, link_type, confidence
                )
                VALUES (:incident_id, :ticket_pk, 'correlated', 0.88)
                """
            ),
            {"incident_id": incident_id, "ticket_pk": ticket_pks[ticket_id]},
        )


def _source_hash(ticket: dict[str, Any]) -> str:
    payload = "|".join(
        [
            str(ticket["ticket_id"]),
            str(ticket["title"]),
            str(ticket["status"]),
            str(ticket["description"]),
        ]
    )
    return hashlib.sha256(payload.encode()).hexdigest()
