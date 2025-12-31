# Document Splitter Security Fixes

**Date:** 2025-12-31
**Feature:** PDF Document Splitter Integration
**Severity:** Critical / Important
**Status:** Resolved

## Summary

During code review of the newly implemented PDF Document Splitter feature, two critical security vulnerabilities and several important issues were identified and fixed.

---

## Critical Issue 1: Missing Tenant Isolation in Celery Tasks

### Problem

The Celery tasks in `app/tasks/document_splitter.py` queried `SplitJob` records without validating the tenant_id. While the API layer enforced tenant isolation, the tasks themselves did not.

**Vulnerable Code (line 58):**
```python
split_job = db.query(SplitJob).filter(SplitJob.id == job_uuid).first()
```

### Risk Assessment

- **Attack Vector:** If an attacker obtained a valid `split_job_id` (through UUID enumeration, leaked logs, or other means), they could potentially trigger processing for jobs belonging to other tenants.
- **Impact:** Cross-tenant data access - documents from other tenants could be processed and potentially exposed.
- **CVSS Score Estimate:** 7.5 (High) - Confidentiality impact, no authentication bypass but authorization bypass possible.

### Root Cause

Defense-in-depth principle was not applied. The implementation relied solely on the API layer for tenant isolation, without secondary validation in the background task layer.

### Solution

Added `tenant_id` parameter to all Celery tasks with optional validation:

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_document_boundaries(
    self: Task,
    split_job_id: str,
    tenant_id: Optional[str] = None,  # Defense in depth
) -> Dict:
    # ...
    query = db.query(SplitJob).filter(SplitJob.id == job_uuid)

    # Defense in depth: validate tenant_id if provided
    if tenant_id:
        tenant_uuid = UUID(tenant_id)
        query = query.filter(SplitJob.tenant_id == tenant_uuid)

    split_job = query.first()

    if not split_job:
        if tenant_id:
            # Log security event for potential tenant mismatch
            logger.warning(
                f"Split job {split_job_id} not found or tenant mismatch "
                f"(requested tenant: {tenant_id})"
            )
        raise ValueError(f"SplitJob {split_job_id} not found")
```

The API layer now passes `tenant_id` when queuing tasks:
```python
process_split_job.delay(str(split_job.id), str(current_user.tenant_id))
```

### Files Modified

- `app/tasks/document_splitter.py` - Added tenant_id validation to all 4 tasks
- `app/api/splits.py` - Updated to pass tenant_id when queuing tasks

---

## Critical Issue 2: Error Information Disclosure

### Problem

The API endpoint returned raw error messages from the database, potentially exposing:
- Internal file paths
- Stack trace information
- Database structure details
- API key configuration errors

**Vulnerable Code (line 197):**
```python
error_message=split_job.error_message,  # Raw error exposed
```

### Risk Assessment

- **Attack Vector:** Error messages could reveal system internals to attackers, aiding further attacks.
- **Impact:** Information disclosure - internal architecture, file paths, exception details exposed.
- **CVSS Score Estimate:** 5.3 (Medium) - Information disclosure without direct system compromise.

### Root Cause

No error sanitization layer between database storage and API response.

### Solution

Added `_sanitize_error_message()` function to map internal errors to safe client-facing messages:

```python
def _sanitize_error_message(error_message: Optional[str]) -> Optional[str]:
    """Sanitize error messages to avoid exposing internal details."""
    if not error_message:
        return None

    # User-initiated cancellation - return as-is
    if error_message == "Cancelled by user":
        return error_message

    # Map known error patterns to safe messages
    error_lower = error_message.lower()

    if "not found" in error_lower:
        return "Resource not found"
    if "permission" in error_lower or "unauthorized" in error_lower:
        return "Permission denied"
    if "timeout" in error_lower:
        return "Operation timed out"
    if "api key" in error_lower:
        return "External service configuration error"
    # ... more patterns ...

    # Generic fallback - don't expose internal details
    return "An error occurred during processing"
```

### Files Modified

- `app/api/splits.py` - Added `_sanitize_error_message()` and applied to all error responses

---

## Important Issues Fixed

### Issue 3: Schema/Response Model Mismatches

Multiple mismatches between Pydantic schemas and actual API responses were identified and fixed:

| Schema | Problem | Fix |
|--------|---------|-----|
| `SplitJobCreateResponse` | Missing `estimated_time_seconds` | Added field |
| `SplitJobProgress` | Had `documents_detected` but API used `documents_created` | Renamed to match |
| `SplitJobProgress` | Missing `total_input_tokens`, `total_output_tokens` | Added fields |
| `SplitJobProgress` | `total_pages` not populated | Added to API response |
| `SplitJobResultsResponse` | Missing `summary` field population | Added `SplitJobSummary` schema and populated |
| `ChildDocumentsListResponse` | Had `total_children` but API returned `total_count` | Changed to `total_count` |

### Issue 4: Missing Input Validation for dspy_model

Added field validator to prevent arbitrary model injection:

```python
ALLOWED_DSPY_MODELS: Set[str] = {
    "qwen3-vl-32b-instruct",
    "qwen3-vl-8b-instruct",
    "qwen-vl-max",
    "qwen-vl-plus",
}

@field_validator("dspy_model")
@classmethod
def validate_dspy_model(cls, v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    if v not in ALLOWED_DSPY_MODELS:
        raise ValueError(
            f"Invalid model: {v}. Allowed models: {', '.join(sorted(ALLOWED_DSPY_MODELS))}"
        )
    return v
```

---

## Verification

```bash
# Verify all imports work correctly
uv run python -c "
from app.api.splits import router, _sanitize_error_message
from app.tasks.document_splitter import process_split_job, analyze_document_boundaries
from app.schemas.document_split import SplitJobCreateRequest, ALLOWED_DSPY_MODELS

# Test error sanitization
assert _sanitize_error_message('File /etc/passwd not found') == 'Resource not found'
assert _sanitize_error_message('API key invalid') == 'External service configuration error'
assert _sanitize_error_message('Some random internal error') == 'An error occurred during processing'
assert _sanitize_error_message('Cancelled by user') == 'Cancelled by user'

# Test model validation
from pydantic import ValidationError
try:
    SplitJobCreateRequest(dspy_model='malicious-model')
    assert False, 'Should have raised validation error'
except ValidationError:
    pass  # Expected

print('All security fixes verified successfully')
"
```

---

## Lessons Learned

1. **Defense in Depth:** Always validate authorization at multiple layers, not just the API entry point. Background tasks should independently verify they're operating on authorized data.

2. **Error Handling:** Internal error messages should never be exposed directly to clients. Use a sanitization layer to map internal errors to safe, generic messages.

3. **Schema-First Development:** Use the contract-first development pattern to ensure schemas and API responses match before implementation.

4. **Input Validation:** All user-provided values that configure system behavior (like model names) must be validated against an allowlist.

5. **Code Review Value:** The @agent-code-review-analyzer caught issues that could have led to security vulnerabilities in production.

---

## Related Files

- `app/api/splits.py` - API endpoints with error sanitization
- `app/tasks/document_splitter.py` - Celery tasks with tenant validation
- `app/schemas/document_split.py` - Fixed Pydantic schemas with validation
- `app/services/document_analyzer_service.py` - DSPy service
- `app/models/document_split.py` - SQLAlchemy models

---

---

## Additional Fixes (Re-Review)

### Issue 3: Raw Exception Messages Stored in Database

**Problem**: Celery tasks stored raw `str(e)` exception messages in the database, potentially persisting sensitive information.

**Fix**: Added `_sanitize_task_error()` function in `app/tasks/document_splitter.py` and applied to all error handling blocks:

```python
def _sanitize_task_error(error_message: str) -> str:
    """Sanitize error messages before storing in database."""
    if not error_message:
        return "Unknown error"

    error_lower = error_message.lower()

    if "not found" in error_lower:
        return "Resource not found"
    # ... pattern matching ...

    return "An error occurred during processing"
```

### Issue 4: Missing Tenant Filter in Child Document Query

**Problem**: The `split_and_extract` task queried child documents without tenant_id filter.

**Fix**: Added tenant isolation to the query:

```python
child_docs = (
    db.query(Document)
    .filter(
        Document.split_job_id == split_job.id,
        Document.tenant_id == split_job.tenant_id,  # Defense in depth
    )
    .order_by(Document.split_sequence)
    .all()
)
```

---

## Prevention

To prevent similar issues in future:

1. Add tenant_id validation to the Celery task template/pattern documentation
2. Create a shared error sanitization utility for all API endpoints
3. Use schema validation in CI/CD to catch mismatches
4. Add security-focused test cases for multi-tenant scenarios
