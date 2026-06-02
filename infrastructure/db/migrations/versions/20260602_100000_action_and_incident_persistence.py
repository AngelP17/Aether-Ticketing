"""Add incident persistence, recommendation timestamps, and action-run metadata.

Revision ID: 20260602_100000
Revises: 20260401_120000
Create Date: 2026-06-02 10:00:00

This migration enables stable incident IDs by giving `incidents` an upsertable
`last_updated_at` column, surfaces the rule-engine freshness on the
`recommendations` table via `created_at`, and ensures `action_runs` has the
columns the new ActionService needs to publish real mutations.
"""
from alembic import op


revision = "20260602_100000"
down_revision = "20260401_120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_recommendations_created_at "
        "ON recommendations (created_at DESC)"
    )

    op.execute(
        "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS last_updated_at TIMESTAMP DEFAULT NOW()"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_incidents_last_updated_at "
        "ON incidents (last_updated_at DESC)"
    )

    op.execute(
        "ALTER TABLE action_runs ADD COLUMN IF NOT EXISTS operator_note VARCHAR(500)"
    )
    op.execute(
        "ALTER TABLE action_runs ADD COLUMN IF NOT EXISTS rollback_payload_json JSON"
    )
    op.execute(
        "ALTER TABLE action_runs ADD COLUMN IF NOT EXISTS ticket_event_id BIGINT"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_action_runs_started_at ON action_runs (started_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_action_runs_started_at")
    op.execute("ALTER TABLE action_runs DROP COLUMN IF EXISTS ticket_event_id")
    op.execute("ALTER TABLE action_runs DROP COLUMN IF EXISTS rollback_payload_json")
    op.execute("ALTER TABLE action_runs DROP COLUMN IF EXISTS operator_note")
    op.execute("DROP INDEX IF EXISTS ix_incidents_last_updated_at")
    op.execute("ALTER TABLE incidents DROP COLUMN IF EXISTS last_updated_at")
    op.execute("DROP INDEX IF EXISTS ix_recommendations_created_at")
    op.execute("ALTER TABLE recommendations DROP COLUMN IF EXISTS created_at")
