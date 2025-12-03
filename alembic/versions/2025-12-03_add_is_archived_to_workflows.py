"""add_is_archived_to_workflows

Revision ID: a1b2c3d4e5f6
Revises: 306f7c4dda3d
Create Date: 2025-12-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '306f7c4dda3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_archived column to workflows table with default False
    op.add_column(
        'workflows',
        sa.Column(
            'is_archived',
            sa.Boolean(),
            nullable=False,
            server_default='false'
        )
    )

    # Add index on is_archived for query performance
    op.create_index(
        'idx_workflows_is_archived',
        'workflows',
        ['is_archived']
    )


def downgrade() -> None:
    # Drop index first
    op.drop_index('idx_workflows_is_archived', table_name='workflows')

    # Drop column
    op.drop_column('workflows', 'is_archived')
