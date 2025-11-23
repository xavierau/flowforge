# Netflix Conductor Integration - Executive Summary

**Date:** 2025-11-15
**Project:** AI Document Processing Platform - Workflow Execution Engine
**Status:** Design Complete - Ready for Implementation

---

## Overview

This document provides an executive summary of the Netflix Conductor integration design for executing visual workflows created in the frontend workflow builder. The integration enables distributed, scalable, and secure execution of document processing workflows with support for custom Python code, HTTP requests, conditional logic, and VLLM-based document extraction.

---

## What Was Delivered

### 1. Comprehensive Architecture Document
**File:** `docs/architecture/2025-11-15-conductor-integration-architecture.md`

**Contents:**
- Complete system architecture with Mermaid diagrams
- Directory structure specification (`app/orchestration/`)
- Database models for workflow execution tracking
- Frontend to Conductor workflow translation strategy
- Worker implementation patterns (5 worker types)
- Expression resolution system design
- Docker sandbox security architecture
- Two execution modes (full workflow + node testing)
- Integration with existing VLLM, Storage, Credit services
- Deployment strategy (Docker Compose → Kubernetes)
- Error handling and retry policies
- Monitoring and observability design
- Security considerations (tenant isolation, sandboxing)
- 12-week implementation roadmap

**Size:** ~2,000 lines of detailed specifications

### 2. Quick Start Guide
**File:** `docs/guides/2025-11-15-conductor-quick-start.md`

**Contents:**
- 5-minute Conductor server setup (Docker Compose)
- Dependency installation
- Directory structure creation
- Configuration updates
- Database migration
- Core component implementation (ConductorClient, BaseWorker, ExtractionWorker)
- Worker startup instructions
- Test workflow execution examples
- Troubleshooting guide
- Code snippets cheat sheet

**Size:** ~600 lines of practical implementation steps

### 3. Technical Decisions Document
**File:** `docs/architecture/2025-11-15-conductor-key-decisions.md`

**Contents:**
- 12 critical technical decisions with rationale
- Alternatives considered for each decision
- Implementation notes and security implications
- Priority matrix (High/Medium/Low)
- Open questions and answers
- Metrics strategy
- Next review timeline

**Size:** ~500 lines of decision documentation

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Orchestration Engine** | Netflix Conductor | Production-grade, battle-tested at Netflix scale |
| **Expression Resolution** | Backend (runtime) | Security, access to execution context |
| **Python Execution** | Docker sandbox | Full isolation with resource limits |
| **Task Type** | SIMPLE (custom workers) | Flexibility, database access, service integration |
| **Execution Modes** | Full + Node Testing | Better developer experience |
| **Deployment** | Separate Conductor server | Independent scaling |
| **Worker Model** | Persistent polling | No cold start, connection pooling |
| **Tenant Isolation** | Strict enforcement | Security, compliance |

---

## Architecture Overview

### High-Level Flow

```
Frontend (React Workflow Builder)
  │
  │ Saves workflow JSON
  ▼
FastAPI Backend
  │
  ├── Translator: Frontend JSON → Conductor Workflow
  ├── ConductorClient: Register & Execute Workflows
  └── API Endpoints: /workflows, /executions
  │
  ▼
Conductor Server (Docker)
  │
  │ Task scheduling & distribution
  ▼
Workers (Polling)
  │
  ├── ExtractionWorker → VLLM Service
  ├── PythonWorker → Docker Sandbox
  ├── HttpRequestWorker → External APIs
  └── ConditionWorker → If/Then Logic
  │
  ▼
Execution Tracker (PostgreSQL)
  │
  └── Stores: workflow executions, task executions, results
```

### Component Breakdown

| Component | Technology | Responsibility |
|-----------|-----------|----------------|
| **Conductor Server** | Netflix Conductor (Docker) | Workflow orchestration, task scheduling |
| **Conductor Client** | conductor-python SDK | API wrapper for workflow operations |
| **Translator** | Python | Convert frontend JSON to Conductor format |
| **Workers** | conductor-python TaskHandler | Execute workflow nodes (5 types) |
| **Expression Resolver** | Python + JSONPath | Resolve `{{$("Node").data.field}}` |
| **Docker Manager** | docker-py | Manage Python sandbox containers |
| **Execution Tracker** | SQLAlchemy + PostgreSQL | Track execution state |

---

## Workflow Node Types → Worker Mapping

| Frontend Node | Conductor Task Type | Worker | Integration |
|---------------|---------------------|--------|-------------|
| **HttpTrigger** | Workflow Input | N/A | Entry point for webhook data |
| **Extraction** | SIMPLE | `extraction_worker.py` | VLLM Service (Gemini/OpenAI/DeepSeek) |
| **PythonRunner** | SIMPLE | `python_worker.py` | Docker sandbox with resource limits |
| **HttpRequest** | SIMPLE | `http_request_worker.py` | HTTP client with timeout |
| **If** | SWITCH | `condition_worker.py` | JavaScript expression evaluation |

---

## Directory Structure

```
app/orchestration/
├── conductor/
│   ├── client.py                 # Conductor API wrapper
│   ├── translator.py             # JSON → Conductor workflow
│   └── task_definitions.py       # Task type mappings
├── workers/
│   ├── base_worker.py            # Abstract base class
│   ├── extraction_worker.py      # VLLM integration
│   ├── python_worker.py          # Docker sandbox
│   ├── http_request_worker.py    # HTTP calls
│   ├── condition_worker.py       # If/condition logic
│   └── worker_manager.py         # Worker lifecycle
├── services/
│   ├── expression_resolver.py    # Expression evaluation
│   ├── docker_manager.py         # Docker container mgmt
│   └── execution_tracker.py      # Execution state tracking
├── models/
│   ├── workflow_execution.py     # SQLAlchemy model
│   └── task_execution.py         # Task execution log
└── api/
    ├── workflows.py              # FastAPI endpoints
    └── schemas.py                # Pydantic models
```

**Total Estimated LOC:** ~1,870 lines of production code

---

## Security Architecture

### 1. Tenant Isolation
- `tenantId` injected into all workflow inputs
- Every worker validates tenant access
- All database queries filtered by tenant
- No cross-tenant data leakage

### 2. Docker Sandbox Security
- **Network isolation:** `network_mode='none'`
- **Read-only filesystem:** `read_only=True`
- **No privileges:** `no-new-privileges`
- **Capability drop:** `cap_drop=['ALL']`
- **Resource limits:** CPU: 0.5 cores, Memory: 128MB
- **Timeout:** 30 seconds default

### 3. Expression Injection Prevention
- Backend-side resolution only
- No `eval()` of user-provided code (except in sandbox)
- Safe JSONPath evaluation
- Expression validation before execution

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /api/v1/workflows` | POST | Create workflow |
| `GET /api/v1/workflows` | GET | List workflows |
| `POST /api/v1/workflows/{id}/execute` | POST | Execute full workflow |
| `POST /api/v1/workflows/test-node` | POST | Test single node in isolation |
| `GET /api/v1/executions/{id}` | GET | Get execution status |
| `POST /api/v1/executions/{id}/cancel` | POST | Cancel execution |

---

## Execution Modes

### Mode 1: Full Workflow Execution
**Use Case:** Production workflow execution from trigger to completion

**Flow:**
1. User clicks "Run Workflow" in UI
2. Frontend sends workflow ID + input data
3. Backend translates workflow to Conductor format
4. Registers workflow (if not already registered)
5. Starts execution with input data
6. Workers poll and execute tasks in sequence
7. Results stored in database
8. Frontend polls for completion status

**Endpoint:** `POST /api/v1/workflows/{id}/execute`

### Mode 2: Isolated Node Testing
**Use Case:** Test individual nodes during development

**Flow:**
1. User selects node in UI, clicks "Test Node"
2. Frontend sends node config + mock input data
3. Backend creates dynamic workflow (single task)
4. Executes workflow without registration
5. Returns task output immediately
6. No workflow tracking in database

**Endpoint:** `POST /api/v1/workflows/test-node`

---

## Expression Resolution

### Frontend Expression Syntax
```
{{$("NodeName").data.field}}
```

**Examples:**
- `{{$('extract_1').data.total}}`
- `{{$('extract_1').data.invoice.items[0].price}}`
- `{{$('trigger_1').data.prompt}}`

### Translation to Conductor
```
${taskReferenceName.output.result.field}
```

**Examples:**
- `${extract_1.output.result.total}`
- `${extract_1.output.result.invoice.items[0].price}`
- `${workflow.input.trigger_1_data.prompt}`

### Resolution Timing
- **Design time:** Expressions preserved as-is
- **Registration time:** Translated to Conductor format
- **Execution time:** Resolved to actual values

---

## Error Handling Strategy

### Three-Level Hierarchy

**1. Task-Level (Automatic Retry)**
- **Scope:** Single task execution
- **Retry:** Exponential backoff (3 retries)
- **Example:** VLLM API timeout → Retry after 5s, 10s, 20s

**2. Workflow-Level (Mark Failed)**
- **Scope:** Entire workflow
- **Retry:** No automatic retry
- **Example:** Invalid workflow definition → FAILED status

**3. Application-Level (Alert)**
- **Scope:** System errors
- **Retry:** N/A
- **Example:** Database connection lost → Alert operator

### Retry Configuration Example
```json
{
  "retryCount": 3,
  "retryLogic": "EXPONENTIAL_BACKOFF",
  "retryDelaySeconds": 5,
  "backoffScaleFactor": 2,
  "timeoutSeconds": 300
}
```

---

## Monitoring & Observability

### Conductor Built-in
- Workflow execution dashboard
- Task execution details
- Worker status monitoring
- Queue depth metrics

### Custom Metrics (Prometheus)
```
workflow_executions_total{tenant_id, workflow_name, status}
task_execution_duration_seconds{task_type}
docker_container_memory_bytes
expression_resolution_time_seconds
```

### Logging Strategy
- Structured logging (structlog)
- Correlation IDs across services
- Tenant ID in all logs
- Task execution traces

---

## Deployment Strategy

### Development
```yaml
# docker-compose.conductor.yml
services:
  conductor-server:
    image: conductor:server
    ports: ["8080:8080", "5000:5000"]
  postgres-conductor:
    image: postgres:15
  redis:
    image: redis:7-alpine
```

**Start:**
```bash
docker-compose -f docker-compose.conductor.yml up -d
python -m app.orchestration.workers.worker_manager
```

### Production (Kubernetes)
- Multi-instance Conductor server (HA)
- Horizontal scaling for workers
- Separate database per environment
- Metrics + alerting (Prometheus + Grafana)

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- Set up Conductor server
- Create directory structure
- Implement ConductorClient wrapper
- Implement WorkflowTranslator (basic)
- Create database models
- Write API endpoints (basic)

### Phase 2: Workers (Week 3-4)
- Implement BaseWorkflowWorker
- Implement ExtractionWorker (VLLM integration)
- Implement HttpRequestWorker
- Implement WorkerManager
- Test worker polling and execution

### Phase 3: Docker Sandbox (Week 5)
- Implement DockerManager
- Implement PythonWorker
- Test resource limits and isolation
- Security testing

### Phase 4: Expression Resolution (Week 6)
- Implement ExpressionResolver
- Test expression parsing and evaluation
- Integrate with workers

### Phase 5: Advanced Features (Week 7-8)
- Implement conditional branching (If nodes)
- Implement ConditionWorker
- Translator: handle SWITCH tasks
- Node testing endpoint

### Phase 6: Integration & Testing (Week 9-10)
- Full workflow execution testing
- Error handling and retry testing
- Performance testing
- Security audit

### Phase 7: Production Readiness (Week 11-12)
- Monitoring and metrics
- Production deployment
- Documentation
- User training

---

## Critical Implementation Notes

### 1. Always Use context7
Before implementing ANY Conductor code, research current API documentation:
```python
# MANDATORY: Verify API before using
from app.orchestration.conductor.client import ConductorClient

# Research: conductor-python SDK latest docs
# Verify: WorkflowResourceApi methods
# Check: TaskHandler initialization
```

### 2. Tenant Isolation (CRITICAL)
```python
# ALWAYS filter by tenant
schema = db.query(Schema).filter(
    Schema.id == schema_id,
    Schema.tenant_id == tenant_id  # CRITICAL - never omit
).first()
```

### 3. Docker Security
```python
# NEVER run without these constraints
container = docker_client.containers.run(
    network_mode='none',      # REQUIRED
    read_only=True,           # REQUIRED
    security_opt=['no-new-privileges'],  # REQUIRED
    cap_drop=['ALL'],         # REQUIRED
    mem_limit='128m',         # REQUIRED
    cpu_quota=50000           # REQUIRED
)
```

### 4. Expression Resolution
```python
# NEVER use eval() directly on user input
# ALWAYS use ExpressionResolver
resolver = ExpressionResolver()
resolved = resolver.resolve_all(input_data, context)
```

---

## Testing Checklist

### Unit Tests
- [ ] ExpressionResolver: expression parsing
- [ ] ExpressionResolver: JSONPath evaluation
- [ ] WorkflowTranslator: node to task mapping
- [ ] WorkflowTranslator: expression preservation
- [ ] DockerManager: container lifecycle
- [ ] DockerManager: resource limits

### Integration Tests
- [ ] ConductorClient: workflow registration
- [ ] ConductorClient: workflow execution
- [ ] Workers: task polling
- [ ] Workers: task execution
- [ ] Workers: error handling
- [ ] End-to-end: full workflow execution

### Security Tests
- [ ] Tenant isolation (cross-tenant access)
- [ ] Docker sandbox (network isolation)
- [ ] Docker sandbox (filesystem access)
- [ ] Expression injection prevention
- [ ] API endpoint authorization

### Performance Tests
- [ ] Workflow execution latency
- [ ] Worker throughput
- [ ] Docker container overhead
- [ ] Expression resolution performance
- [ ] Database query performance

---

## Key Resources

### Documentation
- **Full Architecture:** `docs/architecture/2025-11-15-conductor-integration-architecture.md`
- **Quick Start Guide:** `docs/guides/2025-11-15-conductor-quick-start.md`
- **Technical Decisions:** `docs/architecture/2025-11-15-conductor-key-decisions.md`

### External Resources
- **Conductor Docs:** https://conductor.netflix.com
- **Python SDK:** https://github.com/conductor-oss/conductor-python
- **Docker SDK:** https://docker-py.readthedocs.io

### Local Resources
- **Conductor UI:** http://localhost:5000 (when running)
- **Conductor API:** http://localhost:8080/api
- **Conductor Health:** http://localhost:8080/health

---

## Success Metrics

### Technical Metrics
- Workflow execution latency: < 5s (simple workflows)
- Worker polling interval: 1s
- Docker container overhead: < 500ms
- Expression resolution: < 100ms
- Task retry success rate: > 90%

### Business Metrics
- Workflow creation time: < 10 min (developer)
- Node testing time: < 30s
- Workflow execution success rate: > 95%
- System uptime: > 99.9%

---

## Next Steps

1. **Review & Approval:** Present architecture to team
2. **Setup Development Environment:** Install Conductor server
3. **Begin Phase 1 Implementation:** ConductorClient + BaseWorker
4. **Weekly Progress Reviews:** Track against 12-week roadmap
5. **Security Audit:** After Phase 3 (Docker sandbox)
6. **Performance Testing:** After Phase 6 (integration complete)
7. **Production Deployment:** Week 12

---

## Questions & Contact

For questions about this architecture, contact:
- **Architecture:** Refer to detailed docs in `docs/architecture/`
- **Implementation:** See quick start guide in `docs/guides/`
- **Decisions:** Review `docs/architecture/2025-11-15-conductor-key-decisions.md`

---

**Document Version:** 1.0
**Last Updated:** 2025-11-15
**Status:** Design Complete - Ready for Implementation Approval
