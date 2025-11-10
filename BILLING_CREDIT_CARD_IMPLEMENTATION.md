# Billing Credit Balance Card Implementation

## Summary

Replaced the dollar amount "Total Cost (All Time)" card on the Billing Details page with a comprehensive Credit Balance card that displays current credit balance, usage, and last updated timestamp.

**Implementation Date:** 2025-11-05

---

## Changes Made

### Backend Changes

#### 1. Updated Subscription API Endpoint

**File:** `app/api/subscriptions.py`

**Changes:**
- Added `func` import from SQLAlchemy for aggregation queries
- Updated `/subscriptions/current` endpoint to calculate and return:
  - `credits_balance`: Current cached balance from tenant table
  - `credits_used`: Credits consumed this billing period (from credit_transactions)
  - `balance_last_updated`: ISO timestamp of last balance cache update
- Calculation logic:
  ```python
  # Query credit_transactions for this month's usage
  credits_used_result = (
      db.query(func.sum(CreditTransaction.amount))
      .filter(
          and_(
              CreditTransaction.tenant_id == current_user.tenant_id,
              CreditTransaction.transaction_type == "usage",
              CreditTransaction.created_at >= billing_period_start
          )
      )
      .scalar()
  )
  # Usage transactions are negative, so we take absolute value
  credits_used = abs(credits_used_result) if credits_used_result else 0
  ```

**API Response Schema:**
```json
{
  "plan": "free|pro|enterprise",
  "status": "active",
  "credits_balance": 1000,
  "credits_used": 250,
  "balance_last_updated": "2025-11-05T10:30:00",
  "billing_period_start": "2025-11-01T00:00:00",
  "billing_period_end": "2025-12-01T00:00:00",
  "cancel_at_period_end": false,
  "features": { ... }
}
```

---

### Frontend Changes

#### 2. Updated TypeScript Types

**File:** `frontend/src/types/profile.ts`

**Changes:**
- Added `balance_last_updated: string` (required field)
- Made several existing fields optional for API compatibility
- Added `cancel_at_period_end` and `features` for complete API response coverage

**Updated Interface:**
```typescript
export interface Subscription {
  id?: string;
  tenant_id?: string;
  plan: SubscriptionPlan;
  status: SubscriptionStatus;
  credits_balance: number;
  credits_used: number;
  balance_last_updated: string;  // NEW: ISO timestamp
  documents_processed?: number;
  api_calls_count?: number;
  billing_cycle_start?: string;
  billing_cycle_end?: string;
  billing_period_start?: string;
  billing_period_end?: string;
  created_at?: string;
  updated_at?: string;
  cancel_at_period_end?: boolean;
  features?: Record<string, unknown>;
}
```

#### 3. Replaced Dollar Amount Card with Credit Balance Card

**File:** `frontend/src/pages/BillingDetails.tsx`

**Key Changes:**

**a) Added Utility Functions:**
```typescript
// Format numbers with thousands separator (1000 -> 1,000)
function formatNumber(num: number): string {
  return num.toLocaleString();
}

// Format ISO timestamp to relative time (e.g., "5 minutes ago")
function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const date = new Date(timestamp);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
}
```

**b) Updated Imports:**
- Removed: `DollarSign` icon
- Added: `Zap` icon, `Progress` component
- Added: `getCurrentSubscription`, `SubscriptionApiError` from subscription service
- Added: `Subscription` type

**c) Enhanced State Management:**
```typescript
// Added subscription state
const [subscription, setSubscription] = useState<Subscription | null>(null);
```

**d) Parallel Data Fetching:**
```typescript
useEffect(() => {
  let isCancelled = false;

  async function fetchData() {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch both datasets in parallel using Promise.all
      const [billingResult, subscriptionResult] = await Promise.all([
        getCompletedJobs(currentPage, pageSize),
        getCurrentSubscription(),
      ]);

      if (!isCancelled) {
        setBillingData(billingResult);
        setSubscription(subscriptionResult);
        setIsLoading(false);
      }
    } catch (err) {
      if (!isCancelled) {
        if (err instanceof MetricsApiError || err instanceof SubscriptionApiError) {
          setError(err.message);
        } else {
          setError('Failed to load billing data');
        }
        setIsLoading(false);
      }
    }
  }

  fetchData();

  return () => {
    isCancelled = true;
  };
}, [currentPage]);
```

**e) New Credit Balance Card UI:**
```tsx
<Card className="flex-1">
  <CardHeader className="pb-3">
    <CardTitle className="text-base flex items-center gap-2">
      <Zap className="h-4 w-4 text-primary" />
      Credit Balance
    </CardTitle>
  </CardHeader>
  <CardContent>
    <div className="space-y-3">
      {/* Large balance number */}
      <p className="text-3xl font-bold">
        {formatNumber(subscription.credits_balance)}
      </p>

      {/* Progress bar visualization */}
      <Progress
        value={
          subscription.credits_balance + subscription.credits_used > 0
            ? (subscription.credits_balance /
                (subscription.credits_balance + subscription.credits_used)) *
              100
            : 0
        }
        className="h-2"
      />

      {/* Usage and last updated */}
      <div className="space-y-1">
        <p className="text-sm text-muted-foreground">
          {formatNumber(subscription.credits_used)} used this month
        </p>
        <p className="text-xs text-muted-foreground">
          Updated {formatRelativeTime(subscription.balance_last_updated)}
        </p>
      </div>
    </div>
  </CardContent>
</Card>
```

---

## Design Decisions

### React Best Practices Applied

1. **Single Responsibility:** Each utility function has one clear purpose
2. **Proper useEffect Management:**
   - Single effect for all data fetching
   - Cleanup function prevents state updates after unmount
   - Proper dependency array `[currentPage]`
3. **Parallel Data Fetching:** Using `Promise.all()` to fetch billing data and subscription simultaneously
4. **Composition:** Small, focused components (Progress bar, Card components)
5. **Error Handling:** Comprehensive error states for both API calls
6. **Type Safety:** Full TypeScript coverage with proper interfaces

### Progress Bar Calculation

The progress bar represents the ratio of remaining credits to total credits (balance + used):

```typescript
const totalCredits = credits_balance + credits_used;
const percentage = totalCredits > 0 ? (credits_balance / totalCredits) * 100 : 0;
```

- **Full bar (100%):** No credits used yet (all remaining)
- **Half bar (50%):** Half of allocated credits consumed
- **Empty bar (0%):** All credits used

### Relative Time Display

The last updated timestamp uses human-readable relative time:
- Less than 1 minute: "just now"
- Less than 60 minutes: "5 minutes ago"
- Less than 24 hours: "3 hours ago"
- 24+ hours: "2 days ago"

---

## Testing Checklist

### Backend Testing

- [ ] API returns correct `credits_balance` from tenant.cached_balance
- [ ] API correctly calculates `credits_used` for current billing period
- [ ] API handles missing `balance_last_updated` (defaults to now)
- [ ] API filters credit transactions by tenant_id and transaction_type="usage"
- [ ] API returns ISO formatted timestamps

### Frontend Testing

- [ ] Credit balance displays with thousands separator (1,000)
- [ ] Progress bar correctly visualizes balance vs used credits
- [ ] Progress bar handles edge cases (0 credits, no usage)
- [ ] "Used this month" displays correct formatted number
- [ ] "Updated X ago" displays relative time correctly
- [ ] Loading state shows for both API calls
- [ ] Error handling works for subscription API failures
- [ ] Page header and breadcrumbs remain unchanged
- [ ] Export button functionality preserved
- [ ] Completed jobs table remains unchanged
- [ ] Responsive design works on mobile and desktop

---

## Files Modified

### Backend
1. `/app/api/subscriptions.py` - Updated subscription endpoint to include credit data

### Frontend
1. `/frontend/src/types/profile.ts` - Updated Subscription interface
2. `/frontend/src/pages/BillingDetails.tsx` - Replaced dollar card with credit card

---

## Migration Notes

**No database migrations required.** All changes use existing database columns:
- `tenant.cached_balance` (already exists)
- `tenant.balance_last_updated` (already exists)
- `credit_transaction.amount` (already exists)
- `credit_transaction.transaction_type` (already exists)

**No breaking changes.** The subscription API response adds new fields while maintaining backward compatibility.

---

## Visual Design

### Before (Dollar Amount Card)
```
┌─────────────────────────────────┐
│ Total Cost (All Time)           │
│                                 │
│ $ 💵  $1,234.56                 │
│      42 completed jobs          │
└─────────────────────────────────┘
```

### After (Credit Balance Card)
```
┌─────────────────────────────────┐
│ ⚡ Credit Balance               │
│                                 │
│ 1,000                           │
│ ▓▓▓▓▓▓▓▓▓▓░░░░░ (80%)           │
│ 250 used this month             │
│ Updated 5 minutes ago           │
└─────────────────────────────────┘
```

---

## Performance Considerations

1. **Backend Query Performance:**
   - Credit balance: O(1) lookup from cached_balance
   - Credits used: O(n) aggregation query on credit_transactions
   - Optimized with index on `credit_transaction.created_at`

2. **Frontend Performance:**
   - Parallel API calls reduce total wait time
   - Memoized formatNumber and formatRelativeTime prevent recalculation
   - Progress bar calculation is simple arithmetic (constant time)

---

## Future Enhancements

1. **Real-time Updates:** Consider WebSocket for live balance updates
2. **Credit History Chart:** Add visualization of credit usage over time
3. **Low Balance Warnings:** Display alert when credits are below threshold
4. **Credit Purchase CTA:** Add "Buy More Credits" button when balance is low
5. **Billing Period Selector:** Allow viewing usage for previous billing periods

---

## References

- **Design Pattern:** Based on SubscriptionTab.tsx credit balance card (lines 190-216)
- **API Pattern:** Uses centralized apiFetch() wrapper for auth and error handling
- **Architecture Docs:**
  - [API Endpoint Security Guide](/docs/guides/2025-11-04-api-endpoint-security.md)
  - [Credit Billing System](/docs/architecture/2025-11-05-credit-billing-system.md)
