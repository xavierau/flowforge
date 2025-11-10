"""add_platform_settings_table

Revision ID: 7418694731d3
Revises: 34d31b85caab
Create Date: 2025-11-05 20:16:37.509545

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '7418694731d3'
down_revision: Union[str, None] = '34d31b85caab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create platform_settings table
    op.create_table(
        'platform_settings',
        sa.Column('key', sa.String(100), primary_key=True, nullable=False),
        sa.Column('value', JSONB, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String(50), nullable=False, server_default='general'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Create indexes
    # Note: 'key' is primary key, so no need for separate index
    op.create_index('ix_platform_settings_category', 'platform_settings', ['category'])

    # Seed default settings
    op.execute("""
        INSERT INTO platform_settings (key, value, description, category)
        VALUES
        (
            'trial_credits_amount',
            '100',
            'Number of credits automatically granted to new tenants on signup',
            'credits'
        )
    """)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_platform_settings_category', 'platform_settings')

    # Drop table
    op.drop_table('platform_settings')
