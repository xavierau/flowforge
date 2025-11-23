"""Add constraint to enforce credit deduction for completed jobs

Revision ID: add_credit_deduction_constraint_20251117
Revises: backfill_credit_deductions_20251117
Create Date: 2025-11-17 15:00:00.000000

This migration adds a database CHECK constraint to prevent completed extraction jobs
from existing without corresponding credit deductions.

Constraint:
    (status != 'completed') OR (credits_deducted = TRUE AND credit_transaction_id IS NOT NULL)

This ensures that ANY job reaching 'completed' status MUST have:
1. credits_deducted flag set to TRUE
2. credit_transaction_id referencing a valid transaction

Database will reject UPDATE/INSERT operations that violate this rule.

This prevents recurrence of the credit deduction bug at the database level.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_constraint_20251117'
down_revision = 'backfill_credits_20251117'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add credit deduction constraint."""

    # Add CHECK constraint to extraction_jobs table
    op.create_check_constraint(
        "ck_extraction_jobs_completed_credits_deducted",
        "extraction_jobs",
        sa.text(
            "(status != 'completed') OR "
            "(credits_deducted = TRUE AND credit_transaction_id IS NOT NULL)"
        )
    )

    print("✓ Added constraint: ck_extraction_jobs_completed_credits_deducted")
    print("  Constraint ensures completed jobs MUST have credit deductions")


def downgrade() -> None:
    """Remove credit deduction constraint."""

    op.drop_constraint(
        "ck_extraction_jobs_completed_credits_deducted",
        "extraction_jobs",
        type_="check"
    )

    print("✓ Removed constraint: ck_extraction_jobs_completed_credits_deducted")
