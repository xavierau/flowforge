# AI Document Processing - Quick Reference

AI-powered document processing SaaS using Vision Language Models (VLLMs) with stateless job processing architecture.

**CRITICAL: Always use context7 to verify API usage. Always use @agent-solution-architect, @agent-bug-hunter, and @agent-code-review-analyzer for backend code implementation. Always use @agent-react-best-practices-expert for ONLY editing .ts and .tsx files (React/TypeScript frontend code).**

---

## 📚 Documentation Index

### Guides
- **[Development Commands](../docs/guides/2025-11-02-development-commands.md)** - Complete CLI reference for uv, migrations, testing, Docker
- **[Auth Implementation Guide](../docs/guides/2025-11-03-auth-implementation-guide.md)** - How to protect routes with JWT authentication and permissions
- **[API Endpoint Security](../docs/guides/2025-11-04-api-endpoint-security.md)** - Complete security reference for API development (authentication, permissions, API tokens)
- **[Workflow Builder - User Guide](../docs/guides/2025-11-15-workflow-builder-user-guide.md)** ✨ NEW - Complete guide to visual workflow builder with 5 node types
- **[Workflow Builder - Quick Reference](../docs/guides/2025-11-15-workflow-builder-quick-reference.md)** ✨ NEW - Cheat sheet for workflow builder
- **[Workflow Builder - Examples](../docs/guides/2025-11-15-workflow-examples.md)** ✨ NEW - 7 real-world workflow patterns with configurations

### Architecture
- **[Stateless Job Processing](../docs/architecture/2025-11-02-stateless-job-processing.md)** - Core design principles, state machines, retry strategies
- **[VLLM Integration](../docs/architecture/2025-11-02-vllm-integration.md)** - Multi-provider setup, invoice extraction, adding providers
- **[JWT Authentication & Multi-Tenancy](../docs/architecture/2025-11-03-jwt-authentication-and-multi-tenancy.md)** - Complete auth architecture, security, and patterns
- **[Astro Public Site Architecture](../docs/architecture/2025-11-03-astro-public-site-architecture.md)** - Multi-site setup with Astro for marketing, nginx config, Cloudflare Pages deployment
- **[Workflow Builder Architecture](../docs/architecture/2025-11-15-workflow-builder-architecture.md)** ✨ NEW - Technical implementation, state management, expression system

### Frontend (React + Tailwind)
- **[Testing Guide](../frontend/TESTING_GUIDE.md)** - Complete testing checklist for JSON Schema Builder
- **[Implementation Status](../frontend/IMPLEMENTATION_STATUS.md)** - Progress tracker and phase completion
- **[Expression Syntax](../frontend/EXPRESSION_SYNTAX.md)** ✨ NEW - Complete reference for workflow expression syntax
- **[Workflow Builder README](../frontend/README.md)** - Frontend setup and API wrapper guide (includes workflow builder)

### Troubleshooting
- **[Common Issues & Solutions](../docs/troubleshooting/2025-11-02-common-issues.md)** - All known issues with fixes
- **[Setup Notes](../SETUP_NOTES.md)** - Environment setup and Python 3.12 protobuf issue

### Testing & Schema
- **[Test Results](../TEST_RESULTS.md)** - Complete API testing workflows with examples
- **[Invoice Schema](../invoice_schema.json)** - Production-ready invoice extraction schema

---

## 🚀 Quick Start

### Docker Services (Already Running)
PostgreSQL and Redis containers are already running with container names `postgre` and `redis`. No need to spin up these services.

```bash
# Verify Docker services are running
docker ps | grep -E 'postgres|redis'

# Access PostgreSQL (container name: postgres)
docker exec -it postgre psql -U postgres -d ai_document_processing

# Access Redis (container name: redis)
docker exec -it redis redis-cli
```

### Local Development (Using Existing Docker Services)
```bash
# Install dependencies (use uv, NOT pip)
uv sync

# Apply migrations (connects to Docker postgres container)
alembic upgrade head

# Start services (2 terminals)
uvicorn app.main:app --reload                          # Terminal 1
celery -A app.tasks.celery_app worker --loglevel=info  # Terminal 2

# Test API
curl http://localhost:8000/health
```

**Connection URLs (in .env):**
- PostgreSQL: `postgresql://postgres:password@localhost:5432/ai_document_processing`
- Redis: `redis://localhost:6379/0`

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

**MANDATORY: Use @agent-react-best-practices-expert for ONLY editing .ts and .tsx files (React/TypeScript code). Do NOT use this agent for documentation, markdown, or other file types.**

**Tech Stack:**
- React 19 + TypeScript 5.6+
- Vite 7 (dev server & build)
- Tailwind CSS 4 (use context7 to verify API usage)
- Zustand 5 (state management)
- shadcn/ui components
- Lucide icons

**Critical Rules:**
1. **MANDATORY: All remote API calls MUST use the centralized API wrapper**
   - ❌ NEVER use raw `fetch()` for API calls
   - ✅ ALWAYS use `apiFetch()` wrapper in service files
   - The wrapper provides:
     - Automatic auth header injection
     - 401 interceptor with auto-redirect to login
     - Consistent error handling across all services
   - Pattern:
     ```typescript
     // Define apiFetch in each service file
     async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
       const token = localStorage.getItem('access_token');
       const headers = new Headers(options.headers);
       if (token && !headers.has('Authorization')) {
         headers.set('Authorization', `Bearer ${token}`);
       }
       const response = await fetch(url, { ...options, headers });
       if (response.status === 401) {
         localStorage.removeItem('access_token');
         localStorage.removeItem('refresh_token');
         window.location.href = '/login';
         throw new Error('Unauthorized - Please log in again');
       }
       return response;
     }

     // Use in API functions
     export async function getData(): Promise<Data> {
       const response = await apiFetch(`${API_BASE_URL}/data`, {
         headers: { 'Content-Type': 'application/json' }
       });
       return handleApiResponse(response);
     }
     ```
   - See: `src/lib/api.ts`, `src/services/user.service.ts`, `src/services/subscription.service.ts`

2. **Always use context7** to verify Tailwind CSS 4 API syntax before using utilities
   - Tailwind 4 has breaking changes from v3
   - CSS variables require direct properties, not @apply directives
   - Example: Use `background-color: hsl(var(--background))` NOT `@apply bg-background`

3. **Always use @agent-react-best-practices-expert** for:
   - React component implementation
   - useEffect management
   - State management with Zustand
   - Component composition and architecture
   - Performance optimization

4. **shadcn/ui dependency management:**
   - Manually install peer dependencies: `class-variance-authority`, `@radix-ui/react-icons`
   - Use `npx shadcn@latest add [component]` for components
   - Check package.json after installation

**Frontend File Structure:**
```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/                     # shadcn/ui components
│   │   ├── layout/                 # Layout system (NEW)
│   │   │   ├── AuthenticatedLayout.tsx  # Main app shell
│   │   │   ├── Navbar.tsx               # Top navigation
│   │   │   ├── Sidebar.tsx              # Side navigation
│   │   │   ├── Breadcrumb.tsx           # Breadcrumb component
│   │   │   ├── Page.tsx                 # Page container
│   │   │   ├── PageHeader.tsx           # Page header
│   │   │   ├── PageContent.tsx          # Content wrapper
│   │   │   ├── ProtectedRoute.tsx       # Auth guard
│   │   │   └── index.ts                 # Exports
│   │   ├── preview/                # JSON preview components
│   │   ├── schema-builder/         # Schema tree & editor
│   │   └── templates/              # Template loading UI
│   ├── pages/                      # Application pages (NEW)
│   │   ├── Dashboard.tsx           # Main dashboard
│   │   ├── SchemaBuilder.tsx       # Schema creation page
│   │   ├── Login.tsx               # Login page
│   │   ├── Signup.tsx              # Registration page
│   │   └── LandingPage.tsx         # Public landing
│   ├── services/                   # API services (NEW)
│   │   └── auth.service.ts         # Authentication API
│   ├── lib/
│   │   ├── utils.ts                # cn() utility
│   │   ├── api.ts                  # API client
│   │   ├── schema-converter.ts     # JSON Schema conversion
│   │   └── template-loader.ts      # Template utilities
│   ├── store/
│   │   └── schemaStore.ts          # Zustand state management
│   ├── types/
│   │   ├── schema.ts               # Type definitions
│   │   ├── auth.ts                 # Auth types (NEW)
│   │   ├── user.ts                 # User types (NEW)
│   │   └── template.ts             # Template types
│   └── templates/                  # Pre-built schemas
```

**Layout System (NEW):**

**Component Composition Pattern:**
```tsx
// Every authenticated page should use this pattern
<Page>
  <PageHeader
    breadcrumbs={[
      { label: 'Dashboard', href: '/dashboard' },
      { label: 'Current Page' }
    ]}
    title="Page Title"
    subtitle="Optional description"
  />
  <PageContent>
    {/* Your page content */}
  </PageContent>
</Page>
```

**Layout Component Guidelines:**

1. **Page Component** - Top-level container with consistent spacing
   - Use for ALL authenticated pages
   - Provides `p-6` padding and `space-y-6` vertical spacing
   - Import from `@/components/layout`

2. **PageHeader Component** - Standardized header
   - Required `title` prop
   - Optional `breadcrumbs` array (shows navigation trail)
   - Optional `subtitle` for description
   - Always use semantic `<h1>` for title

3. **PageContent Component** - Main content wrapper
   - Wraps all page content below header
   - Provides `space-y-6` vertical spacing
   - Semantic `<section>` element with ARIA labels

4. **Breadcrumb Navigation**
   - Use for all nested pages (depth > 1)
   - Last item should NOT have `href` (current page)
   - Integrates with React Router
   - Example: `[{ label: 'Home', href: '/' }, { label: 'Current' }]`

5. **AuthenticatedLayout** - Main app shell
   - Wraps all authenticated routes in App.tsx
   - Manages sidebar and navbar state
   - Sidebar state persists to localStorage
   - Don't nest AuthenticatedLayout components

6. **ProtectedRoute** - Authentication guard
   - Wrap all authenticated routes
   - Checks `isAuthenticated()` status
   - Redirects to `/login` if not authenticated
   - Pattern: `<ProtectedRoute><AuthenticatedLayout><YourPage /></AuthenticatedLayout></ProtectedRoute>`

**Creating New Pages:**
```tsx
// 1. Create page component in src/pages/
export function MyPage() {
  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'My Page' }
        ]}
        title="My Page"
        subtitle="Page description"
      />
      <PageContent>
        {/* Your content */}
      </PageContent>
    </Page>
  );
}

// 2. Add route in App.tsx
<Route
  path="/my-page"
  element={
    <ProtectedRoute>
      <AuthenticatedLayout>
        <MyPage />
      </AuthenticatedLayout>
    </ProtectedRoute>
  }
/>

// 3. Add to Sidebar.tsx navigation
{ label: 'My Page', href: '/my-page', icon: MyIcon }
```

**Documentation:**
- Full layout system guide: `frontend/LAYOUT_SYSTEM.md`
- Component reference: `frontend/COMPONENT_REFERENCE.md`
- Auth implementation: `frontend/AUTH_IMPLEMENTATION.md`

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

# Database connection (container name: postgres)
docker exec -it postgres psql -U postgres -d ai_document_processing

# Redis connection (container name: redis)
docker exec -it redis redis-cli
docker exec -it redis redis-cli PING  # Should return PONG
```

### View Logs
```bash
# Docker container logs
docker logs -f postgres
docker logs -f redis

# Local application logs (check terminal output)
# API server: uvicorn terminal
# Celery worker: celery terminal
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
8. **Use enums for constants** - NEVER use magic strings, always use type-safe enums

#### Type Safety: Enums and Constants (CRITICAL)

**MANDATORY: Use enums instead of magic strings for all status fields, transaction types, and domain constants.**

**Why Enums?**
- ✅ Type safety - IDE autocomplete and compile-time checking
- ✅ Single source of truth - All valid values defined once
- ✅ Refactoring safety - Easy to find all usages
- ✅ Runtime validation - Catch invalid values before database
- ❌ Magic strings cause bugs - Typos only caught at runtime

**Backend Pattern (Python):**
```python
# Define enums in app/models/enums.py using str, Enum pattern
from enum import Enum

class CreditTransactionType(str, Enum):
    """Transaction types (matches database schema)"""
    DEDUCTION = "deduction"
    TOPUP = "topup"
    REFUND = "refund"
    # ...

class ReferenceType(str, Enum):
    """Reference types for transactions"""
    EXTRACTION_JOB = "extraction_job"
    PAYMENT = "payment"
    # ...

# Usage in code - use enum values, not strings
from app.models.enums import CreditTransactionType, ReferenceType

# ✅ CORRECT - Type-safe with IDE support
transaction_type=CreditTransactionType.DEDUCTION.value

# ❌ WRONG - Magic string, no type safety
transaction_type="deduction"
```

**Add Validators to Models:**
```python
from sqlalchemy.orm import validates
from app.models.enums import CreditTransactionType

class CreditTransaction(Base):
    @validates('transaction_type')
    def validate_transaction_type(self, key, value):
        if isinstance(value, CreditTransactionType):
            return value.value
        if value not in [t.value for t in CreditTransactionType]:
            raise ValueError(f"Invalid transaction_type: {value}")
        return value
```

**Frontend Pattern (TypeScript):**
```typescript
// Define in frontend/src/types/enums.ts - MUST match backend exactly
export enum CreditTransactionType {
  DEDUCTION = "deduction",
  TOPUP = "topup",
  REFUND = "refund",
  // ...
}

// ✅ CORRECT - Type-safe
const type: CreditTransactionType = CreditTransactionType.DEDUCTION;

// ❌ WRONG - Magic string
const type = "deduction";
```

**Key Rules:**
- All enums in `app/models/enums.py` (backend) and `frontend/src/types/enums.ts` (frontend)
- Frontend enums MUST match backend values exactly
- Use `str, Enum` pattern in Python for JSON/database compatibility
- Add validators to SQLAlchemy models for runtime safety
- Update both files when adding new enum values

**See:** `debugging_journals/2025-11-05-credit-deduction-not-recorded.md` for real example of magic string bug

#### API Endpoint Security (CRITICAL)
**MANDATORY: Follow the API security patterns documented in [API Endpoint Security Guide](../docs/guides/2025-11-04-api-endpoint-security.md)**

**Quick Security Checklist for New Endpoints:**
- [ ] Choose correct authentication method:
  - Public endpoints (health checks) → No auth
  - Self-service (profile, tokens) → `get_current_active_user` (JWT-only, no permission)
  - Sensitive operations (users, billing) → `require_permission("...")` (JWT-only)
  - Core API (documents, jobs, schemas) → `require_permission_flexible("...")` (JWT + API tokens)
- [ ] Use correct permission for the operation (match `resource:action` pattern)
- [ ] Add tenant isolation to ALL database queries (`filter(Model.tenant_id == current_user.tenant_id)`)
- [ ] Document permission requirements in docstring
- [ ] Test with both JWT and API tokens (if using flexible auth)

**Common Patterns:**
```python
# Pattern 1: Core API operation (supports both JWT and API tokens)
from app.dependencies.auth import require_permission_flexible

@router.post("/documents/upload")
async def upload_document(
    current_user: User = Depends(require_permission_flexible("documents:create"))
):
    # Works with BOTH JWT and API tokens
    # API tokens: checks "documents:create" in scopes
    # JWT: checks "documents:create" in role permissions
    pass

# Pattern 2: Sensitive operation (JWT-only)
from app.dependencies.auth import require_permission

@router.post("/users/invite")
async def invite_user(
    current_user: User = Depends(require_permission("users:invite"))
):
    # ONLY JWT tokens work (no API token support)
    pass

# Pattern 3: Always filter by tenant
document = (
    db.query(Document)
    .filter(Document.tenant_id == current_user.tenant_id)  # CRITICAL
    .filter(Document.id == document_id)
    .first()
)
```

**Available Permissions:**
- Documents: `documents:create`, `documents:read`, `documents:update`, `documents:delete`
- Jobs: `extraction:create`, `jobs:read`
- Schemas: `schemas:create`, `schemas:read`, `schemas:update`, `schemas:delete`
- Users: `users:invite`, `users:read`, `users:update`, `users:delete`
- Tenant: `tenant:manage`, `tenant:billing`

**See:** [API Endpoint Security Guide](../docs/guides/2025-11-04-api-endpoint-security.md) for complete reference

### Frontend Development
1. **MANDATORY: Use API wrapper for ALL remote calls** - NEVER use raw `fetch()`, always use `apiFetch()` wrapper
2. **Use @agent-react-best-practices-expert** - For ONLY editing .ts and .tsx files (React/TypeScript code). Do NOT use for documentation, config files, or other file types
3. **Verify Tailwind 4 with context7** - BEFORE using any Tailwind utilities
4. **Check shadcn/ui dependencies** - Manually install peer deps after adding components
5. **State management** - Use Zustand store, avoid prop drilling
6. **Component patterns** - Prefer composition over complexity, keep components focused
7. **CSS variables** - Use direct properties in Tailwind 4, not @apply directives
8. **TypeScript strict mode** - Ensure type safety throughout components

---

## 📖 Further Reading

- [Frontend README](../frontend/README.md) - Complete frontend documentation with API wrapper guide
- [Development Commands Guide](../docs/guides/2025-11-02-development-commands.md) - Complete CLI reference
- [Stateless Architecture](../docs/architecture/2025-11-02-stateless-job-processing.md) - Deep dive into design
- [VLLM Integration](../docs/architecture/2025-11-02-vllm-integration.md) - Provider setup and usage
- [Troubleshooting Guide](../docs/troubleshooting/2025-11-02-common-issues.md) - All known issues
- [API Documentation](http://localhost:8000/docs) - Interactive Swagger UI (when running)

---

**Last Updated:** 2025-11-06
**Version:** 1.6 (Added mandatory enum/constants guidelines; Fixed credit transaction type bug; Added type safety best practices)
