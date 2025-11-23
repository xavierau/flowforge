# Orchestration Layer - Quick Start Guide

## Installation

```bash
# Install dependencies
pip install conductor-python docker requests

# Or with uv
uv pip install conductor-python docker requests
```

## Running Workers

### Local Development

```bash
# Start Conductor server (Docker)
docker run -d -p 8080:8080 conductor:server

# Start workers
python -m app.orchestration.start_workers

# Or with environment variables
CONDUCTOR_SERVER_URL=http://localhost:8080/api \
WORKER_THREADS=4 \
python -m app.orchestration.start_workers
```

### Production

```bash
# Use systemd service
sudo systemctl start conductor-workers

# Or Docker Compose
docker-compose up workflow-workers
```

## Registering Tasks

```python
from app.services.conductor_client import ConductorClient
from app.orchestration.conductor.task_definitions import TaskDefinitionBuilder

client = ConductorClient()

# Register all tasks
task_defs = TaskDefinitionBuilder.build_all_task_definitions()
for task_def in task_defs:
    client.register_task_def(task_def)
    print(f"Registered task: {task_def['name']}")
```

## Creating Workflows

```python
from app.orchestration.conductor.translator import WorkflowTranslator

translator = WorkflowTranslator()

# Frontend workflow definition
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
                    "schema": {"type": "object", "properties": {...}},
                    "provider": "google"
                }
            }
        }
    ],
    "edges": [
        {"source": "trigger_1", "target": "extract_1"}
    ]
}

# Translate to Conductor format
conductor_workflow = translator.translate(
    workflow_definition=frontend_workflow,
    workflow_name="invoice_extraction",
    workflow_version=1
)

# Register with Conductor
client.register_workflow_def(conductor_workflow)
```

## Executing Workflows

```python
from app.services.conductor_client import ConductorClient
from app.orchestration.services.execution_tracker import ExecutionTracker

client = ConductorClient()
tracker = ExecutionTracker(db)

# Create execution record
execution = tracker.start_workflow_execution(
    workflow_id=workflow.id,
    tenant_id=current_user.tenant_id,
    trigger_data={"documentId": "doc_123"}
)

# Start Conductor workflow
conductor_id = client.start_workflow(
    workflow_name="invoice_extraction",
    workflow_input={"documentId": "doc_123"}
)

# Poll for completion
import time
while True:
    status = client.get_workflow_status(conductor_id)

    if status == "COMPLETED":
        results = client.get_workflow_results(conductor_id)
        tracker.complete_workflow_execution(
            execution_id=execution.id,
            status=WorkflowExecutionStatus.COMPLETED,
            output_data=results
        )
        break
    elif status == "FAILED":
        tracker.complete_workflow_execution(
            execution_id=execution.id,
            status=WorkflowExecutionStatus.FAILED,
            error="Workflow execution failed"
        )
        break

    time.sleep(2)
```

## Using Expression Resolver

```python
from app.orchestration.services.expression_resolver import ExpressionResolver

# Node outputs from previous executions
node_outputs = {
    "extract_1": {
        "data": {
            "invoice_number": "INV-001",
            "total": 1500.00,
            "items": [
                {"name": "Item 1", "price": 500},
                {"name": "Item 2", "price": 1000}
            ]
        }
    }
}

resolver = ExpressionResolver(node_outputs)

# Resolve single value
invoice_num = resolver.resolve("{{$('extract_1').data.invoice_number}}")
# Result: "INV-001"

# Resolve in string
message = resolver.resolve("Invoice {{$('extract_1').data.invoice_number}} total: ${{$('extract_1').data.total}}")
# Result: "Invoice INV-001 total: $1500.00"

# Resolve array item
first_item = resolver.resolve("{{$('extract_1').data.items[0].name}}")
# Result: "Item 1"

# Resolve entire config
config = {
    "url": "https://api.example.com/invoice/{{$('extract_1').data.invoice_number}}",
    "amount": "{{$('extract_1').data.total}}",
    "items": "{{$('extract_1').data.items}}"
}
resolved = resolver.resolve(config)
# Result: {
#   "url": "https://api.example.com/invoice/INV-001",
#   "amount": 1500.00,
#   "items": [...]
# }
```

## Worker Examples

### Extraction Worker

```python
# Input
{
    "document_id": "doc_123",
    "schema": {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "total": {"type": "number"}
        }
    },
    "provider": "google",
    "model": "gemini-2.5-flash"
}

# Output
{
    "extracted_data": {
        "invoice_number": "INV-001",
        "total": 1500.00
    },
    "pages_processed": 1,
    "total_tokens": 2500,
    "input_tokens": 2000,
    "output_tokens": 500
}
```

### Python Worker

```python
# Input
{
    "code": """
result = {
    'sum': input_data['a'] + input_data['b'],
    'product': input_data['a'] * input_data['b']
}
""",
    "input_data": {"a": 10, "b": 20},
    "timeout": 30
}

# Output
{
    "result": {"sum": 30, "product": 200},
    "stdout": "",
    "stderr": ""
}
```

### HTTP Request Worker

```python
# Input
{
    "url": "https://api.example.com/data",
    "method": "POST",
    "headers": {"Authorization": "Bearer token123"},
    "body": {"key": "value"},
    "timeout": 30
}

# Output
{
    "status_code": 200,
    "headers": {"content-type": "application/json"},
    "body": {"result": "success"},
    "success": true
}
```

### Condition Worker

```python
# Input
{
    "condition": "status == 'completed' and total > 1000",
    "context": {
        "status": "completed",
        "total": 1500
    }
}

# Output
{
    "result": true,
    "condition": "status == 'completed' and total > 1000"
}
```

## Monitoring

### Worker Health

```bash
# Check worker logs
tail -f logs/conductor_workers.log

# Check Conductor task queue
curl http://localhost:8080/api/tasks/queue/sizes
```

### Execution Tracking

```python
from app.orchestration.services.execution_tracker import ExecutionTracker

tracker = ExecutionTracker(db)

# Get execution state
state = tracker.get_execution_state(execution_id)
print(f"Status: {state['status']}")
print(f"Node outputs: {state['node_outputs']}")

# Get node outputs for expression resolution
node_outputs = tracker.get_node_outputs(execution_id)
resolver = ExpressionResolver(node_outputs)
```

## Troubleshooting

### Workers Not Starting

```bash
# Check Conductor server
curl http://localhost:8080/health

# Check Docker (for Python worker)
docker ps

# Check logs
tail -f logs/conductor_workers.log
```

### Task Execution Failures

```python
# Check task status
task_status = client.get_task_status(task_id)
print(task_status['status'])
print(task_status.get('reasonForIncompletion'))

# Check workflow execution
workflow_status = client.get_workflow_status(workflow_id)
print(workflow_status)
```

### Docker Permission Issues

```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Test Docker access
docker ps
```

## Next Steps

1. **Read Full Documentation**: See `README.md` for complete architecture
2. **Review Workers**: Check `app/orchestration/workers/` for implementation
3. **Test Workflows**: Create test workflows in frontend builder
4. **Monitor Production**: Set up alerts and monitoring
5. **Scale Workers**: Add more worker instances for production load

## Support

- **Documentation**: `app/orchestration/README.md`
- **Architecture**: `docs/architecture/2025-11-15-conductor-integration-architecture.md`
- **API Reference**: Conductor Python SDK documentation
