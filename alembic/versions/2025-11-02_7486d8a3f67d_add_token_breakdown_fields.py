"""add_token_breakdown_fields

Revision ID: 7486d8a3f67d
Revises: 001
Create Date: 2025-11-02 17:05:39.270580

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7486d8a3f67d'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add input_tokens and output_tokens columns to extraction_results
    op.add_column('extraction_results', sa.Column('input_tokens', sa.Integer(), nullable=True))
    op.add_column('extraction_results', sa.Column('output_tokens', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove input_tokens and output_tokens columns
    op.drop_column('extraction_results', 'output_tokens')
    op.drop_column('extraction_results', 'input_tokens')
