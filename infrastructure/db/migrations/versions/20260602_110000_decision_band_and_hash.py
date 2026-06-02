"""Add decision band, priority interval, decision hash, and graph features.

Revision ID: 20260602_110000
Revises: 20260602_100000
Create Date: 2026-06-02 11:00:00

This migration adds the columns required by the v2 deterministic
graph/rules decision engine:

- ``decision_records.decision_band`` — one of ``high_confidence_action``,
  ``review_needed``, or ``standard_queue``.
- ``decision_records.priority_interval_low`` / ``priority_interval_high``
  — the score interval that expresses uncertainty around the point score.
- ``decision_records.decision_hash`` — SHA-256 fingerprint of the
  decision inputs (ticket id, scores, band, root cause, feature snapshot,
  explanation, rule version).

The migration is idempotent and safe to re-run.
"""
from alembic import op


revision = "20260602_110000"
down_revision = "20260602_100000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE decision_records ADD COLUMN IF NOT EXISTS decision_band VARCHAR(40)"
    )
    op.execute(
        "ALTER TABLE decision_records ADD COLUMN IF NOT EXISTS "
        "priority_interval_low DOUBLE PRECISION"
    )
    op.execute(
        "ALTER TABLE decision_records ADD COLUMN IF NOT EXISTS "
        "priority_interval_high DOUBLE PRECISION"
    )
    op.execute(
        "ALTER TABLE decision_records ADD COLUMN IF NOT EXISTS "
        "decision_hash VARCHAR(64)"
    )
    op.execute(
        "ALTER TABLE decision_records ADD COLUMN IF NOT EXISTS "
        "graph_degree INTEGER DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE decision_records ADD COLUMN IF NOT EXISTS "
        "graph_weighted_degree DOUBLE PRECISION DEFAULT 0.0"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_decision_records_decision_band "
        "ON decision_records (decision_band)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_decision_records_decision_hash "
        "ON decision_records (decision_hash)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_decision_records_decision_hash")
    op.execute("DROP INDEX IF EXISTS ix_decision_records_decision_band")
    op.execute("ALTER TABLE decision_records DROP COLUMN IF EXISTS graph_weighted_degree")
    op.execute("ALTER TABLE decision_records DROP COLUMN IF EXISTS graph_degree")
    op.execute("ALTER TABLE decision_records DROP COLUMN IF EXISTS decision_hash")
    op.execute("ALTER TABLE decision_records DROP COLUMN IF EXISTS priority_interval_high")
    op.execute("ALTER TABLE decision_records DROP COLUMN IF EXISTS priority_interval_low")
    op.execute("ALTER TABLE decision_records DROP COLUMN IF EXISTS decision_band")
