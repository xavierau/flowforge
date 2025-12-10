"""add_workflow_credentials_table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create workflow_credentials table for secure API key/secret storage."""
    op.create_table(
        'workflow_credentials',
        # Identity
        sa.Column('id', sa.UUID(), nullable=False),

        # Tenant isolation
        sa.Column('tenant_id', sa.UUID(), nullable=False),

        # Workflow scope (NULL = tenant-level)
        sa.Column('workflow_id', sa.UUID(), nullable=True),

        # Credential data
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Encrypted storage
        sa.Column('encrypted_value', sa.Text(), nullable=False),
        sa.Column('encryption_iv', sa.LargeBinary(), nullable=False),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        # Audit trail
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by_user_id', sa.UUID(), nullable=True),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Foreign keys
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),

        # Unique constraint: name must be unique within tenant+workflow scope
        sa.UniqueConstraint('tenant_id', 'workflow_id', 'name', name='uq_credential_scope_name'),
    )

    # Create indexes for common query patterns
    op.create_index('idx_credentials_tenant', 'workflow_credentials', ['tenant_id'], unique=False)
    op.create_index('idx_credentials_workflow', 'workflow_credentials', ['workflow_id'], unique=False)
    op.create_index('idx_credentials_is_active', 'workflow_credentials', ['is_active'], unique=False)
    op.create_index('idx_credentials_name', 'workflow_credentials', ['name'], unique=False)


def downgrade() -> None:
    """Drop workflow_credentials table."""
    op.drop_index('idx_credentials_name', table_name='workflow_credentials')
    op.drop_index('idx_credentials_is_active', table_name='workflow_credentials')
    op.drop_index('idx_credentials_workflow', table_name='workflow_credentials')
    op.drop_index('idx_credentials_tenant', table_name='workflow_credentials')
    op.drop_table('workflow_credentials')
