"""add_index_extraction_jobs_tenant_id

Revision ID: 922d747266dd
Revises: add_constraint_20251117
Create Date: 2025-11-17 11:35:18.487629

Performance optimization: Add index on extraction_jobs.tenant_id

Problem:
    The extraction_jobs table is missing an index on tenant_id, causing full table
    scans when filtering jobs by tenant (e.g., in /api/v1/jobs endpoint).

Impact:
    Query performance degrades linearly with total jobs in system.
    For N jobs across M tenants, finding one tenant's jobs requires O(N) scan
    instead of O(N/M) with index.

Fix:
    Add B-tree index on tenant_id column for fast tenant-filtered queries.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '922d747266dd'
down_revision: Union[str, None] = 'add_constraint_20251117'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add index on extraction_jobs.tenant_id for performance."""
    # NOTE: First check if tenant_id column exists (may be added by d8f7226ad686)
    # If not, this migration will fail, indicating migration dependency issue
    op.create_index(
        'idx_extraction_jobs_tenant_id',
        'extraction_jobs',
        ['tenant_id'],
        unique=False,
        # Removed postgresql_concurrently=True to allow running in transaction
        # In production, consider running manually with CONCURRENTLY for zero downtime
    )


def downgrade() -> None:
    """Remove index on extraction_jobs.tenant_id."""
    op.drop_index(
        'idx_extraction_jobs_tenant_id',
        table_name='extraction_jobs',
        # Removed postgresql_concurrently=True to allow running in transaction
    )
