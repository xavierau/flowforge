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

```bash
# Run all tests
pytest

# Run specific test directory
pytest tests/unit
pytest tests/integration

# Run with coverage report
pytest -v --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_models.py

# Run specific test function
pytest tests/unit/test_models.py::test_document_creation

# Run with verbose output
pytest -v

# Stop on first failure
pytest -x
```

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
