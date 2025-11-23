"""add_thinking_config_to_extraction_jobs

Revision ID: 29c1376b3fad
Revises: b61940e9e225
Create Date: 2025-11-17 10:02:49.421985

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29c1376b3fad'
down_revision: Union[str, None] = 'b61940e9e225'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add enable_thinking column (boolean, default False)
    op.add_column(
        'extraction_jobs',
        sa.Column('enable_thinking', sa.Boolean(), nullable=False, server_default='false')
    )

    # Add thinking_budget column (integer, default 0)
    op.add_column(
        'extraction_jobs',
        sa.Column('thinking_budget', sa.Integer(), nullable=False, server_default='0')
    )


def downgrade() -> None:
    # Remove columns in reverse order
    op.drop_column('extraction_jobs', 'thinking_budget')
    op.drop_column('extraction_jobs', 'enable_thinking')
