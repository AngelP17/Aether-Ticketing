"""Add notifications table for Phase 5.

Revision ID: 20260603_140000
Revises: 20260603_130000
Create Date: 2026-06-03

Basic notifications for assignment, comments, SLA, etc.
"""
from alembic import op


revision = "20260603_140000"
down_revision = "20260603_130000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(100) NOT NULL,
            ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
            type VARCHAR(50) NOT NULL,
            title VARCHAR(200) NOT NULL,
            body VARCHAR(1000),
            payload_json JSONB,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_ticket_id ON notifications (ticket_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_is_read ON notifications (is_read)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications (created_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_notifications_created_at")
    op.execute("DROP INDEX IF EXISTS ix_notifications_is_read")
    op.execute("DROP INDEX IF EXISTS ix_notifications_ticket_id")
    op.execute("DROP INDEX IF EXISTS ix_notifications_user_id")
    op.execute("DROP TABLE IF EXISTS notifications")
