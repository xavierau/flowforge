"""add_email_verification_token_index

Add index on users.email_verification_token column for performance
when looking up users by invitation/verification token.

Revision ID: g7h8i9j0k1l2
Revises: f6g7h8i9j0k1
Create Date: 2025-12-17
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'g7h8i9j0k1l2'
down_revision = 'f6g7h8i9j0k1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        'idx_users_email_verification_token',
        'users',
        ['email_verification_token'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('idx_users_email_verification_token', table_name='users')
