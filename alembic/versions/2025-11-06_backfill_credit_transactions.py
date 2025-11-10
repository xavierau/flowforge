"""backfill credit transactions for completed jobs

Revision ID: backfill_credits_001
Revises: 743a8a8f6289
Create Date: 2025-11-06

This migration backfills credit transactions for extraction jobs that completed
but did not record credit deductions (before synchronous credit deduction was implemented).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import select, and_
from datetime import datetime
from uuid import uuid4


# revision identifiers
revision = 'backfill_credits_001'
down_revision = '7418694731d3'  # add_platform_settings_table
branch_labels = None
depends_on = None


def upgrade():
    """
    Backfill credit transactions for completed jobs.

    Steps:
    1. Find all extraction_jobs where:
       - status = 'completed'
       - credits_deducted = false
       - completed_at is not null
    2. Create credit_transaction for each job using:
       - amount = -(job.input_tokens + job.output_tokens) or -pages_processed
       - transaction_type = 'deduction'
       - reference_type = 'extraction_job'
       - created_at = job.completed_at (preserve timeline)
    3. Update extraction_jobs.credits_deducted = true
    4. Recalculate tenant.cached_balance for affected tenants
    """
    # Get database connection
    conn = op.get_bind()

    # Define table references (no full ORM models needed)
    extraction_jobs = sa.table(
        'extraction_jobs',
        sa.column('id', UUID),
        sa.column('document_id', UUID),
        sa.column('status', sa.String),
        sa.column('credits_deducted', sa.Boolean),
        sa.column('credit_transaction_id', UUID),
        sa.column('credits_cost', sa.Integer),
        sa.column('completed_at', sa.DateTime),
    )

    documents = sa.table(
        'documents',
        sa.column('id', UUID),
        sa.column('tenant_id', UUID),
        sa.column('page_count', sa.Integer),
    )

    credit_transactions = sa.table(
        'credit_transactions',
        sa.column('id', UUID),
        sa.column('tenant_id', UUID),
        sa.column('amount', sa.Integer),
        sa.column('transaction_type', sa.String),
        sa.column('reference_id', UUID),
        sa.column('reference_type', sa.String),
        sa.column('description', sa.Text),
        sa.column('transaction_metadata', JSONB),
        sa.column('created_at', sa.DateTime),
    )

    tenants = sa.table(
        'tenants',
        sa.column('id', UUID),
        sa.column('cached_balance', sa.Integer),
        sa.column('balance_last_updated', sa.DateTime),
    )

    # Step 1: Find jobs needing backfill (JOIN with documents to get tenant_id and page_count)
    # Only include jobs where document has a tenant_id (multi-tenancy was added later)
    # Credits are 1:1 with page_count (1 page = 1 credit)
    jobs_to_backfill = conn.execute(
        select(
            extraction_jobs.c.id,
            documents.c.tenant_id,
            extraction_jobs.c.document_id,
            documents.c.page_count,
            extraction_jobs.c.credits_cost,
            extraction_jobs.c.completed_at,
        )
        .select_from(
            extraction_jobs.join(
                documents,
                extraction_jobs.c.document_id == documents.c.id
            )
        )
        .where(
            and_(
                extraction_jobs.c.status == 'completed',
                extraction_jobs.c.credits_deducted == False,
                extraction_jobs.c.completed_at.isnot(None),
                documents.c.tenant_id.isnot(None),  # Only include jobs with tenant
            )
        )
    ).fetchall()

    print(f"Found {len(jobs_to_backfill)} jobs needing credit transaction backfill")

    # Step 2 & 3: Create transactions and update jobs
    affected_tenants = set()

    for job in jobs_to_backfill:
        # Credits are 1:1 with page_count (1 page = 1 credit)
        # Use credits_cost if available (newer jobs), otherwise use page_count
        total_credits = job.credits_cost if job.credits_cost else (job.page_count or 0)

        if total_credits == 0:
            print(f"Skipping job {job.id} - zero credits (no pages)")
            continue

        # Create credit transaction
        transaction_id = uuid4()
        conn.execute(
            credit_transactions.insert().values(
                id=transaction_id,
                tenant_id=job.tenant_id,
                amount=-abs(total_credits),  # Negative for deduction
                transaction_type='deduction',  # Enum value
                reference_id=job.id,
                reference_type='extraction_job',  # Enum value
                description=f"Document extraction - {total_credits} page(s) = {total_credits} credit(s) (backfilled)",
                transaction_metadata={
                    'backfilled': True,
                    'backfill_date': datetime.utcnow().isoformat(),
                    'job_id': str(job.id),
                    'document_id': str(job.document_id),
                    'total_credits': total_credits,
                },
                created_at=job.completed_at,  # Use job's completion time
            )
        )

        # Update job's credits_deducted flag
        conn.execute(
            extraction_jobs.update()
            .where(extraction_jobs.c.id == job.id)
            .values(
                credits_deducted=True,
                credit_transaction_id=transaction_id,
            )
        )

        affected_tenants.add(job.tenant_id)
        print(f"Backfilled transaction for job {job.id}: {total_credits} credits")

    # Step 4: Recalculate cached_balance for affected tenants
    for tenant_id in affected_tenants:
        # Calculate actual balance from all transactions
        balance = conn.execute(
            select(sa.func.coalesce(sa.func.sum(credit_transactions.c.amount), 0))
            .where(credit_transactions.c.tenant_id == tenant_id)
        ).scalar()

        # Update cached_balance
        conn.execute(
            tenants.update()
            .where(tenants.c.id == tenant_id)
            .values(
                cached_balance=balance,
                balance_last_updated=datetime.utcnow(),
            )
        )

        print(f"Updated tenant {tenant_id} cached_balance to {balance}")

    print(f"Backfill complete: {len(jobs_to_backfill)} jobs, {len(affected_tenants)} tenants")


def downgrade():
    """
    Rollback backfill migration.

    Steps:
    1. Delete credit_transactions where metadata.backfilled = true
    2. Update extraction_jobs.credits_deducted = false for those jobs
    3. Recalculate tenant.cached_balance
    """
    conn = op.get_bind()

    credit_transactions = sa.table(
        'credit_transactions',
        sa.column('id', UUID),
        sa.column('tenant_id', UUID),
        sa.column('amount', sa.Integer),
        sa.column('reference_id', UUID),
        sa.column('transaction_metadata', JSONB),
    )

    extraction_jobs = sa.table(
        'extraction_jobs',
        sa.column('id', UUID),
        sa.column('credits_deducted', sa.Boolean),
        sa.column('credit_transaction_id', UUID),
    )

    tenants = sa.table(
        'tenants',
        sa.column('id', UUID),
        sa.column('cached_balance', sa.Integer),
        sa.column('balance_last_updated', sa.DateTime),
    )

    # Find backfilled transactions
    backfilled = conn.execute(
        select(
            credit_transactions.c.id,
            credit_transactions.c.tenant_id,
            credit_transactions.c.reference_id,
        )
        .where(credit_transactions.c.transaction_metadata['backfilled'].astext == 'true')
    ).fetchall()

    print(f"Rolling back {len(backfilled)} backfilled transactions")

    affected_tenants = set()
    job_ids = set()

    # Delete backfilled transactions
    for txn in backfilled:
        conn.execute(
            credit_transactions.delete()
            .where(credit_transactions.c.id == txn.id)
        )
        affected_tenants.add(txn.tenant_id)
        if txn.reference_id:
            job_ids.add(txn.reference_id)

    # Reset credits_deducted flag
    if job_ids:
        conn.execute(
            extraction_jobs.update()
            .where(extraction_jobs.c.id.in_(job_ids))
            .values(
                credits_deducted=False,
                credit_transaction_id=None,
            )
        )

    # Recalculate cached_balance
    for tenant_id in affected_tenants:
        balance = conn.execute(
            select(sa.func.coalesce(sa.func.sum(credit_transactions.c.amount), 0))
            .where(credit_transactions.c.tenant_id == tenant_id)
        ).scalar()

        conn.execute(
            tenants.update()
            .where(tenants.c.id == tenant_id)
            .values(
                cached_balance=balance,
                balance_last_updated=datetime.utcnow(),
            )
        )

    print(f"Rollback complete: {len(backfilled)} transactions, {len(affected_tenants)} tenants")
