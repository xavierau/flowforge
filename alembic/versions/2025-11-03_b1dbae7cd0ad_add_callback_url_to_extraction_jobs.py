"""add callback_url to extraction_jobs

Revision ID: b1dbae7cd0ad
Revises: 92e8a3aa9513
Create Date: 2025-11-03 21:09:22.639381

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1dbae7cd0ad'
down_revision: Union[str, None] = '92e8a3aa9513'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add callback_url column to extraction_jobs table
    op.add_column('extraction_jobs', sa.Column('callback_url', sa.String(length=1024), nullable=True))


def downgrade() -> None:
    # Remove callback_url column from extraction_jobs table
    op.drop_column('extraction_jobs', 'callback_url')
