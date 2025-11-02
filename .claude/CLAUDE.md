# AI Document Processing - Quick Reference

AI-powered document processing SaaS using Vision Language Models (VLLMs) with stateless job processing architecture.

**CRITICAL: Always use context7 to verify API usage. Always use @agent-solution-architect, @agent-bug-hunter, and @agent-code-review-analyzer for backend code implementation. Always use @agent-react-best-practices-expert for frontend/React implementation.**

---

## 📚 Documentation Index

### Guides
- **[Development Commands](../docs/guides/2025-11-02-development-commands.md)** - Complete CLI reference for uv, migrations, testing, Docker

### Architecture
- **[Stateless Job Processing](../docs/architecture/2025-11-02-stateless-job-processing.md)** - Core design principles, state machines, retry strategies
- **[VLLM Integration](../docs/architecture/2025-11-02-vllm-integration.md)** - Multi-provider setup, invoice extraction, adding providers

### Frontend (React + Tailwind)
- **[Testing Guide](../frontend/TESTING_GUIDE.md)** - Complete testing checklist for JSON Schema Builder
- **[Implementation Status](../frontend/IMPLEMENTATION_STATUS.md)** - Progress tracker and phase completion

### Troubleshooting
- **[Common Issues & Solutions](../docs/troubleshooting/2025-11-02-common-issues.md)** - All known issues with fixes
- **[Setup Notes](../SETUP_NOTES.md)** - Environment setup and Python 3.12 protobuf issue

### Testing & Schema
- **[Test Results](../TEST_RESULTS.md)** - Complete API testing workflows with examples
- **[Invoice Schema](../invoice_schema.json)** - Production-ready invoice extraction schema

---

## 🚀 Quick Start

### Using Docker (Recommended)
```bash
# Start all services
docker-compose up -d

# Apply migrations
docker-compose exec api alembic upgrade head

# View logs
docker-compose logs -f api

# Test API
curl http://localhost:8000/health
```

### Local Development
```bash
# Install dependencies (use uv, NOT pip)
uv sync

# Apply migrations
alembic upgrade head

# Start services (2 terminals)
uvicorn app.main:app --reload                          # Terminal 1
celery -A app.tasks.celery_app worker --loglevel=info  # Terminal 2
```

---

## 🏗️ Architecture Summary

### Core Principles
1. **Stateless Jobs** - All state in PostgreSQL, workers are stateless
2. **Two-Stage Pipeline** - PDF→Images (once), Images→JSON (many times)
3. **Service Abstraction** - Storage (local/S3) and VLLM (Google/OpenAI/DeepSeek) abstracted
4. **Clean Architecture** - Domain → Application → Infrastructure → Presentation

### Technology Stack
- **API**: FastAPI with async support
- **Database**: PostgreSQL with JSONB for flexible schemas
- **Queue**: Redis + Celery for job processing
- **VLLM**: Gemini 2.5 Flash (default), GPT-4 Vision, DeepSeek
- **Storage**: Local filesystem or S3

### State Machines

**Document Flow:**
```
uploaded → processing → ready_for_extraction → completed
              ↓
            failed
```

**Extraction Job Flow:**
```
queued → processing → completed
            ↓
          failed
```

---

## 📁 Key Files

### Application Structure
```
app/
├── api/              # FastAPI routes
│   ├── documents.py  # Upload & parse endpoints
│   └── jobs.py       # Status & results endpoints
├── models/           # SQLAlchemy models
│   ├── document.py   # Document & DocumentPage
│   └── extraction.py # ExtractionJob & ExtractionResult
├── services/         # Business logic
│   ├── storage.py    # Storage abstraction (local/S3)
│   └── vllm_service.py  # VLLM provider abstraction
├── tasks/            # Celery tasks
│   ├── document_tasks.py    # PDF → Images
│   └── extraction_tasks.py  # Images → JSON
└── schemas/          # Pydantic models
    └── extraction.py # API request/response schemas
```

### Critical Locations

| Component | File | Lines |
|-----------|------|-------|
| Default VLLM model | `app/services/vllm_service.py` | 115, 194 |
| Metadata column fix | `app/models/document.py` | 26 |
| Model config field fix | `app/schemas/extraction.py` | 36 |
| Stateless task pattern | `app/tasks/extraction_tasks.py` | 120-185 |
| Session management | `app/db/session.py` | All |

---

## ⚠️ Common Issues

### 1. Python 3.12 Protobuf Compatibility
**Error:** `AttributeError: module 'google._upb._message' has no attribute 'MessageMapContainer'`

**Solution:** Use Docker OR Python 3.11

See: [Common Issues Guide](../docs/troubleshooting/2025-11-02-common-issues.md#issue-3-protobuf-compatibility-python-312)

### 2. Reserved Word Conflicts
- **SQLAlchemy:** `metadata` → `document_metadata` (line 26 in `app/models/document.py`)
- **Pydantic:** `model_config` → `model_provider_config` (line 36 in `app/schemas/extraction.py`)

### 3. Jobs Stuck in "processing"
```sql
-- Find stuck jobs
SELECT * FROM extraction_jobs
WHERE status = 'processing'
  AND started_at < NOW() - INTERVAL '10 minutes';
```

**More:** [Common Issues Guide](../docs/troubleshooting/2025-11-02-common-issues.md)

---

## 🧪 Testing

### End-to-End Test Flow

```bash
# 1. Upload document
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@invoice_1.pdf"
# → {"document_id": "..."}

# 2. Submit extraction with schema
curl -X POST http://localhost:8000/api/v1/documents/{doc_id}/parse \
  -H "Content-Type: application/json" \
  -d '{
    "extraction_schema": {...},
    "model_provider_config": {
      "provider": "google",
      "model": "gemini-2.5-flash"
    }
  }'
# → {"extraction_job_id": "..."}

# 3. Check status
curl http://localhost:8000/api/v1/jobs/{job_id}/status

# 4. Get results
curl http://localhost:8000/api/v1/jobs/{job_id}/result
```

**See:** [Test Results](../TEST_RESULTS.md) for complete examples

---

## 💡 Development Patterns

### Adding a VLLM Provider

1. **Implement provider class** in `app/services/vllm_service.py`:
   ```python
   class NewProviderVLLMProvider(VLLMProvider):
       async def extract_from_image(...) -> Tuple[Dict, int, int]:
           # Implementation
   ```

2. **Add API key** to `app/core/config.py`:
   ```python
   newprovider_api_key: str = ""
   ```

3. **Register in VLLMService** (`app/services/vllm_service.py`):
   ```python
   if settings.newprovider_api_key:
       self.providers["newprovider"] = NewProviderVLLMProvider(...)
   ```

4. **Update validation** in `app/api/documents.py` line 140

**Details:** [VLLM Integration Guide](../docs/architecture/2025-11-02-vllm-integration.md#adding-a-new-provider)

### Writing Stateless Tasks

```python
@celery_app.task(bind=True, max_retries=3)
def my_task(self: Task, entity_id: str):
    db = SessionLocal()
    try:
        # ALWAYS query current state from DB
        entity = db.query(Entity).filter(...).first()

        # Update state BEFORE work
        entity.status = "processing"
        db.commit()

        # Perform work
        result = do_work(entity)

        # Update state with results
        entity.status = "completed"
        entity.result = result
        db.commit()

    except Exception as e:
        db.rollback()
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()  # CRITICAL
```

**Details:** [Stateless Job Processing](../docs/architecture/2025-11-02-stateless-job-processing.md)

### Frontend Development (React + Tailwind)

**MANDATORY: Use @agent-react-best-practices-expert for ALL React implementation tasks.**

**Tech Stack:**
- React 19 + TypeScript 5.6+
- Vite 7 (dev server & build)
- Tailwind CSS 4 (use context7 to verify API usage)
- Zustand 5 (state management)
- shadcn/ui components
- Lucide icons

**Critical Rules:**
1. **Always use context7** to verify Tailwind CSS 4 API syntax before using utilities
   - Tailwind 4 has breaking changes from v3
   - CSS variables require direct properties, not @apply directives
   - Example: Use `background-color: hsl(var(--background))` NOT `@apply bg-background`

2. **Always use @agent-react-best-practices-expert** for:
   - React component implementation
   - useEffect management
   - State management with Zustand
   - Component composition and architecture
   - Performance optimization

3. **shadcn/ui dependency management:**
   - Manually install peer dependencies: `class-variance-authority`, `@radix-ui/react-icons`
   - Use `npx shadcn@latest add [component]` for components
   - Check package.json after installation

**Frontend File Structure:**
```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/              # shadcn/ui components
│   │   ├── preview/         # JSON preview components
│   │   ├── schema-builder/  # Schema tree & editor
│   │   └── templates/       # Template loading UI
│   ├── lib/
│   │   ├── utils.ts         # cn() utility
│   │   ├── schema-converter.ts  # JSON Schema conversion
│   │   └── template-loader.ts   # Template utilities
│   ├── store/
│   │   └── schemaStore.ts   # Zustand state management
│   ├── types/
│   │   ├── schema.ts        # Type definitions
│   │   └── template.ts      # Template types
│   └── templates/           # Pre-built schemas
```

**Common Tailwind 4 Fixes:**
- ❌ `@apply border-border` → ✅ `border-color: hsl(var(--border))`
- ❌ `@apply bg-background text-foreground` → ✅ `background-color: hsl(var(--background)); color: hsl(var(--foreground));`

**Development Commands:**
```bash
cd frontend
npm run dev      # Start dev server (http://localhost:3002)
npm run build    # Build for production
npm run preview  # Preview production build
```

---

## 🔍 Debugging

### Check Service Status
```bash
# API health
curl http://localhost:8000/health

# Celery workers
celery -A app.tasks.celery_app inspect active

# Database connection
docker-compose exec postgres psql -U postgres -d ai_document_processing
```

### View Logs
```bash
# Docker logs
docker-compose logs -f api
docker-compose logs -f worker

# Local logs (check terminal output)
```

### Database Queries
```sql
-- Status distribution
SELECT status, COUNT(*) FROM documents GROUP BY status;
SELECT status, COUNT(*) FROM extraction_jobs GROUP BY status;

-- Recent jobs
SELECT * FROM extraction_jobs ORDER BY created_at DESC LIMIT 10;

-- Failed jobs
SELECT * FROM extraction_jobs WHERE status = 'failed';
```

---

## 📝 Environment Variables

Required in `.env`:

```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/ai_document_processing

# Redis/Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Storage
STORAGE_BACKEND=local  # or "s3"
LOCAL_STORAGE_PATH=./storage

# VLLM Providers (at least one required)
GOOGLE_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
```

---

## 🎯 Best Practices

### Backend Development
1. **Always use uv** - Not pip, for package management
2. **Query current state** - Never trust state passed as parameters in tasks
3. **Close DB sessions** - Always use try/finally in Celery tasks
4. **Update before work** - Set status to "processing" before starting work
5. **Use context7** - Verify API usage against latest documentation
6. **Use agents** - @agent-solution-architect, @agent-bug-hunter, @agent-code-review-analyzer
7. **Test thoroughly** - Run pytest before commits

### Frontend Development
1. **Use @agent-react-best-practices-expert** - For ALL React/frontend implementation
2. **Verify Tailwind 4 with context7** - BEFORE using any Tailwind utilities
3. **Check shadcn/ui dependencies** - Manually install peer deps after adding components
4. **State management** - Use Zustand store, avoid prop drilling
5. **Component patterns** - Prefer composition over complexity, keep components focused
6. **CSS variables** - Use direct properties in Tailwind 4, not @apply directives
7. **TypeScript strict mode** - Ensure type safety throughout components

---

## 📖 Further Reading

- [Development Commands Guide](../docs/guides/2025-11-02-development-commands.md) - Complete CLI reference
- [Stateless Architecture](../docs/architecture/2025-11-02-stateless-job-processing.md) - Deep dive into design
- [VLLM Integration](../docs/architecture/2025-11-02-vllm-integration.md) - Provider setup and usage
- [Troubleshooting Guide](../docs/troubleshooting/2025-11-02-common-issues.md) - All known issues
- [API Documentation](http://localhost:8000/docs) - Interactive Swagger UI (when running)

---

**Last Updated:** 2025-11-02
**Version:** 1.1 (Added Frontend Development Guidelines)
