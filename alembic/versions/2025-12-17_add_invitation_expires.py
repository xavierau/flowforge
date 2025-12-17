"""add invitation_expires column to users table

Add expiration timestamp for invitation tokens to prevent
old tokens from remaining valid indefinitely.

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2025-12-17
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'h8i9j0k1l2m3'
down_revision = 'g7h8i9j0k1l2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('invitation_expires', sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('users', 'invitation_expires')
