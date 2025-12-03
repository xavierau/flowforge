"""add_hitl_tables

Revision ID: 306f7c4dda3d
Revises: 67afd920ae17
Create Date: 2025-12-02 13:44:51.270072

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '306f7c4dda3d'
down_revision: Union[str, None] = '67afd920ae17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add HITL configuration columns to tenants table
    op.add_column(
        'tenants',
        sa.Column(
            'hitl_auto_approve_threshold',
            sa.Float(),
            nullable=False,
            server_default='0.70'
        )
    )
    op.add_column(
        'tenants',
        sa.Column(
            'hitl_critical_threshold',
            sa.Float(),
            nullable=False,
            server_default='0.30'
        )
    )
    op.add_column(
        'tenants',
        sa.Column(
            'hitl_high_threshold',
            sa.Float(),
            nullable=False,
            server_default='0.50'
        )
    )
    op.add_column(
        'tenants',
        sa.Column(
            'hitl_normal_threshold',
            sa.Float(),
            nullable=False,
            server_default='0.60'
        )
    )
    op.add_column(
        'tenants',
        sa.Column(
            'hitl_low_threshold',
            sa.Float(),
            nullable=False,
            server_default='0.70'
        )
    )

    # Add hitl_threshold to schema_definitions
    op.add_column(
        'schema_definitions',
        sa.Column('hitl_threshold', sa.Float(), nullable=True)
    )

    # Add confidence_score to extraction_jobs
    op.add_column(
        'extraction_jobs',
        sa.Column('confidence_score', sa.Float(), nullable=True)
    )

    # Create review_requests table
    op.create_table(
        'review_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('extraction_job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_to_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=50), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('trigger_reason', sa.String(length=255), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('conductor_task_id', sa.String(length=255), nullable=True),
        sa.Column('conductor_workflow_id', sa.String(length=255), nullable=True),
        sa.Column('sla_deadline', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['assigned_to_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['extraction_job_id'], ['extraction_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('extraction_job_id')
    )

    # Create indexes for review_requests
    # Composite indexes for common query patterns
    op.create_index('idx_review_queue', 'review_requests', ['tenant_id', 'status', 'priority', 'created_at'])
    op.create_index('idx_review_assigned_to', 'review_requests', ['assigned_to_user_id', 'status'])
    # Single-column indexes for filtering and lookups
    op.create_index('idx_review_requests_sla_deadline', 'review_requests', ['sla_deadline'])
    op.create_index('idx_review_requests_conductor_task_id', 'review_requests', ['conductor_task_id'])
    op.create_index('idx_review_requests_conductor_workflow_id', 'review_requests', ['conductor_workflow_id'])

    # Create review_corrections table
    op.create_table(
        'review_corrections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('review_request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('extraction_result_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('corrected_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('field_path', sa.String(length=500), nullable=False),
        sa.Column('original_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('corrected_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('correction_type', sa.String(length=50), nullable=False),
        sa.Column('correction_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['corrected_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['extraction_result_id'], ['extraction_results.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['review_request_id'], ['review_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for review_corrections
    # Note: Removed duplicate indexes (review_id/review_request_id, user_id/corrected_by_user_id)
    op.create_index('idx_review_corrections_review_request_id', 'review_corrections', ['review_request_id'])
    op.create_index('idx_review_corrections_extraction_result_id', 'review_corrections', ['extraction_result_id'])
    op.create_index('idx_review_corrections_corrected_by_user_id', 'review_corrections', ['corrected_by_user_id'])
    op.create_index('idx_review_corrections_field_path', 'review_corrections', ['field_path'])


def downgrade() -> None:
    # Drop review_corrections indexes and table
    op.drop_index('idx_review_corrections_field_path', table_name='review_corrections')
    op.drop_index('idx_review_corrections_corrected_by_user_id', table_name='review_corrections')
    op.drop_index('idx_review_corrections_extraction_result_id', table_name='review_corrections')
    op.drop_index('idx_review_corrections_review_request_id', table_name='review_corrections')
    op.drop_table('review_corrections')

    # Drop review_requests indexes and table
    op.drop_index('idx_review_requests_conductor_workflow_id', table_name='review_requests')
    op.drop_index('idx_review_requests_conductor_task_id', table_name='review_requests')
    op.drop_index('idx_review_requests_sla_deadline', table_name='review_requests')
    op.drop_index('idx_review_assigned_to', table_name='review_requests')
    op.drop_index('idx_review_queue', table_name='review_requests')
    op.drop_table('review_requests')

    # Remove confidence_score from extraction_jobs
    op.drop_column('extraction_jobs', 'confidence_score')

    # Remove hitl_threshold from schema_definitions
    op.drop_column('schema_definitions', 'hitl_threshold')

    # Remove HITL configuration from tenants
    op.drop_column('tenants', 'hitl_low_threshold')
    op.drop_column('tenants', 'hitl_normal_threshold')
    op.drop_column('tenants', 'hitl_high_threshold')
    op.drop_column('tenants', 'hitl_critical_threshold')
    op.drop_column('tenants', 'hitl_auto_approve_threshold')
