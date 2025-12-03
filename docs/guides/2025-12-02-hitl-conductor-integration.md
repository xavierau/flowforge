# HITL Conductor Integration Guide

This guide documents the integration between the Human-in-the-Loop (HITL) review system and Netflix Conductor OSS for workflow orchestration.

## Overview

The HITL Conductor integration enables workflows to pause for human review when AI extraction confidence is below a configurable threshold. This is implemented using Conductor's task callback pattern where:

1. **HumanReviewWorker** picks up HUMAN_REVIEW tasks from Conductor
2. Worker creates a **ReviewRequest** in the database with Conductor task/workflow IDs
3. Worker returns **IN_PROGRESS** status (workflow pauses)
4. Human reviewer submits corrections via the **Review API**
5. **ConductorHITLService** completes the Conductor task with corrected data
6. Workflow resumes with the human-verified data

## Architecture

```
+------------------+     +------------------+     +------------------+
|   Conductor      |     | HumanReview      |     |  ReviewRequest   |
|   Workflow       |---->| Worker           |---->|  Database        |
+------------------+     +------------------+     +------------------+
        |                                                  |
        | (paused)                                        |
        |                                                  v
        |                                          +------------------+
        |                                          |  Review UI       |
        |                                          |  (Human)         |
        |                                          +------------------+
        |                                                  |
        |                                                  v
        |                                          +------------------+
        |                                          |  Review API      |
        |                                          +------------------+
        |                                                  |
        v                                                  v
+------------------+     +------------------+     +------------------+
|   Conductor      |<----| ConductorHITL    |<----|  HITLService     |
|   (resumed)      |     | Service          |     |                  |
+------------------+     +------------------+     +------------------+
```

## Key Components

### 1. HumanReviewWorker

**Location:** `app/orchestration/workers/human_review_worker.py`

The HumanReviewWorker handles HUMAN_REVIEW tasks from Conductor. It differs from regular workers by returning IN_PROGRESS status instead of COMPLETED.

**Key Features:**
- Overrides `execute()` method to return IN_PROGRESS status
- Creates ReviewRequest with Conductor task/workflow IDs
- Determines priority based on confidence score
- Calculates SLA deadline based on priority

**Input Parameters:**
```python
{
    "extraction_job_id": "uuid",     # Required: Extraction job to review
    "confidence_score": 0.45,         # Required: AI confidence (0.0-1.0)
    "trigger_reason": "low_confidence",  # Optional: Why review needed
    "priority": "high",               # Optional: Review priority
    "instructions": "Check totals",   # Optional: Instructions for reviewer
}
```

**Output Parameters (on IN_PROGRESS):**
```python
{
    "review_request_id": "uuid",      # Created review request
    "priority": "high",               # Assigned priority
    "sla_deadline": "2025-12-02T16:00:00Z",  # SLA deadline
    "message": "Review request created",
    "callback_after_seconds": 14400,  # 4 hour timeout
}
```

### 2. ConductorHITLService

**Location:** `app/services/conductor_hitl_service.py`

Handles completing Conductor tasks when human review is submitted.

**Key Features:**
- Retry logic with exponential backoff
- Session-based HTTP client with automatic retries
- Quality score calculation
- Workflow management (terminate, restart)

**Main Methods:**

```python
# Complete task after review
result = conductor_hitl_service.complete_conductor_task(
    review_id=review_request.id,
    db=db_session,
    fail_workflow_on_error=False
)

# Check workflow status
status = conductor_hitl_service.get_workflow_status(workflow_id)

# Get pending human tasks
tasks = conductor_hitl_service.get_pending_human_tasks(workflow_id)
```

### 3. Task Definitions

**Location:** `app/orchestration/conductor/task_definitions.py`

HITL-related task definitions:

```python
# HUMAN_REVIEW task
{
    "name": "HUMAN_REVIEW",
    "description": "Human-in-the-loop review task",
    "retryCount": 0,           # No retries for human tasks
    "timeoutSeconds": 14400,   # 4 hour timeout
    "timeoutPolicy": "ALERT_ONLY",  # Don't fail, just alert
    "responseTimeoutSeconds": 14400,
    "inputKeys": [
        "extraction_job_id",
        "confidence_score",
        "trigger_reason",
        "priority",
        "instructions",
    ],
    "outputKeys": [
        "review_request_id",
        "corrected_data",
        "corrections_count",
        "quality_score",
        "review_notes",
    ],
}
```

### 4. Workflow Definitions

**Location:** `app/orchestration/workflows/extraction_with_hitl.py`

Available workflows:

1. **document_extraction_with_review** - Confidence-based routing
2. **document_extraction_manual_review** - Always routes to human review
3. **batch_extraction_with_selective_review** - Batch processing
4. **configurable_extraction_with_hitl** - Fully configurable

## Workflow Integration Flow

### Step 1: Workflow Reaches HUMAN_REVIEW Task

```json
{
    "name": "HUMAN_REVIEW",
    "taskReferenceName": "human_review_task",
    "type": "SIMPLE",
    "inputParameters": {
        "extraction_job_id": "${workflow.input.extraction_job_id}",
        "confidence_score": "${extract_task.output.confidence_score}",
        "trigger_reason": "low_confidence"
    }
}
```

### Step 2: HumanReviewWorker Creates ReviewRequest

```python
# Worker creates ReviewRequest with Conductor metadata
review_request = ReviewRequest(
    tenant_id=extraction_job.tenant_id,
    extraction_job_id=extraction_job_id,
    conductor_task_id=task_id,      # Conductor task ID
    conductor_workflow_id=workflow_id,  # Conductor workflow ID
    status=ReviewRequestStatus.PENDING.value,
    priority=priority.value,
    confidence_score=confidence_score,
)

# Worker returns IN_PROGRESS
task_result.status = "IN_PROGRESS"
```

### Step 3: Workflow Pauses

The workflow pauses at the HUMAN_REVIEW task, waiting for callback.

### Step 4: Human Submits Review

```python
# Review API endpoint
@router.post("/reviews/{review_id}/submit")
async def submit_review(review_id: UUID, corrections: List[CorrectionCreate]):
    # Process corrections
    hitl_service.submit_corrections(review_id, corrections, user_id, tenant_id)

    # Complete Conductor task
    if review_request.conductor_task_id:
        conductor_hitl_service.complete_conductor_task(
            review_id=review_id,
            db=db
        )
```

### Step 5: ConductorHITLService Completes Task

```python
# Task update payload sent to Conductor
task_update = {
    "workflowInstanceId": workflow_id,
    "taskId": task_id,
    "status": "COMPLETED",
    "outputData": {
        "review_request_id": str(review_request.id),
        "corrected_data": corrected_extraction_data,
        "corrections_count": len(corrections),
        "quality_score": 0.85,
        "review_notes": "Corrected invoice total",
    }
}
```

### Step 6: Workflow Resumes

Workflow continues with `${human_review_task.output.corrected_data}` available for downstream tasks.

## Configuration

### Environment Variables

```bash
# Conductor server URL
CONDUCTOR_SERVER_URL=http://localhost:8080/api

# Enable/disable HITL worker
ENABLE_HITL_WORKER=true

# Worker configuration
WORKER_THREADS=4
WORKER_POLL_INTERVAL=1000
```

### Confidence Thresholds

Priority is determined by confidence score:

| Confidence Score | Priority | SLA |
|-----------------|----------|-----|
| < 0.30 | CRITICAL | 1 hour |
| 0.30 - 0.50 | HIGH | 2 hours |
| 0.50 - 0.60 | NORMAL | 4 hours |
| 0.60 - 0.70 | LOW | 8 hours |
| >= 0.70 | Auto-approve | N/A |

## Starting Workers

```bash
# Start all workers including HITL
python -m app.orchestration.start_workers

# Disable HITL worker
ENABLE_HITL_WORKER=false python -m app.orchestration.start_workers
```

## Registering Task Definitions

```python
from app.orchestration.conductor.task_definitions import TaskDefinitionBuilder

# Get all task definitions including HITL
task_defs = TaskDefinitionBuilder.build_all_task_definitions()

# Get only HITL task definitions
hitl_task_defs = TaskDefinitionBuilder.build_hitl_task_definitions()

# Register with Conductor
import requests
for task_def in task_defs:
    requests.post(
        f"{CONDUCTOR_URL}/metadata/taskdefs",
        json=[task_def]
    )
```

## Registering Workflow Definitions

```python
from app.orchestration.workflows import get_all_workflow_definitions

# Get all HITL workflow definitions
workflows = get_all_workflow_definitions()

# Register with Conductor
for workflow in workflows:
    requests.post(
        f"{CONDUCTOR_URL}/metadata/workflow",
        json=workflow
    )
```

## Error Handling

### Worker Errors

If HumanReviewWorker fails to create ReviewRequest:
- Task status is set to FAILED
- Workflow can be retried or manually intervened

### Conductor API Errors

ConductorHITLService handles errors gracefully:
- Automatic retries with exponential backoff
- Connection errors don't fail the review submission
- 404 errors (task not found) are logged but don't fail

### Timeout Handling

- HUMAN_REVIEW tasks use `timeoutPolicy: ALERT_ONLY`
- Workflow doesn't fail on timeout, just alerts
- SLA tracking is handled by our HITLService independently

## Monitoring

### Workflow Status

```python
# Check workflow status
status = conductor_hitl_service.get_workflow_status(workflow_id)
print(f"Status: {status['status']}")
print(f"Tasks: {status['tasks']}")
```

### Pending Human Tasks

```python
# Get all pending human tasks for a workflow
pending = conductor_hitl_service.get_pending_human_tasks(workflow_id)
for task in pending:
    print(f"Task: {task['task_id']}, Started: {task['start_time']}")
```

### Health Check

```python
# Check if Conductor is available
is_available = conductor_hitl_service.is_conductor_available()

# Get detailed health status
health = conductor_hitl_service.get_conductor_health()
```

## Testing

### Unit Testing HumanReviewWorker

```python
def test_human_review_worker_returns_in_progress():
    worker = HumanReviewWorker()

    # Create mock task
    task = Mock()
    task.task_id = "test-task-id"
    task.workflow_instance_id = "test-workflow-id"
    task.input_data = {
        "extraction_job_id": str(uuid4()),
        "confidence_score": 0.5,
    }

    result = worker.execute(task)

    assert result.status == "IN_PROGRESS"
    assert "review_request_id" in result.output_data
```

### Integration Testing

```python
def test_hitl_workflow_integration():
    # Start workflow
    workflow_id = start_workflow(
        name="document_extraction_with_review",
        input={
            "document_id": "test-doc",
            "extraction_job_id": str(uuid4()),
            "confidence_threshold": 0.70,
        }
    )

    # Wait for HUMAN_REVIEW task
    while True:
        status = get_workflow_status(workflow_id)
        if status["status"] == "RUNNING":
            for task in status["tasks"]:
                if task["taskDefName"] == "HUMAN_REVIEW":
                    if task["status"] == "IN_PROGRESS":
                        # Submit review
                        submit_review(task["inputData"]["extraction_job_id"])
                        break
        elif status["status"] == "COMPLETED":
            break
        time.sleep(1)

    # Verify workflow completed
    assert status["status"] == "COMPLETED"
```

## Troubleshooting

### Workflow Stuck at HUMAN_REVIEW

1. Check if ReviewRequest was created in database
2. Verify conductor_task_id and conductor_workflow_id are set
3. Check if review has been submitted
4. Verify ConductorHITLService can reach Conductor

### Task Completion Fails

1. Check Conductor logs for API errors
2. Verify task hasn't timed out or been cancelled
3. Check if workflow is still running
4. Review ConductorHITLService retry logs

### Worker Not Picking Up Tasks

1. Verify worker is registered with correct task name (HUMAN_REVIEW)
2. Check Conductor task queue
3. Verify worker is polling at correct interval
4. Check worker logs for connection errors

## Best Practices

1. **Always set confidence thresholds** based on your quality requirements
2. **Monitor SLA breaches** using the HITLService escalation checks
3. **Use specific review instructions** to guide human reviewers
4. **Test timeout scenarios** to ensure graceful handling
5. **Log task/workflow IDs** for debugging integration issues
6. **Use retry logic** when calling Conductor APIs
7. **Design idempotent workers** that handle duplicate task deliveries

## Related Documentation

- [HITL Architecture](../architecture/2025-12-02-hitl-architecture.md)
- [HITL Implementation Summary](../architecture/2025-12-02-hitl-implementation-summary.md)
- [Workflow Builder Architecture](../architecture/2025-11-15-workflow-builder-architecture.md)
- [Netflix Conductor Documentation](https://conductor.netflix.com/)
