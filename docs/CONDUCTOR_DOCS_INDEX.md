# Netflix Conductor Integration - Documentation Index

**Last Updated:** 2025-11-15

This index provides a comprehensive overview of all Conductor integration documentation. Start here to navigate the architecture, implementation guides, and technical decisions.

---

## Quick Navigation

| Document Type | File | Purpose | Audience |
|---------------|------|---------|----------|
| **Executive Summary** | [CONDUCTOR_INTEGRATION_SUMMARY.md](../CONDUCTOR_INTEGRATION_SUMMARY.md) | High-level overview, key decisions, roadmap | All stakeholders |
| **Architecture** | [2025-11-15-conductor-integration-architecture.md](architecture/2025-11-15-conductor-integration-architecture.md) | Complete technical architecture (2000 lines) | Architects, senior devs |
| **Quick Start** | [2025-11-15-conductor-quick-start.md](guides/2025-11-15-conductor-quick-start.md) | Step-by-step implementation guide | Developers |
| **Technical Decisions** | [2025-11-15-conductor-key-decisions.md](architecture/2025-11-15-conductor-key-decisions.md) | Decision rationale and alternatives | Architects, tech leads |

---

## Document Summaries

### 1. Executive Summary
**File:** `CONDUCTOR_INTEGRATION_SUMMARY.md`
**Size:** ~500 lines

**What it covers:**
- What was delivered (3 documents)
- Key technical decisions (12 decisions)
- Architecture overview (diagrams)
- Component breakdown
- Security architecture
- API endpoints
- Execution modes
- Error handling strategy
- Monitoring approach
- Deployment strategy
- 12-week implementation roadmap
- Testing checklist
- Success metrics

**When to read:**
- First document to read for project overview
- Before stakeholder presentations
- For quick reference to key decisions

---

### 2. Full Architecture Document
**File:** `docs/architecture/2025-11-15-conductor-integration-architecture.md`
**Size:** ~2,000 lines

**What it covers:**
- System overview (current → target architecture)
- Component architecture with Mermaid diagrams
- Complete directory structure
- Database models (WorkflowExecution, TaskExecution)
- Frontend to Conductor translation (detailed)
- Worker implementation (5 worker types, full code structure)
- Expression resolution system (comprehensive)
- Execution modes (full workflow + node testing)
- Docker sandbox implementation (security-focused)
- Integration with existing services (VLLM, Storage, Credits)
- Deployment strategy (Docker Compose → Kubernetes)
- Error handling & retry (3-level hierarchy)
- Monitoring & observability (metrics, logging)
- Security considerations (tenant isolation, sandboxing)
- Implementation roadmap (12 weeks, 7 phases)

**When to read:**
- Before starting implementation
- For detailed component specifications
- When designing new features
- For security review
- For production deployment planning

**Key sections:**
- Section 4: Frontend to Conductor Translation (with examples)
- Section 5: Worker Implementation (complete code structures)
- Section 6: Expression Resolution (with examples)
- Section 8: Docker Sandbox for Python (security measures)
- Section 14: Implementation Roadmap (week-by-week)

---

### 3. Quick Start Guide
**File:** `docs/guides/2025-11-15-conductor-quick-start.md`
**Size:** ~600 lines

**What it covers:**
- 5-minute Conductor server setup (Docker Compose YAML)
- Dependency installation (uv commands)
- Directory structure creation (bash commands)
- Configuration updates (specific code)
- Database migration (alembic commands)
- Core component implementation:
  - ConductorClient (simplified)
  - BaseWorkflowWorker (simplified)
  - ExtractionWorker (simplified)
- Worker startup instructions
- Test workflow execution (Python examples)
- Common operations (check status, debug)
- Troubleshooting guide
- Code snippets cheat sheet

**When to read:**
- First day of implementation
- For local development setup
- When troubleshooting issues
- For quick reference to commands

**Key sections:**
- Section 1: Setup Conductor Server (copy-paste Docker Compose)
- Section 6: Implement Core Components (working code examples)
- Section 8: Test Workflow Execution (end-to-end test)
- Section 11: Troubleshooting (common issues)
- Section 14: Code Snippets Cheat Sheet

---

### 4. Technical Decisions Document
**File:** `docs/architecture/2025-11-15-conductor-key-decisions.md`
**Size:** ~500 lines

**What it covers:**
- 12 critical technical decisions:
  1. Use Netflix Conductor (vs alternatives)
  2. Backend expression resolution (vs frontend)
  3. Docker sandbox for Python (vs alternatives)
  4. SIMPLE task type (vs HTTP)
  5. Two execution modes (full + testing)
  6. Separate Conductor server (vs embedded)
  7. Expression syntax preservation (vs translation)
  8. Persistent worker polling (vs Lambda-style)
  9. Three-level error handling (hierarchy)
  10. Tenant isolation enforcement (strict)
  11. Runtime expression resolution (vs design-time)
  12. Monitoring strategy (Conductor + custom)

**For each decision:**
- Decision statement
- Rationale with detailed reasoning
- Alternatives considered (comparison table)
- Implementation notes
- Security implications

**When to read:**
- Before architecture review
- When questioning design choices
- For new team members (onboarding)
- Before proposing changes

**Key sections:**
- Decision 1: Use Netflix Conductor (why Conductor over others)
- Decision 3: Docker Sandbox for Python (security measures table)
- Decision 5: Two Execution Modes (developer experience)
- Summary: All 12 decisions in one table

---

## Reading Path by Role

### For Architects
1. Read **Executive Summary** (30 min)
2. Read **Technical Decisions** (1 hour)
3. Skim **Full Architecture** focusing on:
   - System Overview (Section 1)
   - Architecture Design (Section 2)
   - Security Considerations (Section 13)
4. Review diagrams in **Full Architecture**

**Time investment:** ~3 hours

### For Senior Developers
1. Read **Executive Summary** (30 min)
2. Read **Quick Start Guide** (1 hour)
3. Read **Full Architecture** focusing on:
   - Frontend to Conductor Translation (Section 4)
   - Worker Implementation (Section 5)
   - Expression Resolution (Section 6)
   - Docker Sandbox (Section 8)
4. Try examples in **Quick Start Guide**

**Time investment:** ~4 hours

### For Developers (Implementation)
1. Read **Quick Start Guide** (1 hour)
2. Follow setup instructions in **Quick Start Guide** (1 hour)
3. Reference **Full Architecture** as needed for specific components
4. Use **Code Snippets Cheat Sheet** (Quick Start Section 14)

**Time investment:** ~2 hours to start, ongoing reference

### For Product/Project Managers
1. Read **Executive Summary** (30 min)
2. Focus on:
   - Key Technical Decisions (summary table)
   - Implementation Roadmap (12 weeks)
   - Success Metrics
3. Review **Technical Decisions** for business impact

**Time investment:** ~1 hour

### For Security Reviewers
1. Read **Executive Summary** → Security Architecture section
2. Read **Full Architecture** focusing on:
   - Security Considerations (Section 13)
   - Docker Sandbox for Python (Section 8)
   - Tenant Isolation (throughout)
3. Review **Technical Decisions** → Decision 3 (Docker Sandbox)

**Time investment:** ~2 hours

---

## Key Code Examples

### 1. Conductor Client Usage
**File:** Quick Start Guide, Section 6.1

```python
from app.orchestration.conductor.client import ConductorClient

client = ConductorClient()

# Register workflow
client.register_workflow(workflow_def)

# Start execution
workflow_id = client.start_workflow(
    workflow_name="test_extraction",
    workflow_input={"schemaId": "schema_123"}
)

# Check status
status = client.get_workflow_status(workflow_id)
```

### 2. Base Worker Implementation
**File:** Quick Start Guide, Section 6.2

```python
from app.orchestration.workers.base_worker import BaseWorkflowWorker

class MyWorker(BaseWorkflowWorker):
    def __init__(self):
        super().__init__(task_def_name="my_task")

    def execute_node(self, input_data, db, tenant_id):
        # Implement task logic
        return {"result": "success"}
```

### 3. Docker Sandbox Usage
**File:** Full Architecture, Section 8.1

```python
from app.orchestration.services.docker_manager import DockerManager

docker_mgr = DockerManager()

result = docker_mgr.execute_python(
    code="return context['value'] * 2",
    context={"value": 10},
    timeout_seconds=30,
    memory_limit='128m'
)
# result['result'] = 20
```

### 4. Expression Resolution
**File:** Full Architecture, Section 6.2

```python
from app.orchestration.services.expression_resolver import ExpressionResolver

resolver = ExpressionResolver()

context = {
    "extract_1": {"data": {"total": 1500}}
}

value = resolver._resolve_string(
    "{{$('extract_1').data.total}}",
    context
)
# value = 1500
```

---

## Diagrams & Visuals

### System Architecture Diagram
**Location:** Full Architecture, Section 1.2

Shows complete data flow from Frontend → Backend → Conductor → Workers → Docker

### Translation Examples
**Location:** Full Architecture, Section 4.4

Visual examples of frontend JSON → Conductor workflow definition

### Error Handling Hierarchy
**Location:** Technical Decisions, Decision 9

Three-level error handling table with retry strategies

### Security Architecture
**Location:** Executive Summary, Security Architecture section

Docker sandbox security measures table

---

## Implementation Progress Tracking

### Phase Checklist (from Roadmap)

**Phase 1: Foundation (Week 1-2)**
- [ ] Set up Conductor server (Docker)
- [ ] Create directory structure
- [ ] Implement ConductorClient wrapper
- [ ] Implement WorkflowTranslator (basic)
- [ ] Create database models
- [ ] Write API endpoints (basic)

**Phase 2: Workers (Week 3-4)**
- [ ] Implement BaseWorkflowWorker
- [ ] Implement ExtractionWorker (VLLM integration)
- [ ] Implement HttpRequestWorker
- [ ] Implement WorkerManager
- [ ] Test worker polling and execution

**Phase 3: Docker Sandbox (Week 5)**
- [ ] Implement DockerManager
- [ ] Implement PythonWorker
- [ ] Test resource limits and isolation
- [ ] Security testing

**Phase 4: Expression Resolution (Week 6)**
- [ ] Implement ExpressionResolver
- [ ] Test expression parsing and evaluation
- [ ] Integrate with workers

**Phase 5: Advanced Features (Week 7-8)**
- [ ] Implement conditional branching (If nodes)
- [ ] Implement ConditionWorker
- [ ] Translator: handle SWITCH tasks
- [ ] Node testing endpoint

**Phase 6: Integration & Testing (Week 9-10)**
- [ ] Full workflow execution testing
- [ ] Error handling and retry testing
- [ ] Performance testing
- [ ] Security audit

**Phase 7: Production Readiness (Week 11-12)**
- [ ] Monitoring and metrics
- [ ] Production deployment
- [ ] Documentation
- [ ] User training

---

## Related Documentation

### Existing Platform Documentation
- **Workflow Builder User Guide:** `docs/guides/2025-11-15-workflow-builder-user-guide.md`
- **Workflow Builder Architecture:** `docs/architecture/2025-11-15-workflow-builder-architecture.md`
- **Workflow Examples:** `docs/guides/2025-11-15-workflow-examples.md`
- **Frontend Workflow Types:** `frontend/src/types/workflow.ts`

### External Resources
- **Conductor Official Docs:** https://conductor.netflix.com
- **Conductor Python SDK:** https://github.com/conductor-oss/conductor-python
- **Docker Python SDK:** https://docker-py.readthedocs.io
- **JSONPath Spec:** https://goessner.net/articles/JsonPath/

---

## Document Maintenance

### Update Frequency
- **Executive Summary:** Update after major architectural changes
- **Full Architecture:** Update during implementation (add discovered details)
- **Quick Start Guide:** Update when setup process changes
- **Technical Decisions:** Update when new decisions made or decisions reversed

### Version History
- **v1.0 (2025-11-15):** Initial design specification

### Next Review
- **After Phase 1 (Week 4):** Review architecture decisions based on implementation experience
- **After Phase 6 (Week 10):** Update performance metrics based on testing
- **Before Production (Week 12):** Final documentation review

---

## Contributing to Documentation

### When to Update
- Found implementation detail not in docs
- Discovered better approach
- Made architectural change
- Added new feature
- Fixed security issue

### How to Update
1. Update relevant document(s)
2. Update version history
3. Add date to "Last Updated"
4. Update this index if new document added
5. Notify team of changes

---

## Search by Topic

### Architecture Topics
- **Conductor Server Setup:** Quick Start Guide, Section 1
- **Worker Implementation:** Full Architecture, Section 5
- **Expression System:** Full Architecture, Section 6
- **Docker Sandbox:** Full Architecture, Section 8
- **Security:** Full Architecture, Section 13

### Implementation Topics
- **ConductorClient:** Quick Start Guide, Section 6.1
- **BaseWorker:** Quick Start Guide, Section 6.2
- **ExtractionWorker:** Quick Start Guide, Section 6.3
- **Database Models:** Full Architecture, Section 3.2
- **API Endpoints:** Executive Summary, API Endpoints section

### Decision Topics
- **Technology Choice:** Technical Decisions, Decision 1
- **Expression Resolution:** Technical Decisions, Decision 2
- **Python Sandbox:** Technical Decisions, Decision 3
- **Tenant Isolation:** Technical Decisions, Decision 10
- **Monitoring:** Technical Decisions, Decision 12

---

## FAQ

### Q: Where do I start reading?
**A:** Start with the **Executive Summary**, then move to **Quick Start Guide** for hands-on implementation.

### Q: I need to understand a specific component (e.g., Docker sandbox). Where do I look?
**A:** Use the "Search by Topic" section above, or check the Full Architecture document's table of contents.

### Q: Why was decision X made instead of alternative Y?
**A:** Check the **Technical Decisions** document. Each decision includes alternatives considered.

### Q: How do I set up my local environment?
**A:** Follow the **Quick Start Guide** from Section 1 (Setup Conductor Server) through Section 7 (Start Workers).

### Q: What's the implementation timeline?
**A:** See **Executive Summary** → Implementation Roadmap (12 weeks, 7 phases).

### Q: Where are the code examples?
**A:** **Quick Start Guide** (simplified examples) and **Full Architecture** (detailed code structures).

---

**Last Updated:** 2025-11-15
**Version:** 1.0
**Maintained By:** Architecture Team
