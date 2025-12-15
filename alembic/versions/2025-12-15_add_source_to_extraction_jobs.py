"""add_source_to_extraction_jobs

Add source column to track whether jobs were created from WebUI or API.

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2025-12-15
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6g7h8'
down_revision = 'b2c3d4e5f6g7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add source column with default 'api' for existing jobs
    op.add_column(
        'extraction_jobs',
        sa.Column('source', sa.String(20), nullable=False, server_default='api')
    )

    # Add index for efficient filtering
    op.create_index(
        'idx_extraction_jobs_source',
        'extraction_jobs',
        ['source']
    )


def downgrade() -> None:
    op.drop_index('idx_extraction_jobs_source', table_name='extraction_jobs')
    op.drop_column('extraction_jobs', 'source')
