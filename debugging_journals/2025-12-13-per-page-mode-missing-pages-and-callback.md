# Per-Page Mode: Missing Pages and Callback Not Triggered

**Date:** 2025-12-13
**Issue:** Two bugs in "per_page" extraction mode
**Status:** Fixed

---

## Problem Description

When using `per_page` processing mode for multi-page PDFs:

1. **Bug 1: Missing Pages** - The output pages don't match the PDF pages. Some pages are always missing from the extraction results.

2. **Bug 2: Callback Not Triggered** - After all pages are executed (e.g., 5 pages), the callback is never triggered even when `callback_url` is configured.

---

## Root Cause Analysis

### Bug 1: Missing Pages

**Location:** `app/tasks/extractor.py:204-216` (original lines)

The `process_extraction_job` function used `apply_async()` to queue child tasks for each page, but **immediately marked the job as "completed"** without waiting for the child tasks to finish:

```python
# BROKEN CODE
else:
    # PER-PAGE MODE: Process each page separately
    results = []
    for page in pages:
        extract_from_page.apply_async(
            args=(extraction_job_id, str(page.id))
        )
    results = []  # Always empty - child tasks haven't run yet

# Job marked completed immediately here, before child tasks finish
job.status = "completed"
```

The `results = []` meant the job always reported zero results.

### Bug 2: Callback Not Triggered

**Location:** `app/tasks/extractor.py:307-325` (original lines)

The callback logic queried for `ExtractionResult` records immediately after dispatching async tasks:

```python
# BROKEN CODE
extraction_result = (
    db.query(ExtractionResult)
    .filter(ExtractionResult.extraction_job_id == job.id)
    .first()
)

# This is always False because extraction_result is None
if job.callback_url and extraction_result:
    # Never reached - results don't exist yet
    send_extraction_callback.delay(...)
```

The results don't exist yet because the child tasks haven't completed.

### Critical Architecture Gap

The codebase did not use Celery's **chord** primitive for per_page mode. The child task `extract_from_page` had no mechanism to signal completion or trigger a callback after all pages are processed.

---

## Solution

Implemented Celery **chord** pattern to properly orchestrate per-page extraction:

### 1. New `finalize_extraction_job` Task

Created a callback task that runs after ALL page extractions complete:

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=False)
def finalize_extraction_job(
    self: Task,
    page_results: list,  # Results from all page tasks
    extraction_job_id: str,
) -> dict:
    # Aggregates results
    # Marks job as completed
    # Triggers HITL if needed
    # Sends callback with ALL page results
```

### 2. New `on_chord_error` Task

Error handler for when any page extraction fails:

```python
@celery_app.task(...)
def on_chord_error(self: Task, request, exc, traceback, extraction_job_id: str):
    # Handles partial success (some pages extracted)
    # Handles complete failure
    # Updates job status appropriately
```

### 3. Updated Per-Page Mode to Use Chord

```python
# FIXED CODE
else:
    # PER-PAGE MODE: Process each page separately using Celery chord

    # Create a group of page extraction tasks
    page_tasks = group(
        extract_from_page.s(extraction_job_id, str(page.id))
        for page in pages
    )

    # Create chord: group tasks + finalize callback
    extraction_chord = chord(
        page_tasks,
        finalize_extraction_job.s(extraction_job_id).on_error(
            on_chord_error.s(extraction_job_id=extraction_job_id)
        )
    )

    # Dispatch - returns immediately, finalize runs when ALL pages complete
    extraction_chord.apply_async()

    # Return early - finalize_extraction_job handles completion
    return {"status": "processing", "mode": "per_page", ...}
```

### 4. Celery Configuration for Chord Support

Added essential configuration to `app/tasks/celery_app.py`:

```python
celery_app.conf.update(
    # Required for chord to work properly
    result_extended=True,        # Store extended result metadata
    result_expires=3600,         # Results expire after 1 hour
    task_ignore_result=False,    # Tasks must NOT ignore results
    chord_propagate_exceptions=True,
    task_always_eager=False,     # Never run tasks eagerly
)
```

---

## Deadlock Prevention

Key measures to prevent Celery chord deadlocks:

1. **Never call `.get()` inside tasks** - The chord is dispatched with `apply_async()` only
2. **`ignore_result=False`** - Both `extract_from_page` and `finalize_extraction_job` explicitly enable results
3. **`result_extended=True`** - Stores extended metadata required for chord synchronization
4. **Separate callback task** - `finalize_extraction_job` is a separate task, not inline code
5. **`task_always_eager=False`** - Ensures tasks run in worker processes, not synchronously

---

## Files Changed

1. **`app/tasks/extractor.py`**
   - Added `chord`, `group` imports
   - Added `finalize_extraction_job` task (lines 112-259)
   - Added `on_chord_error` task (lines 262-303)
   - Updated per-page mode to use chord (lines 399-441)
   - Added `ignore_result=False` to relevant tasks

2. **`app/tasks/celery_app.py`**
   - Added chord/group configuration (lines 30-39)

---

## Testing

All 64 extraction-related tests passed:
```bash
uv run python -m pytest tests/ -v -k "extract" --tb=short
```

---

## Callback Payload Structure (Per-Page Mode)

After fix, callback now includes ALL page results:

```json
{
  "job_id": "uuid",
  "document_id": "uuid",
  "status": "completed",
  "completed_at": "2025-12-13T10:00:00Z",
  "pages_count": 5,
  "results": [
    {
      "page_number": 1,
      "extracted_data": {...},
      "confidence_score": 0.95
    },
    {
      "page_number": 2,
      "extracted_data": {...},
      "confidence_score": 0.92
    },
    ...
  ]
}
```

---

## References

- [Celery Canvas Documentation](https://docs.celeryq.dev/en/stable/userguide/canvas.html)
- [Celery FAQ - Deadlocks](https://docs.celeryq.dev/en/stable/faq.html)
