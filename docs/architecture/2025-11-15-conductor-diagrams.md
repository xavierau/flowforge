# Conductor Integration - Visual Diagrams

**Date:** 2025-11-15
**Purpose:** Visual reference for system architecture and data flows

This document contains Mermaid diagrams for the Conductor integration architecture. These diagrams provide visual clarity to complement the written specifications.

---

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[React Workflow Builder]
        UI_COMP[Visual Editor<br/>5 Node Types]
    end

    subgraph "Backend Layer"
        API[FastAPI Application]
        TRANS[Workflow Translator]
        CLIENT[Conductor Client]
        TRACKER[Execution Tracker]
    end

    subgraph "Orchestration Layer"
        CONDUCTOR[Conductor Server<br/>Docker Container]
        TASK_Q[Task Queue]
    end

    subgraph "Execution Layer"
        W1[Extraction Worker<br/>VLLM Integration]
        W2[Python Worker<br/>Docker Sandbox]
        W3[HTTP Worker<br/>Request Handler]
        W4[Condition Worker<br/>If/Then Logic]
    end

    subgraph "Service Layer"
        VLLM[VLLM Service<br/>Gemini/OpenAI/DeepSeek]
        DOCKER[Docker Manager<br/>Python Sandbox]
        EXPR[Expression Resolver<br/>JSONPath Engine]
    end

    subgraph "Data Layer"
        DB_APP[(Application DB<br/>PostgreSQL)]
        DB_COND[(Conductor DB<br/>PostgreSQL)]
        REDIS[(Redis Cache)]
    end

    UI --> API
    API --> TRANS
    TRANS --> CLIENT
    CLIENT --> CONDUCTOR
    CONDUCTOR --> TASK_Q
    TASK_Q --> W1
    TASK_Q --> W2
    TASK_Q --> W3
    TASK_Q --> W4

    W1 --> VLLM
    W2 --> DOCKER
    W1 --> EXPR
    W2 --> EXPR

    API --> DB_APP
    CONDUCTOR --> DB_COND
    API --> TRACKER
    TRACKER --> DB_APP

    style UI fill:#e1f5ff
    style CONDUCTOR fill:#fff4e1
    style W1 fill:#f0f8ff
    style W2 fill:#f0f8ff
    style W3 fill:#f0f8ff
    style W4 fill:#f0f8ff
    style VLLM fill:#e8f5e9
    style DOCKER fill:#e8f5e9
```

---

## 2. Full Workflow Execution Flow

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant FastAPI
    participant Translator
    participant ConductorAPI
    participant ConductorEngine
    participant Worker
    participant Service
    participant Database

    User->>Frontend: Click "Run Workflow"
    Frontend->>FastAPI: POST /workflows/{id}/execute<br/>{input: {...}}

    FastAPI->>Database: Load workflow definition
    Database-->>FastAPI: Workflow JSON

    FastAPI->>Translator: Translate workflow
    Translator->>Translator: Map nodes to Conductor tasks
    Translator->>Translator: Convert expressions
    Translator-->>FastAPI: Conductor workflow definition

    FastAPI->>ConductorAPI: Register workflow (if needed)
    ConductorAPI-->>FastAPI: OK

    FastAPI->>ConductorAPI: Start workflow execution
    ConductorAPI->>ConductorEngine: Create workflow instance
    ConductorEngine-->>ConductorAPI: Workflow ID
    ConductorAPI-->>FastAPI: Workflow ID

    FastAPI->>Database: Track execution (RUNNING)
    FastAPI-->>Frontend: Execution started

    loop For each task in workflow
        ConductorEngine->>Worker: Poll for task
        Worker-->>ConductorEngine: Task received

        Worker->>Worker: Validate tenant ID
        Worker->>Worker: Resolve expressions

        alt Extraction Task
            Worker->>Service: Extract data (VLLM)
            Service-->>Worker: Extraction result
        else Python Task
            Worker->>Service: Execute Python (Docker)
            Service-->>Worker: Execution result
        else HTTP Task
            Worker->>Service: Make HTTP request
            Service-->>Worker: HTTP response
        end

        Worker->>Database: Log task execution
        Worker->>ConductorEngine: Complete task with output
    end

    ConductorEngine->>Database: Update workflow status (COMPLETED)
    ConductorEngine-->>Frontend: Workflow completed (webhook/polling)
```

---

## 3. Isolated Node Testing Flow

```mermaid
sequenceDiagram
    actor Developer
    participant Frontend
    participant FastAPI
    participant ConductorAPI
    participant Worker
    participant Service

    Developer->>Frontend: Select node, click "Test"
    Frontend->>Frontend: Prepare mock input

    Frontend->>FastAPI: POST /workflows/test-node<br/>{node: {...}, mockInput: {...}}

    FastAPI->>FastAPI: Create dynamic workflow<br/>(single task, no registration)

    FastAPI->>ConductorAPI: Execute dynamic workflow
    ConductorAPI->>Worker: Poll for task
    Worker-->>ConductorAPI: Task received

    Worker->>Worker: Resolve expressions
    Worker->>Service: Execute node logic
    Service-->>Worker: Node output

    Worker->>ConductorAPI: Complete task
    ConductorAPI-->>FastAPI: Task result

    FastAPI-->>Frontend: Node output data
    Frontend->>Developer: Display result
```

---

## 4. Frontend to Conductor Translation

```mermaid
graph LR
    subgraph "Frontend Workflow JSON"
        F_NODES[Nodes Array<br/>- HttpTrigger<br/>- Extraction<br/>- Python<br/>- HTTP<br/>- If]
        F_EDGES[Edges Array<br/>source → target]
        F_EXPR[Expressions<br/>{{$('Node').data.field}}]
    end

    subgraph "Translator Process"
        T1[Parse nodes & edges]
        T2[Build task sequence]
        T3[Map node types to<br/>Conductor tasks]
        T4[Convert expressions<br/>to Conductor format]
        T5[Generate workflow def]
    end

    subgraph "Conductor Workflow Definition"
        C_TASKS[Tasks Array<br/>- SIMPLE tasks<br/>- SWITCH tasks]
        C_INPUT[Input Parameters]
        C_OUTPUT[Output Parameters]
        C_EXPR[Conductor Expressions<br/>$&#123;task.output.field&#125;]
    end

    F_NODES --> T1
    F_EDGES --> T1
    F_EXPR --> T4

    T1 --> T2
    T2 --> T3
    T3 --> T4
    T4 --> T5

    T5 --> C_TASKS
    T5 --> C_INPUT
    T5 --> C_OUTPUT
    T4 --> C_EXPR

    style F_NODES fill:#e1f5ff
    style C_TASKS fill:#fff4e1
```

---

## 5. Worker Architecture

```mermaid
classDiagram
    class WorkerInterface {
        <<interface>>
        +get_task_def_name() str
        +execute(task) TaskResult
    }

    class BaseWorkflowWorker {
        <<abstract>>
        -task_def_name: str
        -expression_resolver: ExpressionResolver
        +execute(task) TaskResult
        +execute_node(input_data, db, tenant_id)* dict
        -_resolve_input_expressions(task) dict
        -_build_execution_context(task) dict
    }

    class ExtractionWorker {
        -vllm_service: VLLMService
        +execute_node(input_data, db, tenant_id) dict
        -_get_file_content(input_data) bytes
    }

    class PythonWorker {
        -docker_manager: DockerManager
        +execute_node(input_data, db, tenant_id) dict
    }

    class HttpRequestWorker {
        +execute_node(input_data, db, tenant_id) dict
        -_parse_response_body(response) Any
    }

    class ConditionWorker {
        -expression_resolver: ExpressionResolver
        +execute_node(input_data, db, tenant_id) dict
    }

    WorkerInterface <|-- BaseWorkflowWorker
    BaseWorkflowWorker <|-- ExtractionWorker
    BaseWorkflowWorker <|-- PythonWorker
    BaseWorkflowWorker <|-- HttpRequestWorker
    BaseWorkflowWorker <|-- ConditionWorker
```

---

## 6. Docker Sandbox Security Architecture

```mermaid
graph TB
    subgraph "Worker Process"
        PYTHON_WORKER[Python Worker]
        DOCKER_MGR[Docker Manager]
    end

    subgraph "Docker Container (Isolated)"
        PYTHON_ENV[Python 3.11 Environment]
        USER_CODE[User Python Code]
        CONTEXT[Input Context Data]
    end

    subgraph "Security Constraints"
        NET[Network Isolation<br/>network_mode=none]
        FS[Read-Only Filesystem<br/>read_only=True]
        PRIV[No Privileges<br/>no-new-privileges]
        CAP[Capabilities Dropped<br/>cap_drop=ALL]
        RES[Resource Limits<br/>CPU: 0.5 cores<br/>Memory: 128MB<br/>Timeout: 30s]
    end

    PYTHON_WORKER --> DOCKER_MGR
    DOCKER_MGR --> PYTHON_ENV

    NET -.enforces.-> PYTHON_ENV
    FS -.enforces.-> PYTHON_ENV
    PRIV -.enforces.-> PYTHON_ENV
    CAP -.enforces.-> PYTHON_ENV
    RES -.enforces.-> PYTHON_ENV

    CONTEXT --> USER_CODE
    USER_CODE --> PYTHON_ENV

    PYTHON_ENV -.result.-> DOCKER_MGR
    DOCKER_MGR -.output.-> PYTHON_WORKER

    style NET fill:#ffebee
    style FS fill:#ffebee
    style PRIV fill:#ffebee
    style CAP fill:#ffebee
    style RES fill:#ffebee
    style PYTHON_ENV fill:#e8f5e9
```

---

## 7. Expression Resolution Process

```mermaid
graph LR
    subgraph "Input Data"
        RAW[Node Config with Expressions<br/>prompt: '{{$('trigger').data.text}}'<br/>url: '{{$('extract').data.callback}}']
    end

    subgraph "Expression Resolver"
        PARSE[Parse Expression<br/>Regex: {{$("Node").data.field}}]
        EXTRACT[Extract Node Name & Path<br/>Node: 'trigger'<br/>Path: 'data.text']
        LOOKUP[Lookup in Context<br/>context['trigger']['data']['text']]
        JSONPATH[JSONPath Evaluation<br/>$.data.text]
        RESOLVE[Resolve Value<br/>'Extract invoice data']
    end

    subgraph "Execution Context"
        CTX[{<br/>  trigger: {data: {text: 'Extract invoice data'}},<br/>  extract: {data: {callback: 'https://...'}}<br/>}]
    end

    subgraph "Output Data"
        RESOLVED[Resolved Config<br/>prompt: 'Extract invoice data'<br/>url: 'https://...']
    end

    RAW --> PARSE
    PARSE --> EXTRACT
    EXTRACT --> LOOKUP
    LOOKUP --> CTX
    CTX --> JSONPATH
    JSONPATH --> RESOLVE
    RESOLVE --> RESOLVED

    style RAW fill:#e1f5ff
    style RESOLVED fill:#e8f5e9
```

---

## 8. Error Handling Hierarchy

```mermaid
graph TB
    subgraph "Task-Level Errors"
        T_ERR[Task Execution Error<br/>e.g., VLLM timeout]
        T_RETRY{Retry Logic}
        T_SUCCESS[Task Completed]
        T_FAIL[Task Failed]
    end

    subgraph "Workflow-Level Errors"
        W_ERR[Workflow Error<br/>e.g., Invalid definition]
        W_TERM[Workflow Terminated]
        W_FAIL[Workflow Failed]
    end

    subgraph "Application-Level Errors"
        A_ERR[System Error<br/>e.g., DB connection lost]
        A_ALERT[Alert Operator]
        A_RECOVER[Auto-Recovery Attempt]
    end

    T_ERR --> T_RETRY
    T_RETRY -->|Retry 1-3<br/>Exponential Backoff| T_ERR
    T_RETRY -->|Success| T_SUCCESS
    T_RETRY -->|Max Retries| T_FAIL

    T_FAIL --> W_FAIL
    W_ERR --> W_TERM
    W_TERM --> W_FAIL

    A_ERR --> A_ALERT
    A_ERR --> A_RECOVER
    A_RECOVER -->|Success| T_RETRY
    A_RECOVER -->|Failure| A_ALERT

    style T_SUCCESS fill:#e8f5e9
    style T_FAIL fill:#ffebee
    style W_FAIL fill:#ffebee
    style A_ALERT fill:#fff3e0
```

---

## 9. Data Flow: Extraction Node Example

```mermaid
sequenceDiagram
    participant Conductor
    participant ExtractionWorker
    participant ExpressionResolver
    participant VLLMService
    participant Database

    Conductor->>ExtractionWorker: Poll: extraction_task

    ExtractionWorker->>ExpressionResolver: Resolve expressions in input
    Note over ExpressionResolver: prompt: "{{$('trigger').data.prompt}}"<br/>→ "Extract invoice data"

    ExtressionResolver-->>ExtractionWorker: Resolved input

    ExtractionWorker->>ExtractionWorker: Validate tenant ID

    ExtractionWorker->>Database: Load schema<br/>(filtered by tenant)
    Database-->>ExtractionWorker: Schema definition

    ExtractionWorker->>VLLMService: extract_from_image(<br/>  image_data,<br/>  schema,<br/>  prompt<br/>)
    Note over VLLMService: Call Gemini 2.5 Flash API

    VLLMService-->>ExtractionWorker: Extraction result<br/>{total: 1500, currency: 'USD'}

    ExtractionWorker->>Database: Log task execution
    ExtractionWorker->>Conductor: Complete task<br/>output: {result: {...}, metadata: {...}}
```

---

## 10. Component Directory Structure

```mermaid
graph TB
    subgraph "app/orchestration/"
        ROOT[__init__.py]

        subgraph "conductor/"
            C1[client.py<br/>ConductorClient]
            C2[translator.py<br/>WorkflowTranslator]
            C3[task_definitions.py<br/>Task type mappings]
        end

        subgraph "workers/"
            W1[base_worker.py<br/>BaseWorkflowWorker]
            W2[extraction_worker.py<br/>ExtractionWorker]
            W3[python_worker.py<br/>PythonWorker]
            W4[http_request_worker.py<br/>HttpRequestWorker]
            W5[condition_worker.py<br/>ConditionWorker]
            W6[worker_manager.py<br/>WorkerManager]
        end

        subgraph "services/"
            S1[expression_resolver.py<br/>ExpressionResolver]
            S2[docker_manager.py<br/>DockerManager]
            S3[execution_tracker.py<br/>ExecutionTracker]
        end

        subgraph "models/"
            M1[workflow_execution.py<br/>WorkflowExecution]
            M2[task_execution.py<br/>TaskExecution]
        end

        subgraph "api/"
            A1[workflows.py<br/>FastAPI endpoints]
            A2[schemas.py<br/>Pydantic models]
        end
    end

    ROOT --> C1
    ROOT --> C2
    ROOT --> W1
    ROOT --> W2
    ROOT --> S1
    ROOT --> M1
    ROOT --> A1

    W2 -.uses.-> W1
    W3 -.uses.-> W1
    W2 -.uses.-> S1
    W3 -.uses.-> S2
    A1 -.uses.-> C1
    A1 -.uses.-> C2

    style C1 fill:#e1f5ff
    style W2 fill:#f0f8ff
    style W3 fill:#f0f8ff
    style S1 fill:#e8f5e9
    style S2 fill:#e8f5e9
```

---

## 11. Deployment Architecture

```mermaid
graph TB
    subgraph "Development Environment"
        DEV_API[FastAPI<br/>localhost:8000]
        DEV_COND[Conductor Server<br/>localhost:8080]
        DEV_WORK[Workers<br/>Local Process]
        DEV_DB[(PostgreSQL<br/>localhost:5432)]
        DEV_REDIS[(Redis<br/>localhost:6379)]
    end

    subgraph "Production Environment (Kubernetes)"
        subgraph "API Layer"
            API1[FastAPI Pod 1]
            API2[FastAPI Pod 2]
            LB_API[Load Balancer]
        end

        subgraph "Conductor Layer"
            COND1[Conductor Pod 1]
            COND2[Conductor Pod 2]
            LB_COND[Load Balancer]
        end

        subgraph "Worker Layer"
            WORK1[Worker Pod 1<br/>Extraction + Python]
            WORK2[Worker Pod 2<br/>HTTP + Condition]
            WORK3[Worker Pod 3<br/>Auto-scaled]
        end

        subgraph "Data Layer"
            DB_APP[(App DB<br/>PostgreSQL HA)]
            DB_COND[(Conductor DB<br/>PostgreSQL HA)]
            REDIS_HA[(Redis Cluster)]
        end

        subgraph "Observability"
            PROM[Prometheus]
            GRAF[Grafana]
            ALERT[Alertmanager]
        end
    end

    DEV_API --> DEV_COND
    DEV_WORK --> DEV_COND
    DEV_API --> DEV_DB
    DEV_COND --> DEV_DB

    LB_API --> API1
    LB_API --> API2
    API1 --> DB_APP
    API2 --> DB_APP

    LB_COND --> COND1
    LB_COND --> COND2
    COND1 --> DB_COND
    COND2 --> DB_COND

    WORK1 --> LB_COND
    WORK2 --> LB_COND
    WORK3 --> LB_COND

    WORK1 --> DB_APP
    WORK2 --> DB_APP

    API1 -.metrics.-> PROM
    COND1 -.metrics.-> PROM
    WORK1 -.metrics.-> PROM

    PROM --> GRAF
    PROM --> ALERT

    style DEV_API fill:#e1f5ff
    style API1 fill:#e8f5e9
    style API2 fill:#e8f5e9
    style COND1 fill:#fff4e1
    style COND2 fill:#fff4e1
```

---

## 12. Node Type to Task Type Mapping

```mermaid
graph LR
    subgraph "Frontend Node Types"
        N1[HttpTrigger<br/>Entry point]
        N2[Extraction<br/>Document extraction]
        N3[PythonRunner<br/>Python code execution]
        N4[HttpRequest<br/>External API calls]
        N5[If<br/>Conditional branching]
    end

    subgraph "Conductor Task Types"
        T1[Workflow Input<br/>No task]
        T2[SIMPLE<br/>extraction_task]
        T3[SIMPLE<br/>python_task]
        T4[SIMPLE<br/>http_request_task]
        T5[SWITCH<br/>condition_task]
    end

    subgraph "Worker Implementation"
        W1[N/A<br/>Entry point only]
        W2[ExtractionWorker<br/>VLLM integration]
        W3[PythonWorker<br/>Docker sandbox]
        W4[HttpRequestWorker<br/>HTTP client]
        W5[ConditionWorker<br/>Expression evaluation]
    end

    N1 --> T1 --> W1
    N2 --> T2 --> W2
    N3 --> T3 --> W3
    N4 --> T4 --> W4
    N5 --> T5 --> W5

    style N1 fill:#e1f5ff
    style N2 fill:#e1f5ff
    style N3 fill:#e1f5ff
    style N4 fill:#e1f5ff
    style N5 fill:#e1f5ff

    style W2 fill:#e8f5e9
    style W3 fill:#e8f5e9
    style W4 fill:#e8f5e9
    style W5 fill:#e8f5e9
```

---

## 13. Tenant Isolation Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Worker
    participant Database

    User->>Frontend: Login with credentials
    Frontend->>API: POST /auth/login
    API-->>Frontend: JWT (with tenant_id)

    Frontend->>API: POST /workflows/execute<br/>(with JWT)
    API->>API: Extract tenant_id from JWT
    API->>API: Inject tenant_id into workflow input

    API->>Database: Load workflow<br/>WHERE tenant_id = ?
    Database-->>API: Workflow (if owned by tenant)

    API->>Conductor: Start workflow<br/>input: {tenantId: '...', ...}

    Conductor->>Worker: Task with input

    Worker->>Worker: Extract tenant_id from input
    Worker->>Worker: Validate tenant_id exists

    Worker->>Database: Load schema<br/>WHERE schema_id = ? AND tenant_id = ?
    Database-->>Worker: Schema (if owned by tenant)

    alt Schema found
        Worker->>Worker: Execute task
        Worker-->>Conductor: Task completed
    else Schema not found
        Worker-->>Conductor: Task failed<br/>"Resource not found or access denied"
    end

    Note over Worker,Database: CRITICAL: Always filter by tenant_id
```

---

## Diagram Usage Guide

### For Presentations
- **Diagram 1:** High-level system architecture
- **Diagram 11:** Deployment architecture
- **Diagram 8:** Error handling hierarchy

### For Implementation
- **Diagram 5:** Worker class structure
- **Diagram 10:** Directory structure
- **Diagram 12:** Node type mappings

### For Security Review
- **Diagram 6:** Docker sandbox security
- **Diagram 13:** Tenant isolation flow

### For Debugging
- **Diagram 2:** Full workflow execution flow
- **Diagram 9:** Extraction node example
- **Diagram 7:** Expression resolution

---

**Last Updated:** 2025-11-15
**Version:** 1.0
**Related Documents:**
- Full Architecture: `2025-11-15-conductor-integration-architecture.md`
- Quick Start: `../../guides/2025-11-15-conductor-quick-start.md`
- Technical Decisions: `2025-11-15-conductor-key-decisions.md`
