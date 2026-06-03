"""Add missing performance indexes for N+1 avoidance and scale.

Revision ID: 20260603_130000
Revises: 20260602_110000
Create Date: 2026-06-03 13:00:00

Adds:
- tickets.category_id
- tickets.updated_at
(others like decision_ts, operator_feedback.ticket_id already indexed in prior migrations/models)
Safe to re-run (IF NOT EXISTS).
"""
from alembic import op


revision = "20260603_130000"
down_revision = "20260602_110000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tickets_category_id ON tickets (category_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tickets_updated_at ON tickets (updated_at)"
    )
    # Additional high-value ones for common filters/sorts if not present
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tickets_site_id ON tickets (site_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tickets_asset_id ON tickets (asset_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_recommendations_status ON recommendations (status)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_recommendations_status")
    op.execute("DROP INDEX IF EXISTS ix_tickets_asset_id")
    op.execute("DROP INDEX IF EXISTS ix_tickets_site_id")
    op.execute("DROP INDEX IF EXISTS ix_tickets_updated_at")
    op.execute("DROP INDEX IF EXISTS ix_tickets_category_id")
