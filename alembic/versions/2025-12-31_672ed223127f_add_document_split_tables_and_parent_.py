"""add_document_split_tables_and_parent_child

Revision ID: 672ed223127f
Revises: llamaextract001
Create Date: 2025-12-31 21:18:19.795051

This migration adds:
- split_jobs table for tracking document split operations
- split_results table for per-page analysis results
- parent_document_id, split_job_id, split_sequence columns to documents table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '672ed223127f'
down_revision: Union[str, None] = 'llamaextract001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create split_jobs table (must be created before documents FK)
    op.create_table('split_jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('source_document_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('apply_rotation', sa.Boolean(), nullable=False),
        sa.Column('dspy_model', sa.String(length=100), nullable=True),
        sa.Column('pages_analyzed', sa.Integer(), nullable=False),
        sa.Column('documents_created', sa.Integer(), nullable=False),
        sa.Column('pages_rotated', sa.Integer(), nullable=False),
        sa.Column('total_input_tokens', sa.Integer(), nullable=False),
        sa.Column('total_output_tokens', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_split_jobs_created_at', 'split_jobs', ['created_at'], unique=False)
    op.create_index('idx_split_jobs_source_document_id', 'split_jobs', ['source_document_id'], unique=False)
    op.create_index('idx_split_jobs_status', 'split_jobs', ['status'], unique=False)
    op.create_index('idx_split_jobs_tenant_id', 'split_jobs', ['tenant_id'], unique=False)

    # 2. Create split_results table
    op.create_table('split_results',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('split_job_id', sa.UUID(), nullable=False),
        sa.Column('document_page_id', sa.UUID(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        # Boundary detection (reasoning first, then classification - LLM autoregression)
        sa.Column('boundary_reason', sa.Text(), nullable=True),
        sa.Column('detected_document_type', sa.String(length=100), nullable=True),
        sa.Column('is_starting_page', sa.Boolean(), nullable=False),
        sa.Column('boundary_confidence', sa.String(length=20), nullable=True),
        # Rotation detection
        sa.Column('rotation_needed', sa.Integer(), nullable=False),
        sa.Column('rotation_confidence', sa.String(length=20), nullable=True),
        sa.Column('rotation_method', sa.String(length=50), nullable=True),
        # Token tracking
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        # Child document reference
        sa.Column('child_document_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['child_document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['document_page_id'], ['document_pages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['split_job_id'], ['split_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_split_results_child_document_id', 'split_results', ['child_document_id'], unique=False)
    op.create_index('idx_split_results_document_page_id', 'split_results', ['document_page_id'], unique=False)
    op.create_index('idx_split_results_job_page', 'split_results', ['split_job_id', 'page_number'], unique=True)
    op.create_index('idx_split_results_split_job_id', 'split_results', ['split_job_id'], unique=False)

    # 3. Add parent-child columns to documents table
    op.add_column('documents', sa.Column('parent_document_id', sa.UUID(), nullable=True))
    op.add_column('documents', sa.Column('split_job_id', sa.UUID(), nullable=True))
    op.add_column('documents', sa.Column('split_sequence', sa.Integer(), nullable=True))
    op.create_index('idx_documents_parent_document_id', 'documents', ['parent_document_id'], unique=False)

    # 4. Add foreign keys (after split_jobs table exists)
    op.create_foreign_key(
        'fk_documents_split_job_id', 'documents', 'split_jobs',
        ['split_job_id'], ['id'], ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_documents_parent_document_id', 'documents', 'documents',
        ['parent_document_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    # 1. Remove foreign keys from documents
    op.drop_constraint('fk_documents_parent_document_id', 'documents', type_='foreignkey')
    op.drop_constraint('fk_documents_split_job_id', 'documents', type_='foreignkey')

    # 2. Remove columns from documents
    op.drop_index('idx_documents_parent_document_id', table_name='documents')
    op.drop_column('documents', 'split_sequence')
    op.drop_column('documents', 'split_job_id')
    op.drop_column('documents', 'parent_document_id')

    # 3. Drop split_results table
    op.drop_index('idx_split_results_split_job_id', table_name='split_results')
    op.drop_index('idx_split_results_job_page', table_name='split_results')
    op.drop_index('idx_split_results_document_page_id', table_name='split_results')
    op.drop_index('idx_split_results_child_document_id', table_name='split_results')
    op.drop_table('split_results')

    # 4. Drop split_jobs table
    op.drop_index('idx_split_jobs_tenant_id', table_name='split_jobs')
    op.drop_index('idx_split_jobs_status', table_name='split_jobs')
    op.drop_index('idx_split_jobs_source_document_id', table_name='split_jobs')
    op.drop_index('idx_split_jobs_created_at', table_name='split_jobs')
    op.drop_table('split_jobs')
