"""Add indexes for split_mode and extraction_mode columns

Revision ID: 1085110220be
Revises: 95e04b53dcfe
Create Date: 2026-01-03

These indexes optimize queries filtering by split_mode and extraction_mode,
which are used by the frontend JobList.tsx filters to prevent full table scans.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '1085110220be'
down_revision: Union[str, None] = '95e04b53dcfe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('idx_extraction_jobs_split_mode', 'extraction_jobs', ['split_mode'])
    op.create_index('idx_extraction_jobs_extraction_mode', 'extraction_jobs', ['extraction_mode'])


def downgrade() -> None:
    op.drop_index('idx_extraction_jobs_extraction_mode', table_name='extraction_jobs')
    op.drop_index('idx_extraction_jobs_split_mode', table_name='extraction_jobs')
