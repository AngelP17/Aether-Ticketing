from __future__ import annotations

from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.orm import Session


@lru_cache(maxsize=128)
def _table_columns_cached(database_url: str, table_name: str) -> frozenset[str]:
    from infrastructure.db.session import engine

    with engine.connect() as connection:
        rows = list(
            connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = :table_name
                    """
                ),
                {"table_name": table_name},
            )
        )
    return frozenset(str(row[0]) for row in rows)


@lru_cache(maxsize=64)
def _table_exists_cached(database_url: str, table_name: str) -> bool:
    from infrastructure.db.session import engine

    with engine.connect() as connection:
        return bool(
            connection.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = :table_name
                    )
                    """
                ),
                {"table_name": table_name},
            ).scalar()
        )


def table_columns(db: Session, table_name: str) -> frozenset[str]:
    if not hasattr(db, "get_bind"):
        return _modern_table_columns(table_name)
    return _table_columns_cached(_database_cache_key(db), table_name)


def table_exists(db: Session, table_name: str) -> bool:
    if not hasattr(db, "get_bind"):
        return bool(_modern_table_columns(table_name))
    return _table_exists_cached(_database_cache_key(db), table_name)


def _database_cache_key(db: Session) -> str:
    bind = db.get_bind()
    return str(getattr(bind, "url", ""))


def column_expr(
    db: Session,
    table_name: str,
    column_name: str,
    *,
    alias: str = "t",
    fallback: str = "NULL",
) -> str:
    if column_name in table_columns(db, table_name):
        return f"{alias}.{column_name}"
    return fallback


def category_join_sql(db: Session) -> tuple[str, str]:
    ticket_columns = table_columns(db, "tickets")
    has_category_join = (
        "category_id" in ticket_columns
        and table_exists(db, "categories")
        and "id" in table_columns(db, "categories")
        and "name" in table_columns(db, "categories")
    )
    if not has_category_join:
        return "NULL AS category_name", ""
    return "c.name AS category_name", "LEFT JOIN categories c ON c.id = t.category_id"


def _modern_table_columns(table_name: str) -> frozenset[str]:
    if table_name == "tickets":
        return frozenset(
            {
                "id",
                "ticket_id",
                "title",
                "status",
                "priority",
                "request_type",
                "category_id",
                "staff_assigned",
                "requester",
                "date_opened",
                "description",
                "resolution_notes",
                "created_at",
                "updated_at",
                "resolved_at",
                "clean_summary",
                "site_id",
                "asset_id",
            }
        )
    if table_name == "categories":
        return frozenset({"id", "name"})
    return frozenset()
