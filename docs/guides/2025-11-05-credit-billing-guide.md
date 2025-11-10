# Credit Billing System - Implementation Guide

**Date:** 2025-11-05
**Version:** 1.0
**Status:** Production Ready

## Quick Start

### 1. Check Credit Balance

```bash
curl -H "Authorization: Bearer $JWT_TOKEN" \
  http://localhost:8000/api/v1/credits/balance
```

**Response:**
```json
{
  "tenant_id": "uuid",
  "balance": 150,
  "updated_at": "2025-11-05T10:30:00Z"
}
```

### 2. Top Up Credits

```bash
curl -X POST \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "credits": 100,
    "amount_usd": 10.00,
    "payment_intent_id": "pi_123456789"
  }' \
  http://localhost:8000/api/v1/credits/topup
```

### 3. Submit Extraction (Credits Checked Automatically)

```bash
curl -X POST \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "extraction_schema": {...},
    "model_provider_config": {
      "provider": "google",
      "model": "gemini-2.5-flash"
    },
    "processing_mode": "batch"
  }' \
  http://localhost:8000/api/v1/documents/{document_id}/parse
```

**Success (202 Accepted):**
```json
{
  "extraction_job_id": "uuid",
  "status": "queued",
  "estimated_time_seconds": 20
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

## API Reference

### GET /api/v1/credits/balance

Get current credit balance for authenticated tenant.

**Authentication:** JWT-only (no API tokens)
**Permission:** None (self-service)

**Response:**
```json
{
  "tenant_id": "uuid",
  "balance": 250,
  "updated_at": "2025-11-05T..."
}
```

---

### GET /api/v1/credits/transactions

Get paginated transaction history.

**Authentication:** JWT-only
**Permission:** None (self-service)

**Query Parameters:**
- `transaction_type` (optional): Filter by type (topup, deduction, refund, admin_adjustment)
- `limit` (default: 50, max: 100): Results per page
- `offset` (default: 0): Pagination offset

**Response:**
```json
{
  "transactions": [
    {
      "id": "uuid",
      "transaction_type": "deduction",
      "amount": -5,
      "reference_type": "extraction_job",
      "reference_id": "uuid",
      "description": "Document extraction - 5 page(s)",
      "created_at": "2025-11-05T...",
      "metadata": {
        "job_id": "uuid",
        "document_id": "uuid",
        "page_count": 5
      }
    }
  ],
  "total": 45,
  "limit": 50,
  "offset": 0
}
```

---

### POST /api/v1/credits/topup

Purchase credits (integrates with Stripe).

**Authentication:** JWT-only
**Permission:** `tenant:billing`

**Request Body:**
```json
{
  "credits": 100,
  "amount_usd": 10.00,
  "payment_intent_id": "pi_123456789"
}
```

**Response (201 Created):**
```json
{
  "transaction_id": "uuid",
  "credits_added": 100,
  "new_balance": 150,
  "created_at": "2025-11-05T..."
}
```

**Validation:**
- `credits`: 1-100,000
- `amount_usd`: > 0
- `payment_intent_id`: Optional (for Stripe integration)

---

### POST /api/v1/credits/adjust

Manually adjust credits (admin operation).

**Authentication:** JWT-only
**Permission:** `tenant:manage`

**Request Body:**
```json
{
  "amount": 50,
  "reason": "Promotional credit bonus for new customer"
}
```

**Validation:**
- `amount`: Non-zero, ±100,000 max
  - Positive: Add credits
  - Negative: Deduct credits
- `reason`: 10-500 characters

**Response (201 Created):**
```json
{
  "id": "uuid",
  "transaction_type": "admin_adjustment",
  "amount": 50,
  "description": "Promotional credit bonus...",
  "created_at": "2025-11-05T..."
}
```

## Developer Guide

### Adding Credits Programmatically

```python
from app.services.credit_service import CreditService
from app.database import SessionLocal

db = SessionLocal()
credit_service = CreditService(db)

# Add credits (top-up)
transaction = credit_service.add_credits(
    tenant_id=tenant.id,
    amount=100,
    transaction_type="topup",
    description="Credit purchase - 100 credits",
    stripe_payment_intent_id="pi_123456789",
    metadata={"package": "starter", "amount_usd": "10.00"}
)
db.commit()
```

### Checking Balance

```python
balance = credit_service.calculate_balance(tenant_id)
has_sufficient, current_balance = credit_service.check_sufficient_credits(
    tenant_id=tenant.id,
    required_credits=10
)
```

### Deducting Credits

```python
# Deduct credits with idempotency
transaction = credit_service.finalize_job_credits(
    job_id=job.id,
    tenant_id=tenant.id,
    actual_credits_used=5,
    user_id=user.id  # Optional
)

if transaction:
    print(f"Deducted {transaction.amount} credits")
else:
    print("Credits already deducted (idempotent)")
```

### Transaction History

```python
transactions, total = credit_service.get_transaction_history(
    tenant_id=tenant.id,
    limit=50,
    offset=0,
    transaction_type="deduction"  # Optional filter
)

for tx in transactions:
    print(f"{tx.created_at}: {tx.amount} - {tx.description}")
```

## Integration Patterns

### Pattern 1: Pre-Flight Credit Check

Check credits BEFORE expensive operations:

```python
# In API endpoint
required_credits = calculate_cost(document.page_count)

has_sufficient, balance = credit_service.check_sufficient_credits(
    tenant_id=current_user.tenant_id,
    required_credits=required_credits
)

if not has_sufficient:
    raise HTTPException(
        status_code=402,
        detail={
            "error": "insufficient_credits",
            "required_credits": required_credits,
            "available_credits": balance
        }
    )

# Proceed with operation...
```

### Pattern 2: Reserve & Finalize

Reserve credits upfront, deduct after completion:

```python
# 1. Reserve (API layer)
success, error = credit_service.reserve_credits_for_job(
    tenant_id=tenant.id,
    job_id=job.id,
    required_credits=10
)

# 2. Finalize (Celery task after completion)
credit_service.finalize_job_credits(
    job_id=job.id,
    tenant_id=tenant.id,
    actual_credits_used=10
)
```

### Pattern 3: Pessimistic Locking

Prevent race conditions with concurrent submissions:

```python
# Lock tenant row
tenant = (
    db.query(Tenant)
    .filter(Tenant.id == tenant_id)
    .with_for_update()  # Pessimistic lock
    .first()
)

# Check balance while locked
has_sufficient, balance = credit_service.check_sufficient_credits(
    tenant_id, required_credits
)

# Create job and commit (releases lock)
```

## Error Handling

### HTTP 402 Payment Required

```json
{
  "detail": {
    "error": "insufficient_credits",
    "message": "Insufficient credits...",
    "required_credits": 10,
    "available_credits": 5,
    "credits_needed": 5
  }
}
```

**Client Action:** Prompt user to purchase more credits

### HTTP 400 Bad Request

```json
{
  "detail": "Credit amount must be positive"
}
```

**Validation Errors:**
- Negative credit amounts
- Invalid transaction types
- Amount exceeds limits (100,000)

### HTTP 500 Internal Server Error

```json
{
  "detail": "Failed to add credits: Database error"
}
```

**Server Action:** Check logs, retry operation, contact admin

## Monitoring & Alerts

### Key Metrics

1. **Balance Distribution**
   ```sql
   SELECT
     CASE
       WHEN balance < 10 THEN 'critical'
       WHEN balance < 50 THEN 'low'
       ELSE 'healthy'
     END as status,
     COUNT(*) as tenant_count
   FROM (
     SELECT tenant_id, SUM(amount) as balance
     FROM credit_transactions
     GROUP BY tenant_id
   ) balances
   GROUP BY status;
   ```

2. **Top-Up Conversion Rate**
   ```sql
   SELECT
     DATE(created_at) as date,
     COUNT(*) as topups,
     SUM(amount) as total_credits
   FROM credit_transactions
   WHERE transaction_type = 'topup'
   GROUP BY DATE(created_at);
   ```

3. **Average Credit Consumption**
   ```sql
   SELECT
     AVG(ABS(amount)) as avg_credits_per_job
   FROM credit_transactions
   WHERE transaction_type = 'deduction'
   AND created_at > NOW() - INTERVAL '30 days';
   ```

### Alert Thresholds

- **Low Balance Warning:** < 10 credits
- **Negative Balance Alert:** balance < 0 (review needed)
- **High Deduction Rate:** > 100 credits/hour
- **Failed Deductions:** credit_deduction_error in job metadata

## Troubleshooting

### Issue: Balance Mismatch

**Symptom:** Reported balance doesn't match expected value

**Debug:**
```sql
-- Recalculate balance
SELECT tenant_id, SUM(amount) as calculated_balance
FROM credit_transactions
WHERE tenant_id = 'xxx'
GROUP BY tenant_id;

-- Audit transaction log
SELECT * FROM credit_transactions
WHERE tenant_id = 'xxx'
ORDER BY created_at DESC
LIMIT 50;
```

---

### Issue: Credits Not Deducted

**Symptom:** Job completed but credits not deducted

**Debug:**
```sql
-- Check job deduction status
SELECT id, status, credits_cost, credits_deducted, credit_transaction_id
FROM extraction_jobs
WHERE id = 'xxx';

-- Check for deduction errors
SELECT document_metadata->'credit_deduction_error'
FROM extraction_jobs
WHERE id = 'xxx';
```

**Fix:** Manually create deduction transaction

---

### Issue: Duplicate Deductions

**Symptom:** Credits deducted multiple times for same job

**Prevention:** `credits_deducted` flag ensures idempotency

**Debug:**
```sql
-- Find jobs with multiple deductions
SELECT reference_id, COUNT(*) as deduction_count
FROM credit_transactions
WHERE transaction_type = 'deduction'
AND reference_type = 'extraction_job'
GROUP BY reference_id
HAVING COUNT(*) > 1;
```

---

### Issue: Race Condition

**Symptom:** Multiple jobs submitted simultaneously, balance overdrawn

**Expected:** Pessimistic locking prevents this

**Debug:**
```sql
-- Check concurrent job submissions
SELECT tenant_id, created_at, COUNT(*) as concurrent_jobs
FROM extraction_jobs
WHERE created_at > NOW() - INTERVAL '1 minute'
GROUP BY tenant_id, created_at
HAVING COUNT(*) > 1;
```

## Best Practices

✅ **DO:**
- Always check credits BEFORE queuing expensive operations
- Use pessimistic locking for concurrent submissions
- Log credit operations with descriptive messages
- Monitor balance distribution across tenants
- Set up alerts for low/negative balances

❌ **DON'T:**
- Store balance in a column (use event sourcing)
- Update/delete credit transactions (append-only log)
- Skip idempotency checks (prevents double-charging)
- Allow API tokens to access credit operations (JWT-only)
- Fail jobs if credit deduction fails (log for review)

## References

- Architecture: `docs/architecture/2025-11-05-credit-billing-system.md`
- API Implementation: `app/api/credits.py`
- Service Layer: `app/services/credit_service.py`
- Models: `app/models/credit_transaction.py`
- Integration: `app/api/documents.py`, `app/tasks/extractor.py`

---

**Last Updated:** 2025-11-05
**Version:** 1.0
**Status:** Production Ready
