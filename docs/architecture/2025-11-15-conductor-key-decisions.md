# Conductor Integration - Key Technical Decisions

**Date:** 2025-11-15
**Status:** Design Specification
**Version:** 1.0

## Overview

This document summarizes critical technical decisions made for the Netflix Conductor integration into the AI Document Processing platform. Each decision includes rationale, alternatives considered, and implementation notes.

---

## Decision 1: Use Netflix Conductor (vs Custom Orchestration)

### Decision
Use Netflix Conductor as the workflow orchestration engine instead of building a custom solution.

### Rationale
- **Production-grade:** Battle-tested at Netflix scale
- **Feature-complete:** Built-in retry, error handling, monitoring
- **Language-agnostic:** Workers in any language
- **Scalability:** Designed for high-throughput distributed systems
- **Active development:** Strong community and enterprise support

### Alternatives Considered

| Alternative | Pros | Cons | Verdict |
|------------|------|------|---------|
| **Apache Airflow** | Popular, Python-native | Batch-oriented, not real-time | Rejected - not designed for event-driven workflows |
| **Temporal** | Modern, good developer experience | Newer, smaller ecosystem | Rejected - less mature than Conductor |
| **Custom (Celery-based)** | Full control, no new dependency | High development cost, reinventing wheel | Rejected - too much effort |
| **Step Functions (AWS)** | Fully managed | Vendor lock-in, cost | Rejected - platform-agnostic requirement |

### Implementation Notes
- Deploy Conductor server as Docker container
- Use official Python SDK (`conductor-python`)
- Separate Conductor DB from application DB (isolation)

---

## Decision 2: Backend Expression Resolution (vs Frontend)

### Decision
Resolve workflow expressions (`{{$("Node").data.field}}`) on the backend during task execution, not in the frontend.

### Rationale
- **Security:** Prevent expression injection attacks
- **Data access:** Backend has access to task execution context
- **Consistency:** Single source of truth for data
- **Flexibility:** Can use actual runtime data, not just static config

### How It Works
1. Frontend saves expressions as-is in workflow JSON: `{{$("extract_1").data.total}}`
2. Translator converts to Conductor format: `${extract_1.output.result.total}`
3. Workers resolve at runtime using `ExpressionResolver` service
4. Conductor engine handles `${...}` expressions natively

### Security Benefits
- Frontend cannot inject malicious code
- Tenant isolation enforced at execution time
- Expression evaluation in sandboxed environment

---

## Decision 3: Docker Sandbox for Python Execution

### Decision
Execute user-provided Python code in isolated Docker containers with strict resource limits and security constraints.

### Rationale
- **Security:** Full isolation from host system
- **Resource control:** CPU, memory, timeout limits
- **Network isolation:** No internet access by default
- **Reproducibility:** Consistent Python environment

### Security Measures

| Measure | Configuration | Purpose |
|---------|--------------|---------|
| Network isolation | `network_mode='none'` | Prevent network access |
| Read-only FS | `read_only=True` | Prevent file modifications |
| No privileges | `no-new-privileges` | Prevent escalation |
| Drop capabilities | `cap_drop=['ALL']` | Minimal permissions |
| Resource limits | CPU: 0.5 cores, Memory: 128MB | Prevent DoS |
| Timeout | 30 seconds default | Prevent infinite loops |

### Alternatives Considered

| Alternative | Pros | Cons | Verdict |
|------------|------|------|---------|
| **RestrictedPython** | No container overhead | Can be bypassed, limited isolation | Rejected - insufficient security |
| **PyPy sandbox** | Lightweight | Deprecated, not maintained | Rejected - unmaintained |
| **WebAssembly (Pyodide)** | Browser-based, safe | Limited Python library support | Future consideration |
| **AWS Lambda** | Fully managed | Vendor lock-in, cold start latency | Rejected - cost and latency |

### Performance Considerations
- Container lifecycle: ~500ms overhead per execution
- Image caching: Use pre-pulled Python image
- Container reuse: Not implemented (security over performance)

---

## Decision 4: SIMPLE Task Type (vs HTTP Task)

### Decision
Use Conductor's `SIMPLE` task type for all custom workers instead of `HTTP` task type.

### Rationale
- **Flexibility:** Full control over task execution logic
- **Database access:** Workers can access PostgreSQL directly
- **Service integration:** Easy to call existing VLLM, Storage services
- **Error handling:** Custom retry logic per task type
- **Tenant isolation:** Enforce tenant checks in worker code

### When to Use Each

| Task Type | Use Case | Example |
|-----------|----------|---------|
| `SIMPLE` | Custom business logic, DB access | Extraction worker, Python worker |
| `HTTP` | External API calls (generic) | Simple HTTP requests (future) |
| `SWITCH` | Conditional branching | If node evaluation |
| `SUB_WORKFLOW` | Reusable workflows | Complex multi-step processes |

### Worker Pattern
```python
class ExtractionWorker(WorkerInterface):
    def get_task_def_name(self) -> str:
        return "extraction_task"

    def execute(self, task: Task) -> TaskResult:
        # Custom logic with DB access
        db = SessionLocal()
        # ... execute node logic ...
        db.close()
        return task_result
```

---

## Decision 5: Two Execution Modes

### Decision
Support both full workflow execution and isolated node testing as separate execution modes.

### Rationale
- **Development workflow:** Test nodes before building full workflow
- **Debugging:** Isolate node issues quickly
- **Performance:** Faster feedback for node development
- **User experience:** Better developer experience in UI

### Implementation

| Mode | API Endpoint | Workflow Registration | Input Source | Use Case |
|------|--------------|----------------------|--------------|----------|
| **Full Execution** | `POST /workflows/{id}/execute` | Registered | Workflow definition | Production execution |
| **Node Testing** | `POST /workflows/test-node` | Dynamic (temp) | Mock data | Development, debugging |

### Node Testing Flow
```
Frontend (test node button)
  → POST /workflows/test-node
  → Create dynamic workflow (single task)
  → Execute with mock input
  → Return task output
  → No workflow registration
```

---

## Decision 6: Conductor Server Deployment

### Decision
Deploy Conductor server as separate Docker container, not embedded in FastAPI application.

### Rationale
- **Separation of concerns:** Orchestration engine separate from API
- **Scalability:** Scale Conductor independently
- **Upgrades:** Update Conductor without app deployment
- **Reliability:** Conductor failures don't crash API

### Architecture
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│  Conductor  │────▶│   Workers   │
│     API     │     │   Server    │     │  (polling)  │
└─────────────┘     └─────────────┘     └─────────────┘
      │                     │
      ▼                     ▼
┌─────────────┐     ┌─────────────┐
│  App DB     │     │ Conductor DB│
│ (Postgres)  │     │ (Postgres)  │
└─────────────┘     └─────────────┘
```

### Deployment Options

| Environment | Deployment Method | Notes |
|-------------|------------------|-------|
| **Development** | Docker Compose | Single-node, local |
| **Staging** | Docker Compose | Same as dev |
| **Production** | Kubernetes | HA deployment, multi-node |

---

## Decision 7: Expression Syntax Preservation

### Decision
Preserve frontend expression syntax (`{{$("Node").data.field}}`) in workflow JSON, translate to Conductor format during workflow registration.

### Rationale
- **Frontend consistency:** Same syntax across UI
- **No translation overhead:** Only translate once (registration time)
- **Debuggability:** Easier to trace expressions in UI
- **Flexibility:** Can change backend implementation without frontend changes

### Translation Strategy

```
Frontend Expression:
  {{$('extract_1').data.total}}

Translator converts to Conductor Expression:
  ${extract_1.output.result.total}

Conductor resolves at runtime:
  1500 (actual value from task output)
```

### Expression Resolver Service
- Handles frontend expressions in node config
- Uses JSONPath for nested field access
- Supports condition evaluation (for If nodes)
- Safe evaluation (no code execution)

---

## Decision 8: Worker Registration Strategy

### Decision
Register workers as persistent processes that poll Conductor for tasks, not as ephemeral Lambda-style functions.

### Rationale
- **Performance:** No cold start latency
- **Database connections:** Persistent connection pooling
- **Conductor recommendation:** Official pattern from Netflix
- **Resource efficiency:** Reuse worker processes

### Worker Lifecycle
```
Application Startup
  → Start WorkerManager
  → Initialize workers (Extraction, Python, HTTP, Condition)
  → Start TaskHandler (begins polling)
  → Workers poll Conductor every 1s
  → Execute tasks as they arrive
  → Report results back to Conductor
```

### Scaling Strategy
- **Development:** Single worker process
- **Production:** Multiple worker processes (horizontal scaling)
- **Auto-scaling:** Scale based on task queue depth

---

## Decision 9: Error Handling Hierarchy

### Decision
Implement three-level error handling: task-level, workflow-level, and application-level.

### Rationale
- **Granular control:** Different retry strategies per error type
- **User experience:** Clear error messages at each level
- **Debugging:** Easy to identify failure point
- **Reliability:** Automatic recovery where appropriate

### Error Handling Levels

| Level | Scope | Retry Strategy | Example |
|-------|-------|---------------|---------|
| **Task-level** | Single task execution | Exponential backoff (3 retries) | VLLM API timeout |
| **Workflow-level** | Entire workflow | No retry, mark as FAILED | Invalid workflow definition |
| **Application-level** | System errors | Alert operator | Database connection lost |

### Retry Configuration
```python
{
    "name": "extraction_task",
    "retryCount": 3,
    "retryLogic": "EXPONENTIAL_BACKOFF",
    "retryDelaySeconds": 5,
    "backoffScaleFactor": 2,
    "timeoutSeconds": 300
}
```

---

## Decision 10: Tenant Isolation Enforcement

### Decision
Inject `tenantId` into all workflow inputs and validate tenant access in every worker execution.

### Rationale
- **Security:** Prevent cross-tenant data access
- **Compliance:** Support multi-tenant SaaS requirements
- **Auditability:** Track execution by tenant
- **Resource limits:** Enforce tenant-level quotas

### Implementation Pattern

**Workflow Execution:**
```python
workflow_input = {
    **user_provided_input,
    'tenantId': str(current_user.tenant_id),  # Injected by API
    'userId': str(current_user.id)
}
```

**Worker Validation:**
```python
def execute_node(self, input_data: dict, db, tenant_id: str):
    # ALWAYS filter by tenant
    schema = db.query(Schema).filter(
        Schema.id == schema_id,
        Schema.tenant_id == tenant_id  # CRITICAL
    ).first()

    if not schema:
        raise ValueError("Resource not found or access denied")
```

### Security Audit
- [ ] All workers validate tenant ID
- [ ] All DB queries include tenant filter
- [ ] Workflow input sanitization
- [ ] No tenant ID in URLs (only in request body)

---

## Decision 11: Expression Resolution Timing

### Decision
Resolve expressions at task execution time (runtime), not at workflow registration time (design time).

### Rationale
- **Dynamic data:** Access actual task outputs, not static config
- **Conditional logic:** Evaluate based on runtime state
- **Error handling:** Graceful handling of missing data
- **Flexibility:** Same workflow with different input data

### Resolution Flow

```
Workflow Registration (Design Time):
  - Store expressions as-is: {{$('extract_1').data.total}}
  - No resolution

Workflow Execution (Runtime):
  - Task 1 executes → produces output: {total: 1500}
  - Task 2 input has expression: {{$('extract_1').data.total}}
  - Worker resolves at execution time: 1500
  - Task 2 executes with resolved value
```

### Benefits
- Can reuse workflows with different data
- Expressions always use latest data
- No stale data issues

---

## Decision 12: Monitoring & Observability

### Decision
Use Conductor's built-in monitoring plus custom application metrics.

### Rationale
- **Conductor UI:** View workflow executions, task details
- **Custom metrics:** Track business-specific metrics
- **Prometheus:** Standard metrics format
- **Distributed tracing:** Correlate across services

### Metrics Strategy

| Metric Type | Source | Purpose |
|-------------|--------|---------|
| **Workflow metrics** | Conductor UI | Execution status, duration |
| **Worker metrics** | Prometheus | Task execution time, errors |
| **Business metrics** | Application | Credits used, documents processed |
| **Infrastructure** | Docker, K8s | Container resource usage |

### Key Metrics
- `workflow_executions_total{tenant_id, workflow_name, status}`
- `task_execution_duration_seconds{task_type}`
- `docker_container_memory_bytes`
- `expression_resolution_time_seconds`

---

## Summary of Key Decisions

1. **Orchestration Engine:** Netflix Conductor (production-grade, feature-complete)
2. **Expression Resolution:** Backend (security, data access)
3. **Python Execution:** Docker sandbox (isolation, security)
4. **Task Type:** SIMPLE (flexibility, integration)
5. **Execution Modes:** Full + Node Testing (developer experience)
6. **Deployment:** Separate Conductor server (scalability)
7. **Expression Syntax:** Preserve frontend format (consistency)
8. **Worker Model:** Persistent polling (performance)
9. **Error Handling:** Three-level hierarchy (reliability)
10. **Tenant Isolation:** Strict enforcement (security)
11. **Expression Timing:** Runtime resolution (dynamic data)
12. **Monitoring:** Conductor UI + custom metrics (observability)

---

## Implementation Priorities

### High Priority (Week 1-4)
- Conductor server setup
- Base worker implementation
- Extraction worker (VLLM integration)
- Expression resolver
- Workflow translator

### Medium Priority (Week 5-8)
- Docker sandbox for Python
- HTTP request worker
- Conditional branching (If nodes)
- Node testing endpoint
- Error handling

### Low Priority (Week 9-12)
- Advanced monitoring
- Performance optimization
- Production deployment
- Documentation

---

## Open Questions

1. **Workflow versioning:** How to handle workflow definition updates?
   - **Decision:** Use Conductor's built-in versioning (v1, v2, etc.)
   - **Rationale:** Allows A/B testing, gradual rollout

2. **Long-running workflows:** How to handle workflows that take hours?
   - **Decision:** Use Conductor's WAIT task for async completion
   - **Rationale:** Avoid tying up worker threads

3. **Workflow sharing:** Can workflows be shared across tenants?
   - **Decision:** No, workflows are tenant-isolated
   - **Rationale:** Security, customization per tenant

4. **Conductor server HA:** How to ensure high availability?
   - **Decision:** Deploy multiple Conductor instances behind load balancer
   - **Rationale:** Standard HA pattern

---

**Last Updated:** 2025-11-15
**Version:** 1.0
**Next Review:** After Phase 1 implementation (Week 4)
