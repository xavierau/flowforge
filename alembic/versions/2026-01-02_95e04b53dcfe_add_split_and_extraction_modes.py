"""add_split_and_extraction_modes

Revision ID: 95e04b53dcfe
Revises: 4e870e3d9cea
Create Date: 2026-01-02 21:54:38.558829

This migration adds split_mode and extraction_mode columns to extraction_jobs table,
replacing the deprecated processing_mode field with more granular control:
- split_mode: per_page, batch, auto (how pages are grouped)
- extraction_mode: vllm, markdown (how extraction is performed)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '95e04b53dcfe'
down_revision: Union[str, None] = '4e870e3d9cea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add new columns as nullable first
    op.add_column('extraction_jobs', sa.Column('split_mode', sa.String(length=20), nullable=True))
    op.add_column('extraction_jobs', sa.Column('extraction_mode', sa.String(length=20), nullable=True))
    op.add_column('extraction_jobs', sa.Column('parent_split_job_id', sa.UUID(), nullable=True))

    # Step 2: Migrate existing data from processing_mode to new fields
    # Mapping:
    #   batch -> split_mode=batch, extraction_mode=vllm
    #   per_page/direct -> split_mode=per_page, extraction_mode=vllm
    #   markdown -> split_mode=batch, extraction_mode=markdown
    op.execute("""
        UPDATE extraction_jobs SET
            split_mode = CASE
                WHEN processing_mode = 'batch' THEN 'batch'
                WHEN processing_mode IN ('per_page', 'direct') THEN 'per_page'
                WHEN processing_mode = 'markdown' THEN 'batch'
                ELSE 'batch'
            END,
            extraction_mode = CASE
                WHEN processing_mode = 'markdown' THEN 'markdown'
                ELSE 'vllm'
            END
        WHERE split_mode IS NULL OR extraction_mode IS NULL
    """)

    # Step 3: Set NOT NULL constraints after migration with defaults for any remaining nulls
    op.execute("UPDATE extraction_jobs SET split_mode = 'batch' WHERE split_mode IS NULL")
    op.execute("UPDATE extraction_jobs SET extraction_mode = 'vllm' WHERE extraction_mode IS NULL")

    op.alter_column('extraction_jobs', 'split_mode',
                    existing_type=sa.String(length=20),
                    nullable=False,
                    server_default='batch')
    op.alter_column('extraction_jobs', 'extraction_mode',
                    existing_type=sa.String(length=20),
                    nullable=False,
                    server_default='vllm')

    # Step 4: Create index and FK for parent_split_job_id
    op.create_index('idx_extraction_jobs_parent_split_job_id', 'extraction_jobs', ['parent_split_job_id'], unique=False)
    op.create_foreign_key(
        'fk_extraction_jobs_parent_split_job',
        'extraction_jobs',
        'split_jobs',
        ['parent_split_job_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Remove FK and index
    op.drop_constraint('fk_extraction_jobs_parent_split_job', 'extraction_jobs', type_='foreignkey')
    op.drop_index('idx_extraction_jobs_parent_split_job_id', table_name='extraction_jobs')

    # Drop new columns
    op.drop_column('extraction_jobs', 'parent_split_job_id')
    op.drop_column('extraction_jobs', 'extraction_mode')
    op.drop_column('extraction_jobs', 'split_mode')
