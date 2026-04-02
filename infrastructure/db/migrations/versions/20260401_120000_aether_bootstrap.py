"""Bootstrap Aether operational tables.

Revision ID: 20260401_120000
Revises:
Create Date: 2026-04-01 12:00:00
"""

from alembic import op


revision = "20260401_120000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS clean_summary TEXT")
    op.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS source_hash VARCHAR(64)")
    op.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS site_id VARCHAR(100)")
    op.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS asset_id INTEGER")
    op.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP")
    op.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS source_system VARCHAR(50) DEFAULT 'legacy'")
    op.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS assets (
            id SERIAL PRIMARY KEY,
            asset_name VARCHAR(255) NOT NULL,
            asset_type VARCHAR(100),
            site_id VARCHAR(100),
            criticality VARCHAR(20),
            owner_team VARCHAR(100),
            dependency_json JSON
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS incidents (
            id SERIAL PRIMARY KEY,
            incident_key VARCHAR(50) UNIQUE NOT NULL,
            title VARCHAR(255) NOT NULL,
            status VARCHAR(50) DEFAULT 'open',
            root_cause_hypothesis VARCHAR(100),
            site_scope VARCHAR(255),
            asset_scope VARCHAR(255),
            business_impact_score DOUBLE PRECISION DEFAULT 0,
            confidence DOUBLE PRECISION DEFAULT 0,
            opened_at TIMESTAMP DEFAULT NOW(),
            closed_at TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_records (
            id SERIAL PRIMARY KEY,
            ticket_id INTEGER NOT NULL,
            incident_id INTEGER,
            decision_ts TIMESTAMP DEFAULT NOW(),
            feature_snapshot_json JSON,
            severity_score DOUBLE PRECISION DEFAULT 0,
            urgency_score DOUBLE PRECISION DEFAULT 0,
            business_impact_score DOUBLE PRECISION DEFAULT 0,
            sla_risk_score DOUBLE PRECISION DEFAULT 0,
            recurrence_score DOUBLE PRECISION DEFAULT 0,
            dependency_criticality_score DOUBLE PRECISION DEFAULT 0,
            actionability_score DOUBLE PRECISION DEFAULT 0,
            uncertainty_penalty DOUBLE PRECISION DEFAULT 0,
            priority_score DOUBLE PRECISION DEFAULT 0,
            root_cause_hypothesis VARCHAR(100),
            confidence_score DOUBLE PRECISION DEFAULT 0,
            decision_version VARCHAR(20) DEFAULT 'v1',
            rule_version VARCHAR(20) DEFAULT 'rules-2024-Q1',
            model_version VARCHAR(20),
            explanation_json JSON
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendations (
            id SERIAL PRIMARY KEY,
            decision_record_id INTEGER NOT NULL,
            rank INTEGER NOT NULL,
            action_type VARCHAR(50) NOT NULL,
            action_label VARCHAR(255) NOT NULL,
            rationale VARCHAR(500),
            risk_level VARCHAR(20) DEFAULT 'low',
            expected_benefit VARCHAR(255),
            confidence DOUBLE PRECISION DEFAULT 0,
            requires_approval BOOLEAN DEFAULT FALSE,
            recommended_runbook_id VARCHAR(50),
            status VARCHAR(20) DEFAULT 'proposed'
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ticket_events (
            id SERIAL PRIMARY KEY,
            ticket_id INTEGER NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            event_ts TIMESTAMP DEFAULT NOW(),
            actor_type VARCHAR(20) NOT NULL,
            actor_id VARCHAR(100),
            payload_json JSON,
            source_hash VARCHAR(64)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS operator_feedback (
            id SERIAL PRIMARY KEY,
            recommendation_id INTEGER NOT NULL,
            ticket_id INTEGER NOT NULL,
            feedback_type VARCHAR(30) NOT NULL,
            feedback_note VARCHAR(500),
            feedback_ts TIMESTAMP DEFAULT NOW(),
            operator_id VARCHAR(100)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_records (
            id SERIAL PRIMARY KEY,
            entity_type VARCHAR(30) NOT NULL,
            entity_id VARCHAR(50) NOT NULL,
            snapshot_ts TIMESTAMP NOT NULL,
            snapshot_json JSON NOT NULL,
            version_tag VARCHAR(30),
            reason VARCHAR(100)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_records")
    op.execute("DROP TABLE IF EXISTS operator_feedback")
    op.execute("DROP TABLE IF EXISTS ticket_events")
    op.execute("DROP TABLE IF EXISTS recommendations")
    op.execute("DROP TABLE IF EXISTS decision_records")
    op.execute("DROP TABLE IF EXISTS incidents")
    op.execute("DROP TABLE IF EXISTS assets")
