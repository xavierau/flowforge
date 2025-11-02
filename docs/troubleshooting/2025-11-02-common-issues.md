# Common Issues and Solutions

## Issue 1: SQLAlchemy Reserved Word - 'metadata'

**Error:**
```
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
```

**Root Cause:** SQLAlchemy reserves the `metadata` attribute on declarative models.

**Solution Applied:**
- Column renamed from `metadata` → `document_metadata` in:
  - `app/models/document.py:26`
  - `alembic/versions/2025-11-02_001_initial_schema.py:32`
- All references updated across codebase

**Prevention:** Never use `metadata` as a column name in SQLAlchemy models.

---

## Issue 2: Pydantic Reserved Word - 'model_config'

**Error:**
```
pydantic.errors.PydanticUserError: "Config" and "model_config" cannot be used together

For further information visit https://errors.pydantic.dev/2.11/u/config-both
```

**Root Cause:** Pydantic v2 reserves `model_config` as a class attribute for configuration.

**Solution Applied:**
- Field renamed from `model_config` → `model_provider_config` in:
  - `app/schemas/extraction.py:36`
  - `app/api/documents.py:143, 154, 155`

**Prevention:** Never use `model_config` as a field name in Pydantic models.

---

## Issue 3: Protobuf Compatibility (Python 3.12)

**Error:**
```
AttributeError: module 'google._upb._message' has no attribute 'MessageMapContainer'
```

**Root Cause:** Python 3.12.1 has incompatibility with the protobuf version required by `google-generativeai`.

**Solutions (in order of preference):**

### Option 1: Use Docker (Recommended)
```bash
docker-compose up -d
docker-compose exec api alembic upgrade head
```
Docker handles all dependency compatibility automatically.

### Option 2: Downgrade to Python 3.11
```bash
# Using pyenv
pyenv install 3.11.9
pyenv local 3.11.9

# Recreate virtual environment
uv venv --python 3.11
source .venv/bin/activate

# Reinstall dependencies
uv sync
```

### Option 3: Pin Exact Versions
Update `pyproject.toml`:
```toml
dependencies = [
    "protobuf==4.25.3",
    "proto-plus==1.24.0",
    "google-generativeai==0.7.0",
    # ... rest of dependencies
]
```

Then run:
```bash
uv sync
```

**Additional Resources:** See `SETUP_NOTES.md` for detailed troubleshooting steps.

---

## Issue 4: Missing boto3 Module

**Error:**
```
ModuleNotFoundError: No module named 'boto3'
```

**Root Cause:** boto3 is imported at module level but only needed when using S3 storage backend.

**Solution Applied:**
- Made boto3 import conditional in `app/services/storage.py`
- Import only happens inside `S3StorageBackend.__init__()`
- Uses `TYPE_CHECKING` for type hints

**If you need S3 storage:**
```bash
uv pip install boto3
```

**Configuration:**
```bash
# .env file
STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
S3_BUCKET_NAME=your_bucket_name
AWS_REGION=us-east-1
```

---

## Issue 5: Jobs Stuck in "processing" Status

**Symptoms:**
- Jobs remain in "processing" status indefinitely
- Worker logs show task completed or crashed
- Database shows old `started_at` timestamp

**Root Cause:** Worker crashed mid-task without updating job status.

**Diagnosis:**
```sql
-- Find stuck jobs
SELECT id, status, started_at, updated_at
FROM extraction_jobs
WHERE status = 'processing'
  AND started_at < NOW() - INTERVAL '10 minutes';
```

**Solution:**
```sql
-- Manual reset (development only)
UPDATE extraction_jobs
SET status = 'queued', started_at = NULL
WHERE status = 'processing'
  AND started_at < NOW() - INTERVAL '10 minutes';
```

**Prevention:**
- Use Celery task timeouts: `task_time_limit=600`
- Implement task heartbeat monitoring
- Use proper exception handling in tasks

---

## Issue 6: VLLM API Failures

**Symptoms:**
- Tasks fail with API errors
- Rate limit errors
- Timeout errors

**Common Causes:**

### Rate Limiting
```
Error: Rate limit exceeded (429)
```

**Solution:**
- Implement exponential backoff in tasks
- Use Celery retry with delay: `default_retry_delay=60`
- Consider task queuing/throttling

### Invalid API Key
```
Error: Invalid API key (401)
```

**Solution:**
```bash
# Verify API keys in .env
echo $GOOGLE_API_KEY
echo $OPENAI_API_KEY

# Test API key manually
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

### Network Timeouts
```
Error: Request timed out
```

**Solution:**
- Increase timeout in VLLM provider configuration
- Check network connectivity
- Consider using different provider as fallback

**Fallback Strategy:**
```python
# In extraction task
try:
    result = await vllm_service.extract(provider="google", ...)
except ProviderError:
    logger.warning("Google API failed, trying OpenAI fallback")
    result = await vllm_service.extract(provider="openai", ...)
```

---

## Issue 7: PDF Conversion Fails

**Error:**
```
FileNotFoundError: pdftoppm not found
```

**Root Cause:** Missing poppler-utils dependency.

**Solution:**

### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install poppler-utils
```

### macOS
```bash
brew install poppler
```

### Docker
Already included in Dockerfile:
```dockerfile
RUN apt-get update && apt-get install -y poppler-utils
```

**Test conversion:**
```bash
pdftoppm -v  # Should show version
```

---

## Issue 8: Database Connection Pool Exhausted

**Error:**
```
sqlalchemy.exc.TimeoutError: QueuePool limit exceeded
```

**Root Cause:** Too many concurrent database connections.

**Solution:**

### Increase pool size
```python
# app/db/session.py
engine = create_engine(
    settings.database_url,
    pool_size=20,        # Increase from default 10
    max_overflow=40,     # Increase from default 20
    pool_pre_ping=True,
)
```

### Fix connection leaks
Ensure all database sessions are properly closed:
```python
# Always use try/finally
db = SessionLocal()
try:
    # Database operations
    db.commit()
except Exception:
    db.rollback()
    raise
finally:
    db.close()  # CRITICAL
```

---

## Issue 9: Celery Worker Not Processing Tasks

**Symptoms:**
- Tasks queued but not executing
- Worker appears idle
- No errors in logs

**Diagnosis:**
```bash
# Check worker status
celery -A app.tasks.celery_app inspect active

# Check registered tasks
celery -A app.tasks.celery_app inspect registered

# Check queue length
celery -A app.tasks.celery_app inspect stats
```

**Common Causes:**

### 1. Worker not started
```bash
# Start worker
celery -A app.tasks.celery_app worker --loglevel=info
```

### 2. Wrong queue name
```python
# Ensure task uses correct queue
@celery_app.task(queue='default')  # Match worker queue
def my_task():
    pass
```

### 3. Redis connection issue
```bash
# Test Redis connection
redis-cli ping  # Should return "PONG"

# Check Redis connection in logs
docker-compose logs worker | grep -i redis
```

---

## Issue 10: File Upload Fails

**Error:**
```
413 Request Entity Too Large
```

**Root Cause:** File size exceeds limit.

**Solution:**

### Increase FastAPI limit
```python
# app/main.py
app = FastAPI(
    title="AI Document Processing",
    max_request_size=50 * 1024 * 1024,  # 50MB
)
```

### Increase Nginx limit (if using reverse proxy)
```nginx
client_max_body_size 50M;
```

### Update application settings
```python
# app/core/config.py
class Settings(BaseSettings):
    max_file_size_bytes: int = 50 * 1024 * 1024  # 50MB
```

---

## Debugging Checklist

When encountering issues, check in this order:

1. **Environment Variables:** Verify all required variables in `.env`
2. **Database Connection:** Test PostgreSQL connectivity
3. **Redis Connection:** Test Redis connectivity
4. **API Keys:** Verify VLLM provider API keys
5. **Service Status:** Ensure all services are running (API, worker, DB, Redis)
6. **Logs:** Check logs for error messages
7. **Dependencies:** Verify all packages installed with correct versions

## Getting Help

1. Check this troubleshooting guide
2. Review `SETUP_NOTES.md` for environment issues
3. Check logs: `docker-compose logs -f`
4. Review database state: SQL queries in Issue #5
5. Test individual components in isolation
