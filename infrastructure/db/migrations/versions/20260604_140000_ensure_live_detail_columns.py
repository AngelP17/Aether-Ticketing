"""Ensure live ticket detail and decision columns exist.

Revision ID: 20260604_140000
Revises: 20260604_130000
"""
from alembic import op


revision = "20260604_140000"
down_revision = "20260604_130000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS custom_fields JSONB")
    op.execute("ALTER TABLE decision_records ADD COLUMN IF NOT EXISTS anomaly_zscore FLOAT")
    op.execute("ALTER TABLE decision_records ADD COLUMN IF NOT EXISTS graph_signal_density FLOAT DEFAULT 0.0")
    op.execute("ALTER TABLE decision_records ADD COLUMN IF NOT EXISTS band_rationale TEXT")
    op.execute("ALTER TABLE decision_records ADD COLUMN IF NOT EXISTS operator_action TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE decision_records DROP COLUMN IF EXISTS operator_action")
    op.execute("ALTER TABLE decision_records DROP COLUMN IF EXISTS band_rationale")
    op.execute("ALTER TABLE decision_records DROP COLUMN IF EXISTS graph_signal_density")
    op.execute("ALTER TABLE decision_records DROP COLUMN IF EXISTS anomaly_zscore")
    op.execute("ALTER TABLE tickets DROP COLUMN IF EXISTS custom_fields")
