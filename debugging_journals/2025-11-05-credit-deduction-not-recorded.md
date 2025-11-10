# Bug Report: Credit Deductions Not Recording Despite Completed Jobs

**Date:** 2025-11-05
**Severity:** CRITICAL
**Confidence:** HIGH
**Category:** Logic/Data Inconsistency

---

## Executive Summary

The billing system shows "0 used this month" despite 10+ completed extraction jobs in November. Root cause: All extraction jobs created BEFORE the synchronous credit deduction implementation (November 5, 2025, 14:34:06 UTC) have `credits_deducted = false` and no linked credit transactions. The subscription endpoint filters for `transaction_type = "usage"` but the system uses `transaction_type = "deduction"`.

---

## Location

**Affected Files:**
- `app/api/subscriptions.py:38-51` - Query filtering for wrong transaction_type
- `app/api/documents.py:206-319` - Synchronous credit deduction (implemented Nov 5)
- `app/services/credit_service.py:163-166` - Creates transactions with type "deduction"

**Affected Tables:**
- `credit_transactions` - Contains credit movement records
- `extraction_jobs` - Contains job completion status

---

## Evidence from Database

### 1. Completed Jobs with No Credit Deduction

```sql
-- All 10+ completed jobs have credits_deducted = false
SELECT id, status, credits_cost, credits_deducted, credit_transaction_id, created_at
FROM extraction_jobs
WHERE status = 'completed' AND created_at >= '2025-11-01'
ORDER BY completed_at DESC LIMIT 10;

Result:
- 10 completed jobs from Nov 2-5
- ALL have credits_deducted = false
- ALL have credit_transaction_id = NULL
- ALL have credits_cost = NULL
```

### 2. No Extraction Job Transactions Exist

```sql
-- Zero credit transactions linked to extraction jobs
SELECT COUNT(*) FROM credit_transactions
WHERE reference_type = 'extraction_job';

Result: 0 rows
```

### 3. Transaction Types in Database

```sql
SELECT transaction_type, COUNT(*), SUM(amount)
FROM credit_transactions
GROUP BY transaction_type;

Result:
- deduction: 1 row, -50 credits (test transaction)
- trial_signup: 1 row, +100 credits
- migration_balance_import: 2 rows, +1,000,100 credits
- NO "usage" type exists!
```

### 4. Subscription Query Filter Mismatch

```python
# app/api/subscriptions.py:43
CreditTransaction.transaction_type == "usage"  # ❌ WRONG

# app/services/credit_service.py:165
transaction_type="deduction"  # ✅ ACTUAL TYPE
```

---

## Root Cause Analysis

### Primary Issue: Transaction Type Mismatch

**The Problem:**
1. **Credit Service** creates transactions with `transaction_type = "deduction"` (line 165 in `credit_service.py`)
2. **Subscription Endpoint** queries for `transaction_type = "usage"` (line 43 in `subscriptions.py`)
3. These never match, resulting in **zero credits_used** being returned

### Secondary Issue: Jobs Created Before Implementation

**Timeline:**
- **Before Nov 5, 14:34 UTC**: Credit deduction was NOT implemented
  - Jobs were created and completed
  - No credit transactions were created
  - `extraction_jobs.credits_deducted = false`
  - `extraction_jobs.credit_transaction_id = NULL`

- **After Nov 5, 14:34 UTC**: Synchronous credit deduction implemented
  - New jobs now deduct credits upfront (lines 206-319 in `documents.py`)
  - But transaction_type is "deduction", not "usage"

### Evidence from Code

#### 1. Credit Service Implementation

**File:** `app/services/credit_service.py`

```python
# Line 163-166: Creates transaction with type "deduction"
transaction = CreditTransaction(
    tenant_id=tenant_id,
    transaction_type="deduction",  # ✅ Uses "deduction"
    amount=-amount,
    reference_type=reference_type,
    reference_id=reference_id,
    # ...
)
```

**Valid Transaction Types (Line 230-237):**
```python
valid_types = [
    "topup",
    "deduction",      # ✅ Used for job credits
    "refund",
    "admin_adjustment",
    "trial_signup",
    "migration_balance_import"
]
# Note: "usage" is NOT a valid type!
```

#### 2. Subscription Endpoint Query

**File:** `app/api/subscriptions.py`

```python
# Line 38-48: Queries for WRONG transaction type
credits_used_result = (
    db.query(func.sum(CreditTransaction.amount))
    .filter(
        and_(
            CreditTransaction.tenant_id == current_user.tenant_id,
            CreditTransaction.transaction_type == "usage",  # ❌ WRONG TYPE
            CreditTransaction.created_at >= billing_period_start
        )
    )
    .scalar()
)
```

#### 3. Documents API Implementation

**File:** `app/api/documents.py`

```python
# Line 270-286: Synchronous credit deduction (implemented Nov 5)
credit_transaction = credit_service.deduct_credits(
    tenant_id=current_user.tenant_id,
    amount=required_credits,
    reference_type="extraction_job",  # ✅ Correct reference
    reference_id=job.id,
    description=f"Document extraction - {required_credits} page(s) (job {job.id})",
    created_by_user_id=current_user.id,
    metadata={
        "job_id": str(job.id),
        "document_id": str(document.id),
        "page_count": required_credits,
        # ...
    },
    allow_negative=False,
)
```

**Lines 245-250 in extractor.py:**
```python
# --- CREDIT BILLING NOTE ---
# Credits are now deducted SYNCHRONOUSLY in the API endpoint (app/api/documents.py)
# when the job is created. This eliminates the TOCTOU race condition.
# No async deduction needed here for successful jobs.
# If the job fails, credits are refunded in the exception handler below.
# --- END CREDIT BILLING NOTE ---
```

---

## Reproduction Steps

### Scenario 1: Query Returns Zero (Current Bug)

1. Create and complete extraction jobs before Nov 5, 14:34 UTC
2. Navigate to Billing page in frontend
3. Observe "0 used this month" despite completed jobs table showing credit usage
4. **Expected:** Sum of all job credits (11+ credits)
5. **Actual:** 0 credits (query finds no matching transactions)

### Scenario 2: Database Verification

```sql
-- Step 1: Check for "usage" transactions (what the query looks for)
SELECT COUNT(*) FROM credit_transactions
WHERE transaction_type = 'usage';
-- Result: 0 rows ❌

-- Step 2: Check for "deduction" transactions (what actually exists)
SELECT COUNT(*) FROM credit_transactions
WHERE transaction_type = 'deduction'
  AND reference_type = 'extraction_job';
-- Result: 0 rows ❌ (because old jobs never created transactions)

-- Step 3: Check jobs without credit transactions
SELECT COUNT(*) FROM extraction_jobs
WHERE status = 'completed'
  AND credits_deducted = false
  AND created_at >= '2025-11-01';
-- Result: 10+ rows ✅ (all November jobs before the fix)
```

---

## Fix Attempt #1: Change Query to Use "deduction"

### Implementation

**File:** `app/api/subscriptions.py`

```python
# BEFORE (Line 43):
CreditTransaction.transaction_type == "usage"

# AFTER:
CreditTransaction.transaction_type == "deduction"
```

### Testing

```sql
-- Verify query will find deduction transactions
SELECT
    DATE_TRUNC('day', created_at) as day,
    COUNT(*) as transactions,
    SUM(amount) as total_amount
FROM credit_transactions
WHERE transaction_type = 'deduction'
  AND created_at >= '2025-11-01'
GROUP BY day
ORDER BY day DESC;

-- Expected result: 1 test transaction (-50 credits)
-- Still won't show job credits because old jobs didn't create transactions
```

### Result

**Status:** PARTIAL FIX
**Outcome:**
- ✅ Query will now find future job deductions (after Nov 5, 14:34)
- ❌ Still won't show credits for old completed jobs (before Nov 5, 14:34)
- **Reason:** Old jobs were completed without creating credit transactions

---

## Fix Attempt #2: Backfill Missing Credit Transactions

### Analysis

The synchronous credit deduction was implemented on Nov 5, 14:34 UTC. All jobs completed before this date have:
- `credits_deducted = false`
- `credit_transaction_id = NULL`
- No corresponding `credit_transactions` record

### Implementation Options

#### Option A: One-Time Migration Script (RECOMMENDED)

Create a migration to backfill credit transactions for completed jobs:

```python
# alembic/versions/YYYY-MM-DD_backfill_job_credits.py

def upgrade():
    # Get database session
    bind = op.get_bind()
    session = Session(bind=bind)

    from app.models import ExtractionJob, Document, Tenant, CreditTransaction
    from datetime import datetime
    from uuid import uuid4

    # Find all completed jobs without credit transactions
    orphaned_jobs = (
        session.query(ExtractionJob)
        .filter(
            ExtractionJob.status == 'completed',
            ExtractionJob.credits_deducted == False,
            ExtractionJob.credits_cost == None  # Old jobs don't have cost recorded
        )
        .all()
    )

    print(f"Found {len(orphaned_jobs)} orphaned jobs")

    for job in orphaned_jobs:
        # Get document to find tenant and page count
        document = session.query(Document).filter(Document.id == job.document_id).first()
        if not document:
            continue

        # Calculate credits (1 per page)
        credits_used = document.page_count or 1

        # Create backfill transaction
        transaction = CreditTransaction(
            id=uuid4(),
            tenant_id=document.tenant_id,
            transaction_type="deduction",
            amount=-credits_used,
            reference_type="extraction_job",
            reference_id=job.id,
            description=f"[BACKFILL] Document extraction - {credits_used} page(s) (job {job.id})",
            created_by_user_id=None,  # System backfill
            transaction_metadata={
                "job_id": str(job.id),
                "document_id": str(document.id),
                "page_count": credits_used,
                "backfill": True,
                "backfill_date": datetime.utcnow().isoformat(),
                "model_provider": job.model_provider,
                "model_name": job.model_name,
            },
            created_at=job.completed_at or job.created_at  # Use job completion time
        )

        session.add(transaction)

        # Update job record
        job.credits_deducted = True
        job.credits_cost = credits_used
        job.credit_transaction_id = transaction.id

    # Update tenant cached balances
    tenants = session.query(Tenant).all()
    for tenant in tenants:
        from app.services.credit_service import CreditService
        credit_service = CreditService(session)
        credit_service.recalculate_cached_balance(tenant.id)

    session.commit()
```

#### Option B: API Endpoint for Manual Backfill

```python
# app/api/admin.py

@router.post("/admin/credits/backfill-jobs")
async def backfill_job_credits(
    current_user: User = Depends(require_permission("admin:credits:manage")),
    db: Session = Depends(get_db)
):
    """Backfill credit transactions for completed jobs (admin only)."""
    # Same logic as migration above
    pass
```

### Testing Plan

```sql
-- 1. Before backfill: Check orphaned jobs
SELECT COUNT(*) FROM extraction_jobs
WHERE status = 'completed'
  AND credits_deducted = false
  AND created_at >= '2025-11-01';
-- Expected: 10+ rows

-- 2. Run backfill migration
alembic revision --autogenerate -m "backfill job credits"
alembic upgrade head

-- 3. After backfill: Verify transactions created
SELECT COUNT(*) FROM credit_transactions
WHERE reference_type = 'extraction_job'
  AND transaction_type = 'deduction';
-- Expected: 10+ rows (matching orphaned jobs)

-- 4. Verify jobs updated
SELECT COUNT(*) FROM extraction_jobs
WHERE status = 'completed'
  AND credits_deducted = true
  AND credit_transaction_id IS NOT NULL;
-- Expected: ALL completed jobs

-- 5. Test subscription endpoint
curl http://localhost:8000/api/v1/subscriptions/current
-- Expected: credits_used shows sum of all November job credits
```

### Result

**Status:** NOT YET IMPLEMENTED
**Expected Outcome:**
- ✅ All completed jobs will have credit transactions
- ✅ `credits_used` in billing will show accurate usage
- ✅ Tenant balances will be correctly adjusted
- ✅ Historical data will be consistent

---

## Recommended Fix (Combined Solution)

### Step 1: Fix Query Transaction Type (IMMEDIATE)

**File:** `app/api/subscriptions.py`

```python
# Line 43: Change from "usage" to "deduction"
credits_used_result = (
    db.query(func.sum(CreditTransaction.amount))
    .filter(
        and_(
            CreditTransaction.tenant_id == current_user.tenant_id,
            CreditTransaction.transaction_type == "deduction",  # FIX: Changed from "usage"
            CreditTransaction.reference_type == "extraction_job",  # ADDED: Only count job deductions
            CreditTransaction.created_at >= billing_period_start
        )
    )
    .scalar()
)
```

**Rationale:**
- Matches actual transaction type created by `credit_service.deduct_credits()`
- Adds `reference_type` filter to only count job-related deductions
- Excludes other deduction types (manual adjustments, etc.)

### Step 2: Backfill Missing Transactions (DATA MIGRATION)

**Create Migration:**

```bash
alembic revision -m "backfill_job_credit_transactions"
```

**Implementation:** Use Option A code above

**Rationale:**
- Ensures historical accuracy
- Corrects tenant balances
- Provides complete audit trail

### Step 3: Verify Fix

```bash
# 1. Apply fixes
cd /Users/xavierau/Code/python/ai_document_processing

# 2. Edit subscriptions.py (Step 1)
# ... make the changes ...

# 3. Create and run migration (Step 2)
alembic revision -m "backfill_job_credit_transactions"
# ... add upgrade() code ...
alembic upgrade head

# 4. Restart API server
# ... restart uvicorn ...

# 5. Test endpoint
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/subscriptions/current

# Expected response:
# {
#   "credits_balance": 100,
#   "credits_used": 11,  # Sum of all November job credits
#   "billing_period_start": "2025-11-01T00:00:00",
#   ...
# }
```

---

## Prevention Strategies

### 1. Transaction Type Consistency

**Create Enum for Transaction Types:**

```python
# app/models/credit_transaction.py
from enum import Enum

class TransactionType(str, Enum):
    TOPUP = "topup"
    DEDUCTION = "deduction"
    REFUND = "refund"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    TRIAL_SIGNUP = "trial_signup"
    MIGRATION = "migration_balance_import"

# Update model
transaction_type = Column(
    Enum(TransactionType),
    nullable=False,
    index=True
)
```

**Benefits:**
- Type safety (compile-time checking)
- IDE autocomplete
- Prevents string typos
- Self-documenting code

### 2. Database Constraints

**Add CHECK Constraint:**

```sql
ALTER TABLE credit_transactions
ADD CONSTRAINT check_valid_transaction_type
CHECK (transaction_type IN (
    'topup',
    'deduction',
    'refund',
    'admin_adjustment',
    'trial_signup',
    'migration_balance_import'
));
```

### 3. Integration Tests

**Test Credit Flow End-to-End:**

```python
# tests/integration/test_credit_billing.py

def test_job_creation_deducts_credits(client, auth_headers, db):
    """Verify job creation creates credit transaction."""

    # 1. Upload document
    response = client.post("/api/v1/documents/upload", ...)
    doc_id = response.json()["document_id"]

    # 2. Get initial balance
    initial_balance = get_credit_balance(client, auth_headers)

    # 3. Create extraction job
    response = client.post(f"/api/v1/documents/{doc_id}/parse", ...)
    job_id = response.json()["extraction_job_id"]

    # 4. Verify credit transaction created
    transactions = db.query(CreditTransaction).filter(
        CreditTransaction.reference_type == "extraction_job",
        CreditTransaction.reference_id == job_id
    ).all()

    assert len(transactions) == 1
    assert transactions[0].transaction_type == "deduction"
    assert transactions[0].amount < 0

    # 5. Verify balance decreased
    new_balance = get_credit_balance(client, auth_headers)
    assert new_balance == initial_balance - abs(transactions[0].amount)

    # 6. Verify subscription endpoint reflects usage
    response = client.get("/api/v1/subscriptions/current", headers=auth_headers)
    assert response.json()["credits_used"] > 0
```

### 4. Database Integrity Checks

**Create Admin Endpoint for Audit:**

```python
# app/api/admin.py

@router.get("/admin/credits/audit")
async def audit_credit_consistency(
    current_user: User = Depends(require_permission("admin:credits:audit")),
    db: Session = Depends(get_db)
):
    """Check for credit data inconsistencies."""

    issues = []

    # Check 1: Jobs without transactions
    orphaned_jobs = db.query(ExtractionJob).filter(
        ExtractionJob.status == "completed",
        ExtractionJob.credits_deducted == False
    ).count()

    if orphaned_jobs > 0:
        issues.append({
            "type": "orphaned_jobs",
            "count": orphaned_jobs,
            "severity": "high",
            "message": f"{orphaned_jobs} completed jobs without credit transactions"
        })

    # Check 2: Transactions without jobs
    orphaned_transactions = db.query(CreditTransaction).filter(
        CreditTransaction.reference_type == "extraction_job",
        ~CreditTransaction.reference_id.in_(
            db.query(ExtractionJob.id)
        )
    ).count()

    if orphaned_transactions > 0:
        issues.append({
            "type": "orphaned_transactions",
            "count": orphaned_transactions,
            "severity": "medium",
            "message": f"{orphaned_transactions} credit transactions with missing jobs"
        })

    # Check 3: Cached balance vs actual balance mismatch
    tenants = db.query(Tenant).all()
    for tenant in tenants:
        cached = tenant.cached_balance
        actual = db.query(func.sum(CreditTransaction.amount)).filter(
            CreditTransaction.tenant_id == tenant.id
        ).scalar() or 0

        if cached != actual:
            issues.append({
                "type": "balance_mismatch",
                "tenant_id": str(tenant.id),
                "severity": "critical",
                "cached_balance": cached,
                "actual_balance": actual,
                "difference": cached - actual
            })

    return {
        "status": "healthy" if len(issues) == 0 else "issues_found",
        "issues": issues,
        "timestamp": datetime.utcnow().isoformat()
    }
```

### 5. Monitoring and Alerts

**Add Prometheus Metrics:**

```python
# app/middleware/metrics.py

from prometheus_client import Counter, Gauge

# Counter for credit deductions
credit_deductions = Counter(
    'credit_deductions_total',
    'Total credit deductions',
    ['tenant_id', 'reference_type']
)

# Gauge for orphaned jobs
orphaned_jobs_gauge = Gauge(
    'orphaned_jobs_count',
    'Number of completed jobs without credit transactions'
)

# Update gauge periodically
@celery_app.task
def update_orphaned_jobs_metric():
    count = db.query(ExtractionJob).filter(
        ExtractionJob.status == "completed",
        ExtractionJob.credits_deducted == False
    ).count()

    orphaned_jobs_gauge.set(count)
```

---

## Related Documentation

### Architecture Docs
- [docs/guides/2025-11-05-synchronous-credit-deduction.md](../docs/guides/2025-11-05-synchronous-credit-deduction.md) - Credit deduction implementation
- [docs/guides/2025-11-05-credit-billing-guide.md](../docs/guides/2025-11-05-credit-billing-guide.md) - Credit system design
- [docs/architecture/2025-11-05-credit-billing-system.md](../docs/architecture/2025-11-05-credit-billing-system.md) - Credit architecture

### Related Code Files
- `app/api/subscriptions.py` - Subscription and billing endpoints
- `app/api/documents.py` - Document upload and job creation (credit deduction point)
- `app/services/credit_service.py` - Credit operations service
- `app/models/credit_transaction.py` - Credit transaction model
- `app/models/extraction_job.py` - Extraction job model
- `app/tasks/extractor.py` - Job processing task

### Database Schema
- `credit_transactions` table - Event sourcing for credit movements
- `extraction_jobs` table - Job status and credit tracking
- `tenants` table - Cached balance storage

---

## Summary

### Root Cause
1. **Transaction Type Mismatch:** Query looks for "usage", but system creates "deduction"
2. **Historical Data Gap:** Old jobs (before Nov 5, 14:34) never created credit transactions

### Impact
- **User Experience:** Billing page shows incorrect usage (0 instead of 11+)
- **Data Integrity:** Missing audit trail for completed jobs
- **Trust:** Users may question billing accuracy

### Solution
1. **Immediate:** Fix query to use "deduction" transaction type
2. **Data Migration:** Backfill missing credit transactions for old jobs
3. **Prevention:** Add type safety, constraints, and monitoring

### Confidence Level
**HIGH** - Clear evidence from database queries and code inspection confirms both issues.

---

**Investigation Completed:** 2025-11-05
**Status:** Solution identified, implementation pending
