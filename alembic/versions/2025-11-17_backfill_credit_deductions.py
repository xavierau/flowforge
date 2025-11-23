"""Backfill credit deductions for historical extraction jobs

Revision ID: backfill_credit_deductions_20251117
Revises: 29c1376b3fad
Create Date: 2025-11-17 14:00:00.000000

This migration addresses a billing bug where the /api/v1/jobs/extract endpoint
created extraction jobs without deducting credits (fixed in this release).

Affected jobs:
- All completed extraction jobs with credits_deducted = FALSE
- Status: completed
- Total credits owed: varies by page count

This migration:
1. Identifies affected jobs (completed, no credit deduction)
2. Creates credit_transactions records (DEDUCTION type)
3. Updates tenant.cached_balance
4. Links transactions to jobs (credit_transaction_id)
5. Sets credits_deducted = TRUE flag

Idempotency:
- Checks for existing transactions before creating
- Safe to run multiple times (no duplicates)

Rollback:
- Deletes created transactions
- Restores tenant.cached_balance
- Resets job flags

Performance:
- Current implementation: Individual operations per job (4 queries per job)
- For 21 jobs = 84 database round-trips (~0.5 seconds total)
- Batch optimization strategy (implement if jobs > 100):
  * Use UNNEST for bulk INSERT of credit_transactions
  * Use UPDATE FROM for bulk tenant balance updates
  * Example: INSERT INTO credit_transactions SELECT * FROM UNNEST(arrays...)
  * Reduces round-trips from O(N) to O(1)
  * Complexity vs benefit: Only worthwhile for large datasets
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import uuid


# revision identifiers, used by Alembic.
revision = 'backfill_credits_20251117'
down_revision = '29c1376b3fad'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Backfill credit deductions for historical jobs."""

    # Get database connection
    connection = op.get_bind()

    # Track migration timing for performance monitoring
    import time
    import os
    migration_start = time.time()

    # Audit logging: Track who is running the migration
    migration_operator = os.environ.get('MIGRATION_USER', 'unknown')
    migration_timestamp = datetime.utcnow().isoformat()

    print(f"\n{'='*70}")
    print(f"MIGRATION: Backfill Credit Deductions")
    print(f"Operator: {migration_operator}")
    print(f"Started at: {migration_timestamp}")
    print(f"{'='*70}\n")

    try:
        # Find all completed jobs without credit deductions
        # Use raw SQL for precise control over transaction handling
        # CRITICAL: Use FOR UPDATE to prevent concurrent migration runs from processing same jobs
        affected_jobs_query = text("""
            SELECT
                ej.id as job_id,
                ej.document_id,
                ej.model_provider,
                ej.model_name,
                ej.completed_at,
                d.tenant_id,
                d.page_count,
                d.filename
            FROM extraction_jobs ej
            JOIN documents d ON d.id = ej.document_id
            WHERE ej.status = 'completed'
              AND (ej.credits_deducted = FALSE OR ej.credits_deducted IS NULL)
              AND ej.credit_transaction_id IS NULL
            ORDER BY ej.completed_at ASC
            FOR UPDATE OF ej  -- Lock jobs to prevent duplicate processing
        """)

        affected_jobs = connection.execute(affected_jobs_query).fetchall()

        if not affected_jobs:
            print("✓ No jobs require backfilling. Migration complete.")
            return

        print(f"Found {len(affected_jobs)} jobs requiring credit deduction backfill")

        # Process each job
        total_credits = 0
        processed_count = 0
        skipped_count = 0
        affected_tenants = set()  # Track affected tenants for audit
        tenant_balance_changes = {}  # Track before/after balances for audit

        for job in affected_jobs:
            job_id = job.job_id
            tenant_id = job.tenant_id
            document_id = job.document_id
            page_count = job.page_count or 1
            model_provider = job.model_provider or "unknown"
            model_name = job.model_name or "unknown"
            completed_at = job.completed_at or datetime.utcnow()
            filename = job.filename or "unknown"

            # DEFENSIVE: Double-check job hasn't been processed (race condition protection)
            check_query = text("""
                SELECT credits_deducted, credit_transaction_id
                FROM extraction_jobs
                WHERE id = :job_id
            """)
            current_state = connection.execute(check_query, {"job_id": job_id}).fetchone()

            if current_state and (current_state.credits_deducted or current_state.credit_transaction_id):
                print(f"  ⊘ Skipping job {job_id} - already processed by concurrent migration")
                skipped_count += 1
                continue

            # Calculate credits (1 per page)
            required_credits = page_count
            total_credits += required_credits

            # Track tenant for audit
            affected_tenants.add(tenant_id)

            # Get tenant's balance BEFORE deduction for audit trail
            if tenant_id not in tenant_balance_changes:
                balance_query = text("SELECT cached_balance FROM tenants WHERE id = :tenant_id")
                balance_result = connection.execute(balance_query, {"tenant_id": tenant_id}).fetchone()
                before_balance = balance_result.cached_balance if balance_result else 0
                tenant_balance_changes[tenant_id] = {
                    "before": before_balance,
                    "deducted": 0
                }

            tenant_balance_changes[tenant_id]["deducted"] += required_credits

            print(f"  Processing job {job_id}: {filename} ({required_credits} credits)")

            # Create credit transaction
            transaction_id = uuid.uuid4()

            # Build metadata JSON manually
            import json as json_lib
            metadata_dict = {
                "job_id": str(job_id),
                "document_id": str(document_id),
                "page_count": required_credits,
                "model_provider": model_provider,
                "model_name": model_name,
                "backfill": True,
                "backfill_date": datetime.utcnow().isoformat(),
                "backfill_reason": "Missing credit deduction from /jobs/extract bug"
            }
            metadata_json = json_lib.dumps(metadata_dict)

            insert_transaction_query = text("""
                INSERT INTO credit_transactions (
                    id,
                    tenant_id,
                    transaction_type,
                    amount,
                    reference_type,
                    reference_id,
                    description,
                    transaction_metadata,
                    created_at,
                    created_by_user_id
                ) VALUES (
                    :transaction_id,
                    :tenant_id,
                    'deduction',
                    :amount,
                    'extraction_job',
                    :job_id,
                    :description,
                    CAST(:metadata AS jsonb),
                    :created_at,
                    NULL
                )
            """)

            connection.execute(
                insert_transaction_query,
                {
                    "transaction_id": transaction_id,
                    "tenant_id": tenant_id,
                    "amount": -required_credits,  # Negative for deduction
                    "job_id": job_id,
                    "description": f"[BACKFILL] Document extraction - {required_credits} page(s) (job {job_id})",
                    "metadata": metadata_json,
                    "created_at": completed_at,  # Use original completion date
                }
            )

            # Update tenant cached_balance
            update_tenant_query = text("""
                UPDATE tenants
                SET cached_balance = GREATEST(0, cached_balance - :amount),
                    balance_last_updated = :updated_at
                WHERE id = :tenant_id
            """)

            connection.execute(
                update_tenant_query,
                {
                    "amount": required_credits,
                    "tenant_id": tenant_id,
                    "updated_at": datetime.utcnow(),
                }
            )

            # Update job credits_cost if NULL
            update_job_cost_query = text("""
                UPDATE extraction_jobs
                SET credits_cost = :credits_cost
                WHERE id = :job_id AND credits_cost IS NULL
            """)

            connection.execute(
                update_job_cost_query,
                {
                    "credits_cost": required_credits,
                    "job_id": job_id,
                }
            )

            # Link transaction to job
            update_job_query = text("""
                UPDATE extraction_jobs
                SET credits_deducted = TRUE,
                    credit_transaction_id = :transaction_id
                WHERE id = :job_id
            """)

            connection.execute(
                update_job_query,
                {
                    "transaction_id": transaction_id,
                    "job_id": job_id,
                }
            )

            print(f"    ✓ Created transaction {transaction_id}, deducted {required_credits} credits")
            processed_count += 1

        # Calculate migration duration
        migration_end = time.time()
        duration_seconds = migration_end - migration_start

        print(f"\n{'='*70}")
        print(f"✓ Backfill complete:")
        print(f"  - Total jobs found: {len(affected_jobs)}")
        print(f"  - Jobs processed: {processed_count}")
        print(f"  - Jobs skipped (already processed): {skipped_count}")
        print(f"  - Total credits deducted: {total_credits}")
        print(f"  - Migration duration: {duration_seconds:.2f} seconds")
        print(f"  - Average time per job: {duration_seconds / max(processed_count, 1):.3f} seconds")
        print(f"Completed at: {datetime.utcnow().isoformat()}")
        print(f"{'='*70}\n")

        # Audit trail: Log affected tenants and balance changes
        print(f"AUDIT TRAIL:")
        print(f"  - Migration operator: {migration_operator}")
        print(f"  - Affected tenants: {len(affected_tenants)}")
        for tenant_id, changes in tenant_balance_changes.items():
            after_balance = changes["before"] - changes["deducted"]
            print(f"    * Tenant {tenant_id}:")
            print(f"      - Balance before: {changes['before']}")
            print(f"      - Credits deducted: {changes['deducted']}")
            print(f"      - Balance after: {after_balance}")
        print(f"")

        # Performance guidance for future scaling
        if processed_count > 100:
            print("⚠️  PERFORMANCE NOTE:")
            print("    Migration processed >100 jobs with individual operations.")
            print("    Consider batching INSERT/UPDATE operations for better performance.")
            print("    See migration comments for batch optimization strategy.\n")

    except Exception as e:
        migration_end = time.time()
        duration_seconds = migration_end - migration_start
        print(f"\n{'='*70}")
        print(f"✗ ERROR during backfill: {e}")
        print(f"  - Migration duration before failure: {duration_seconds:.2f} seconds")
        print(f"  - Failed at: {datetime.utcnow().isoformat()}")
        print(f"{'='*70}\n")
        raise


def downgrade() -> None:
    """
    Rollback credit deduction backfill.

    SAFETY CHECKS:
    - Verifies no post-migration activity before restoring balances
    - Aborts if tenants have new transactions after migration
    - Requires manual intervention for tenants with activity

    This prevents giving tenants free credits if they've done work after migration.
    """

    connection = op.get_bind()
    import os

    # Track rollback operator
    rollback_operator = os.environ.get('MIGRATION_USER', 'unknown')

    print(f"\n{'='*70}")
    print(f"MIGRATION ROLLBACK: Backfill Credit Deductions")
    print(f"Operator: {rollback_operator}")
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print(f"{'='*70}\n")

    try:
        # Find backfilled transactions
        backfilled_transactions_query = text("""
            SELECT
                ct.id as transaction_id,
                ct.tenant_id,
                ct.amount,
                ct.reference_id as job_id,
                ct.created_at as migration_date
            FROM credit_transactions ct
            WHERE ct.transaction_metadata->>'backfill' = 'true'
              AND ct.reference_type = 'extraction_job'
            ORDER BY ct.created_at ASC
        """)

        backfilled = connection.execute(backfilled_transactions_query).fetchall()

        if not backfilled:
            print("✓ No backfilled transactions to rollback.")
            return

        # Get migration date (earliest backfill transaction)
        migration_date = backfilled[0].migration_date

        print(f"Found {len(backfilled)} backfilled transactions")
        print(f"Migration date: {migration_date}\n")

        # SAFETY CHECK: Verify no post-migration activity
        print("Running safety checks...")

        # Check for post-migration transactions
        post_migration_check = text("""
            SELECT
                tenant_id,
                COUNT(*) as post_migration_transactions
            FROM credit_transactions
            WHERE created_at > :migration_date
              AND transaction_metadata->>'backfill' IS DISTINCT FROM 'true'
            GROUP BY tenant_id
        """)

        post_migration_activity = connection.execute(
            post_migration_check,
            {"migration_date": migration_date}
        ).fetchall()

        if post_migration_activity:
            print(f"\n{'='*70}")
            print(f"✗ ROLLBACK ABORTED - POST-MIGRATION ACTIVITY DETECTED")
            print(f"{'='*70}")
            print(f"\nThe following tenants have activity after migration:")
            for activity in post_migration_activity:
                print(f"  - Tenant {activity.tenant_id}: {activity.post_migration_transactions} transactions")

            print(f"\n⚠️  MANUAL INTERVENTION REQUIRED:")
            print(f"    1. Review post-migration transactions for each tenant")
            print(f"    2. Manually calculate correct balances")
            print(f"    3. Update tenant balances via SQL:")
            print(f"       UPDATE tenants SET cached_balance = <correct_balance> WHERE id = '<tenant_id>';")
            print(f"    4. Delete backfill transactions manually:")
            print(f"       DELETE FROM credit_transactions WHERE transaction_metadata->>'backfill' = 'true';")
            print(f"\n❌ Automatic rollback cannot proceed safely.\n")
            raise Exception(
                f"Rollback aborted: {len(post_migration_activity)} tenants have post-migration activity. "
                f"Manual intervention required to prevent data corruption."
            )

        print("✓ No post-migration activity detected. Safe to rollback.\n")
        print(f"Rolling back {len(backfilled)} backfilled transactions...")

        total_credits = 0
        for transaction in backfilled:
            transaction_id = transaction.transaction_id
            tenant_id = transaction.tenant_id
            amount = transaction.amount  # Negative value
            job_id = transaction.job_id

            credits = abs(amount)
            total_credits += credits

            # Restore tenant balance (add back the credits)
            restore_balance_query = text("""
                UPDATE tenants
                SET cached_balance = cached_balance + :amount,
                    balance_last_updated = :updated_at
                WHERE id = :tenant_id
            """)

            connection.execute(
                restore_balance_query,
                {
                    "amount": credits,  # Make positive
                    "tenant_id": tenant_id,
                    "updated_at": datetime.utcnow(),
                }
            )

            # Reset job flags
            reset_job_query = text("""
                UPDATE extraction_jobs
                SET credits_deducted = FALSE,
                    credit_transaction_id = NULL
                WHERE id = :job_id
            """)

            connection.execute(reset_job_query, {"job_id": job_id})

            # Delete transaction
            delete_transaction_query = text("""
                DELETE FROM credit_transactions
                WHERE id = :transaction_id
            """)

            connection.execute(delete_transaction_query, {"transaction_id": transaction_id})

            print(f"  ✓ Rolled back transaction {transaction_id}, restored {credits} credits")

        print(f"\n{'='*70}")
        print(f"✓ Rollback complete:")
        print(f"  - Transactions removed: {len(backfilled)}")
        print(f"  - Credits restored: {total_credits}")
        print(f"  - Operator: {rollback_operator}")
        print(f"Completed at: {datetime.utcnow().isoformat()}")
        print(f"{'='*70}\n")

    except Exception as e:
        print(f"\n{'='*70}")
        print(f"✗ ERROR during rollback: {e}")
        print(f"  - Operator: {rollback_operator}")
        print(f"  - Failed at: {datetime.utcnow().isoformat()}")
        print(f"{'='*70}\n")
        raise
