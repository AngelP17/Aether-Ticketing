"""Phase 8 competitor parity tables: articles (KB), webhooks, sla_policies, user_preferences, dashboard_layouts.

Revision ID: 20260604_100000
Revises: 20260603_140000
Create Date: 2026-06-04

Extends for email/WS/portal/RBAC/builder/SLA/KB/webhooks parity with Datto/Jira/Zendesk.
"""
from alembic import op


revision = "20260604_100000"
down_revision = "20260603_140000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Articles (KB)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id SERIAL PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            body TEXT NOT NULL,
            root_cause_class VARCHAR(100),
            author_id VARCHAR(100),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_articles_root_cause_class ON articles (root_cause_class)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_articles_created_at ON articles (created_at)")

    # Webhooks
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS webhooks (
            id SERIAL PRIMARY KEY,
            url VARCHAR(500) NOT NULL,
            secret VARCHAR(200),
            events JSONB NOT NULL DEFAULT '[]',
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_webhooks_active ON webhooks (active)")

    # SLA Policies
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sla_policies (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            priority VARCHAR(20),
            category VARCHAR(100),
            target_hours FLOAT NOT NULL,
            warn_at_percent FLOAT DEFAULT 75.0,
            breach_action VARCHAR(50) DEFAULT 'escalate',
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_sla_policies_priority ON sla_policies (priority)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sla_policies_category ON sla_policies (category)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sla_policies_active ON sla_policies (active)")

    # User Preferences (for theme, dashboard etc)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_preferences (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            key VARCHAR(100) NOT NULL,
            value_json JSONB,
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_user_preferences_user_key ON user_preferences (username, key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_preferences_username ON user_preferences (username)")

    # Dashboard Layouts (for builder)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS dashboard_layouts (
            id SERIAL PRIMARY KEY,
            owner_username VARCHAR(100) NOT NULL,
            name VARCHAR(100) NOT NULL,
            widgets_json JSONB NOT NULL DEFAULT '[]',
            is_default BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_dashboard_layouts_owner ON dashboard_layouts (owner_username)")

    # Optional: extend notifications for email delivery status (add column if not present)
    op.execute(
        """
        ALTER TABLE notifications
        ADD COLUMN IF NOT EXISTS delivery_status VARCHAR(20) DEFAULT 'pending',
        ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMP
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE notifications DROP COLUMN IF EXISTS delivered_at")
    op.execute("ALTER TABLE notifications DROP COLUMN IF EXISTS delivery_status")
    op.execute("DROP TABLE IF EXISTS dashboard_layouts")
    op.execute("DROP TABLE IF EXISTS user_preferences")
    op.execute("DROP TABLE IF EXISTS sla_policies")
    op.execute("DROP TABLE IF EXISTS webhooks")
    op.execute("DROP TABLE IF EXISTS articles")
