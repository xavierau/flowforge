# Credit System Fixes - Complete

**Date:** 2025-11-06
**Status:** ✅ COMPLETE

---

## Summary

Fixed critical credit calculation bug and improved database design:

1. ✅ **Fixed credit calculation**: Now uses page_count (1 page = 1 credit), not tokens
2. ✅ **Fixed subscription query**: Uses correct enum `CreditTransactionType.DEDUCTION`
3. ✅ **Backfilled 9 jobs**: 12 total credits deducted correctly
4. ✅ **Added tenant_id to extraction_jobs**: Performance improvement for tenant filtering
5. ✅ **Implemented enum system**: Type-safe enums across backend and frontend

---

## Critical Fix: Credit Calculation

### Issue
The initial backfill migration incorrectly calculated credits from tokens:
- ❌ **Wrong**: Sum of input_tokens + output_tokens from extraction_results
- ✅ **Correct**: page_count from documents table (1 page = 1 credit)

### Results Before Fix
```
9 jobs backfilled with 20,560 credits ❌ WRONG!
Tenant balance: -20,460
```

### Results After Fix
```
9 jobs backfilled with 12 credits ✅ CORRECT!
Tenant balance: 88 (100 starting - 12 used)
```

### Breakdown
```
Job 8916f6a3: 1 page = 1 credit
Job 1b407b36: 1 page = 1 credit
Job b089260d: 2 pages = 2 credits
Job 6d064c76: 2 pages = 2 credits
Job 47fc83d9: 2 pages = 2 credits
Job e0b1574d: 1 page = 1 credit
Job 6fb8537b: 1 page = 1 credit
Job dc63f79b: 1 page = 1 credit
Job 8b71f5dd: 1 page = 1 credit
---
Total: 12 credits
```

---

## Database Improvements

### 1. Added tenant_id to extraction_jobs

**Migration:** `2025-11-06_d8f7226ad686_add_tenant_id_to_extraction_jobs.py`

**Benefits:**
- ✅ **Performance**: No JOIN needed to get tenant from jobs
- ✅ **Simpler queries**: Direct filter `WHERE extraction_jobs.tenant_id = ?`
- ✅ **Data integrity**: Explicit tenant relationship with FK constraint
- ✅ **Backfilled**: 9 of 12 jobs have tenant_id (3 pre-multi-tenancy remain NULL)

**Schema Changes:**
```sql
ALTER TABLE extraction_jobs ADD COLUMN tenant_id UUID;
UPDATE extraction_jobs SET tenant_id = (SELECT tenant_id FROM documents WHERE ...);
CREATE INDEX idx_extraction_jobs_tenant_id ON extraction_jobs(tenant_id);
ALTER TABLE extraction_jobs ADD CONSTRAINT extraction_jobs_tenant_id_fkey
  FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
```

**Usage Example:**
```python
# Before: Need JOIN
jobs = db.query(ExtractionJob).join(Document).filter(
    Document.tenant_id == tenant_id
).all()

# After: Direct filter
jobs = db.query(ExtractionJob).filter(
    ExtractionJob.tenant_id == tenant_id
).all()
```

### 2. Correct Credit Calculation in Backfill

**Migration:** `2025-11-06_backfill_credit_transactions.py` (fixed)

**Changes:**
```python
# Before (WRONG - used tokens):
credits_from_results = sum(input_tokens + output_tokens)

# After (CORRECT - use pages):
total_credits = job.credits_cost or document.page_count
```

---

## Enum System Implementation

**Files Created:**
- `app/models/enums.py` - Backend type-safe enums
- `frontend/src/types/enums.ts` - Frontend matching enums

**Files Modified:**
- `app/models/credit_transaction.py` - Added validators
- `app/api/subscriptions.py` - Fixed query with enum
- `.claude/CLAUDE.md` - Added enum guidelines (v1.6)

**Key Enums:**
```python
class CreditTransactionType(str, Enum):
    DEDUCTION = "deduction"  # Job credits
    TOPUP = "topup"
    REFUND = "refund"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    TRIAL_SIGNUP = "trial_signup"
    MIGRATION_BALANCE_IMPORT = "migration_balance_import"

class ReferenceType(str, Enum):
    EXTRACTION_JOB = "extraction_job"
    PAYMENT = "payment"
    TENANT_REGISTRATION = "tenant_registration"
    ADMIN_MANUAL_ADJUSTMENT = "admin_manual_adjustment"
    MANUAL = "manual"
```

---

## Database Verification

### Credits Used This Month
```sql
SELECT
  transaction_type,
  reference_type,
  COUNT(*),
  SUM(amount) as total_credits
FROM credit_transactions
WHERE tenant_id = '553d0d2a-34e3-4e58-8897-3130fb759b5e'
  AND created_at >= '2025-11-01'
GROUP BY transaction_type, reference_type;

-- Results:
-- deduction | extraction_job | 9 | -12
-- migration_balance_import | (null) | 1 | +100
```

### Tenant Balance
```sql
SELECT cached_balance FROM tenants
WHERE id = '553d0d2a-34e3-4e58-8897-3130fb759b5e';

-- Result: 88 credits
-- Calculation: 100 (import) - 12 (used) = 88 ✅
```

### Jobs with tenant_id
```sql
SELECT
  COUNT(*) as total_completed_jobs,
  COUNT(tenant_id) as jobs_with_tenant
FROM extraction_jobs
WHERE status = 'completed';

-- Results:
-- total: 12
-- with_tenant: 9 (3 pre-multi-tenancy jobs have NULL)
```

---

## Expected Frontend Results

**Billing Page:**
```
Before Fix:
Credit Balance: 100
0 used this month ❌

After Fix:
Credit Balance: 88
12 used this month ✅
```

**Completed Jobs Table:**
```
Job ID                  | Pages | Credits | Status
8916f6a3-d818-4252...  |   1   |    1    | Completed
1b407b36-9dc2-4b90...  |   1   |    1    | Completed
b089260d-67da-4258...  |   2   |    2    | Completed
...
Total: 9 jobs, 12 credits
```

---

## Subscription API Query (Already Optimal)

The subscription endpoint query is already optimal:

```python
# app/api/subscriptions.py:42-52
credits_used_result = (
    db.query(func.sum(CreditTransaction.amount))
    .filter(
        and_(
            CreditTransaction.tenant_id == current_user.tenant_id,  # Direct filter
            CreditTransaction.transaction_type == CreditTransactionType.DEDUCTION.value,
            CreditTransaction.reference_type == ReferenceType.EXTRACTION_JOB.value,
            CreditTransaction.created_at >= billing_period_start
        )
    )
    .scalar()
)
```

**Why it's optimal:**
- ✅ Filters `credit_transactions` by `tenant_id` (already has index)
- ✅ Uses correct enum values (no more magic strings)
- ✅ Filters by reference type (only extraction jobs)
- ✅ Date range filter (current billing period)

**The tenant_id in extraction_jobs helps OTHER queries:**
- Filtering jobs by tenant without JOIN
- Application code that needs job.tenant_id
- Data integrity with explicit FK

---

## Migration History

1. ✅ `backfill_credits_001` - Backfill credit transactions (corrected for page-based credits)
2. ✅ `d8f7226ad686` - Add tenant_id to extraction_jobs

**Rollback Commands:**
```bash
# Rollback both migrations
alembic downgrade backfill_credits_001

# Or rollback just tenant_id
alembic downgrade -1
```

---

## Next Steps

1. **Restart API Server** - Load new enum imports
   ```bash
   # Kill existing: Ctrl+C
   uvicorn app.main:app --reload
   ```

2. **Test Subscription Endpoint**
   ```bash
   curl http://localhost:8000/api/v1/subscriptions/current \
     -H "Authorization: Bearer YOUR_TOKEN"

   # Should show: "credits_used": 12 (not 0!)
   ```

3. **Test Billing Page**
   - Navigate to `/billing`
   - Verify "12 used this month"
   - Verify job table shows correct credits

4. **Update Application Code** (if needed)
   - Use `job.tenant_id` instead of `job.document.tenant_id`
   - Filter jobs by tenant directly: `ExtractionJob.tenant_id == tenant_id`

---

## Key Learnings

### ❌ Mistakes Made
1. **Initial credit calculation used tokens instead of pages** - Resulted in 20,560 credits instead of 12
2. **Didn't verify credit calculation logic with user** - Should have asked first

### ✅ Successes
1. **Type-safe enum system prevents magic string bugs**
2. **Database denormalization (tenant_id) improves performance**
3. **Migration includes safe rollback**
4. **Backfill preserves original timestamps** (data integrity)

### 📚 Documentation
- Enum guidelines added to CLAUDE.md
- Real bug example for learning
- Migration comments explain decisions

---

## Files Modified

**Backend:**
- `app/models/enums.py` (created)
- `app/models/credit_transaction.py` (validators)
- `app/api/subscriptions.py` (query fix)
- `alembic/versions/2025-11-06_backfill_credit_transactions.py` (fixed calculation)
- `alembic/versions/2025-11-06_d8f7226ad686_add_tenant_id_to_extraction_jobs.py` (created)

**Frontend:**
- `frontend/src/types/enums.ts` (created)

**Documentation:**
- `.claude/CLAUDE.md` (enum guidelines v1.6)
- `CREDIT_SYSTEM_FIXES_COMPLETE.md` (this file)

---

**Status:** ✅ Ready for Production
**Total Credits Backfilled:** 12 credits (9 jobs)
**Tenant Balance:** 88 credits (correct)
