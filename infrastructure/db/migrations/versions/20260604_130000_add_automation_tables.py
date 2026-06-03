"""Add automation rule tables for in-house if/then workflows.

Revision ID: 20260604_130000
Revises: 20260604_120000
"""
from alembic import op


revision = "20260604_130000"
down_revision = "20260604_120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
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
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_automation_rules_enabled_trigger "
        "ON automation_rules (enabled, trigger_type)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS automation_execution_log (
            id SERIAL PRIMARY KEY,
            rule_id INTEGER REFERENCES automation_rules(id) ON DELETE SET NULL,
            ticket_id VARCHAR(50),
            trigger_event JSONB,
            actions_taken JSONB,
            executed_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_automation_execution_log_rule_id "
        "ON automation_execution_log (rule_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_automation_execution_log_ticket_id "
        "ON automation_execution_log (ticket_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS automation_execution_log")
    op.execute("DROP TABLE IF EXISTS automation_rules")
