"""
Similar Cases: Find prior tickets with similar text for operational memory.

Public entry points:

- `find_similar_cases(ticket_id, top_k=5)` — DB-backed retrieval that prefers the
  precomputed `similar_case_links` table and falls back to an on-the-fly
  Jaccard overlap score over recent tickets. Returns the same shape the API
  layer has always consumed.
- `compute_text_similarity(text_a, text_b)` — pure helper used by both
  find_similar_cases and the offline `rebuild_similarity_index.py` script.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from infrastructure.db.session import get_db_context


def find_similar_cases(ticket_id: str, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Return similar prior cases for the given external `ticket_id`.

    The function reads from `similar_case_links` (populated by
    `scripts/rebuild_similarity_index.py`) and falls back to a live
    Jaccard-overlap scan if no cached links exist for the ticket.
    """
    with get_db_context() as db:
        cached_rows = list(
            db.execute(
                text(
                    """
                    SELECT
                        st.ticket_id AS similar_ticket_id,
                        st.title,
                        st.status,
                        st.priority,
                        st.request_type,
                        st.staff_assigned,
                        st.requester,
                        st.date_opened,
                        scl.similarity_score
                    FROM similar_case_links scl
                    JOIN tickets t ON t.id = scl.ticket_id
                    JOIN tickets st ON st.id = scl.similar_ticket_id
                    WHERE t.ticket_id = :ticket_id
                    ORDER BY scl.similarity_score DESC
                    LIMIT :top_k
                    """
                ),
                {"ticket_id": ticket_id, "top_k": top_k},
            ).mappings()
        )
        if cached_rows:
            return [_format_cached(row) for row in cached_rows]

        return _live_overlap(db, ticket_id, top_k)


def _format_cached(row: Any) -> dict[str, Any]:
    return {
        "ticket_id": row["similar_ticket_id"],
        "title": row["title"],
        "status": row["status"],
        "priority_raw": row["priority"],
        "assignee": row["staff_assigned"],
        "requester": row["requester"],
        "date_opened": _iso(row["date_opened"]),
        "similarity_score": float(row["similarity_score"] or 0.0),
        "match_basis": "precomputed_index",
    }


def _live_overlap(db: Session, ticket_id: str, top_k: int) -> list[dict[str, Any]]:
    source = db.execute(
        text(
            """
            SELECT id, title, description
            FROM tickets
            WHERE ticket_id = :ticket_id
            """
        ),
        {"ticket_id": ticket_id},
    ).mappings().first()
    if source is None:
        return []
    source_text = f"{source['title'] or ''} {source['description'] or ''}".strip()
    if not source_text:
        return []

    candidates = list(
        db.execute(
            text(
                """
                SELECT id, ticket_id, title, description, status, priority,
                       request_type, staff_assigned, requester, date_opened
                FROM tickets
                WHERE id != :source_id
                ORDER BY date_opened DESC NULLS LAST, id DESC
                LIMIT 200
                """
            ),
            {"source_id": source["id"]},
        ).mappings()
    )

    scored: list[tuple[float, dict[str, Any]]] = []
    for cand in candidates:
        cand_text = f"{cand['title'] or ''} {cand['description'] or ''}".strip()
        if not cand_text:
            continue
        score = compute_text_similarity(source_text, cand_text)
        if score > 0:
            scored.append(
                (
                    score,
                    {
                        "ticket_id": cand["ticket_id"],
                        "title": cand["title"],
                        "status": cand["status"],
                        "priority_raw": cand["priority"],
                        "request_type": cand["request_type"],
                        "assignee": cand["staff_assigned"],
                        "requester": cand["requester"],
                        "date_opened": _iso(cand["date_opened"]),
                        "similarity_score": round(score, 4),
                        "match_basis": "live_overlap",
                    },
                )
            )
    scored.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in scored[:top_k]]


def compute_text_similarity(text_a: str, text_b: str) -> float:
    """Compute text similarity 0.0–1.0 between two text strings (Jaccard overlap)."""
    words_a = [word for word in (text_a or "").lower().split() if word]
    words_b = [word for word in (text_b or "").lower().split() if word]
    if not words_a or not words_b:
        return 0.0

    counter_a = Counter(words_a)
    counter_b = Counter(words_b)
    shared = set(counter_a).intersection(counter_b)
    numerator = sum(min(counter_a[word], counter_b[word]) for word in shared)
    denominator = max(sum(counter_a.values()), sum(counter_b.values()))
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        iso = value.isoformat()
        return str(iso) if iso is not None else None
    return str(value)
