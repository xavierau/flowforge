"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-11-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('document_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('uploaded', 'processing', 'ready_for_extraction', 'completed', 'failed')", name='valid_document_status')
    )
    op.create_index(op.f('ix_documents_status'), 'documents', ['status'], unique=False)
    op.create_index(op.f('ix_documents_created_at'), 'documents', ['created_at'], unique=False)

    # Create document_pages table
    op.create_table(
        'document_pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('image_path', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name='valid_page_status')
    )
    op.create_index(op.f('ix_document_pages_document_id'), 'document_pages', ['document_id'], unique=False)
    op.create_index(op.f('ix_document_pages_status'), 'document_pages', ['status'], unique=False)

    # Create extraction_jobs table
    op.create_table(
        'extraction_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('extraction_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('custom_prompt', sa.Text(), nullable=True),
        sa.Column('model_provider', sa.String(length=50), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('celery_task_id', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')", name='valid_job_status')
    )
    op.create_index(op.f('ix_extraction_jobs_document_id'), 'extraction_jobs', ['document_id'], unique=False)
    op.create_index(op.f('ix_extraction_jobs_status'), 'extraction_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_extraction_jobs_celery_task_id'), 'extraction_jobs', ['celery_task_id'], unique=False)
    op.create_index(op.f('ix_extraction_jobs_created_at'), 'extraction_jobs', ['created_at'], unique=False)

    # Create extraction_results table
    op.create_table(
        'extraction_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('extraction_job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_page_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('extracted_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('model_used', sa.String(length=150), nullable=True),
        sa.Column('validation_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_page_id'], ['document_pages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['extraction_job_id'], ['extraction_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_extraction_results_extraction_job_id'), 'extraction_results', ['extraction_job_id'], unique=False)
    op.create_index(op.f('ix_extraction_results_document_page_id'), 'extraction_results', ['document_page_id'], unique=False)

    # Create model_provider_keys table
    op.create_table(
        'model_provider_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_name', sa.String(length=50), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("provider_name IN ('google', 'openai', 'deepseek')", name='valid_provider_name')
    )
    op.create_index(op.f('ix_model_provider_keys_provider_name'), 'model_provider_keys', ['provider_name'], unique=False)
    op.create_index(op.f('ix_model_provider_keys_is_active'), 'model_provider_keys', ['is_active'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_index(op.f('ix_model_provider_keys_is_active'), table_name='model_provider_keys')
    op.drop_index(op.f('ix_model_provider_keys_provider_name'), table_name='model_provider_keys')
    op.drop_table('model_provider_keys')

    op.drop_index(op.f('ix_extraction_results_document_page_id'), table_name='extraction_results')
    op.drop_index(op.f('ix_extraction_results_extraction_job_id'), table_name='extraction_results')
    op.drop_table('extraction_results')

    op.drop_index(op.f('ix_extraction_jobs_created_at'), table_name='extraction_jobs')
    op.drop_index(op.f('ix_extraction_jobs_celery_task_id'), table_name='extraction_jobs')
    op.drop_index(op.f('ix_extraction_jobs_status'), table_name='extraction_jobs')
    op.drop_index(op.f('ix_extraction_jobs_document_id'), table_name='extraction_jobs')
    op.drop_table('extraction_jobs')

    op.drop_index(op.f('ix_document_pages_status'), table_name='document_pages')
    op.drop_index(op.f('ix_document_pages_document_id'), table_name='document_pages')
    op.drop_table('document_pages')

    op.drop_index(op.f('ix_documents_created_at'), table_name='documents')
    op.drop_index(op.f('ix_documents_status'), table_name='documents')
    op.drop_table('documents')
