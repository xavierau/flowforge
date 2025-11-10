"""add_admin_audit_logs_table

Revision ID: 5d14d51c20c3
Revises: 54d4c2493a01
Create Date: 2025-11-05 14:51:44.350576

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5d14d51c20c3'
down_revision: Union[str, None] = '54d4c2493a01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create admin_audit_logs table for tracking admin actions."""
    op.create_table(
        'admin_audit_logs',
        # Identity
        sa.Column('id', sa.UUID(), nullable=False),

        # Actor (who performed the action)
        sa.Column('user_id', sa.UUID(), nullable=False),

        # Action details
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.UUID(), nullable=True),

        # Request details
        sa.Column('endpoint', sa.String(length=255), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),

        # Response details
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Additional metadata
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),

        # Timestamp
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Foreign key
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )

    # Create indexes for efficient querying
    op.create_index('idx_admin_audit_logs_user_id', 'admin_audit_logs', ['user_id'], unique=False)
    op.create_index('idx_admin_audit_logs_action', 'admin_audit_logs', ['action'], unique=False)
    op.create_index('idx_admin_audit_logs_resource', 'admin_audit_logs', ['resource_type', 'resource_id'], unique=False)
    op.create_index('idx_admin_audit_logs_created_at', 'admin_audit_logs', ['created_at'], unique=False)


def downgrade() -> None:
    """Drop admin_audit_logs table."""
    op.drop_index('idx_admin_audit_logs_created_at', table_name='admin_audit_logs')
    op.drop_index('idx_admin_audit_logs_resource', table_name='admin_audit_logs')
    op.drop_index('idx_admin_audit_logs_action', table_name='admin_audit_logs')
    op.drop_index('idx_admin_audit_logs_user_id', table_name='admin_audit_logs')
    op.drop_table('admin_audit_logs')
