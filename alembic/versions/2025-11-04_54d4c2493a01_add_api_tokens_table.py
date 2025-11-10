"""add_api_tokens_table

Revision ID: 54d4c2493a01
Revises: 924445a7dc1b
Create Date: 2025-11-04 10:28:47.779793

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '54d4c2493a01'
down_revision: Union[str, None] = '924445a7dc1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create api_tokens table for external service authentication."""
    op.create_table(
        'api_tokens',
        # Identity
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),

        # Token data
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('token_prefix', sa.String(length=20), nullable=False),

        # Permissions & Scoping
        sa.Column('scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),

        # Expiration
        sa.Column('expires_at', sa.DateTime(), nullable=True),

        # Usage tracking
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_ip', sa.String(length=45), nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        # Audit trail
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_by_user_id', sa.UUID(), nullable=True),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['revoked_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )

    # Create indexes
    op.create_index('idx_api_tokens_user_id', 'api_tokens', ['user_id'], unique=False)
    op.create_index('idx_api_tokens_tenant_id', 'api_tokens', ['tenant_id'], unique=False)
    op.create_index('idx_api_tokens_token_hash', 'api_tokens', ['token_hash'], unique=True)
    op.create_index('idx_api_tokens_is_active', 'api_tokens', ['is_active'], unique=False)
    op.create_index('idx_api_tokens_expires_at', 'api_tokens', ['expires_at'], unique=False)


def downgrade() -> None:
    """Drop api_tokens table."""
    op.drop_index('idx_api_tokens_expires_at', table_name='api_tokens')
    op.drop_index('idx_api_tokens_is_active', table_name='api_tokens')
    op.drop_index('idx_api_tokens_token_hash', table_name='api_tokens')
    op.drop_index('idx_api_tokens_tenant_id', table_name='api_tokens')
    op.drop_index('idx_api_tokens_user_id', table_name='api_tokens')
    op.drop_table('api_tokens')
