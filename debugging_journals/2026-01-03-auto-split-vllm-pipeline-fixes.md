# Auto Split + VLLM Pipeline Fixes

**Date:** 2026-01-03
**Issue:** Multiple errors when using auto split mode with VLLM extraction in production
**Severity:** Critical - Feature completely broken
**Resolution:** Fixed via 6 sequential commits

---

## Summary

The auto split + VLLM extraction pipeline had multiple bugs that caused a cascade of failures:
1. Wrong field name when creating SplitJob
2. Wrong parameter passed to Celery task
3. Missing task in pipeline chain
4. Database constraint violation on child jobs
5. Wrong model format for document analyzer
6. Race condition from nested async chains

---

## Issue 1: Invalid Keyword Argument for SplitJob

### Error
```
TypeError: 'document_id' is an invalid keyword argument for SplitJob
```

### Root Cause
`app/api/jobs.py:369` used `document_id` but the `SplitJob` model defines the field as `source_document_id`.

### Fix
```python
# Before
split_job = SplitJob(
    document_id=document.id,  # WRONG
    ...
)

# After
split_job = SplitJob(
    source_document_id=document.id,  # CORRECT
    ...
)
```

### Commit
```
2166911 fix(jobs): use correct field name source_document_id for SplitJob
```

---

## Issue 2: Tenant ID Mismatch in Worker

### Error
```
Split job {id} not found or tenant mismatch (requested tenant: {user_id})
ValueError: SplitJob {id} not found
```

### Root Cause
`app/api/jobs.py:403` passed `current_user.id` (user ID) instead of `current_user.tenant_id` to the `split_and_extract` task.

The task signature expects `tenant_id` for defense-in-depth validation:
```python
def split_and_extract(
    self: Task,
    split_job_id: str,
    tenant_id: Optional[str] = None,  # Expects tenant_id
    extraction_config: Optional[Dict] = None,
)
```

### Fix
```python
# Before
task = split_and_extract.delay(
    str(split_job.id),
    str(current_user.id),  # WRONG - passing user ID
    extraction_config
)

# After
task = split_and_extract.delay(
    str(split_job.id),
    str(current_user.tenant_id),  # CORRECT - passing tenant ID
    extraction_config
)
```

### Commit
```
01ff1c6 fix(jobs): pass tenant_id instead of user_id to split_and_extract task
```

---

## Issue 3: Split Job Never Executed

### Error
```
Split job {id} still in progress: queued
celery.exceptions.Retry: Retry in 30s
```

### Root Cause
The `split_and_extract` task was called directly without first calling `process_split_job`. The split job remained in "queued" status forever because nothing executed the actual splitting tasks:
- `analyze_document_boundaries` - detects page boundaries
- `split_and_create_documents` - creates child documents

### Fix
Added `process_split_job` to the chain:
```python
# Before - split_and_extract called directly, expects split to be done
task = split_and_extract.delay(...)

# After - chain includes process_split_job first
workflow = chain(
    process_split_job.s(str(split_job.id), str(current_user.tenant_id)),
    split_and_extract.si(str(split_job.id), str(current_user.tenant_id), extraction_config),
)
task = workflow.apply_async()
```

### Commit
```
accefcf fix(jobs): chain process_split_job before split_and_extract
```

---

## Issue 4: Credit Deduction Constraint Violation

### Error
```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.CheckViolation)
new row for relation "extraction_jobs" violates check constraint
"ck_extraction_jobs_completed_credits_deducted"
```

### Root Cause
Child extraction jobs created by `process_extraction` in `combined_extraction.py` didn't have:
- `credits_deducted = True`
- `credit_transaction_id` set

The database constraint requires both when `status = 'completed'`:
```sql
CHECK (
    (status != 'completed') OR
    (credits_deducted = TRUE AND credit_transaction_id IS NOT NULL)
)
```

The parent job deducts credits upfront, but child jobs need to reference the same transaction.

### Fix
1. Pass parent's credit transaction ID in extraction config:
```python
# jobs.py
extraction_config = {
    ...
    "parent_credit_transaction_id": str(job.credit_transaction_id) if job.credit_transaction_id else None,
}
```

2. Set credit fields on child jobs:
```python
# combined_extraction.py - process_extraction()
job = ExtractionJob(
    ...
    credits_deducted=True if parent_credit_transaction_id else False,
    credit_transaction_id=UUID(parent_credit_transaction_id) if parent_credit_transaction_id else None,
)
```

### Commit
```
353057d fix(jobs): pass parent credit transaction to child extraction jobs
```

---

## Issue 5: Invalid Model Name for LiteLLM

### Error
```
litellm.NotFoundError: OpenAIException - Error code: 404 -
{'error': {'message': 'The model `google/gemini-2.5-flash` does not exist'}}
litellm.completion(model=openai/google/gemini-2.5-flash)
```

### Root Cause
`jobs.py` set `dspy_model=f"{model_provider}/{model_name}"` (e.g., `google/gemini-2.5-flash`).

`DocumentAnalyzerService` prepends `openai/` for Dashscope compatibility:
```python
self._lm = dspy.LM(
    model=f"openai/{self.model}",  # Becomes openai/google/gemini-2.5-flash
    ...
)
```

The service is specifically designed for Dashscope/Qwen VL models, not arbitrary providers.

### Fix
Use the default Qwen VL model for splitting (it's optimized for this task):
```python
# Before
split_job = SplitJob(
    dspy_model=f"{model_provider}/{model_name}",  # Wrong
    ...
)

# After
split_job = SplitJob(
    dspy_model=None,  # Use default qwen3-vl-32b-instruct
    ...
)
```

### Commit
```
87b31c9 fix(jobs): use default Qwen VL model for document splitting
```

---

## Issue 6: Race Condition from Nested Chains

### Error
```
[ForkPoolWorker-1] Starting boundary analysis for split job: {id}
[ForkPoolWorker-2] Starting split-and-extract pipeline for job: {id}
[ForkPoolWorker-2] Error: Split job {id} still in progress: queued
```

Both tasks started simultaneously instead of sequentially.

### Root Cause
`process_split_job` creates its own async chain internally and returns immediately:
```python
def process_split_job(...):
    workflow = chain(
        analyze_document_boundaries.s(...),
        split_and_create_documents.s(),
    )
    result = workflow.apply_async()  # Returns immediately!
    return result.id
```

When chained with `split_and_extract`:
```python
chain(
    process_split_job.s(...),      # Returns immediately
    split_and_extract.si(...),      # Runs before internal chain completes
)
```

### Fix
Use a flat chain with individual tasks instead of nesting:
```python
# Before - nested chain, process_split_job returns immediately
workflow = chain(
    process_split_job.s(...),
    split_and_extract.si(...),
)

# After - flat chain, proper sequencing
workflow = chain(
    analyze_document_boundaries.s(str(split_job.id), str(current_user.tenant_id)),
    split_and_create_documents.s(),  # receives result from analyze
    split_and_extract.si(str(split_job.id), str(current_user.tenant_id), extraction_config),
)
```

### Commit
```
7a88209 fix(jobs): use flat chain instead of nested async chains
```

---

## Final Pipeline Flow

```
API Request (POST /api/v1/jobs/extract with split_mode=auto)
    │
    ├── Create ExtractionJob (credits deducted)
    ├── Create SplitJob (status=queued)
    │
    └── Queue Celery Chain:
            │
            ├── 1. analyze_document_boundaries
            │       - Downloads PDF
            │       - Uses Qwen VL for boundary detection
            │       - Uses Tesseract for rotation detection
            │       - Creates SplitResult records
            │       - Status: queued → analyzing
            │
            ├── 2. split_and_create_documents
            │       - Splits PDF at boundaries
            │       - Applies rotation corrections
            │       - Creates child Document records
            │       - Uploads to storage
            │       - Status: analyzing → completed
            │
            └── 3. split_and_extract
                    - Creates ExtractionJob for each child
                    - Inherits parent's credit_transaction_id
                    - Queues process_document_and_extract for each
```

---

## Key Lessons

1. **Field names matter**: Always verify SQLAlchemy model column names match constructor arguments.

2. **Parameter order matters**: When passing arguments to Celery tasks, verify the function signature.

3. **Async chains don't wait**: A task that creates an internal async chain returns immediately - don't chain after it expecting the internal work to be done.

4. **Database constraints catch bugs**: The `ck_extraction_jobs_completed_credits_deducted` constraint caught the missing credit tracking.

5. **Service design assumptions**: `DocumentAnalyzerService` was designed for Dashscope/Qwen - don't assume it works with arbitrary model providers.

6. **Test the full flow**: These issues only appeared when testing the complete auto-split + VLLM flow in production, not individual components.

---

## Files Modified

- `app/api/jobs.py` - 6 fixes across multiple commits
- `app/tasks/combined_extraction.py` - Added parent_credit_transaction_id support

## Related Files (not modified, but relevant)

- `app/models/document_split.py` - SplitJob model with `source_document_id`
- `app/tasks/document_splitter.py` - Split pipeline tasks
- `app/services/document_analyzer_service.py` - DSPy/Qwen VL integration
