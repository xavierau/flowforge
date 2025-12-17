# Development Commands Reference

## Package Management

**CRITICAL: Always use `uv`, NOT `pip`**

```bash
# Install/sync all dependencies
uv sync

# Add new package
uv pip install <package>

# Remove package
uv pip uninstall <package>

# Update dependencies
uv pip install --upgrade <package>
```

## Database Migrations

```bash
# Show current migration version
alembic current

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Create new migration (auto-generate from models)
alembic revision --autogenerate -m "description"

# Create empty migration
alembic revision -m "description"
```

## Running Services

### Development Mode

```bash
# Start API server (port 8000)
uvicorn app.main:app --reload

# Start API on custom port
uvicorn app.main:app --reload --port 8001

# Start Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# Start Celery worker with auto-reload
watchmedo auto-restart --directory=./app --pattern=*.py --recursive -- celery -A app.tasks.celery_app worker --loglevel=info
```

### Production Mode

```bash
# Start API with multiple workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Start Celery with concurrency
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
```

## Testing

### Running Tests

```bash
# Run all tests (recommended - uses uv)
uv run python -m pytest tests/ -v

# Run with coverage report
uv run python -m pytest tests/ --cov=app --cov-report=term-missing

# Run specific test directory
uv run python -m pytest tests/unit -v
uv run python -m pytest tests/integration -v

# Run specific test file
uv run python -m pytest tests/unit/test_models.py -v

# Run specific test function
uv run python -m pytest tests/unit/test_models.py::test_document_creation -v

# Stop on first failure
uv run python -m pytest tests/ -x

# Run tests matching a pattern
uv run python -m pytest tests/ -k "auth" -v
```

### Test Environment Configuration

The test environment is configured in `tests/conftest.py` with the following settings:

#### Test Database URL

Tests use PostgreSQL by default (required for JSONB column support). The database URL can be configured via environment variable:

```bash
# Default test database URL
TEST_DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/doc_processing

# Override for CI/CD or different environments
TEST_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/test_db uv run python -m pytest tests/ -v
```

**Note:** Tests automatically create and drop tables for isolation. Each test function gets a fresh database state.

#### Rate Limiting in Tests

Rate limiting is **disabled by default** in the test environment to prevent test interference. This is controlled by the `RATE_LIMIT_ENABLED` environment variable.

```bash
# Default behavior (rate limiting disabled)
uv run python -m pytest tests/ -v

# Enable rate limiting for specific tests
RATE_LIMIT_ENABLED=true uv run python -m pytest tests/integration/api/test_rate_limiting.py -v
```

**How it works:**
- `tests/conftest.py` sets `RATE_LIMIT_ENABLED=false` before importing app modules
- When disabled, each request gets a unique key, bypassing rate limits
- Rate limiting tests are automatically skipped when rate limiting is disabled

**Files involved:**
- `app/config.py` - `rate_limit_enabled: bool = True` setting
- `app/dependencies/rate_limit.py` - Conditional rate limiting logic
- `tests/conftest.py` - Sets `RATE_LIMIT_ENABLED=false`
- `tests/integration/api/test_rate_limiting.py` - Skipped when rate limiting disabled

### Test Markers

```bash
# Run only unit tests
uv run python -m pytest tests/ -m unit

# Run only integration tests
uv run python -m pytest tests/ -m integration

# Run workflow tests
uv run python -m pytest tests/ -m workflow

# Run tests requiring PostgreSQL
uv run python -m pytest tests/ -m postgres

# Run Conductor integration tests (requires Conductor server)
uv run python -m pytest tests/ --conductor-integration -m conductor
```

### Available Test Fixtures

Key fixtures defined in `tests/conftest.py`:

| Fixture | Description |
|---------|-------------|
| `db_session` | Fresh database session per test |
| `client` | FastAPI TestClient with DB override |
| `test_tenant` | Test tenant entity |
| `test_user` | Regular test user (member role) |
| `test_admin_user` | Admin test user |
| `auth_headers` | JWT auth headers for test_user |
| `admin_auth_headers` | JWT auth headers for admin |
| `seed_roles` | Seed admin/member/viewer roles |
| `seed_permissions` | Seed all permissions |

## Code Quality

```bash
# Format code with Black
black app tests

# Check formatting without changes
black --check app tests

# Lint code with Ruff
ruff check app tests

# Auto-fix linting issues
ruff check --fix app tests

# Type checking with mypy
mypy app

# Run all quality checks
black app tests && ruff check app tests && mypy app
```

## Docker Commands

```bash
# Start all services (detached)
docker-compose up -d

# Start specific service
docker-compose up -d postgres

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f postgres

# Rebuild services
docker-compose build

# Rebuild and restart
docker-compose up -d --build

# Execute command in running container
docker-compose exec api bash
docker-compose exec postgres psql -U postgres

# Run migrations in Docker
docker-compose exec api alembic upgrade head
```

## Database Management

```bash
# Connect to PostgreSQL (local)
psql -h localhost -U postgres -d ai_document_processing

# Connect to PostgreSQL (Docker)
docker-compose exec postgres psql -U postgres -d ai_document_processing

# Dump database
pg_dump -h localhost -U postgres ai_document_processing > backup.sql

# Restore database
psql -h localhost -U postgres ai_document_processing < backup.sql

# Reset database (development only)
docker-compose down -v
docker-compose up -d postgres
docker-compose exec api alembic upgrade head
```

## Celery Monitoring

```bash
# Check active tasks
celery -A app.tasks.celery_app inspect active

# Check scheduled tasks
celery -A app.tasks.celery_app inspect scheduled

# Check registered tasks
celery -A app.tasks.celery_app inspect registered

# Purge all tasks from queue
celery -A app.tasks.celery_app purge

# Monitor tasks in real-time (Flower)
celery -A app.tasks.celery_app flower
```

## Useful Development Shortcuts

```bash
# Start development environment
docker-compose up -d && docker-compose logs -f api

# Restart API after code changes (Docker)
docker-compose restart api && docker-compose logs -f api

# Clean everything and start fresh
docker-compose down -v && docker-compose up -d --build && docker-compose exec api alembic upgrade head

# Run tests in Docker
docker-compose exec api pytest

# Check API health
curl http://localhost:8000/health
```

## Environment Variables

Required variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/ai_document_processing

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Storage
STORAGE_BACKEND=local  # or "s3"
LOCAL_STORAGE_PATH=./storage

# VLLM Providers
GOOGLE_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
```

### Test Environment Variables

These variables configure the test environment:

```bash
# Test database URL (separate from production/development)
# Default: postgresql+psycopg://postgres:password@localhost:5432/doc_processing
TEST_DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/test_db

# Rate limiting toggle (default: true in production, false in tests)
# Set to "false" to disable rate limiting (useful for testing)
RATE_LIMIT_ENABLED=false
```

### Rate Limiting Configuration

The `RATE_LIMIT_ENABLED` setting controls whether rate limiting is active:

| Environment | Default | Description |
|-------------|---------|-------------|
| Production | `true` | Rate limiting enabled to protect against abuse |
| Development | `true` | Rate limiting enabled (can be disabled if needed) |
| Testing | `false` | Rate limiting disabled to prevent test interference |

Rate limits in production (when enabled):
- `/api/v1/auth/login` - 10 requests/minute
- `/api/v1/auth/forgot-password` - 3 requests/minute
- `/api/v1/auth/reset-password` - 5 requests/minute
- `/api/v1/auth/accept-invitation` - 5 requests/minute
