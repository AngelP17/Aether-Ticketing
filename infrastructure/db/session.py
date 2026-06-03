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
    import infrastructure.db.models.article  # noqa: F401
    import infrastructure.db.models.sla_policy  # noqa: F401
    import infrastructure.db.models.webhook  # noqa: F401
    import infrastructure.db.models.ticket_sla_tracking  # noqa: F401
    import infrastructure.db.models.dashboard_layout  # noqa: F401
    import infrastructure.db.models.user_preference  # noqa: F401
    import infrastructure.db.models.notification  # noqa: F401


def _ensure_legacy_compatibility() -> None:
    ticket_statements = {
        "clean_summary": "ALTER TABLE tickets ADD COLUMN clean_summary TEXT",
        "source_hash": "ALTER TABLE tickets ADD COLUMN source_hash VARCHAR(64)",
        "site_id": "ALTER TABLE tickets ADD COLUMN site_id VARCHAR(100)",
        "asset_id": "ALTER TABLE tickets ADD COLUMN asset_id INTEGER",
        "category_id": "ALTER TABLE tickets ADD COLUMN category_id INTEGER REFERENCES categories(id)",
        "root_cause_hypothesis": "ALTER TABLE tickets ADD COLUMN root_cause_hypothesis VARCHAR(100)",
        "priority_score_cache": "ALTER TABLE tickets ADD COLUMN priority_score_cache INTEGER",
        "confidence_score_cache": "ALTER TABLE tickets ADD COLUMN confidence_score_cache INTEGER",
        "created_at": "ALTER TABLE tickets ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "ALTER TABLE tickets ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "resolved_at": "ALTER TABLE tickets ADD COLUMN resolved_at TIMESTAMP",
        "source_system": "ALTER TABLE tickets ADD COLUMN source_system VARCHAR(50) DEFAULT 'legacy'",
        "is_active": "ALTER TABLE tickets ADD COLUMN is_active BOOLEAN DEFAULT TRUE",
        "custom_fields": "ALTER TABLE tickets ADD COLUMN custom_fields JSONB",
    }

    decision_statements = {
        "decision_band": "ALTER TABLE decision_records ADD COLUMN decision_band VARCHAR(40)",
        "priority_interval_low": "ALTER TABLE decision_records ADD COLUMN priority_interval_low FLOAT",
        "priority_interval_high": "ALTER TABLE decision_records ADD COLUMN priority_interval_high FLOAT",
        "decision_hash": "ALTER TABLE decision_records ADD COLUMN decision_hash VARCHAR(64)",
        "graph_degree": "ALTER TABLE decision_records ADD COLUMN graph_degree INTEGER DEFAULT 0",
        "graph_weighted_degree": "ALTER TABLE decision_records ADD COLUMN graph_weighted_degree FLOAT DEFAULT 0.0",
        "anomaly_zscore": "ALTER TABLE decision_records ADD COLUMN anomaly_zscore FLOAT",
        "graph_signal_density": "ALTER TABLE decision_records ADD COLUMN graph_signal_density FLOAT DEFAULT 0.0",
        "band_rationale": "ALTER TABLE decision_records ADD COLUMN band_rationale TEXT",
        "operator_action": "ALTER TABLE decision_records ADD COLUMN operator_action TEXT",
        "explanation_json": "ALTER TABLE decision_records ADD COLUMN explanation_json JSONB",
    }

    incident_statements = {
        "last_updated_at": "ALTER TABLE incidents ADD COLUMN last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "closed_at": "ALTER TABLE incidents ADD COLUMN closed_at TIMESTAMP",
        "asset_scope": "ALTER TABLE incidents ADD COLUMN asset_scope VARCHAR(255)",
    }

    recommendation_statements = {
        "created_at": "ALTER TABLE recommendations ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    }

    action_run_statements = {
        "operator_note": "ALTER TABLE action_runs ADD COLUMN operator_note VARCHAR(500)",
        "rollback_payload_json": "ALTER TABLE action_runs ADD COLUMN rollback_payload_json JSON",
        "ticket_event_id": "ALTER TABLE action_runs ADD COLUMN ticket_event_id BIGINT",
    }

    with engine.begin() as connection:
        for table_name, statements in [
            ("tickets", ticket_statements),
            ("decision_records", decision_statements),
            ("incidents", incident_statements),
            ("recommendations", recommendation_statements),
            ("action_runs", action_run_statements),
        ]:
            existing_columns = {
                row[0]
                for row in connection.execute(
                    text(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = :tbl
                        """
                    ),
                    {"tbl": table_name},
                )
            }
            for column_name, statement in statements.items():
                if column_name in existing_columns:
                    continue
                connection.execute(text(statement))

        compatibility_statements = [
            """
            CREATE TABLE IF NOT EXISTS automation_rules (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                enabled BOOLEAN DEFAULT TRUE,
                trigger_type VARCHAR(50) NOT NULL,
                conditions JSONB NOT NULL DEFAULT '[]',
                actions JSONB NOT NULL DEFAULT '[]',
                execution_count INTEGER DEFAULT 0,
                last_executed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_automation_rules_enabled_trigger
            ON automation_rules (enabled, trigger_type)
            """,
            """
            CREATE TABLE IF NOT EXISTS automation_execution_log (
                id SERIAL PRIMARY KEY,
                rule_id INTEGER REFERENCES automation_rules(id) ON DELETE SET NULL,
                ticket_id VARCHAR(50),
                trigger_event JSONB,
                actions_taken JSONB,
                executed_at TIMESTAMP DEFAULT NOW()
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_automation_execution_log_rule_id
            ON automation_execution_log (rule_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_automation_execution_log_ticket_id
            ON automation_execution_log (ticket_id)
            """,
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
