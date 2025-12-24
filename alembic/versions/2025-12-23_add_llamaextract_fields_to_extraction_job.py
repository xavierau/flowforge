"""add llamaextract fields to extraction_jobs table

Revision ID: llamaextract001
Revises: a1b2c3d4e5f6
Create Date: 2025-12-23

Adds LlamaExtract-specific fields to extraction_jobs table:
- llamaextract_mode: extraction mode (standard or premium)
- llamaextract_target: extraction target (per_doc or per_page)
- llamaextract_job_id: external job ID for tracking
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'llamaextract001'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add LlamaExtract fields to extraction_jobs table."""
    op.add_column(
        'extraction_jobs',
        sa.Column('llamaextract_mode', sa.String(20), nullable=True)
    )
    op.add_column(
        'extraction_jobs',
        sa.Column('llamaextract_target', sa.String(20), nullable=True)
    )
    op.add_column(
        'extraction_jobs',
        sa.Column('llamaextract_job_id', sa.String(100), nullable=True)
    )


def downgrade() -> None:
    """Remove LlamaExtract fields from extraction_jobs table."""
    op.drop_column('extraction_jobs', 'llamaextract_job_id')
    op.drop_column('extraction_jobs', 'llamaextract_target')
    op.drop_column('extraction_jobs', 'llamaextract_mode')
