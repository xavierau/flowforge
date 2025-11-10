# Metrics and Billing System - Architecture Diagrams

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                               │
│  ┌───────────────────┐              ┌─────────────────────────┐     │
│  │  Dashboard Page   │              │  Billing Details Page   │     │
│  │                   │              │                         │     │
│  │  ┌─────────────┐  │              │  ┌───────────────────┐ │     │
│  │  │ Stats Cards │  │              │  │  Summary Card     │ │     │
│  │  └─────────────┘  │              │  └───────────────────┘ │     │
│  │  ┌─────────────┐  │              │  ┌───────────────────┐ │     │
│  │  │   Charts    │  │              │  │  Jobs Table       │ │     │
│  │  │  Jobs/Pages │  │              │  │  (Paginated)      │ │     │
│  │  │  Tokens/Pie │  │              │  └───────────────────┘ │     │
│  │  └─────────────┘  │              │                         │     │
│  └───────────────────┘              └─────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS / JWT
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         API LAYER (FastAPI)                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  GET /api/v1/metrics/dashboard                              │   │
│  │  - Query params: start_date, end_date, tenant_id           │   │
│  │  - Auth: JWT Bearer Token                                   │   │
│  │  - Returns: DashboardMetricsResponse                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  GET /api/v1/metrics/jobs/completed                         │   │
│  │  - Query params: page, page_size, sort_by, sort_order      │   │
│  │  - Auth: JWT Bearer Token                                   │   │
│  │  - Returns: CompletedJobsResponse                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ Dependency Injection
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      APPLICATION SERVICES                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   MetricsService                             │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │ get_dashboard_metrics()                               │  │   │
│  │  │  - Resolve tenant (enforce isolation)                 │  │   │
│  │  │  - Build base query with filters                      │  │   │
│  │  │  - Calculate stats                                    │  │   │
│  │  │  - Aggregate time series data                         │  │   │
│  │  │  - Calculate costs (via PricingService)               │  │   │
│  │  │  - Return DashboardMetricsResponse                    │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │ get_completed_jobs()                                  │  │   │
│  │  │  - Resolve tenant (enforce isolation)                 │  │   │
│  │  │  - Build query with pagination                        │  │   │
│  │  │  - Transform to DTOs                                  │  │   │
│  │  │  - Calculate costs (via PricingService)               │  │   │
│  │  │  - Return CompletedJobsResponse                       │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ Uses
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DOMAIN SERVICES                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   PricingService                             │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │ calculate_cost(token_usage, model_provider, model)    │  │   │
│  │  │  - Lookup pricing from PRICING_TABLE                  │  │   │
│  │  │  - Calculate input cost (tokens * rate)               │  │   │
│  │  │  - Calculate output cost (tokens * rate)              │  │   │
│  │  │  - Return CostEstimate                                │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  │                                                              │   │
│  │  PRICING_TABLE:                                              │   │
│  │    google/gemini-2.5-flash: $0.075/$0.30 per 1M tokens     │   │
│  │    openai/gpt-4o: $2.50/$10.00 per 1M tokens               │   │
│  │    deepseek/deepseek-chat: $0.14/$0.28 per 1M tokens       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   Value Objects                              │   │
│  │  DateRange, TokenUsage, CostEstimate, MetricsPeriod         │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ Queries
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DATABASE (PostgreSQL)                         │
│  ┌─────────────────┐   ┌──────────────────┐   ┌─────────────────┐  │
│  │ ExtractionResult│   │ ExtractionJob    │   │    Document     │  │
│  ├─────────────────┤   ├──────────────────┤   ├─────────────────┤  │
│  │ id              │   │ id               │   │ id              │  │
│  │ extraction_job_id◄──┤ document_id      ◄───┤ tenant_id       │  │
│  │ input_tokens    │   │ model_provider   │   │ filename        │  │
│  │ output_tokens   │   │ model_name       │   │ page_count      │  │
│  │ processing_time │   │ status           │   │ created_at      │  │
│  │ created_at      │   │ completed_at     │   │                 │  │
│  └─────────────────┘   └──────────────────┘   └─────────────────┘  │
│                                                                      │
│  Indexes:                                                            │
│  - idx_documents_tenant_id (tenant_id)                              │
│  - idx_extraction_jobs_status (status)                              │
│  - idx_extraction_results_job_id (extraction_job_id)                │
│  - idx_documents_created_at (created_at)                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Dashboard Metrics

```
┌──────────────┐
│  Dashboard   │
│    Page      │
└──────┬───────┘
       │ 1. User loads dashboard
       │
       ▼
┌──────────────────────────────────────────┐
│  metricsService.getDashboardMetrics()    │
│  - Calls: GET /api/v1/metrics/dashboard │
│  - Headers: Authorization: Bearer token │
└──────┬───────────────────────────────────┘
       │ 2. HTTP request
       │
       ▼
┌───────────────────────────────────────────────────┐
│  API Endpoint: /api/v1/metrics/dashboard         │
│  - Extract JWT token                              │
│  - Get current user (auth dependency)             │
│  - Check admin role for cross-tenant access       │
└──────┬────────────────────────────────────────────┘
       │ 3. Call service
       │
       ▼
┌────────────────────────────────────────────────────┐
│  MetricsService.get_dashboard_metrics()           │
│  ┌────────────────────────────────────────────┐   │
│  │ Step 1: Resolve tenant (enforce isolation)│   │
│  └────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────┐   │
│  │ Step 2: Build base query                  │   │
│  │   - Filter by tenant_id                   │   │
│  │   - Filter by date range                  │   │
│  │   - Filter by status = 'completed'        │   │
│  └────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────┐   │
│  │ Step 3: Aggregate stats                   │   │
│  │   - COUNT(DISTINCT jobs)                  │   │
│  │   - COUNT(pages)                          │   │
│  │   - SUM(tokens)                           │   │
│  │   - AVG(processing_time)                  │   │
│  └────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────┐   │
│  │ Step 4: Get time series                   │   │
│  │   - GROUP BY DATE_TRUNC('day', created_at)│   │
│  │   - Order by day                          │   │
│  └────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────┐   │
│  │ Step 5: Calculate costs                   │   │
│  │   - For each result:                      │   │
│  │     * Get token_usage                     │   │
│  │     * Call PricingService.calculate_cost()│   │
│  │     * Aggregate totals                    │   │
│  └────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────┐   │
│  │ Step 6: Build response DTO                │   │
│  │   - DashboardMetricsResponse              │   │
│  └────────────────────────────────────────────┘   │
└──────┬─────────────────────────────────────────────┘
       │ 4. Return response
       │
       ▼
┌──────────────────────┐
│  Dashboard Page      │
│  - Render stats cards│
│  - Render charts     │
│  - Display costs     │
└──────────────────────┘
```

---

## Data Flow: Billing Details

```
┌──────────────┐
│  Billing     │
│  Details     │
│  Page        │
└──────┬───────┘
       │ 1. User navigates to billing page
       │    (page=1, page_size=20)
       │
       ▼
┌─────────────────────────────────────────────┐
│  metricsService.getCompletedJobs()          │
│  - Calls: GET /api/v1/metrics/jobs/completed│
│  - Query: ?page=1&page_size=20              │
└──────┬──────────────────────────────────────┘
       │ 2. HTTP request
       │
       ▼
┌────────────────────────────────────────────────┐
│  API Endpoint: /api/v1/metrics/jobs/completed │
│  - Extract JWT token                           │
│  - Get current user                            │
│  - Validate pagination params                  │
└──────┬─────────────────────────────────────────┘
       │ 3. Call service
       │
       ▼
┌─────────────────────────────────────────────────┐
│  MetricsService.get_completed_jobs()            │
│  ┌──────────────────────────────────────────┐   │
│  │ Step 1: Resolve tenant                  │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │ Step 2: Build query                     │   │
│  │   - Filter by tenant_id                 │   │
│  │   - Filter by date range (if provided)  │   │
│  │   - Filter by status = 'completed'      │   │
│  │   - Apply sorting (completed_at DESC)   │   │
│  │   - Eager load: document, results       │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │ Step 3: Count total items               │   │
│  │   - COUNT(*) for pagination metadata    │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │ Step 4: Apply pagination                │   │
│  │   - OFFSET = (page - 1) * page_size     │   │
│  │   - LIMIT = page_size                   │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │ Step 5: Transform to DTOs               │   │
│  │   - For each job:                       │   │
│  │     * Sum tokens from all results       │   │
│  │     * Calculate cost via PricingService │   │
│  │     * Build CompletedJobItem            │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │ Step 6: Build response                  │   │
│  │   - CompletedJobsResponse               │   │
│  │   - Include pagination metadata         │   │
│  │   - Calculate total cost for page       │   │
│  └──────────────────────────────────────────┘   │
└──────┬──────────────────────────────────────────┘
       │ 4. Return response
       │
       ▼
┌──────────────────────┐
│  Billing Details     │
│  - Render table      │
│  - Show pagination   │
│  - Display total cost│
└──────────────────────┘
```

---

## Multi-Tenant Isolation Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    REQUEST FLOW                             │
└─────────────────────────────────────────────────────────────┘

1. User authenticates and receives JWT
   JWT contains: { sub: user_id, tenant_id: tenant_A }

2. User makes request to /api/v1/metrics/dashboard
   Headers: Authorization: Bearer <JWT>

3. FastAPI extracts token via oauth2_scheme dependency

4. get_current_user() dependency:
   - Verifies JWT signature
   - Decodes payload
   - Queries User from database
   - Returns User object (with tenant_id)

5. API endpoint receives current_user
   - current_user.tenant_id = tenant_A

6. MetricsService.get_dashboard_metrics() called:
   ┌─────────────────────────────────────────────────────────┐
   │  _resolve_tenant_id(                                    │
   │    user_tenant_id = tenant_A,                           │
   │    is_admin = False,                                    │
   │    requested_tenant_id = None                           │
   │  )                                                       │
   │  Returns: tenant_A  ✓                                   │
   └─────────────────────────────────────────────────────────┘

7. Query built with WHERE document.tenant_id = tenant_A

8. Only tenant_A's data returned ✓

┌─────────────────────────────────────────────────────────────┐
│              ADMIN CROSS-TENANT ACCESS                      │
└─────────────────────────────────────────────────────────────┘

1. Admin user (tenant_A) wants to view tenant_B's metrics
   Request: GET /api/v1/metrics/dashboard?tenant_id=tenant_B

2. API endpoint:
   - current_user.tenant_id = tenant_A
   - requested_tenant_id = tenant_B
   - Check if user has admin role

3. MetricsService._resolve_tenant_id():
   ┌─────────────────────────────────────────────────────────┐
   │  if requested_tenant_id:                                │
   │    if not is_admin:                                     │
   │      raise ValueError("Only admins...")  ✗              │
   │    return requested_tenant_id                           │
   └─────────────────────────────────────────────────────────┘

4. Admin check passes, returns tenant_B ✓

5. Query built with WHERE document.tenant_id = tenant_B

6. Admin sees tenant_B's data ✓

┌─────────────────────────────────────────────────────────────┐
│           NON-ADMIN CROSS-TENANT BLOCKED                    │
└─────────────────────────────────────────────────────────────┘

1. Regular user (tenant_A) tries to view tenant_B's metrics
   Request: GET /api/v1/metrics/dashboard?tenant_id=tenant_B

2. MetricsService._resolve_tenant_id():
   ┌─────────────────────────────────────────────────────────┐
   │  if requested_tenant_id:        # tenant_B              │
   │    if not is_admin:             # False                 │
   │      raise ValueError(...)      # BLOCKED ✗             │
   └─────────────────────────────────────────────────────────┘

3. Returns 403 Forbidden ✗

4. User cannot access tenant_B's data ✓
```

---

## Database Query Optimization

```
┌─────────────────────────────────────────────────────────────┐
│                  DASHBOARD METRICS QUERY                    │
└─────────────────────────────────────────────────────────────┘

SELECT
    COUNT(DISTINCT ej.id) as total_jobs,
    COUNT(er.id) as total_pages,
    SUM(er.input_tokens) as total_input_tokens,
    SUM(er.output_tokens) as total_output_tokens,
    AVG(er.processing_time_ms) as avg_processing_time
FROM extraction_results er
JOIN extraction_jobs ej ON er.extraction_job_id = ej.id
JOIN documents d ON ej.document_id = d.id
WHERE
    d.tenant_id = 'tenant_A'           -- Indexed ✓
    AND ej.status = 'completed'        -- Indexed ✓
    AND er.created_at >= '2025-01-01'  -- Indexed ✓
    AND er.created_at <= '2025-01-31'  -- Indexed ✓

┌─────────────────────────────────────────────────────────────┐
│  EXECUTION PLAN (Expected):                                 │
│  1. Index Scan on documents using idx_documents_tenant_id   │
│  2. Nested Loop with extraction_jobs                        │
│  3. Index Scan on extraction_jobs using idx_status          │
│  4. Nested Loop with extraction_results                     │
│  5. Index Scan on extraction_results using idx_created_at   │
│  6. Aggregate                                               │
│                                                             │
│  Estimated Time: < 100ms for 10K jobs                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                TIME SERIES AGGREGATION QUERY                │
└─────────────────────────────────────────────────────────────┘

SELECT
    DATE_TRUNC('day', er.created_at) as day,
    COUNT(DISTINCT ej.id) as jobs_count,
    SUM(er.input_tokens + er.output_tokens) as total_tokens
FROM extraction_results er
JOIN extraction_jobs ej ON er.extraction_job_id = ej.id
JOIN documents d ON ej.document_id = d.id
WHERE
    d.tenant_id = 'tenant_A'
    AND ej.status = 'completed'
    AND er.created_at >= '2025-01-01'
    AND er.created_at <= '2025-01-31'
GROUP BY DATE_TRUNC('day', er.created_at)
ORDER BY day

┌─────────────────────────────────────────────────────────────┐
│  EXECUTION PLAN (Expected):                                 │
│  1. Similar to above with GROUP BY                          │
│  2. Estimated Time: < 150ms for 10K jobs                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                 COMPLETED JOBS LIST QUERY                   │
└─────────────────────────────────────────────────────────────┘

SELECT ej.*, d.filename, d.page_count
FROM extraction_jobs ej
JOIN documents d ON ej.document_id = d.id
WHERE
    d.tenant_id = 'tenant_A'
    AND ej.status = 'completed'
    AND ej.completed_at >= '2025-01-01'
    AND ej.completed_at <= '2025-01-31'
ORDER BY ej.completed_at DESC
LIMIT 20 OFFSET 0

┌─────────────────────────────────────────────────────────────┐
│  EXECUTION PLAN (Expected):                                 │
│  1. Index Scan on documents using idx_documents_tenant_id   │
│  2. Nested Loop with extraction_jobs                        │
│  3. Index Scan on extraction_jobs using idx_status          │
│  4. Sort by completed_at (may use index if available)       │
│  5. Limit                                                   │
│                                                             │
│  Estimated Time: < 50ms for 10K jobs                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Hierarchy: Dashboard Page

```
Dashboard
├── Page
│   ├── PageHeader
│   │   ├── Breadcrumb (Dashboard)
│   │   └── Title + Subtitle
│   └── PageContent
│       ├── StatsGrid (4 columns)
│       │   ├── StatsCard (Completed Jobs)
│       │   ├── StatsCard (Pages Processed)
│       │   ├── StatsCard (Total Tokens)
│       │   └── StatsCard (Avg. Time)
│       ├── ChartsRow1 (2 columns)
│       │   ├── JobsChart (LineChart)
│       │   └── PagesChart (LineChart)
│       ├── ChartsRow2 (2 columns)
│       │   ├── TokensChart (LineChart)
│       │   └── ModelDistributionChart (PieChart)
│       └── CostSummaryCard
│           ├── Input Cost
│           ├── Output Cost
│           └── Total Cost
```

---

## Component Hierarchy: Billing Details Page

```
BillingDetails
├── Page
│   ├── PageHeader
│   │   ├── Breadcrumb (Dashboard > Billing Details)
│   │   └── Title + Subtitle
│   └── PageContent
│       ├── SummaryCard
│       │   ├── Page Total Cost
│       │   └── Total Jobs Count
│       └── CompletedJobsTable
│           ├── Table
│           │   ├── TableHeader (Column names)
│           │   └── TableBody
│           │       └── TableRow (per job)
│           │           ├── Document name
│           │           ├── Page count
│           │           ├── Model info
│           │           ├── Token usage
│           │           ├── Processing time
│           │           ├── Cost
│           │           └── Completed date
│           └── PaginationControls
│               ├── Results info
│               ├── Previous button
│               └── Next button
```

---

## State Management: Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│                    REACT STATE                              │
└─────────────────────────────────────────────────────────────┘

const Dashboard = () => {
  // State
  const [metrics, setMetrics] = useState<DashboardMetricsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Effect: Fetch on mount
  useEffect(() => {
    fetchMetrics()
  }, [])

  // Fetch function
  const fetchMetrics = async () => {
    setLoading(true)
    try {
      const data = await metricsService.getDashboardMetrics()
      setMetrics(data)
    } catch (err) {
      setError('Failed to load metrics')
    } finally {
      setLoading(false)
    }
  }

  // Render states
  if (loading) return <LoadingState />
  if (error) return <ErrorState error={error} />
  if (!metrics) return <EmptyState />

  return (
    <Page>
      {/* Render dashboard with metrics */}
    </Page>
  )
}
```

---

## Cost Calculation Flow

```
┌─────────────────────────────────────────────────────────────┐
│              SINGLE JOB COST CALCULATION                    │
└─────────────────────────────────────────────────────────────┘

Input:
  ExtractionJob:
    - model_provider: "google"
    - model_name: "gemini-2.5-flash"
  ExtractionResults (3 pages):
    - Page 1: input=10000, output=2000
    - Page 2: input=12000, output=2500
    - Page 3: input=11000, output=2200

Step 1: Aggregate tokens
  total_input = 10000 + 12000 + 11000 = 33000
  total_output = 2000 + 2500 + 2200 = 6700

Step 2: Create TokenUsage value object
  token_usage = TokenUsage(
    input_tokens=33000,
    output_tokens=6700
  )

Step 3: Lookup pricing
  PRICING_TABLE["google"]["gemini-2.5-flash"] = {
    "input": 0.075,    # per 1M tokens
    "output": 0.30     # per 1M tokens
  }

Step 4: Calculate cost
  input_millions = 33000 / 1000000 = 0.033
  output_millions = 6700 / 1000000 = 0.0067

  input_cost = 0.033 * 0.075 = 0.002475
  output_cost = 0.0067 * 0.30 = 0.00201
  total_cost = 0.002475 + 0.00201 = 0.004485

Step 5: Return CostEstimate
  CostEstimate(
    input_cost=0.002475,
    output_cost=0.00201,
    total_cost=0.004485,
    currency="USD"
  )

Result: $0.0045 (displayed in UI)
```

---

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    ERROR SCENARIOS                          │
└─────────────────────────────────────────────────────────────┘

1. AUTHENTICATION ERROR
   Request: No Authorization header
   ↓
   oauth2_scheme → 401 Unauthorized
   ↓
   Frontend: Redirect to /login

2. INVALID TOKEN ERROR
   Request: Malformed or expired JWT
   ↓
   get_current_user() → InvalidTokenError → 401
   ↓
   Frontend: Clear token, redirect to /login

3. INSUFFICIENT PERMISSIONS ERROR
   Request: Non-admin tries to access other tenant
   ↓
   _resolve_tenant_id() → ValueError → 403 Forbidden
   ↓
   Frontend: Show error alert

4. VALIDATION ERROR
   Request: Invalid query parameters (e.g., page=0)
   ↓
   FastAPI validation → 422 Unprocessable Entity
   ↓
   Frontend: Show validation error message

5. DATABASE ERROR
   Query fails (connection lost, timeout)
   ↓
   SQLAlchemy exception → 500 Internal Server Error
   ↓
   Frontend: Show generic error message
   Backend: Log error with stack trace

6. EMPTY DATA
   No completed jobs found for tenant
   ↓
   Service returns empty arrays
   ↓
   Frontend: Show "No data" message (not an error)
```

---

These diagrams provide a visual representation of the metrics and billing system architecture, data flows, and component hierarchies. Use them as reference during implementation and when explaining the system to stakeholders.

