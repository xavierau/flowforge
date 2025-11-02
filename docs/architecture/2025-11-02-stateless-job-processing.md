# Stateless Job Processing Architecture

## Overview

This system implements a **stateless job processing architecture** where all job state is persisted in PostgreSQL, not in worker memory. This is a critical design decision that enables horizontal scalability, fault tolerance, and simplified failure recovery.

## Core Principle

**Database as Single Source of Truth**

All Celery tasks are completely stateless. They:
1. Read current state from database
2. Perform processing
3. Write results back to database
4. Never maintain state between invocations

## Why Stateless?

### 1. Horizontal Scalability
- Workers can be added/removed without state synchronization
- Tasks can run on any worker without dependency on specific instances
- Load balancing works seamlessly across worker pool

### 2. Fault Tolerance
- Worker crashes don't lose job state
- Tasks can be retried on different workers
- State transitions are atomic with ACID guarantees

### 3. Simplified Failure Recovery
- Just query current state from database
- No need to reconstruct state from logs or memory
- Clear audit trail of state transitions

### 4. Observability
- All state queryable via SQL
- Job progress visible in database
- Historical state transitions preserved

## Implementation Pattern

### ❌ WRONG: Stateful Task

```python
@celery_app.task
def process_document(document_id, current_status, page_count):
    """
    DON'T DO THIS:
    - Passing state as parameters
    - Storing state in task variables
    - Assuming state hasn't changed since task was queued
    """
    if current_status != "uploaded":
        return  # State might have changed!

    # Process document...
    return {"status": "completed", "pages": page_count}
```

**Problems:**
- State passed as parameters can become stale
- No way to handle concurrent state changes
- Retry logic complex (must reconstruct state)
- Testing difficult (must mock state)

### ✅ CORRECT: Stateless Task

```python
@celery_app.task(bind=True, max_retries=3)
def process_document(self: Task, document_id: str):
    """
    Stateless task that queries current state from database.
    """
    db = SessionLocal()
    try:
        # Always fetch current state from database
        document = db.query(Document).filter(
            Document.id == UUID(document_id)
        ).first()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Check current status (may have changed since task queued)
        if document.status != "uploaded":
            logger.info(f"Document {document_id} already processed")
            return

        # Update state atomically
        document.status = "processing"
        document.started_at = datetime.utcnow()
        db.commit()

        # Perform work (PDF conversion, etc.)
        try:
            pages = convert_pdf_to_images(document)

            # Update state with results
            document.status = "ready_for_extraction"
            document.page_count = len(pages)
            document.completed_at = datetime.utcnow()
            db.commit()

        except Exception as e:
            # Update state on failure
            document.status = "failed"
            document.error_message = str(e)
            db.commit()

            # Retry with exponential backoff
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    finally:
        db.close()
```

**Benefits:**
- Always works with current state
- Atomic state transitions
- Simple retry logic
- Easy to test (just need database)

## State Machine Design

### Document State Flow

```
uploaded → processing → ready_for_extraction → completed
               ↓
             failed
```

**State Transitions:**

| From State | To State | Trigger | Handler |
|------------|----------|---------|---------|
| uploaded | processing | `process_document_task` started | Task updates DB |
| processing | ready_for_extraction | PDF conversion complete | Task updates DB |
| processing | failed | PDF conversion error | Task updates DB |
| ready_for_extraction | completed | All extractions done | API updates DB |

### Extraction Job State Flow

```
queued → processing → completed
            ↓
          failed
```

**State Transitions:**

| From State | To State | Trigger | Handler |
|------------|----------|---------|---------|
| queued | processing | `process_extraction_task` started | Task updates DB |
| processing | completed | All pages extracted | Task updates DB |
| processing | failed | Extraction error | Task updates DB |

## Database Session Management

### FastAPI Endpoints (Request-Scoped)

```python
from app.db.session import get_db
from sqlalchemy.orm import Session

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile,
    db: Session = Depends(get_db)  # Dependency injection
):
    """
    Session automatically managed:
    - Created at request start
    - Committed on success
    - Rolled back on exception
    - Closed at request end
    """
    document = Document(filename=file.filename)
    db.add(document)
    db.commit()
    db.refresh(document)
    return document
```

**Key Points:**
- Session lifecycle tied to HTTP request
- Automatic commit/rollback via middleware
- No need to manually close session

### Celery Tasks (Task-Scoped)

```python
from app.db.session import SessionLocal

@celery_app.task
def process_extraction_task(job_id: str):
    """
    Session must be manually managed in tasks.
    """
    db = SessionLocal()  # Create new session
    try:
        # All database operations
        job = db.query(ExtractionJob).filter(...).first()
        job.status = "processing"
        db.commit()

        # ... perform work ...

        job.status = "completed"
        db.commit()

    except Exception as e:
        db.rollback()  # Rollback on error
        raise
    finally:
        db.close()  # ALWAYS close
```

**Key Points:**
- Create new session per task
- Use try/finally to ensure cleanup
- Explicit commit/rollback
- Always close session in finally block

## Atomic State Transitions

### Pattern: Update-Before-Work

```python
@celery_app.task
def process_task(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()

        # Update status BEFORE starting work
        job.status = "processing"
        job.started_at = datetime.utcnow()
        db.commit()

        # Now perform the work
        result = perform_work(job)

        # Update with results
        job.status = "completed"
        job.result_data = result
        db.commit()

    finally:
        db.close()
```

**Why?**
- If worker crashes during work, status shows "processing"
- Easy to detect stuck jobs: `status='processing' AND started_at < NOW() - INTERVAL '10 minutes'`
- Can implement automatic retry for stuck jobs

### Pattern: Optimistic Locking

```python
@celery_app.task
def process_task(job_id: str):
    db = SessionLocal()
    try:
        # Use SELECT FOR UPDATE to lock row
        job = db.query(Job).filter(
            Job.id == job_id
        ).with_for_update().first()

        # Check if already processed (concurrent tasks)
        if job.status != "queued":
            logger.info(f"Job {job_id} already processed")
            return

        # Update and process atomically
        job.status = "processing"
        db.commit()

        # ... perform work ...

    finally:
        db.close()
```

**Why?**
- Prevents duplicate processing if task queued multiple times
- Database-level locking ensures atomicity
- Race conditions eliminated

## Two-Stage Pipeline

The system uses a two-stage pipeline that leverages stateless design:

### Stage 1: PDF → Images

```python
@celery_app.task
def process_document_task(document_id: str):
    """
    Stateless: Only needs document_id.
    Queries current state from DB.
    """
    db = SessionLocal()
    try:
        document = db.query(Document).filter(...).first()

        # State check
        if document.status != "uploaded":
            return

        # Update state
        document.status = "processing"
        db.commit()

        # Convert PDF to images
        pages = convert_pdf(document)

        # Store page records
        for i, page_data in enumerate(pages):
            page = DocumentPage(
                document_id=document.id,
                page_number=i + 1,
                image_path=page_data["path"]
            )
            db.add(page)

        document.status = "ready_for_extraction"
        db.commit()

    finally:
        db.close()
```

### Stage 2: Images → JSON

```python
@celery_app.task
def process_extraction_task(job_id: str):
    """
    Stateless: Only needs job_id.
    Queries current state and spawns parallel tasks.
    """
    db = SessionLocal()
    try:
        job = db.query(ExtractionJob).filter(...).first()
        pages = job.document.pages

        # State check
        if job.status != "queued":
            return

        # Update state
        job.status = "processing"
        db.commit()

        # Create parallel tasks (also stateless)
        from celery import group
        tasks = group(
            extract_page_task.s(job.id, str(page.id))
            for page in pages
        )

        # Wait for completion
        results = tasks.apply_async().get(timeout=600)

        # Aggregate results (re-query for latest state)
        db.refresh(job)
        all_results = [r.extracted_data for r in job.results]

        job.result_data = aggregate_results(all_results)
        job.status = "completed"
        db.commit()

    finally:
        db.close()
```

**Key Benefits:**
- Each stage is independently retryable
- Stages can scale independently (different worker pools)
- Clear separation of concerns
- PDF processed once, can extract multiple times

## Retry Strategy

### Exponential Backoff

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def flaky_task(self: Task, job_id: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(...).first()

        # Attempt work
        try:
            result = call_external_api(job.data)

            job.status = "completed"
            job.result_data = result
            db.commit()

        except ExternalAPIError as e:
            # Update state before retry
            job.retry_count = self.request.retries + 1
            job.last_error = str(e)
            db.commit()

            # Retry with exponential backoff
            countdown = 60 * (2 ** self.request.retries)
            raise self.retry(exc=e, countdown=countdown)

    finally:
        db.close()
```

**Backoff Schedule:**
- Retry 1: 60 seconds
- Retry 2: 120 seconds
- Retry 3: 240 seconds
- After 3 retries: Mark as failed

## Monitoring and Observability

### Query Stuck Jobs

```sql
-- Find jobs stuck in processing
SELECT
    id,
    status,
    started_at,
    NOW() - started_at as stuck_duration
FROM extraction_jobs
WHERE status = 'processing'
  AND started_at < NOW() - INTERVAL '10 minutes'
ORDER BY started_at ASC;
```

### Query Job Statistics

```sql
-- Job status distribution
SELECT
    status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds
FROM extraction_jobs
WHERE started_at IS NOT NULL
GROUP BY status;
```

### Query Worker Load

```sql
-- Currently processing jobs
SELECT
    COUNT(*) as active_jobs,
    MIN(started_at) as oldest_job,
    MAX(started_at) as newest_job
FROM extraction_jobs
WHERE status = 'processing';
```

## Testing Stateless Tasks

### Unit Test Example

```python
def test_process_document_task(db_session):
    """Test stateless task with database state."""

    # Setup: Create document in database
    document = Document(
        id=uuid4(),
        filename="test.pdf",
        status="uploaded"
    )
    db_session.add(document)
    db_session.commit()

    # Execute: Run task (stateless, queries DB)
    process_document_task(str(document.id))

    # Assert: Verify state in database
    db_session.refresh(document)
    assert document.status == "ready_for_extraction"
    assert document.page_count > 0
```

**Benefits:**
- No need to mock task state
- Just need database fixture
- Tests actual state transitions
- Catches race conditions

## Best Practices

1. **Always Query Current State**: Never trust state passed as parameters
2. **Use Transactions**: Wrap state updates in DB transactions
3. **Update State Before Work**: Mark job as "processing" before starting
4. **Handle Idempotency**: Check if work already done before processing
5. **Close Sessions**: Always close DB sessions in finally block
6. **Log State Transitions**: Log every status change for debugging
7. **Use Retry Logic**: Implement exponential backoff for transient failures
8. **Monitor Stuck Jobs**: Query for jobs stuck in "processing" state

## References

- Task implementation: `app/tasks/`
- Database models: `app/models/`
- Session management: `app/db/session.py`
- API integration: `app/api/documents.py`
