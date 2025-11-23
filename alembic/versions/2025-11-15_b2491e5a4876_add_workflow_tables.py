"""add_workflow_tables

Revision ID: b2491e5a4876
Revises: d8f7226ad686
Create Date: 2025-11-15 10:50:38.491149

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'b2491e5a4876'
down_revision: Union[str, None] = 'd8f7226ad686'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create workflows table
    op.create_table(
        'workflows',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('current_version_number', sa.Integer, nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_workflows_tenant_id', 'workflows', ['tenant_id'])
    op.create_index('idx_workflows_is_active', 'workflows', ['is_active'])
    op.create_index('idx_workflows_created_at', 'workflows', ['created_at'])

    # Create workflow_versions table
    op.create_table(
        'workflow_versions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workflow_id', UUID(as_uuid=True), sa.ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('definition', JSONB, nullable=False),
        sa.Column('conductor_workflow_name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_workflow_versions_workflow_id', 'workflow_versions', ['workflow_id'])
    op.create_index('idx_workflow_versions_conductor_name', 'workflow_versions', ['conductor_workflow_name'])
    op.create_index('idx_workflow_versions_unique', 'workflow_versions', ['workflow_id', 'version_number'], unique=True)

    # Create workflow_executions table
    op.create_table(
        'workflow_executions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workflow_id', UUID(as_uuid=True), sa.ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workflow_version_id', UUID(as_uuid=True), sa.ForeignKey('workflow_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('conductor_workflow_id', sa.String(255), nullable=True),
        sa.Column('input_data', JSONB, nullable=False, server_default='{}'),
        sa.Column('output_data', JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('error_trace', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
    )
    op.create_index('idx_workflow_executions_tenant_id', 'workflow_executions', ['tenant_id'])
    op.create_index('idx_workflow_executions_workflow_id', 'workflow_executions', ['workflow_id'])
    op.create_index('idx_workflow_executions_status', 'workflow_executions', ['status'])
    op.create_index('idx_workflow_executions_created_at', 'workflow_executions', ['created_at'])
    op.create_index('idx_workflow_executions_conductor_id', 'workflow_executions', ['conductor_workflow_id'])

    # Create workflow_node_executions table
    op.create_table(
        'workflow_node_executions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workflow_execution_id', UUID(as_uuid=True), sa.ForeignKey('workflow_executions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('node_id', sa.String(255), nullable=False),
        sa.Column('node_type', sa.String(50), nullable=False),
        sa.Column('node_label', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('execution_order', sa.Integer, nullable=True),
        sa.Column('input_data', JSONB, nullable=True),
        sa.Column('output_data', JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('error_trace', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
    )
    op.create_index('idx_workflow_node_executions_workflow_execution_id', 'workflow_node_executions', ['workflow_execution_id'])
    op.create_index('idx_workflow_node_executions_node_id', 'workflow_node_executions', ['node_id'])
    op.create_index('idx_workflow_node_executions_status', 'workflow_node_executions', ['status'])
    op.create_index('idx_workflow_node_executions_created_at', 'workflow_node_executions', ['created_at'])
    op.create_index('idx_workflow_node_executions_unique', 'workflow_node_executions', ['workflow_execution_id', 'node_id'], unique=True)


def downgrade() -> None:
    # Drop tables in reverse order (due to foreign keys)
    op.drop_table('workflow_node_executions')
    op.drop_table('workflow_executions')
    op.drop_table('workflow_versions')
    op.drop_table('workflows')
