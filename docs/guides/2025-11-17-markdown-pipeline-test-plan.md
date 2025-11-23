# Markdown Pipeline Testing Plan

**Date:** 2025-11-17
**Author:** System
**Status:** Implementation Complete

## Executive Summary

This document outlines the comprehensive testing strategy for the two-stage markdown pipeline feature. The feature enables efficient document extraction by converting images to markdown once, then extracting JSON multiple times from the cached markdown using cheaper text-only models.

**Testing Coverage Target:** 80%+ for new code

**Test Pyramid:**
- Unit Tests: 60+ test cases covering all converter classes, tasks, and utilities
- Integration Tests: 15+ test cases covering end-to-end workflows and API integration
- Manual API Tests: 10+ scenarios for production validation

## 1. Unit Tests (Python - pytest)

### 1.1 Converter Base Interface Tests
**File:** `app/tests/services/converters/test_base.py`

**Purpose:** Validate abstract interfaces and dataclass contracts

**Test Cases:**
1. `test_markdown_conversion_result_creation` - Validate dataclass instantiation
2. `test_markdown_conversion_result_validation` - Test field validation (types, required fields)
3. `test_markdown_extraction_result_creation` - Validate extraction result dataclass
4. `test_markdown_extraction_result_validation` - Test validation errors list
5. `test_interface_abstract_methods` - Ensure interfaces cannot be instantiated
6. `test_interface_method_signatures` - Validate method signatures match contracts

**Key Assertions:**
- Dataclasses accept correct fields
- Type validation enforces contracts
- Abstract methods raise NotImplementedError
- Validation errors are properly typed

---

### 1.2 Converter Factory Tests
**File:** `app/tests/services/converters/test_converter_factory.py`

**Purpose:** Validate converter registration and dependency injection

**Test Cases:**
1. `test_factory_singleton_pattern` - Verify only one factory instance exists
2. `test_register_gemini_converter_with_api_key` - Register Gemini when key present
3. `test_register_gpt4v_converter_with_api_key` - Register GPT-4V when key present
4. `test_skip_registration_without_api_key` - Skip converters without keys
5. `test_get_markdown_converter_valid` - Retrieve registered converter
6. `test_get_markdown_converter_invalid` - Raise error for missing converter
7. `test_get_json_extractor_valid` - Retrieve registered extractor
8. `test_get_json_extractor_invalid` - Raise error for missing extractor
9. `test_list_available_converters` - List all registered converters
10. `test_factory_with_no_api_keys` - Factory works with empty configuration
11. `test_registration_error_handling` - Handle converter initialization errors

**Key Assertions:**
- Singleton pattern enforced
- Converters registered based on API key presence
- Proper error messages for missing converters
- Graceful handling of registration failures

---

### 1.3 Gemini Converter Tests
**File:** `app/tests/services/converters/test_gemini_markdown_converter.py`

**Purpose:** Test Gemini vision-based markdown conversion

**Test Cases:**
1. `test_convert_single_standard_format` - Single page conversion with standard format
2. `test_convert_single_table_heavy_format` - Single page with table-heavy format
3. `test_convert_single_layout_preserved_format` - Single page with layout preservation
4. `test_convert_single_page_marker` - Verify page marker insertion
5. `test_convert_batch_multiple_pages` - Batch conversion with multiple pages
6. `test_convert_batch_page_markers` - Verify page markers in batch mode
7. `test_convert_single_invalid_image` - Handle invalid base64 image
8. `test_convert_api_timeout` - Handle API timeout errors
9. `test_convert_rate_limiting` - Handle rate limit errors
10. `test_token_counting` - Verify input/output token counting
11. `test_processing_time_tracking` - Verify timing metadata
12. `test_build_conversion_prompt_standard` - Validate standard prompt generation
13. `test_build_conversion_prompt_table_heavy` - Validate table-heavy prompt
14. `test_build_conversion_prompt_layout_preserved` - Validate layout prompt
15. `test_timeout_configuration` - Verify extended timeout settings

**Key Assertions:**
- Markdown content generated correctly
- Page markers inserted properly
- Format-specific prompts generated
- Token counting accurate
- Error handling robust (timeout, rate limit, invalid input)
- Processing time tracked

**Mocking Strategy:**
- Mock `genai.Client` for API calls
- Mock PIL.Image for image processing
- Use fixtures for sample base64 images

---

### 1.4 GPT-4V Converter Tests
**File:** `app/tests/services/converters/test_gpt4v_markdown_converter.py`

**Purpose:** Test OpenAI GPT-4V markdown conversion

**Test Cases:** (Same as Gemini, adapted for OpenAI API)
1. `test_convert_single_standard_format`
2. `test_convert_single_table_heavy_format`
3. `test_convert_single_layout_preserved_format`
4. `test_convert_batch_multiple_pages`
5. `test_convert_api_error_handling`
6. `test_token_counting`
7. `test_processing_time_tracking`
8. `test_build_conversion_prompt_formats`

**Key Assertions:**
- OpenAI API integration working
- Same interface compliance as Gemini
- Proper error handling for OpenAI-specific errors

**Mocking Strategy:**
- Mock `openai.Client` for API calls
- Use same image fixtures as Gemini tests

---

### 1.5 Markdown JSON Extractor Tests
**File:** `app/tests/services/converters/test_markdown_json_extractor.py`

**Purpose:** Test markdown-to-JSON extraction with text models

**Test Cases:**
1. `test_extract_from_markdown_valid_schema` - Extract with valid schema
2. `test_extract_from_markdown_custom_prompt` - Extract with custom instructions
3. `test_extract_with_page_markers` - Handle multi-page markdown with markers
4. `test_extract_schema_validation_pass` - Valid JSON passes schema validation
5. `test_extract_schema_validation_fail` - Invalid JSON fails validation
6. `test_extract_malformed_json` - Handle malformed JSON response
7. `test_extract_empty_markdown` - Handle empty input
8. `test_token_counting` - Verify token usage tracking
9. `test_processing_time_tracking` - Verify timing metadata
10. `test_gemini_provider` - Test Gemini 2.0 Flash text model
11. `test_openai_provider` - Test GPT-4o-mini text model
12. `test_api_error_handling` - Handle API errors gracefully

**Key Assertions:**
- JSON extraction accurate
- Schema validation works
- Validation errors captured
- Custom prompts applied
- Token counting correct
- Both providers (Gemini/OpenAI) work

**Mocking Strategy:**
- Mock Gemini/OpenAI API calls
- Use fixture markdown content with page markers
- Use fixture JSON schemas (invoice, receipt, etc.)

---

### 1.6 Markdown Generator Task Tests
**File:** `app/tests/tasks/test_markdown_generator.py`

**Purpose:** Test image-to-markdown Celery task

**Test Cases:**
1. `test_generate_markdown_batch_mode` - Batch conversion of all pages
2. `test_generate_markdown_single_mode` - Per-page conversion
3. `test_generate_markdown_caching_logic` - Skip generation if cached
4. `test_generate_markdown_partial_cache` - Generate only missing pages
5. `test_generate_markdown_storage_integration` - Load images from storage
6. `test_generate_markdown_preprocessed_images` - Prefer preprocessed images
7. `test_generate_markdown_page_marker_splitting` - Split batch results by markers
8. `test_generate_markdown_database_update` - Update DocumentPage records
9. `test_generate_markdown_retry_on_failure` - Retry logic on errors
10. `test_generate_markdown_max_retries_exhausted` - Fail after max retries
11. `test_generate_markdown_invalid_document_id` - Handle missing document
12. `test_generate_markdown_no_pages` - Handle document with no pages

**Key Assertions:**
- Batch mode sends all images in one call
- Single mode processes pages individually
- Caching prevents redundant generation
- Storage service integration works
- Database updates committed correctly
- Retry logic with exponential backoff

**Mocking Strategy:**
- Mock ConverterFactory and converters
- Mock storage service
- Mock database sessions
- Use Celery test harness for retry testing

---

### 1.7 Markdown Extractor Task Tests
**File:** `app/tests/tasks/test_markdown_extractor.py`

**Purpose:** Test markdown-to-JSON Celery task

**Test Cases:**
1. `test_extract_from_markdown_success` - Successful extraction
2. `test_extract_from_markdown_combines_pages` - Combine multi-page markdown
3. `test_extract_from_markdown_missing_markdown` - Handle missing markdown
4. `test_extract_from_markdown_database_update` - Update ExtractionJob and Result
5. `test_extract_from_markdown_document_status_update` - Update Document status
6. `test_extract_from_markdown_retry_on_failure` - Retry logic
7. `test_extract_from_markdown_max_retries_exhausted` - Final failure handling
8. `test_extract_from_markdown_credit_refund_on_failure` - Refund credits
9. `test_extract_from_markdown_callback_webhook` - Queue callback task
10. `test_extract_from_markdown_no_callback` - Skip callback if not configured
11. `test_extract_from_markdown_provider_mapping` - Map VLLM provider to extractor

**Key Assertions:**
- Markdown combined from all pages
- Extraction results stored correctly
- Job status transitions correct
- Credits refunded on final failure
- Webhook callbacks queued
- Provider mapping works (google→gemini, openai→openai)

**Mocking Strategy:**
- Mock ConverterFactory and extractors
- Mock database sessions
- Mock CreditService for refund testing
- Mock callback task queue

---

### 1.8 Markdown Pipeline Orchestrator Tests
**File:** `app/tests/tasks/test_markdown_pipeline.py`

**Purpose:** Test pipeline orchestration task

**Test Cases:**
1. `test_pipeline_orchestration_batch_mode` - Full pipeline with batch conversion
2. `test_pipeline_orchestration_single_mode` - Full pipeline with single conversion
3. `test_pipeline_markdown_generation_failure` - Handle markdown generation failure
4. `test_pipeline_extraction_failure` - Handle extraction failure
5. `test_pipeline_task_chaining` - Verify task chain execution
6. `test_pipeline_result_propagation` - Results passed between tasks

**Key Assertions:**
- Tasks execute in correct order (generate → extract)
- Failures handled at each stage
- Results propagated correctly

**Mocking Strategy:**
- Mock individual tasks
- Use Celery chain testing utilities

---

## 2. Integration Tests (Python - pytest)

### 2.1 End-to-End Pipeline Tests
**File:** `app/tests/integration/test_markdown_pipeline.py`

**Purpose:** Test complete pipeline workflows with real database and mocked APIs

**Test Cases:**
1. `test_e2e_pipeline_standard_format` - Upload PDF → images → markdown → JSON
2. `test_e2e_pipeline_table_heavy_format` - Test table-heavy format
3. `test_e2e_pipeline_layout_preserved_format` - Test layout preservation
4. `test_e2e_markdown_caching` - Run pipeline twice, verify caching
5. `test_e2e_gemini_converter` - Test with Gemini vision
6. `test_e2e_gpt4v_converter` - Test with GPT-4V
7. `test_e2e_batch_mode` - Test batch conversion mode
8. `test_e2e_single_mode` - Test single conversion mode
9. `test_e2e_invalid_image_failure` - Handle invalid images
10. `test_e2e_api_timeout_retry` - Handle API timeouts with retries
11. `test_e2e_schema_mismatch` - Handle extraction schema errors
12. `test_e2e_credit_deduction` - Verify credits deducted
13. `test_e2e_credit_refund_on_failure` - Verify credits refunded on failure
14. `test_e2e_multi_tenant_isolation` - Verify tenant isolation
15. `test_e2e_callback_webhook` - Verify webhook called on completion

**Key Assertions:**
- Complete workflow succeeds
- Markdown cached at DocumentPage level
- Extraction results stored correctly
- Credits handled correctly
- Tenant isolation maintained
- Different format options work

**Setup:**
- Use test database with migrations
- Mock external API calls (Gemini, OpenAI)
- Use real storage service (local test directory)
- Run Celery tasks synchronously with `task_always_eager=True`

---

### 2.2 API Integration Tests
**File:** `app/tests/integration/test_markdown_api.py`

**Purpose:** Test API endpoints for markdown pipeline

**Test Cases:**
1. `test_api_upload_document` - POST /documents/upload
2. `test_api_parse_markdown_mode` - POST /documents/{id}/parse with markdown mode
3. `test_api_parse_validation_converter` - Validate markdown_converter field
4. `test_api_parse_validation_format` - Validate markdown_format field
5. `test_api_get_document_pages` - GET /documents/{id}/pages with markdown
6. `test_api_get_job_status` - GET /jobs/{id}/status
7. `test_api_get_job_result` - GET /jobs/{id}/result
8. `test_api_permission_jwt_token` - Test with JWT authentication
9. `test_api_permission_api_token` - Test with API token authentication
10. `test_api_tenant_isolation` - Verify tenant isolation in API
11. `test_api_invalid_converter_name` - Reject invalid converter
12. `test_api_invalid_format` - Reject invalid format
13. `test_api_missing_api_key` - Handle missing provider API key

**Key Assertions:**
- API validation works
- Authentication enforced
- Tenant isolation enforced
- Error messages clear
- Status codes correct

**Setup:**
- Use FastAPI TestClient
- Mock authentication
- Use test database
- Mock Celery tasks

---

## 3. Frontend Tests (TypeScript - Vitest)

### 3.1 Hook Tests
**File:** `frontend/src/hooks/__tests__/useDocumentMarkdown.test.ts`

**Test Cases:**
1. `test_hook_successful_fetch` - Fetch markdown successfully
2. `test_hook_loading_state` - Loading state transitions
3. `test_hook_error_handling` - Error state on API failure
4. `test_hook_cleanup` - Cleanup on unmount (isMounted pattern)
5. `test_hook_refetch` - Refetch functionality
6. `test_hook_empty_response` - Handle empty pages

**Mocking Strategy:**
- Mock fetch API
- Use React Testing Library

---

### 3.2 Component Tests
**File:** `frontend/src/components/markdown/__tests__/ProcessingModeBadge.test.tsx`

**Test Cases:**
1. `test_badge_direct_mode` - Render "Direct" badge
2. `test_badge_markdown_mode` - Render "Markdown" badge
3. `test_badge_styles` - Verify correct styling

**File:** `frontend/src/components/markdown/__tests__/MarkdownPipelineConfig.test.tsx`

**Test Cases:**
1. `test_config_converter_selection` - Select markdown converter
2. `test_config_format_selection` - Select markdown format
3. `test_config_default_values` - Default selections
4. `test_config_onChange_callbacks` - onChange handlers called

**File:** `frontend/src/components/markdown/__tests__/MarkdownViewer.test.tsx`

**Test Cases:**
1. `test_viewer_markdown_rendering` - Render markdown with react-markdown
2. `test_viewer_xss_prevention` - Sanitize with DOMPurify
3. `test_viewer_xss_script_injection` - Block malicious scripts
4. `test_viewer_copy_to_clipboard` - Copy functionality
5. `test_viewer_preview_toggle` - Toggle preview mode
6. `test_viewer_multiple_pages_tabs` - Tab navigation for pages
7. `test_viewer_empty_markdown` - Handle empty content

**Mocking Strategy:**
- Mock DOMPurify
- Use React Testing Library
- Use userEvent for interactions

---

### 3.3 Page Integration Tests
**File:** `frontend/src/pages/jobs/__tests__/JobCreate.test.tsx`

**Test Cases:**
1. `test_job_create_processing_mode_selection` - Select processing mode
2. `test_job_create_markdown_config_conditional` - Show config only for markdown mode
3. `test_job_create_form_submission` - Submit with markdown mode

**File:** `frontend/src/pages/jobs/__tests__/JobDetail.test.tsx`

**Test Cases:**
1. `test_job_detail_markdown_tab_visibility` - Show markdown tab for markdown jobs
2. `test_job_detail_markdown_data_display` - Display markdown content
3. `test_job_detail_no_markdown_tab_direct_mode` - Hide tab for direct mode

**File:** `frontend/src/pages/jobs/__tests__/JobList.test.tsx`

**Test Cases:**
1. `test_job_list_processing_mode_badge` - Display processing mode badges
2. `test_job_list_filtering_by_mode` - Filter by processing mode

---

## 4. Manual API Tests

### 4.1 Test Scripts
**File:** `app/tests/api/test_markdown_endpoints.py`

Runnable pytest scripts for manual/postman-style testing:

**Test Scenarios:**
1. Upload invoice PDF → Extract with markdown mode (standard format)
2. Upload invoice PDF → Extract with markdown mode (table_heavy format)
3. Upload invoice PDF → Extract with markdown mode (layout_preserved format)
4. Upload multi-page PDF → Batch markdown conversion → Extract
5. Upload PDF → Extract with markdown → Extract again (verify caching)
6. Upload PDF → Extract with Gemini → Extract with GPT-4V (compare results)
7. Upload invalid PDF → Verify error handling
8. Extract without sufficient credits → Verify error
9. Extract with invalid schema → Verify validation error
10. Extract with callback URL → Verify webhook called

---

## 5. Test Fixtures and Configuration

### 5.1 Pytest Configuration
**File:** `pytest.ini`

```ini
[pytest]
testpaths = app/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --cov=app --cov-report=term-missing --cov-report=html
markers =
    unit: Unit tests
    integration: Integration tests
    api: API tests
    slow: Slow-running tests
asyncio_mode = auto
```

### 5.2 Common Fixtures
**File:** `app/tests/conftest.py`

**Fixtures:**
- `db_session` - Test database session
- `test_client` - FastAPI TestClient
- `mock_google_api_key` - Mock Google API key
- `mock_openai_api_key` - Mock OpenAI API key
- `mock_converter_factory` - Mock ConverterFactory
- `mock_storage_service` - Mock storage service
- `sample_invoice_image_base64` - Sample invoice image
- `sample_receipt_image_base64` - Sample receipt image
- `sample_invoice_schema` - Invoice extraction schema
- `sample_markdown_content` - Sample markdown with page markers
- `create_test_document` - Factory for creating test documents
- `create_test_extraction_job` - Factory for creating test jobs
- `celery_eager_mode` - Configure Celery for synchronous testing

### 5.3 Sample Data
**Directory:** `app/tests/fixtures/`

**Files:**
- `invoice_sample.pdf` - Sample invoice PDF
- `receipt_sample.pdf` - Sample receipt PDF
- `invoice_page_1.png` - Sample invoice image
- `invoice_schema.json` - Invoice extraction schema
- `receipt_schema.json` - Receipt extraction schema
- `sample_markdown.md` - Sample markdown with page markers

---

## 6. Test Execution

### 6.1 Running Tests

**All Tests:**
```bash
pytest app/tests/
```

**Unit Tests Only:**
```bash
pytest app/tests/ -m unit
```

**Integration Tests Only:**
```bash
pytest app/tests/ -m integration
```

**Specific Test File:**
```bash
pytest app/tests/services/converters/test_gemini_markdown_converter.py
```

**With Coverage:**
```bash
pytest app/tests/ --cov=app --cov-report=html
```

**Parallel Execution:**
```bash
pytest app/tests/ -n auto
```

### 6.2 Frontend Tests

**All Frontend Tests:**
```bash
cd frontend
npm run test
```

**With Coverage:**
```bash
cd frontend
npm run test:coverage
```

**Watch Mode:**
```bash
cd frontend
npm run test:watch
```

---

## 7. Coverage Goals

**Target Coverage:** 80%+

**Priority Areas (>90% coverage):**
- Converter interfaces and implementations
- Task orchestration logic
- Credit refund logic
- API validation and authentication
- XSS prevention in frontend

**Acceptable Lower Coverage (<70%):**
- Error handling edge cases
- External API mock inconsistencies
- UI styling and animations

---

## 8. Continuous Integration

**GitHub Actions Workflow:**
```yaml
name: Markdown Pipeline Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
      redis:
        image: redis:7

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install uv
          uv sync --dev
      - name: Run backend tests
        run: pytest app/tests/ --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 9. Known Limitations

1. **External API Mocking:** Tests mock Gemini/OpenAI APIs. Real API integration tested manually.
2. **Image Processing:** Tests use small sample images. Large image handling tested manually.
3. **Celery Async:** Integration tests run Celery synchronously. Production async behavior tested manually.
4. **Timeout Testing:** Hard to test timeout scenarios in unit tests. Covered in integration tests.
5. **Rate Limiting:** API rate limit handling tested with mocks, not real rate limits.

---

## 10. Maintenance

**Test Review Frequency:** Every sprint (2 weeks)

**Update Triggers:**
- New converter added
- API contract changes
- Schema validation updates
- Frontend component refactoring

**Ownership:**
- Backend Tests: Backend team
- Frontend Tests: Frontend team
- Integration Tests: Full-stack team
- API Tests: QA team

---

## Appendix: Test Data Examples

### Sample Markdown with Page Markers
```markdown
<!-- PAGE 1 -->
# Invoice

**Invoice Number:** INV-001
**Date:** 2024-01-15

| Item | Quantity | Price |
|------|----------|-------|
| Widget | 10 | $50.00 |

<!-- PAGE 2 -->
## Payment Details

**Total:** $500.00
**Due Date:** 2024-02-15
```

### Sample Invoice Schema
```json
{
  "type": "object",
  "properties": {
    "invoice_number": {"type": "string"},
    "date": {"type": "string"},
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "quantity": {"type": "number"},
          "price": {"type": "number"}
        }
      }
    },
    "total": {"type": "number"}
  },
  "required": ["invoice_number", "total"]
}
```

---

**End of Test Plan**
