"""add parent_extraction_job_id to extraction_jobs

Revision ID: 211166f9b3fe
Revises: 1085110220be
Create Date: 2026-01-03 16:56:05.590642

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '211166f9b3fe'
down_revision: Union[str, None] = '1085110220be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add parent_extraction_job_id column to extraction_jobs table
    # This enables tracking child jobs created during auto-split to update parent job status
    op.add_column('extraction_jobs', sa.Column('parent_extraction_job_id', sa.UUID(), nullable=True))
    op.create_index('idx_extraction_jobs_parent_extraction_job_id', 'extraction_jobs', ['parent_extraction_job_id'], unique=False)
    op.create_foreign_key(
        'fk_extraction_jobs_parent_extraction_job',
        'extraction_jobs',
        'extraction_jobs',
        ['parent_extraction_job_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_extraction_jobs_parent_extraction_job', 'extraction_jobs', type_='foreignkey')
    op.drop_index('idx_extraction_jobs_parent_extraction_job_id', table_name='extraction_jobs')
    op.drop_column('extraction_jobs', 'parent_extraction_job_id')
