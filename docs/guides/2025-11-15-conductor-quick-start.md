# Conductor Integration - Quick Start Guide

**Date:** 2025-11-15
**Audience:** Development Team
**Related:** [Full Architecture Document](../architecture/2025-11-15-conductor-integration-architecture.md)

## TL;DR

This guide provides a quick reference for implementing Netflix Conductor integration into the AI Document Processing platform. For comprehensive architecture details, see the [full architecture document](../architecture/2025-11-15-conductor-integration-architecture.md).

---

## 1. Setup Conductor Server (5 minutes)

### Using Docker Compose

Create `docker-compose.conductor.yml`:

```yaml
version: '3.8'

services:
  conductor-server:
    image: conductor:server
    container_name: conductor-server
    ports:
      - "8080:8080"  # API
      - "5000:5000"  # UI
    environment:
      - DB=postgres
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=conductor
      - POSTGRES_USER=conductor
      - POSTGRES_PASSWORD=conductor_password
    depends_on:
      - postgres-conductor
    networks:
      - conductor-network

  postgres-conductor:
    image: postgres:15
    container_name: postgres-conductor
    environment:
      - POSTGRES_DB=conductor
      - POSTGRES_USER=conductor
      - POSTGRES_PASSWORD=conductor_password
    volumes:
      - conductor-postgres-data:/var/lib/postgresql/data
    networks:
      - conductor-network

volumes:
  conductor-postgres-data:

networks:
  conductor-network:
    driver: bridge
```

**Start Conductor:**

```bash
docker-compose -f docker-compose.conductor.yml up -d

# Verify
curl http://localhost:8080/health
# Expected: {"healthy": true}

# Access UI
open http://localhost:5000
```

---

## 2. Install Dependencies

```bash
# Add to pyproject.toml
uv add conductor-python
uv add docker
uv add jsonpath-ng

# Sync dependencies
uv sync
```

---

## 3. Create Directory Structure

```bash
mkdir -p app/orchestration/{conductor,workers,services,models,api}

touch app/orchestration/__init__.py
touch app/orchestration/conductor/{__init__.py,client.py,translator.py,task_definitions.py}
touch app/orchestration/workers/{__init__.py,base_worker.py,extraction_worker.py,python_worker.py,http_request_worker.py,condition_worker.py,worker_manager.py}
touch app/orchestration/services/{__init__.py,expression_resolver.py,docker_manager.py,execution_tracker.py}
touch app/orchestration/models/{__init__.py,workflow_execution.py,task_execution.py}
touch app/orchestration/api/{__init__.py,workflows.py,schemas.py}
```

---

## 4. Configuration Updates

**File:** `app/core/config.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Conductor settings
    conductor_server_url: str = "http://localhost:8080/api"
    conductor_ui_url: str = "http://localhost:5000"
    conductor_worker_poll_interval: float = 1.0
    conductor_worker_thread_count: int = 10

    # Docker sandbox settings
    docker_python_image: str = "python:3.11-slim"
    docker_execution_timeout: int = 30
    docker_memory_limit: str = "128m"
    docker_cpu_limit: float = 0.5
```

---

## 5. Create Database Models

**File:** `app/orchestration/models/workflow_execution.py`

```python
from sqlalchemy import Column, String, JSON, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import uuid
from datetime import datetime
import enum

class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    workflow_id = Column(String, nullable=False)
    conductor_workflow_id = Column(String, nullable=False)
    status = Column(SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING)
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Migration:**

```bash
alembic revision -m "Add workflow execution tables"
# Edit migration file...
alembic upgrade head
```

---

## 6. Implement Core Components

### 6.1 Conductor Client Wrapper

**File:** `app/orchestration/conductor/client.py`

```python
from conductor.client.configuration.configuration import Configuration
from conductor.client.http.api_client import ApiClient
from conductor.client.http.api.workflow_resource_api import WorkflowResourceApi
from conductor.client.http.api.metadata_resource_api import MetadataResourceApi
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class ConductorClient:
    def __init__(self):
        self.configuration = Configuration(
            server_api_url=settings.conductor_server_url,
            debug=settings.debug
        )
        self.api_client = ApiClient(configuration=self.configuration)
        self.workflow_api = WorkflowResourceApi(api_client=self.api_client)
        self.metadata_api = MetadataResourceApi(api_client=self.api_client)

    def register_workflow(self, workflow_def: dict, overwrite: bool = True):
        """Register workflow definition"""
        from conductor.client.http.models import WorkflowDef
        workflow_obj = WorkflowDef(**workflow_def)
        self.metadata_api.create(body=workflow_obj, overwrite=overwrite)
        logger.info(f"Registered workflow: {workflow_def['name']}")

    def start_workflow(self, workflow_name: str, workflow_input: dict, version: int = 1) -> str:
        """Start workflow execution"""
        from conductor.client.http.models import StartWorkflowRequest
        request = StartWorkflowRequest(
            name=workflow_name,
            version=version,
            input=workflow_input
        )
        workflow_id = self.workflow_api.start_workflow(body=request)
        logger.info(f"Started workflow {workflow_name}: {workflow_id}")
        return workflow_id

    def get_workflow_status(self, workflow_id: str) -> dict:
        """Get workflow execution status"""
        workflow = self.workflow_api.get_execution_status(
            workflow_id=workflow_id,
            include_tasks=True
        )
        return {
            'workflow_id': workflow.workflow_id,
            'status': workflow.status,
            'output': workflow.output
        }
```

### 6.2 Base Worker

**File:** `app/orchestration/workers/base_worker.py`

```python
from abc import ABC, abstractmethod
from conductor.client.worker.worker_interface import WorkerInterface
from conductor.client.http.models import Task, TaskResult
from app.db.session import SessionLocal
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaseWorkflowWorker(WorkerInterface, ABC):
    def __init__(self, task_def_name: str):
        self.task_def_name = task_def_name

    def get_task_def_name(self) -> str:
        return self.task_def_name

    def execute(self, task: Task) -> TaskResult:
        task_result = self.get_task_result_from_task(task)
        db = SessionLocal()

        try:
            tenant_id = task.input_data.get('tenantId')
            if not tenant_id:
                raise ValueError("Missing tenantId")

            output_data = self.execute_node(
                input_data=task.input_data,
                db=db,
                tenant_id=tenant_id
            )

            task_result.add_output_data('result', output_data)
            task_result.status = 'COMPLETED'

        except Exception as e:
            logger.error(f"Task failed: {str(e)}")
            task_result.status = 'FAILED'
            task_result.reason_for_incompletion = str(e)

        finally:
            db.close()

        return task_result

    @abstractmethod
    def execute_node(self, input_data: Dict[str, Any], db, tenant_id: str) -> Dict[str, Any]:
        pass
```

### 6.3 Extraction Worker

**File:** `app/orchestration/workers/extraction_worker.py`

```python
from app.orchestration.workers.base_worker import BaseWorkflowWorker
from app.services.vllm_service import VLLMService
from typing import Dict, Any

class ExtractionWorker(BaseWorkflowWorker):
    def __init__(self):
        super().__init__(task_def_name="extraction_task")
        self.vllm_service = VLLMService()

    def execute_node(self, input_data: Dict[str, Any], db, tenant_id: str) -> Dict[str, Any]:
        from app.models.schema import Schema

        schema_id = input_data.get('schemaId')
        prompt = input_data.get('prompt')

        schema = db.query(Schema).filter(
            Schema.id == schema_id,
            Schema.tenant_id == tenant_id
        ).first()

        if not schema:
            raise ValueError(f"Schema {schema_id} not found")

        # Get file content (simplified - add file source logic)
        file_content = self._get_file_content(input_data)

        # Call VLLM service
        result = self.vllm_service.extract_from_image(
            image_data=file_content,
            extraction_schema=schema.schema_definition,
            prompt=prompt
        )

        return {
            'result': result['data'],
            'metadata': {
                'schemaId': schema_id,
                'tokensUsed': result.get('tokens_used', 0)
            }
        }

    def _get_file_content(self, input_data: dict) -> bytes:
        # TODO: Implement file source logic
        pass
```

---

## 7. Start Workers

**File:** `app/orchestration/workers/worker_manager.py`

```python
from conductor.client.automator.task_handler import TaskHandler
from conductor.client.configuration.configuration import Configuration
from app.orchestration.workers.extraction_worker import ExtractionWorker
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def start_workers():
    configuration = Configuration(
        server_api_url=settings.conductor_server_url
    )

    workers = [
        ExtractionWorker(),
        # Add other workers...
    ]

    task_handler = TaskHandler(
        workers=workers,
        configuration=configuration
    )

    logger.info("Starting Conductor workers...")
    task_handler.start_processes()

if __name__ == '__main__':
    start_workers()
```

**Run workers:**

```bash
python -m app.orchestration.workers.worker_manager
```

---

## 8. Test Workflow Execution

### 8.1 Register Test Workflow

```python
from app.orchestration.conductor.client import ConductorClient

client = ConductorClient()

workflow_def = {
    "name": "test_extraction",
    "version": 1,
    "tasks": [
        {
            "name": "extraction_task",
            "taskReferenceName": "extract_1",
            "type": "SIMPLE",
            "inputParameters": {
                "schemaId": "${workflow.input.schemaId}",
                "prompt": "${workflow.input.prompt}",
                "tenantId": "${workflow.input.tenantId}"
            }
        }
    ],
    "inputParameters": ["schemaId", "prompt", "tenantId"],
    "outputParameters": {
        "result": "${extract_1.output.result}"
    },
    "schemaVersion": 2
}

client.register_workflow(workflow_def)
```

### 8.2 Execute Workflow

```python
workflow_id = client.start_workflow(
    workflow_name="test_extraction",
    workflow_input={
        "schemaId": "schema_123",
        "prompt": "Extract invoice data",
        "tenantId": "tenant_456"
    }
)

print(f"Workflow started: {workflow_id}")

# Check status
import time
time.sleep(5)
status = client.get_workflow_status(workflow_id)
print(f"Status: {status['status']}")
print(f"Output: {status['output']}")
```

---

## 9. Common Operations

### Check Worker Status

```bash
# In Conductor UI
open http://localhost:5000

# Navigate to "Task Queues" to see registered workers
```

### View Workflow Executions

```bash
# In Conductor UI
# Navigate to "Workflow Executions"
# Filter by workflow name or status
```

### Debug Failed Tasks

```bash
# In Conductor UI
# Click on failed workflow execution
# View task details and error messages
```

### Manually Complete Stuck Tasks

```python
from app.orchestration.conductor.client import ConductorClient

client = ConductorClient()

# Get task details
workflow_status = client.get_workflow_status(workflow_id)

# Find stuck task
for task in workflow_status['tasks']:
    if task['status'] == 'IN_PROGRESS':
        print(f"Stuck task: {task['task_id']}")
```

---

## 10. Testing Checklist

- [ ] Conductor server is running (`http://localhost:8080/health`)
- [ ] Workers are registered (check Conductor UI)
- [ ] Database migrations applied
- [ ] Can register workflow definition
- [ ] Can start workflow execution
- [ ] Workers poll and execute tasks
- [ ] Task results are persisted
- [ ] Workflow completes successfully
- [ ] Error handling works (try invalid input)
- [ ] Tenant isolation enforced

---

## 11. Troubleshooting

### Workers not polling tasks

**Check:**
```bash
# Verify Conductor server is accessible
curl http://localhost:8080/api/metadata/taskdefs

# Check worker logs
# Look for "Starting Conductor workers..." message
```

**Solution:**
- Ensure `CONDUCTOR_SERVER_URL` is correct in `.env`
- Check network connectivity between worker and Conductor server
- Verify task definitions are registered

### Workflow stuck in RUNNING state

**Check:**
```bash
# In Conductor UI, view workflow execution
# Look for tasks in IN_PROGRESS state
```

**Solution:**
- Check worker logs for errors
- Verify workers are running
- Check database connectivity in workers
- Review task timeout configuration

### Expression resolution errors

**Check worker logs:**
```
ERROR: Node 'extract_1' not found in execution context
```

**Solution:**
- Verify expression syntax: `{{$("NodeName").data.field}}`
- Check node ID matches exactly
- Ensure previous task completed successfully

---

## 12. Next Steps

1. **Implement Remaining Workers**
   - Python worker (Docker sandbox)
   - HTTP request worker
   - Condition worker

2. **Add Workflow Translation**
   - Frontend JSON → Conductor workflow
   - Handle conditional branching
   - Expression preservation

3. **Build API Endpoints**
   - `POST /api/v1/workflows/{id}/execute`
   - `POST /api/v1/workflows/test-node`
   - `GET /api/v1/executions/{id}`

4. **Add Expression Resolution**
   - Implement `ExpressionResolver`
   - Integrate with workers
   - Test complex expressions

5. **Implement Docker Sandbox**
   - `DockerManager` service
   - Security hardening
   - Resource limits

---

## 13. Key Resources

- **Full Architecture:** [2025-11-15-conductor-integration-architecture.md](../architecture/2025-11-15-conductor-integration-architecture.md)
- **Conductor Docs:** https://conductor.netflix.com
- **Python SDK Docs:** https://github.com/conductor-oss/conductor-python
- **Conductor UI:** http://localhost:5000 (when running)

---

## 14. Code Snippets Cheat Sheet

### Register Task Definition

```python
task_def = {
    "name": "my_task",
    "retryCount": 3,
    "retryLogic": "EXPONENTIAL_BACKOFF",
    "retryDelaySeconds": 5,
    "timeoutSeconds": 300,
    "responseTimeoutSeconds": 280
}

client.metadata_api.register_task_def([task_def])
```

### Create SWITCH Task (Conditional)

```python
{
    "name": "condition_check",
    "taskReferenceName": "if_1",
    "type": "SWITCH",
    "evaluatorType": "javascript",
    "expression": "$.total > 1000",
    "inputParameters": {
        "total": "${extract_1.output.result.total}"
    },
    "decisionCases": {
        "true": [
            {"name": "high_value_task", "taskReferenceName": "high_value", "type": "SIMPLE"}
        ],
        "false": [
            {"name": "low_value_task", "taskReferenceName": "low_value", "type": "SIMPLE"}
        ]
    }
}
```

### Access Previous Task Output

```python
# In workflow definition
"inputParameters": {
    "extractedData": "${extract_1.output.result}",
    "total": "${extract_1.output.result.total}",
    "items": "${extract_1.output.result.items[0]}"
}
```

---

**Last Updated:** 2025-11-15
**Version:** 1.0
