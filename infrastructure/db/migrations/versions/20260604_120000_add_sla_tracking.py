"""Add ticket_sla_tracking table for full SLA (response/resolution breach tracking).

Revision ID: 20260604_120000
Revises: 20260604_110000_add_ticket_custom_fields
"""
from alembic import op
import sqlalchemy as sa

revision = '20260604_120000'
down_revision = '20260604_110000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ticket_sla_tracking',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('sla_policy_id', sa.Integer(), nullable=True),
        sa.Column('first_response_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('response_breach', sa.Boolean(), nullable=True),
        sa.Column('resolution_breach', sa.Boolean(), nullable=True),
        sa.Column('paused', sa.Boolean(), nullable=True),
        sa.Column('pause_reason', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ticket_sla_tracking_ticket_id'), 'ticket_sla_tracking', ['ticket_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ticket_sla_tracking_ticket_id'), table_name='ticket_sla_tracking')
    op.drop_table('ticket_sla_tracking')
