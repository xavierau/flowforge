"""add_schema_definition_id_to_extraction_jobs

Revision ID: 924445a7dc1b
Revises: b1dbae7cd0ad
Create Date: 2025-11-03 22:20:51.898070

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '924445a7dc1b'
down_revision: Union[str, None] = 'b1dbae7cd0ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add schema_definition_id column to extraction_jobs table
    op.add_column(
        'extraction_jobs',
        sa.Column('schema_definition_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_extraction_jobs_schema_definition_id',
        'extraction_jobs',
        'schema_definitions',
        ['schema_definition_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Add index for faster lookups
    op.create_index(
        'idx_extraction_jobs_schema_definition_id',
        'extraction_jobs',
        ['schema_definition_id']
    )


def downgrade() -> None:
    # Drop index
    op.drop_index('idx_extraction_jobs_schema_definition_id', table_name='extraction_jobs')

    # Drop foreign key constraint
    op.drop_constraint('fk_extraction_jobs_schema_definition_id', 'extraction_jobs', type_='foreignkey')

    # Drop column
    op.drop_column('extraction_jobs', 'schema_definition_id')
