"""add split to document status constraint

Revision ID: 8a2c3f5d9e1b
Revises: 211166f9b3fe
Create Date: 2026-01-03 17:15:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '8a2c3f5d9e1b'
down_revision: Union[str, None] = '211166f9b3fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old check constraint
    op.drop_constraint('valid_document_status', 'documents', type_='check')

    # Add new check constraint with 'split' status included
    op.create_check_constraint(
        'valid_document_status',
        'documents',
        "status IN ('uploaded', 'processing', 'ready_for_extraction', 'completed', 'failed', 'split')"
    )


def downgrade() -> None:
    # Drop the new check constraint
    op.drop_constraint('valid_document_status', 'documents', type_='check')

    # Restore the old check constraint (without 'split')
    op.create_check_constraint(
        'valid_document_status',
        'documents',
        "status IN ('uploaded', 'processing', 'ready_for_extraction', 'completed', 'failed')"
    )
