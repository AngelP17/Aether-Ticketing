from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from apps.api.config import settings


def clean_database_url(url: str) -> str:
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    for param in ["channel_binding", "options"]:
        params.pop(param, None)

    clean_params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
    new_query = urlencode(clean_params)
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )


engine = create_engine(
    clean_database_url(settings.DATABASE_URL),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_use_lifo=True,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    _import_models()

    from infrastructure.db.base import Base

    Base.metadata.create_all(bind=engine)
    _ensure_legacy_compatibility()


def _import_models() -> None:
    import infrastructure.db.models.action_run  # noqa: F401
    import infrastructure.db.models.assignee  # noqa: F401
    import infrastructure.db.models.asset  # noqa: F401
    import infrastructure.db.models.audit_record  # noqa: F401
    import infrastructure.db.models.category  # noqa: F401
    import infrastructure.db.models.decision_record  # noqa: F401
    import infrastructure.db.models.incident  # noqa: F401
    import infrastructure.db.models.incident_ticket_link  # noqa: F401
    import infrastructure.db.models.label  # noqa: F401
    import infrastructure.db.models.operator_feedback  # noqa: F401
    import infrastructure.db.models.recommendation  # noqa: F401
    import infrastructure.db.models.similar_case_link  # noqa: F401
    import infrastructure.db.models.ticket  # noqa: F401
    import infrastructure.db.models.ticket_attachment  # noqa: F401
    import infrastructure.db.models.ticket_comment  # noqa: F401
    import infrastructure.db.models.ticket_event  # noqa: F401


def _ensure_legacy_compatibility() -> None:
    statements_by_column = {
        "clean_summary": "ALTER TABLE tickets ADD COLUMN clean_summary TEXT",
        "source_hash": "ALTER TABLE tickets ADD COLUMN source_hash VARCHAR(64)",
        "site_id": "ALTER TABLE tickets ADD COLUMN site_id VARCHAR(100)",
        "asset_id": "ALTER TABLE tickets ADD COLUMN asset_id INTEGER",
        "category_id": "ALTER TABLE tickets ADD COLUMN category_id INTEGER REFERENCES categories(id)",
        "resolved_at": "ALTER TABLE tickets ADD COLUMN resolved_at TIMESTAMP",
        "source_system": "ALTER TABLE tickets ADD COLUMN source_system VARCHAR(50) DEFAULT 'legacy'",
        "is_active": "ALTER TABLE tickets ADD COLUMN is_active BOOLEAN DEFAULT TRUE",
    }

    with engine.begin() as connection:
        existing_columns = {
            row[0]
            for row in connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'tickets'
                    """
                )
            )
        }
        for column_name, statement in statements_by_column.items():
            if column_name in existing_columns:
                continue
            connection.execute(text(statement))

        compatibility_statements = [
            """
            CREATE TABLE IF NOT EXISTS ticket_labels (
                ticket_id VARCHAR(20) REFERENCES tickets(ticket_id) ON DELETE CASCADE,
                label_id INTEGER REFERENCES labels(id) ON DELETE CASCADE,
                PRIMARY KEY (ticket_id, label_id)
            )
            """,
            """
            ALTER TABLE ticket_attachments
            ADD COLUMN IF NOT EXISTS comment_id INTEGER REFERENCES ticket_comments(id) ON DELETE CASCADE
            """,
            """
            ALTER TABLE ticket_attachments
            ADD COLUMN IF NOT EXISTS uploaded_by VARCHAR(100)
            """,
            """
            ALTER TABLE ticket_comments
            ADD COLUMN IF NOT EXISTS author_display_name VARCHAR(100)
            """,
            """
            ALTER TABLE ticket_comments
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """,
        ]
        for statement in compatibility_statements:
            connection.execute(text(statement))
