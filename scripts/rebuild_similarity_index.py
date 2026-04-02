from __future__ import annotations

import argparse

from sqlalchemy import text

from infrastructure.db.session import get_db_context, init_db
from pipelines.retrieval.similar_cases import compute_text_similarity


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild the lightweight Aether similar-case index."
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.35,
        help="Minimum text similarity score required to persist a case link.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Maximum number of similar tickets to retain per ticket.",
    )
    args = parser.parse_args()

    init_db()
    with get_db_context() as db:
        rows = list(
            db.execute(
                text(
                    """
                    SELECT id, ticket_id, title, description, status, date_opened
                    FROM tickets
                    ORDER BY date_opened DESC NULLS LAST, id DESC
                    """
                )
            ).mappings()
        )

        db.execute(text("DELETE FROM similar_case_links"))

        inserted = 0
        for source in rows:
            scored_matches: list[tuple[float, dict]] = []
            source_text = f"{source['title'] or ''} {source['description'] or ''}".strip()
            if not source_text:
                continue

            for candidate in rows:
                if candidate["id"] == source["id"]:
                    continue
                candidate_text = f"{candidate['title'] or ''} {candidate['description'] or ''}".strip()
                score = compute_text_similarity(source_text, candidate_text)
                if score >= args.threshold:
                    scored_matches.append((score, candidate))

            scored_matches.sort(key=lambda item: item[0], reverse=True)
            for score, candidate in scored_matches[: args.top_k]:
                resolution_effective = "yes" if candidate["status"] in {"Resolved", "Closed"} else "unknown"
                db.execute(
                    text(
                        """
                        INSERT INTO similar_case_links (
                            ticket_id,
                            similar_ticket_id,
                            similarity_score,
                            match_basis_json,
                            resolution_effective,
                            time_to_resolve_hours
                        )
                        VALUES (
                            :ticket_id,
                            :similar_ticket_id,
                            :similarity_score,
                            CAST(:match_basis_json AS JSONB),
                            :resolution_effective,
                            NULL
                        )
                        """
                    ),
                    {
                        "ticket_id": source["id"],
                        "similar_ticket_id": candidate["id"],
                        "similarity_score": score,
                        "match_basis_json": (
                            '{"basis":"title_description_overlap","source_ticket":"%s","matched_ticket":"%s"}'
                            % (source["ticket_id"], candidate["ticket_id"])
                        ),
                        "resolution_effective": resolution_effective,
                    },
                )
                inserted += 1

        db.commit()
        print(f"Tickets scanned: {len(rows)}")
        print(f"Similar-case links rebuilt: {inserted}")
        print(f"Threshold used: {args.threshold}")


if __name__ == "__main__":
    main()
