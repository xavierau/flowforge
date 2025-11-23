# Netflix Conductor Orchestration Layer

Complete orchestration layer for executing workflow definitions using Netflix Conductor.

## Architecture Overview

```
app/orchestration/
├── conductor/          # Conductor integration
│   ├── translator.py   # Frontend JSON → Conductor workflow
│   └── task_definitions.py  # Task definition templates
├── workers/            # Conductor workers
│   ├── base_worker.py  # Abstract base worker
│   ├── extraction_worker.py  # Document extraction
│   ├── python_worker.py  # Python code execution (Docker sandbox)
│   ├── http_request_worker.py  # HTTP requests
│   └── condition_worker.py  # Condition evaluation
└── services/           # Supporting services
    ├── expression_resolver.py  # Expression resolution
    └── execution_tracker.py  # Database state tracking
```

## Components

### 1. Workers (app/orchestration/workers/)

All workers extend `BaseWorker` which provides:
- Error handling
- Logging
- Input validation
- Output formatting
- Retry support

#### ExtractionWorker
- **Task Name**: `document_extraction`
- **Purpose**: Extract structured data from documents using VLLM
- **Input**:
  - `document_id` (str): Document ID
  - `schema` (dict): JSON schema for extraction
  - `provider` (str): VLLM provider ("google", "openai", "deepseek")
  - `model` (str, optional): Model name
- **Output**:
  - `extracted_data`: Extracted structured data
  - `pages_processed`: Number of pages
  - `total_tokens`: Token usage

#### PythonWorker
- **Task Name**: `python_runner`
- **Purpose**: Execute Python code in secure Docker sandbox
- **Security Features**:
  - Network isolation (no external access)
  - Memory limit: 256MB
  - CPU limit: 50% of one core
  - Read-only filesystem
  - Non-root user execution
  - Automatic container cleanup
- **Input**:
  - `code` (str): Python code to execute
  - `input_data` (dict): Data available as `input_data` variable
  - `timeout` (int): Timeout in seconds (default: 30, max: 300)
- **Output**:
  - `result`: Return value from script
  - `stdout`: Standard output
  - `stderr`: Standard error

#### HttpRequestWorker
- **Task Name**: `http_request`
- **Purpose**: Execute HTTP requests with retry logic
- **Input**:
  - `url` (str): Target URL
  - `method` (str): HTTP method (GET, POST, PUT, DELETE, PATCH)
  - `headers` (dict): Request headers
  - `body` (dict): Request body
  - `timeout` (int): Timeout in seconds (default: 30)
- **Output**:
  - `status_code`: HTTP status code
  - `headers`: Response headers
  - `body`: Response body (parsed JSON or text)
  - `success`: Boolean (true if 2xx status)

#### ConditionWorker
- **Task Name**: `condition_evaluator`
- **Purpose**: Evaluate conditional expressions for If nodes
- **Supported Operators**:
  - Comparison: `==`, `!=`, `<`, `<=`, `>`, `>=`
  - Logical: `and`, `or`, `not`
  - Membership: `in`, `not in`
  - String: `contains`, `startswith`, `endswith`
- **Input**:
  - `condition` (str): Condition expression
  - `context` (dict): Variables for evaluation
- **Output**:
  - `result` (bool): Evaluation result
  - `condition`: The evaluated condition

**Example conditions**:
```python
"status == 'completed'"
"count > 10"
"name in ['Alice', 'Bob']"
"message contains 'error'"
"status == 'active' and count > 5"
```

### 2. Expression Resolver (app/orchestration/services/expression_resolver.py)

Resolves expressions in workflow node inputs.

**Expression Syntax**: `{{$("NodeName").path.to.field}}`

**Features**:
- Nested path traversal: `{{$("Node").data.items[0].total}}`
- Array indexing: `{{$("Node").results[2].value}}`
- Multiple expressions in strings
- Type-safe resolution (returns actual values, not strings)
- Security: No eval() or exec(), pure string parsing

**Example**:
```python
resolver = ExpressionResolver(node_outputs={
    "ExtractNode": {
        "data": {
            "invoice_number": "INV-001",
            "total": 1500.00
        }
    }
})

# Resolve single expression
result = resolver.resolve("{{$('ExtractNode').data.total}}")  # Returns: 1500.00

# Resolve in string
result = resolver.resolve("Invoice {{$('ExtractNode').data.invoice_number}} total: ${{$('ExtractNode').data.total}}")
# Returns: "Invoice INV-001 total: $1500.00"

# Resolve complex structures
config = {
    "url": "https://api.example.com/invoice/{{$('ExtractNode').data.invoice_number}}",
    "amount": "{{$('ExtractNode').data.total}}"
}
resolved = resolver.resolve(config)
# Returns: {
#   "url": "https://api.example.com/invoice/INV-001",
#   "amount": 1500.00
# }
```

### 3. Execution Tracker (app/orchestration/services/execution_tracker.py)

Tracks workflow execution state in database.

**Methods**:
- `start_workflow_execution()`: Create new execution
- `complete_workflow_execution()`: Mark workflow as done
- `start_node_execution()`: Create node execution
- `complete_node_execution()`: Mark node as done
- `get_execution_state()`: Get current state
- `get_node_outputs()`: Get outputs for expression resolution

**Example**:
```python
from app.orchestration.services.execution_tracker import ExecutionTracker

tracker = ExecutionTracker(db)

# Start workflow
execution = tracker.start_workflow_execution(
    workflow_id="wf_123",
    tenant_id="tenant_1",
    trigger_data={"documentId": "doc_456"}
)

# Track node execution
node_exec = tracker.start_node_execution(
    execution_id=execution.id,
    node_id="extract_node",
    conductor_task_id="task_abc",
    input_data={"documentId": "doc_456"}
)

# Complete node
tracker.complete_node_execution(
    conductor_task_id="task_abc",
    status=WorkflowNodeStatus.COMPLETED,
    output_data={"extracted_data": {...}}
)

# Get outputs for next node
node_outputs = tracker.get_node_outputs(execution.id)
# Use with ExpressionResolver to resolve expressions
```

### 4. Workflow Translator (app/orchestration/conductor/translator.py)

Translates frontend workflow definitions to Conductor format.

**Node Type Mapping**:
- `HttpTrigger` → Workflow input (not a task)
- `Extraction` → SIMPLE task (`document_extraction` worker)
- `PythonRunner` → SIMPLE task (`python_runner` worker)
- `HttpRequest` → HTTP task
- `If` → SWITCH task

**Example**:
```python
from app.orchestration.conductor.translator import WorkflowTranslator

translator = WorkflowTranslator()

frontend_workflow = {
    "nodes": [
        {
            "id": "trigger_1",
            "type": "HttpTrigger",
            "data": {"inputs": {"documentId": "string"}}
        },
        {
            "id": "extract_1",
            "type": "Extraction",
            "data": {
                "inputs": {
                    "documentId": "{{$('trigger_1').documentId}}",
                    "schema": {...},
                    "provider": "google"
                }
            }
        }
    ],
    "edges": [
        {"source": "trigger_1", "target": "extract_1"}
    ]
}

conductor_workflow = translator.translate(
    workflow_definition=frontend_workflow,
    workflow_name="invoice_processing",
    workflow_version=1
)

# Returns Conductor workflow definition ready for registration
```

### 5. Task Definitions (app/orchestration/conductor/task_definitions.py)

Provides templates for Conductor task definitions.

**Example**:
```python
from app.orchestration.conductor.task_definitions import TaskDefinitionBuilder

# Get all task definitions for registration
task_defs = TaskDefinitionBuilder.build_all_task_definitions()

# Or build individual definitions
extraction_task = TaskDefinitionBuilder.build_extraction_task()
python_task = TaskDefinitionBuilder.build_python_runner_task()
```

**Task Configuration**:
- **Extraction**: 3 retries, 5min timeout, 10 concurrent
- **Python Runner**: 2 retries, 6min timeout, 5 concurrent (Docker limit)
- **HTTP Request**: 3 retries with exponential backoff, 2min timeout
- **Condition Evaluator**: 1 retry, 10sec timeout, 100 concurrent

## Usage Examples

### Starting Workers

```python
from conductor.client.automator.task_handler import TaskHandler
from conductor.client.configuration.configuration import Configuration
from app.orchestration.workers import (
    ExtractionWorker,
    PythonWorker,
    HttpRequestWorker,
    ConditionWorker
)

# Configure Conductor client
config = Configuration(
    server_api_url="http://localhost:8080/api",
    debug=True
)

# Initialize workers
workers = [
    ExtractionWorker(),
    PythonWorker(),
    HttpRequestWorker(),
    ConditionWorker(),
]

# Start task handler
with TaskHandler(workers, config) as task_handler:
    task_handler.start()
```

### Registering Tasks and Workflows

```python
from app.services.conductor_client import ConductorClient
from app.orchestration.conductor.task_definitions import TaskDefinitionBuilder
from app.orchestration.conductor.translator import WorkflowTranslator

client = ConductorClient()

# Register task definitions
task_defs = TaskDefinitionBuilder.build_all_task_definitions()
for task_def in task_defs:
    client.register_task_def(task_def)

# Translate and register workflow
translator = WorkflowTranslator()
conductor_workflow = translator.translate(frontend_workflow, "my_workflow")
client.register_workflow_def(conductor_workflow)
```

### Executing Workflows

```python
from app.services.conductor_client import ConductorClient
from app.orchestration.services.execution_tracker import ExecutionTracker

client = ConductorClient()
tracker = ExecutionTracker(db)

# Start workflow execution
execution = tracker.start_workflow_execution(
    workflow_id=workflow.id,
    tenant_id=current_user.tenant_id,
    trigger_data={"documentId": "doc_123"}
)

# Start Conductor workflow
conductor_execution_id = client.start_workflow(
    workflow_name="my_workflow",
    workflow_input={"documentId": "doc_123"}
)

# Poll for status
status = client.get_workflow_status(conductor_execution_id)

# Get results
if status == "COMPLETED":
    results = client.get_workflow_results(conductor_execution_id)
    tracker.complete_workflow_execution(
        execution_id=execution.id,
        status=WorkflowExecutionStatus.COMPLETED,
        output_data=results
    )
```

## Security Considerations

### Python Worker Security

The Python worker uses **Docker sandboxing** with strict security measures:

1. **Network Isolation**: `network_mode="none"` - No external network access
2. **Resource Limits**:
   - Memory: 256MB limit
   - CPU: 50% of one core
   - Timeout: Configurable (max 5 minutes)
3. **Filesystem**: Read-only filesystem
4. **User**: Runs as `nobody` (non-root)
5. **Privileges**: `no-new-privileges` security option
6. **Cleanup**: Automatic container removal

**Docker API Configuration**:
```python
container = docker_client.containers.run(
    image="python:3.11-slim",
    command=["python", "-c", script],
    network_mode="none",           # No network
    mem_limit="256m",              # Memory limit
    cpu_quota=50000,               # CPU limit (50%)
    security_opt=["no-new-privileges"],
    read_only=True,                # Read-only FS
    user="nobody",                 # Non-root user
    remove=False,                  # Manual cleanup
    detach=False,                  # Wait for completion
)
```

### Expression Resolver Security

- **No eval() or exec()**: Pure string parsing
- **Whitelist-based**: Only dot notation and array indexing
- **Type-safe**: Returns actual types, not strings
- **Validation**: Missing paths return None, not errors

### Condition Worker Security

- **No eval()**: Safe expression parsing
- **Limited operators**: Predefined set only
- **No arbitrary code**: Cannot execute Python
- **Input validation**: Strict type checking

## Testing

### Unit Tests

```python
# Test expression resolver
def test_expression_resolver():
    resolver = ExpressionResolver({
        "Node1": {"data": {"value": 42}}
    })
    assert resolver.resolve("{{$('Node1').data.value}}") == 42

# Test condition worker
def test_condition_worker():
    worker = ConditionWorker()
    result = worker.execute_task({
        "condition": "count > 10",
        "context": {"count": 15}
    })
    assert result["result"] == True

# Test workflow translator
def test_workflow_translator():
    translator = WorkflowTranslator()
    conductor_wf = translator.translate(frontend_workflow, "test")
    assert conductor_wf["schemaVersion"] == 2
    assert len(conductor_wf["tasks"]) > 0
```

### Integration Tests

```python
# Test Python worker with Docker
def test_python_worker_execution():
    worker = PythonWorker()
    result = worker.execute_task({
        "code": "result = input_data['x'] + input_data['y']",
        "input_data": {"x": 10, "y": 20}
    })
    assert result["result"] == 30

# Test extraction worker
def test_extraction_worker():
    worker = ExtractionWorker()
    result = worker.execute_task({
        "document_id": "doc_123",
        "schema": invoice_schema,
        "provider": "google"
    })
    assert "extracted_data" in result
```

## Dependencies

- **conductor-python**: Conductor Python SDK
- **docker**: Docker Python SDK for sandbox execution
- **requests**: HTTP client for HTTP request worker
- **SQLAlchemy**: Database ORM for execution tracking

## Deployment

### Docker Compose

```yaml
services:
  conductor-server:
    image: conductor:server
    ports:
      - "8080:8080"
    environment:
      - DB_URL=postgresql://...
      - REDIS_URL=redis://...

  workflow-workers:
    build: .
    command: python -m app.orchestration.start_workers
    depends_on:
      - conductor-server
      - postgres
      - redis
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # For Python worker
```

### Environment Variables

```bash
# Conductor server
CONDUCTOR_SERVER_URL=http://localhost:8080/api

# Docker (for Python worker)
DOCKER_HOST=unix:///var/run/docker.sock

# Database
DATABASE_URL=postgresql://...

# VLLM (for extraction worker)
GOOGLE_API_KEY=...
OPENAI_API_KEY=...
```

## Troubleshooting

### Docker Permission Issues

If Python worker fails with Docker permission errors:

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Or run workers as root (not recommended for production)
```

### Conductor Connection Issues

If workers can't connect to Conductor:

```python
# Check Conductor server URL
curl http://localhost:8080/health

# Verify network connectivity
ping conductor-server
```

### Task Timeout Issues

If tasks are timing out:

1. Check task definition timeout settings
2. Increase `timeoutSeconds` and `responseTimeoutSeconds`
3. Monitor worker logs for execution time
4. Consider adding more workers for parallel processing

## Performance Optimization

### Worker Scaling

- Run multiple worker instances for parallel processing
- Scale based on queue depth metrics
- Use container orchestration (Kubernetes) for auto-scaling

### Resource Optimization

- Adjust Docker resource limits for Python worker
- Tune Conductor task queue settings
- Monitor memory usage and adjust limits

### Caching

- Cache Docker images for Python worker
- Cache VLLM responses for repeated extractions
- Use Redis for expression resolution cache

## License

Internal use only - AI Document Processing Platform
