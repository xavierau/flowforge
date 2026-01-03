# Auto-Split Parent Job Status Fix

**Date:** 2026-01-03
**Issue:** Auto-split jobs show parent job stuck in "queued" status; parent document never updates status

## Problem Description

When using `split_mode="auto"` for document extraction:
1. Frontend redirects to job detail page showing "Waiting in queue..." indefinitely
2. Parent document remains in "uploaded" status forever
3. Child jobs complete successfully but parent never updates

## Root Cause Analysis

### Issue 1: Parent ExtractionJob Status Never Updated
- Parent job created with `status="queued"` in `/api/v1/jobs/extract`
- Split pipeline creates child jobs but never updates parent status
- `extraction_config` didn't include `parent_extraction_job_id`
- No mechanism to update parent when children complete

### Issue 2: Parent Document Status Never Updated
- In `split_and_create_documents` task, only `split_job.status` was updated
- `source_doc.status` remained "uploaded" after splitting

### Credit Calculation (Working Correctly)
- Credits deducted once for entire document at job creation
- Child jobs inherit `credit_transaction_id` from parent
- No double-charging - this was working correctly

## Solution

### 1. Added DocumentStatus.SPLIT Enum
**Files:** `app/models/enums.py`, `frontend/src/types/enums.ts`
```python
class DocumentStatus(str, Enum):
    # ... existing values
    SPLIT = "split"  # Parent document has been split into children
```

### 2. Added parent_extraction_job_id to ExtractionJob Model
**File:** `app/models/extraction_job.py`
```python
parent_extraction_job_id = Column(
    UUID(as_uuid=True),
    ForeignKey("extraction_jobs.id", ondelete="SET NULL"),
    nullable=True
)
```

**Migration:** `alembic/versions/2026-01-03_211166f9b3fe_add_parent_extraction_job_id_to_.py`

### 3. Updated Parent Document Status After Splitting
**File:** `app/tasks/document_splitter.py:416`
```python
# After creating child documents
source_doc.status = DocumentStatus.SPLIT.value
```

### 4. Pass parent_extraction_job_id to Child Jobs
**File:** `app/api/jobs.py:407-408`
```python
extraction_config = {
    # ...existing config
    "parent_extraction_job_id": str(job.id),
}
```

Also set parent job to "processing" immediately:
```python
job.status = "processing"
job.started_at = datetime.utcnow()
```

### 5. Set parent_extraction_job_id on Child ExtractionJob
**File:** `app/tasks/combined_extraction.py:130`
```python
job = ExtractionJob(
    # ...existing fields
    parent_extraction_job_id=UUID(parent_extraction_job_id) if parent_extraction_job_id else None,
)
```

### 6. Update Parent Status When All Children Complete
**File:** `app/tasks/combined_extraction.py:20-89`

Added `_update_parent_job_status()` helper function that:
1. Checks if job has `parent_extraction_job_id`
2. Gets all sibling jobs (same parent)
3. If all siblings completed: parent → "completed"
4. If any failed and all terminal: parent → "failed"

Called after child job completes or fails.

## Flow After Fix

```
1. POST /jobs/extract (split_mode=auto)
   - Parent job created with status="processing" ✓
   - Parent document status="uploaded"

2. analyze_document_boundaries task
   - Analyzes document for split points

3. split_and_create_documents task
   - Creates child documents
   - Parent document status="split" ✓

4. split_and_extract task
   - Queues child extraction jobs with parent_extraction_job_id

5. process_extraction for each child
   - Child job created with parent_extraction_job_id
   - After completion, calls _update_parent_job_status()

6. All children complete
   - Parent job status="completed" ✓
   - Frontend shows results
```

## Testing

- 654 unit tests passed
- TypeScript compilation successful
- Pre-existing circular dependency issue in test fixtures (unrelated to this fix)

## Files Changed

1. `app/models/enums.py` - Added DocumentStatus.SPLIT
2. `app/models/extraction_job.py` - Added parent_extraction_job_id column + relationship
3. `app/api/jobs.py` - Pass parent_extraction_job_id, set parent to processing
4. `app/tasks/document_splitter.py` - Update parent document status to SPLIT
5. `app/tasks/combined_extraction.py` - Set parent_extraction_job_id, update parent status
6. `frontend/src/types/enums.ts` - Added DocumentStatus.SPLIT
7. `alembic/versions/2026-01-03_*.py` - Migration for new column
