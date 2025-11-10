# Synchronous Credit Deduction - Implementation Guide

**Date:** 2025-11-05
**Version:** 2.0
**Status:** Production Ready
**Architecture:** Synchronous Deduction with Automatic Refunds

---

## Overview

This system implements **synchronous credit deduction** where credits are deducted IMMEDIATELY when a job is created (not asynchronously after completion). If the job fails, credits are automatically refunded via compensating transactions.

**Key Benefits:**
- ✅ **Eliminates TOCTOU race conditions** - Credits deducted atomically with job creation
- ✅ **Automatic refunds** - Failed jobs refund credits immediately
- ✅ **Complete audit trail** - Full transaction history with refund tracking
- ✅ **O(1) performance** - Cached balance for instant lookups

---

## Architecture

### Synchronous Deduction Flow

```
┌─────────────────────────────────────────────────────────┐
│ POST /documents/{id}/parse                               │
└─────────────────────────────────────────────────────────┘
                        ↓
         ┌──────────────────────────┐
         │ BEGIN TRANSACTION        │
         │ (REPEATABLE READ)        │
         └──────────────────────────┘
                        ↓
         ┌──────────────────────────┐
         │ SELECT tenant FOR UPDATE │ ← Pessimistic lock
         └──────────────────────────┘
                        ↓
         ┌──────────────────────────┐
         │ Check balance >= cost?   │
         └──────────────────────────┘
                ↙              ↘
              NO               YES
               ↓                ↓
    ┌─────────────────┐  ┌────────────────┐
    │ HTTP 402        │  │ Create job     │
    │ ROLLBACK        │  │ Deduct credits │ ← IMMEDIATE
    └─────────────────┘  │ Update cache   │
                         │ COMMIT         │
                         └────────────────┘
                                 ↓
                    ┌────────────────────────┐
                    │ Queue Celery task      │
                    └────────────────────────┘
                                 ↓
         ┌───────────────────────────────────┐
         │ Celery: process_extraction_job    │
         └───────────────────────────────────┘
                    ↙                  ↘
            JOB SUCCESS            JOB FAILS
                 ↓                      ↓
    ┌──────────────────────┐  ┌──────────────────────┐
    │ Mark "completed"     │  │ Mark "failed"        │
    │ (credits already     │  │ REFUND credits       │ ← AUTOMATIC
    │  deducted)           │  │ Log refund TX ID     │
    └──────────────────────┘  └──────────────────────┘
```

---

## Key Components

### 1. Synchronous Deduction in API

**File:** `app/api/documents.py` (lines 206-319)

**Implementation:**
```python
# Single atomic transaction
try:
    # 1. Lock tenant row
    tenant = db.query(Tenant).filter(...).with_for_update().first()

    # 2. Check balance
    has_sufficient, current_balance = credit_service.check_sufficient_credits(...)

    if not has_sufficient:
        raise HTTPException(status_code=402, detail={...})

    # 3. Create job
    job = ExtractionJob(...)
    db.add(job)
    db.flush()

    # 4. Deduct credits IMMEDIATELY (within same transaction)
    credit_transaction = credit_service.deduct_credits(
        tenant_id=tenant_id,
        amount=required_credits,
        reference_type="extraction_job",
        reference_id=job.id,
        description=f"Document extraction - {required_credits} page(s)",
        allow_negative=False
    )

    # 5. Link transaction to job
    job.credits_deducted = True
    job.credit_transaction_id = credit_transaction.id

    # 6. COMMIT (all or nothing)
    db.commit()

except Exception:
    db.rollback()
    raise
```

**Key Points:**
- Credits deducted BEFORE job starts processing
- If deduction fails, job is not created (atomic rollback)
- No window for race conditions

---

### 2. Automatic Refunds on Failure

**File:** `app/tasks/extractor.py` (lines 408-443)

**Implementation:**
```python
# When job fails after all retries
if job:
    job.status = "failed"
    job.error_message = str(e)
    job.completed_at = datetime.utcnow()
    db.commit()

    # AUTOMATIC REFUND
    if job.credits_deducted and job.credits_cost:
        try:
            credit_service = CreditService(db)
            refund_transaction = credit_service.refund_job_credits(
                job_id=job.id,
                tenant_id=job.document.tenant_id,
                refund_amount=job.credits_cost,
                reason=f"Job failed after {max_retries} retries: {error}",
                user_id=None  # System refund
            )
            db.commit()

            logger.info(f"✓ Refunded {credits} credits for failed job")

        except Exception as refund_error:
            logger.error(f"BILLING ERROR: Failed to refund. MANUAL REFUND REQUIRED.")
            # Store in job metadata for admin review
            job.document_metadata["refund_error"] = {...}
            db.commit()
```

**Key Points:**
- Refunds happen automatically when job fails
- Refund failures are logged and flagged for manual review
- Full audit trail maintained

---

### 3. Refund Method in CreditService

**File:** `app/services/credit_service.py` (lines 454-509)

**Implementation:**
```python
def refund_job_credits(
    self,
    job_id: UUID,
    tenant_id: UUID,
    refund_amount: int,
    reason: str,
    user_id: Optional[UUID] = None
) -> CreditTransaction:
    """
    Refund credits for a failed or cancelled extraction job.

    Creates a compensating transaction (credit addition) to reverse
    the deduction that occurred when the job was created.
    """
    # Create refund transaction (positive amount)
    transaction = self.add_credits(
        tenant_id=tenant_id,
        amount=refund_amount,
        transaction_type="refund",
        description=f"Refund for failed job {job_id}: {reason}",
        created_by_user_id=user_id,
        metadata={
            "job_id": str(job_id),
            "refund_reason": reason,
            "original_deduction_id": str(original_tx_id),
            "document_id": str(document_id),
            "page_count": refund_amount,
        }
    )

    return transaction
```

**Key Points:**
- Refunds are new transactions (not deletions)
- Full metadata links refund to original deduction
- Complete audit trail maintained

---

## Transaction Types

| Type | Direction | When Used | Example |
|------|-----------|-----------|---------|
| `topup` | Credit (+) | User purchases credits | +100 credits |
| `deduction` | Debit (-) | Job created | -10 credits |
| `refund` | Credit (+) | Job failed | +10 credits |
| `admin_adjustment` | Either | Manual correction | +50 or -50 |
| `migration_balance_import` | Credit (+) | Data migration | +100 (legacy) |

---

## Audit Trail Example

### Scenario: Job Submission and Failure

**Timeline:**
```
10:00:00 - User tops up 100 credits
10:01:00 - Job created, 10 credits deducted immediately
10:05:00 - Job fails after 3 retries, 10 credits refunded
```

**Transaction Log:**

```sql
SELECT
    created_at,
    transaction_type,
    amount,
    description,
    reference_id
FROM credit_transactions
WHERE tenant_id = 'tenant-abc'
ORDER BY created_at;
```

| Timestamp | Type | Amount | Description | Reference |
|-----------|------|--------|-------------|-----------|
| 10:00:00 | topup | +100 | Credit purchase - 100 credits | - |
| 10:01:00 | deduction | -10 | Document extraction - 10 page(s) (job abc-123) | job:abc-123 |
| 10:05:00 | refund | +10 | Refund for failed job abc-123: VLLM timeout | job:abc-123 |

**Final Balance:** 100 credits (original balance restored)

---

## API Integration

### Submit Extraction Job

```bash
curl -X POST http://localhost:8000/api/v1/documents/{doc_id}/parse \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "extraction_schema": {...},
    "model_provider_config": {
      "provider": "google",
      "model": "gemini-2.5-flash"
    },
    "processing_mode": "batch"
  }'
```

**Success Response (202 Accepted):**
```json
{
  "extraction_job_id": "abc-123",
  "status": "queued",
  "estimated_time_seconds": 20,
  "credits_deducted": 10,
  "credit_transaction_id": "tx-456"
}
```

**Insufficient Credits (402 Payment Required):**
```json
{
  "detail": {
    "error": "insufficient_credits",
    "message": "Insufficient credits. Required: 10, Available: 5",
    "required_credits": 10,
    "available_credits": 5,
    "credits_needed": 5
  }
}
```

---

## Database Schema

### ExtractionJob Updates

**New/Modified Fields:**
```sql
-- Tracks credit deduction
credits_cost INTEGER;              -- Cost estimate (page count)
credits_deducted BOOLEAN DEFAULT FALSE;  -- Idempotency flag
credit_transaction_id UUID;        -- Links to credit_transactions.id
```

### CreditTransaction Schema

```sql
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),

    -- Transaction details
    transaction_type VARCHAR(50) NOT NULL,  -- topup, deduction, refund, admin_adjustment
    amount INTEGER NOT NULL,                -- Signed: +100 (credit), -10 (debit)

    -- References
    reference_type VARCHAR(50),             -- extraction_job, payment, manual
    reference_id UUID,

    -- Stripe payment tracking
    stripe_payment_intent_id VARCHAR(255) UNIQUE,
    stripe_charge_id VARCHAR(255),

    -- Audit trail
    created_by_user_id UUID REFERENCES users(id),
    description TEXT NOT NULL,
    transaction_metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_credit_tx_tenant_created ON credit_transactions(tenant_id, created_at);
CREATE INDEX idx_credit_tx_reference ON credit_transactions(reference_type, reference_id);
CREATE INDEX idx_credit_tx_stripe_intent ON credit_transactions(stripe_payment_intent_id);
```

### Tenant Updates

**Cached Balance for O(1) Lookups:**
```sql
ALTER TABLE tenants ADD COLUMN cached_balance INTEGER NOT NULL DEFAULT 0;
ALTER TABLE tenants ADD COLUMN balance_last_updated TIMESTAMP;
CREATE INDEX idx_tenants_cached_balance ON tenants(cached_balance);
```

---

## Performance Optimizations

### 1. Cached Balance (O(1) Lookups)

**Before:** O(n) - Sum all transactions
```python
# Slow: 10-50ms for 10k transactions
balance = db.query(func.sum(CreditTransaction.amount)).filter(...).scalar()
```

**After:** O(1) - Cached column
```python
# Fast: <1ms
tenant = db.query(Tenant).filter(...).first()
balance = tenant.cached_balance
```

**Cache Update (Atomic):**
```python
# SQL-level arithmetic prevents race conditions
db.execute(
    update(Tenant)
    .where(Tenant.id == tenant_id)
    .values(cached_balance=Tenant.cached_balance - amount)
)
```

### 2. Database Isolation Level

**Configuration:** `app/database.py`
```python
engine = create_engine(
    settings.database_url,
    isolation_level="REPEATABLE READ"  # Prevents phantom reads
)
```

**Benefits:**
- Prevents non-repeatable reads
- Eliminates phantom reads
- Safer than READ COMMITTED for credit operations

---

## Error Handling

### Failed Job Refund

**Scenario:** Job fails, but refund operation also fails

**System Behavior:**
1. Job marked as `"failed"`
2. Refund attempted automatically
3. If refund fails:
   - Logged with CRITICAL severity
   - Stored in job metadata:
   ```json
   {
     "refund_error": {
       "error": "Database connection timeout",
       "credits_to_refund": 10,
       "timestamp": "2025-11-05T10:05:00Z"
     }
   }
   ```
4. Admin alerted for manual refund

**Manual Refund Process:**
```bash
# Admin manually refunds credits
curl -X POST http://localhost:8000/api/v1/credits/adjust \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 10,
    "reason": "Manual refund for failed job abc-123 (auto-refund failed)"
  }'
```

### Insufficient Credits After Job Creation

**Scenario:** Race condition causes balance check to pass, but deduction fails

**System Behavior:**
```python
try:
    # Check balance
    if not has_sufficient:
        raise HTTPException(status_code=402)

    # Create job
    job = ExtractionJob(...)

    # Deduct credits
    credit_service.deduct_credits(...)  # Might fail if race condition

    db.commit()

except InsufficientCreditsError:
    db.rollback()  # Job not created
    raise HTTPException(status_code=402)
```

**Result:** Transaction rolled back, no orphaned jobs

---

## Monitoring & Alerts

### Key Metrics

**1. Refund Rate**
```sql
SELECT
    DATE(created_at) as date,
    COUNT(*) FILTER (WHERE transaction_type = 'deduction') as jobs_created,
    COUNT(*) FILTER (WHERE transaction_type = 'refund') as jobs_refunded,
    ROUND(100.0 * COUNT(*) FILTER (WHERE transaction_type = 'refund') /
          COUNT(*) FILTER (WHERE transaction_type = 'deduction'), 2) as refund_rate_pct
FROM credit_transactions
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

**2. Failed Refunds**
```sql
SELECT
    id,
    error_message,
    document_metadata->'refund_error' as refund_error,
    credits_cost,
    created_at
FROM extraction_jobs
WHERE status = 'failed'
  AND document_metadata ? 'refund_error'
  AND created_at > NOW() - INTERVAL '24 hours';
```

**3. Balance Reconciliation**
```sql
-- Compare cached balance vs actual transaction sum
SELECT
    t.id as tenant_id,
    t.name,
    t.cached_balance,
    COALESCE(SUM(ct.amount), 0) as actual_balance,
    t.cached_balance - COALESCE(SUM(ct.amount), 0) as discrepancy
FROM tenants t
LEFT JOIN credit_transactions ct ON ct.tenant_id = t.id
GROUP BY t.id, t.name, t.cached_balance
HAVING t.cached_balance != COALESCE(SUM(ct.amount), 0);
```

### Alert Thresholds

| Alert | Threshold | Action |
|-------|-----------|--------|
| High refund rate | > 10% | Investigate job failures |
| Failed refunds | Any occurrence | Manual refund required |
| Cache desync | Discrepancy > 0 | Run `recalculate_cached_balance()` |
| Negative balance | < 0 | Investigate race condition |

---

## Testing

### Test Case 1: Concurrent Job Submissions

**Scenario:** 10 requests submitted simultaneously

**Setup:**
```python
# Tenant has 100 credits
# Each job costs 20 credits
# Submit 10 concurrent requests
```

**Expected Result:**
- 5 jobs created (100 / 20 = 5)
- 5 requests get HTTP 402 (insufficient credits)
- Final balance: 0 credits
- No negative balance

**Test Script:**
```python
import asyncio
import httpx

async def submit_job(client, doc_id, token):
    response = await client.post(
        f"/documents/{doc_id}/parse",
        headers={"Authorization": f"Bearer {token}"},
        json={"extraction_schema": {...}}
    )
    return response.status_code

async def test_concurrent_submissions():
    async with httpx.AsyncClient() as client:
        tasks = [submit_job(client, doc_id, token) for _ in range(10)]
        results = await asyncio.gather(*tasks)

    assert results.count(202) == 5  # 5 jobs accepted
    assert results.count(402) == 5  # 5 jobs rejected (insufficient credits)
```

### Test Case 2: Failed Job Refund

**Scenario:** Job fails, verify automatic refund

**Steps:**
1. Create job (10 credits deducted)
2. Simulate job failure (kill worker, invalid schema, etc.)
3. Wait for all retries to exhaust
4. Verify refund transaction created
5. Verify balance restored

**Verification:**
```sql
-- Check transaction log
SELECT
    transaction_type,
    amount,
    description
FROM credit_transactions
WHERE reference_id = 'failed-job-id'
ORDER BY created_at;

-- Should show:
-- 1. deduction: -10 (job created)
-- 2. refund: +10 (job failed)
```

### Test Case 3: Cache Consistency

**Scenario:** Verify cached balance matches actual sum

**Test:**
```python
def test_cache_consistency(db, tenant_id):
    # Perform 100 random operations
    for _ in range(100):
        operation = random.choice(['add', 'deduct'])
        amount = random.randint(1, 10)

        if operation == 'add':
            credit_service.add_credits(tenant_id, amount, "topup", "Test")
        else:
            try:
                credit_service.deduct_credits(tenant_id, amount, "test", uuid4(), "Test")
            except InsufficientCreditsError:
                pass

        db.commit()

    # Compare cached vs actual
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    cached_balance = tenant.cached_balance

    actual_balance = db.query(func.sum(CreditTransaction.amount))\
        .filter(CreditTransaction.tenant_id == tenant_id)\
        .scalar() or 0

    assert cached_balance == actual_balance, f"Cache desync: {cached_balance} != {actual_balance}"
```

---

## Migration Guide

### Step 1: Apply Database Migration

```bash
# Generate migration (already done)
alembic revision --autogenerate -m "add_cached_balance_to_tenants"

# Review migration file
cat alembic/versions/2025-11-05_34d31b85caab_add_cached_balance_to_tenants.py

# Apply migration
alembic upgrade head
```

**Migration Actions:**
1. Adds `cached_balance` column to `tenants` table
2. Adds `balance_last_updated` column
3. Populates cached values from existing transaction history
4. Creates index on `cached_balance`

### Step 2: Deploy Code Changes

```bash
# Pull latest code
git pull origin feature/saas_setup

# Restart services
docker-compose restart api worker
```

### Step 3: Verify Deployment

```bash
# Check balance endpoint
curl -H "Authorization: Bearer $JWT" \
  http://localhost:8000/api/v1/credits/balance

# Submit test job
curl -X POST http://localhost:8000/api/v1/documents/{doc_id}/parse \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{...}'

# Verify credits deducted immediately
curl -H "Authorization: Bearer $JWT" \
  http://localhost:8000/api/v1/credits/transactions
```

---

## Troubleshooting

### Issue: Job Created but Credits Not Deducted

**Symptom:** Job in database, but no deduction transaction

**Diagnosis:**
```sql
SELECT
    id,
    status,
    credits_cost,
    credits_deducted,
    credit_transaction_id
FROM extraction_jobs
WHERE id = 'job-id';
```

**Possible Causes:**
1. Transaction rolled back after job creation (shouldn't happen)
2. Database error during commit

**Resolution:**
- Check API logs for transaction errors
- Manually create deduction transaction if needed

### Issue: Refund Not Applied

**Symptom:** Job failed, but credits not refunded

**Diagnosis:**
```sql
-- Check for refund transaction
SELECT * FROM credit_transactions
WHERE reference_id = 'failed-job-id'
  AND transaction_type = 'refund';

-- Check job metadata for refund errors
SELECT document_metadata->'refund_error'
FROM extraction_jobs
WHERE id = 'failed-job-id';
```

**Resolution:**
```python
# Manual refund via admin endpoint
POST /api/v1/credits/adjust
{
  "amount": 10,
  "reason": "Manual refund for failed job [job-id]"
}
```

### Issue: Cache Desynchronization

**Symptom:** `cached_balance` doesn't match SUM(transactions)

**Diagnosis:**
```sql
SELECT
    t.id,
    t.cached_balance,
    COALESCE(SUM(ct.amount), 0) as actual_balance
FROM tenants t
LEFT JOIN credit_transactions ct ON ct.tenant_id = t.id
WHERE t.id = 'tenant-id'
GROUP BY t.id;
```

**Resolution:**
```python
# Recalculate cache from transaction log
from app.services.credit_service import CreditService

credit_service = CreditService(db)
actual_balance = credit_service.recalculate_cached_balance(tenant_id)
db.commit()

print(f"Balance recalculated: {actual_balance}")
```

---

## Best Practices

### ✅ DO

1. **Always use transactions**
   - Wrap credit operations in database transactions
   - Commit atomically with related operations

2. **Check credits before expensive operations**
   - Deduct credits BEFORE queueing jobs
   - Prevent wasted processing for insufficient credits

3. **Monitor refund rates**
   - High refund rates indicate system issues
   - Set up alerts for abnormal refund patterns

4. **Maintain audit trail**
   - Never delete credit transactions
   - Store full metadata for troubleshooting

5. **Test concurrency**
   - Simulate concurrent job submissions
   - Verify no race conditions or overdrafts

### ❌ DON'T

1. **Don't skip balance checks**
   - Always validate balance before deduction
   - Use `allow_negative=False` (default)

2. **Don't delete transactions**
   - Transactions are immutable audit log
   - Use refunds for corrections

3. **Don't update cached_balance directly**
   - Always use atomic SQL updates
   - Let CreditService manage cache

4. **Don't swallow refund errors**
   - Log all refund failures
   - Alert admins for manual intervention

5. **Don't bypass credit system**
   - All job creations must go through credit check
   - No hardcoded bypasses for "free" jobs

---

## References

- **Architecture:** `docs/architecture/2025-11-05-credit-billing-system.md`
- **API Guide:** `docs/guides/2025-11-05-credit-billing-guide.md`
- **API Implementation:** `app/api/documents.py` (lines 206-319)
- **Service Layer:** `app/services/credit_service.py`
- **Celery Tasks:** `app/tasks/extractor.py`
- **Models:** `app/models/credit_transaction.py`, `app/models/tenant.py`

---

**Last Updated:** 2025-11-05
**Version:** 2.0 (Synchronous Deduction)
**Status:** Production Ready ✅
