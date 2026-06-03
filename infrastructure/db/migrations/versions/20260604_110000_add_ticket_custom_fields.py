"""Add custom_fields JSONB to tickets for OSS hybrid forms/integrations.

Revision ID: 20260604_110000
Revises: 20260604_100000_phase8_competitor_tables
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260604_110000'
down_revision = '20260604_100000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'tickets',
        sa.Column('custom_fields', postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )
    # Optional index for future JSON queries if needed (GIN for containment etc.)
    # op.create_index('ix_tickets_custom_fields_gin', 'tickets', ['custom_fields'], postgresql_using='gin')


def downgrade() -> None:
    op.drop_column('tickets', 'custom_fields')
