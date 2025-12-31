"""add_cost_tracking_to_split_jobs

Revision ID: 4e870e3d9cea
Revises: 672ed223127f
Create Date: 2025-12-31 22:37:16.890377

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4e870e3d9cea'
down_revision: Union[str, None] = '672ed223127f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cost tracking columns to split_jobs table."""
    op.add_column(
        'split_jobs',
        sa.Column('estimated_cost', sa.Numeric(precision=10, scale=6), nullable=True)
    )
    op.add_column(
        'split_jobs',
        sa.Column('pricing_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    """Remove cost tracking columns from split_jobs table."""
    op.drop_column('split_jobs', 'pricing_snapshot')
    op.drop_column('split_jobs', 'estimated_cost')
