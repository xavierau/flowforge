# Markdown Pipeline Test Execution Guide

**Date:** 2025-11-17
**Status:** Ready for Execution

## Quick Start

### Install Test Dependencies

```bash
# Ensure dev dependencies are installed
uv sync --dev
```

### Run All Tests

```bash
# Run all tests with coverage
pytest app/tests/ --cov=app --cov-report=html --cov-report=term

# Run specific test categories
pytest app/tests/ -m unit                # Unit tests only
pytest app/tests/ -m integration         # Integration tests only
pytest app/tests/ -m "not slow"          # Skip slow tests
```

## Test Categories

### 1. Converter Base Tests

**Location:** `app/tests/services/converters/test_base.py`

**Run:**
```bash
pytest app/tests/services/converters/test_base.py -v
```

**What's Tested:**
- Dataclass validation (MarkdownConversionResult, MarkdownExtractionResult)
- Abstract interface contracts
- Type safety enforcement

**Expected Output:**
```
test_base.py::TestMarkdownConversionResult::test_creation_with_valid_data PASSED
test_base.py::TestMarkdownConversionResult::test_field_types PASSED
test_base.py::TestMarkdownExtractionResult::test_creation_with_valid_data PASSED
test_base.py::TestImageToMarkdownConverterInterface::test_cannot_instantiate_interface PASSED
...
```

### 2. Converter Factory Tests

**Location:** `app/tests/services/converters/test_converter_factory.py`

**Run:**
```bash
pytest app/tests/services/converters/test_converter_factory.py -v
```

**What's Tested:**
- Singleton pattern enforcement
- Converter registration based on API keys
- Converter retrieval and error handling
- List available converters

**Expected Output:**
```
test_converter_factory.py::TestConverterFactoryInitialization::test_factory_singleton_pattern PASSED
test_converter_factory.py::TestConverterRegistration::test_register_gemini_with_google_api_key PASSED
test_converter_factory.py::TestConverterRetrieval::test_get_markdown_converter_valid_name PASSED
...
```

### 3. Gemini Converter Tests

**Location:** `app/tests/services/converters/test_gemini_markdown_converter.py`

**Run:**
```bash
pytest app/tests/services/converters/test_gemini_markdown_converter.py -v
```

**What's Tested:**
- Single page conversion
- Batch multi-page conversion
- Format-specific prompts (standard, table_heavy, layout_preserved)
- Error handling (invalid images, API errors)
- Token counting and timing

**Expected Output:**
```
test_gemini_markdown_converter.py::TestSinglePageConversion::test_convert_single_success PASSED
test_gemini_markdown_converter.py::TestBatchConversion::test_convert_batch_success PASSED
test_gemini_markdown_converter.py::TestFormatStyles::test_standard_format PASSED
...
```

### 4. JSON Extractor Tests

**Location:** `app/tests/services/converters/test_markdown_json_extractor.py`

**Run:**
```bash
pytest app/tests/services/converters/test_markdown_json_extractor.py -v
```

**What's Tested:**
- Markdown-to-JSON extraction
- Schema validation
- Custom prompts
- Provider-specific implementations (Gemini, OpenAI)
- Error handling (malformed JSON, invalid schemas)

**Expected Output:**
```
test_markdown_json_extractor.py::TestMarkdownJsonExtraction::test_extract_with_valid_schema PASSED
test_markdown_json_extractor.py::TestMarkdownJsonExtraction::test_extract_schema_validation_pass PASSED
...
```

## Test Coverage

### Generate Coverage Report

```bash
# Generate HTML coverage report
pytest app/tests/ --cov=app --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage Targets

- **Converter Interfaces:** >95%
- **Converter Implementations:** >80%
- **Factory Logic:** >90%
- **Task Orchestration:** >75%
- **API Integration:** >70%

## Continuous Integration

### GitHub Actions Workflow

Create `.github/workflows/markdown-pipeline-tests.yml`:

```yaml
name: Markdown Pipeline Tests

on:
  push:
    branches: [develop, main]
  pull_request:
    branches: [develop, main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install uv
        run: pip install uv

      - name: Install dependencies
        run: uv sync --dev

      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
          GOOGLE_API_KEY: test_key
          OPENAI_API_KEY: test_key
        run: |
          pytest app/tests/ --cov=app --cov-report=xml --cov-report=term

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: markdown-pipeline
          name: markdown-pipeline-coverage
```

## Debugging Failed Tests

### Common Issues

**1. Import Errors**
```bash
# Ensure package is installed in editable mode
uv pip install -e .
```

**2. Database Connection Errors**
```bash
# Use in-memory SQLite for tests (already configured in conftest.py)
# Tests should not require PostgreSQL
```

**3. API Key Errors**
```bash
# Tests mock API calls, no real keys needed
# If tests fail with API errors, check mocking in test file
```

**4. Async Test Errors**
```bash
# Ensure pytest-asyncio is installed
uv pip install pytest-asyncio

# Verify pytest.ini has asyncio_mode = auto
```

### Verbose Debugging

```bash
# Run with maximum verbosity
pytest app/tests/services/converters/test_gemini_markdown_converter.py -vvs

# Show print statements
pytest app/tests/ -s

# Stop on first failure
pytest app/tests/ -x

# Show local variables on failure
pytest app/tests/ -l
```

## Performance Benchmarking

### Measure Test Execution Time

```bash
# Show slowest 10 tests
pytest app/tests/ --durations=10

# Profile test execution
pytest app/tests/ --profile

# Run with timing breakdown
pytest app/tests/ -vv --durations=0
```

## Test Maintenance

### Adding New Tests

1. **Create test file** in appropriate directory:
   - Unit tests: `app/tests/services/converters/`
   - Integration tests: `app/tests/integration/`
   - API tests: `app/tests/api/`

2. **Follow naming convention:**
   - File: `test_<module_name>.py`
   - Class: `Test<FeatureName>`
   - Method: `test_<specific_behavior>`

3. **Use markers:**
   ```python
   @pytest.mark.unit
   @pytest.mark.asyncio
   async def test_new_feature():
       ...
   ```

4. **Add fixtures** to `conftest.py` if reusable

### Updating Existing Tests

1. **Run tests before changes:**
   ```bash
   pytest app/tests/services/converters/test_gemini_markdown_converter.py
   ```

2. **Make changes to implementation code**

3. **Update tests** to match new behavior

4. **Verify coverage not reduced:**
   ```bash
   pytest app/tests/ --cov=app --cov-report=term
   ```

## Manual Testing Checklist

For features that cannot be fully automated:

### 1. Real API Integration

```bash
# Test with real Gemini API (requires API key)
export GOOGLE_API_KEY="your_real_key"
python -c "
import asyncio
from app.services.converters.gemini_markdown_converter import GeminiMarkdownConverter

async def test():
    converter = GeminiMarkdownConverter(api_key='your_key')
    # Use real image base64
    result = await converter.convert_single(image_base64='...', format_style='standard', page_number=1)
    print(result.markdown_content)

asyncio.run(test())
"
```

### 2. Large Document Testing

- Test with 10+ page PDF
- Verify batch mode performance
- Check memory usage
- Validate markdown caching

### 3. Production Smoke Test

After deployment:

1. Upload sample invoice via UI
2. Create extraction job with markdown mode
3. Verify job completes successfully
4. Check markdown cached in database
5. Submit second extraction job (same document)
6. Verify cached markdown reused (faster execution)

## Reporting Issues

When reporting test failures:

1. **Include full pytest output:**
   ```bash
   pytest app/tests/path/to/test.py -vv > test_output.txt 2>&1
   ```

2. **Include coverage report:**
   ```bash
   pytest app/tests/ --cov=app --cov-report=term > coverage.txt
   ```

3. **Include environment info:**
   ```bash
   python --version
   uv pip list
   ```

4. **Create minimal reproduction:**
   ```python
   # Isolate failing test
   import pytest

   def test_minimal_repro():
       # Smallest code that reproduces the issue
       assert False, "Describe the issue"
   ```

## Next Steps

After all tests pass:

1. **Review coverage report** - Identify untested code paths
2. **Add integration tests** - Test complete workflows
3. **Add API tests** - Test HTTP endpoints
4. **Add frontend tests** - Test UI components
5. **Update documentation** - Document any test patterns or discoveries

---

**Test Status:** ✅ Base tests implemented | ⚠️ Integration tests pending | ⚠️ API tests pending
