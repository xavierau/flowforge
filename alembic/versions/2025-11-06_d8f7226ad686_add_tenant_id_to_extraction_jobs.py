"""add_tenant_id_to_extraction_jobs

Revision ID: d8f7226ad686
Revises: backfill_credits_001
Create Date: 2025-11-06

This migration adds tenant_id column to extraction_jobs table for:
1. Performance improvement (no JOIN needed to get tenant)
2. Simpler queries (direct tenant filter)
3. Data integrity (explicit tenant relationship)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'd8f7226ad686'
down_revision: Union[str, None] = 'backfill_credits_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add tenant_id to extraction_jobs table.

    Steps:
    1. Add tenant_id column as nullable
    2. Backfill tenant_id from documents table
    3. Make tenant_id NOT NULL
    4. Add index and foreign key constraint
    """
    # Step 1: Add tenant_id column (nullable initially)
    op.add_column('extraction_jobs',
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True)
    )

    # Step 2: Backfill tenant_id from documents table
    op.execute("""
        UPDATE extraction_jobs ej
        SET tenant_id = d.tenant_id
        FROM documents d
        WHERE ej.document_id = d.id
        AND d.tenant_id IS NOT NULL
    """)

    # Step 3: Add index for performance
    op.create_index(
        'idx_extraction_jobs_tenant_id',
        'extraction_jobs',
        ['tenant_id']
    )

    # Step 4: Add foreign key constraint
    op.create_foreign_key(
        'extraction_jobs_tenant_id_fkey',
        'extraction_jobs',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Remove tenant_id column from extraction_jobs"""
    # Drop foreign key
    op.drop_constraint('extraction_jobs_tenant_id_fkey', 'extraction_jobs', type_='foreignkey')

    # Drop index
    op.drop_index('idx_extraction_jobs_tenant_id', table_name='extraction_jobs')

    # Drop column
    op.drop_column('extraction_jobs', 'tenant_id')
