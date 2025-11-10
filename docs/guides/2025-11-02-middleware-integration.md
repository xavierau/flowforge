# Middleware Integration Guide

**Date:** 2025-11-02
**Status:** Active

---

## Integrating Tenant Context Middleware

To enable tenant context extraction in your FastAPI application, add the `TenantContextMiddleware` to `app/main.py`.

### Step 1: Update `app/main.py`

```python
"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import documents, jobs, health, schemas
from app.config import settings
from app.middleware import TenantContextMiddleware  # ADD THIS IMPORT

# Create FastAPI app
app = FastAPI(
    title="AI Document Processing API",
    description="VLLM-powered document processing with custom schema extraction",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ADD TENANT CONTEXT MIDDLEWARE
app.add_middleware(TenantContextMiddleware)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
app.include_router(jobs.router, prefix="/api/v1", tags=["Jobs"])
app.include_router(schemas.router, prefix="/api/v1", tags=["Schemas"])


@app.on_event("startup")
async def startup_event() -> None:
    """Run on application startup."""
    print("🚀 AI Document Processing API starting...")
    print(f"📊 Database: {settings.database_url.split('@')[-1]}")
    print(f"💾 Storage: {settings.storage_type}")
    print(f"🤖 VLLM Providers configured: ", end="")
    providers = []
    if settings.google_api_key:
        providers.append("Google Gemini")
    if settings.openai_api_key:
        providers.append("OpenAI GPT-4V")
    print(", ".join(providers) if providers else "None")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Run on application shutdown."""
    print("👋 AI Document Processing API shutting down...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
```

---

## Step 2: Using Tenant Context in Routes

Once the middleware is registered, you can access tenant context in any route:

```python
from fastapi import Request, APIRouter, Depends
from app.dependencies.auth import get_current_active_user
from app.middleware import get_tenant_id, get_user_id
from app.models import User

router = APIRouter()

@router.get("/documents")
async def list_documents(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List tenant-specific documents."""
    # Option 1: Get tenant_id from middleware
    tenant_id = get_tenant_id(request)

    # Option 2: Use current_user.tenant_id (RECOMMENDED)
    tenant_id = current_user.tenant_id

    # Query with tenant isolation
    documents = db.query(Document).filter(
        Document.tenant_id == tenant_id
    ).all()

    return [{"id": str(d.id), "filename": d.filename} for d in documents]
```

---

## Step 3: Middleware Behavior

### For Authenticated Requests

**Request:**
```http
GET /api/v1/documents
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Middleware extracts:**
- `request.state.tenant_id` → UUID from token
- `request.state.user_id` → UUID from token

---

### For Unauthenticated Requests

**Request:**
```http
GET /health
```

**Middleware behavior:**
- No Authorization header → `request.state.tenant_id` = `None`
- Public routes work normally
- No errors raised

---

### For Invalid Tokens

**Request:**
```http
GET /api/v1/documents
Authorization: Bearer invalid-token
```

**Middleware behavior:**
- Token validation fails → `request.state.tenant_id` = `None`
- Auth dependency will handle the error (401 response)
- Middleware doesn't block the request

---

## Best Practices

### 1. Always Use `current_user.tenant_id` Over Middleware

**Reason:** Auth dependency already queries the user, so tenant_id is readily available.

```python
# PREFERRED: Use current_user.tenant_id
@router.get("/documents")
async def list_documents(current_user: User = Depends(get_current_active_user)):
    tenant_id = current_user.tenant_id
    # Query documents
```

```python
# ACCEPTABLE: Use middleware for logging/metrics
@router.get("/documents")
async def list_documents(request: Request, current_user: User = Depends(get_current_active_user)):
    # Log with tenant context
    logger.info(f"User {get_user_id(request)} accessing documents in tenant {get_tenant_id(request)}")
```

---

### 2. Middleware Order Matters

Middleware is executed in the order it's added (LIFO - Last In, First Out):

```python
# Execution order: CORS → Tenant Context → Routes
app.add_middleware(CORSMiddleware)      # Executes first
app.add_middleware(TenantContextMiddleware)  # Executes second
```

**Recommendation:** Add `TenantContextMiddleware` after CORS but before any custom middleware that depends on tenant context.

---

### 3. Don't Rely on Middleware for Security

**Middleware sets context - it does NOT enforce security:**

```python
# BAD: Middleware alone doesn't protect routes
@router.get("/documents")
async def list_documents(request: Request):
    tenant_id = get_tenant_id(request)  # Could be None!
    # No authentication check - INSECURE
```

```python
# GOOD: Use auth dependency for security
@router.get("/documents")
async def list_documents(
    request: Request,
    current_user: User = Depends(get_current_active_user)  # Enforces auth
):
    tenant_id = current_user.tenant_id  # Guaranteed to exist
    # Secure
```

---

## Troubleshooting

### Issue: `request.state.tenant_id` is always `None`

**Possible Causes:**
1. Middleware not registered in `app/main.py`
2. Authorization header missing or malformed
3. Token is expired or invalid

**Solution:**
```python
# Check if middleware is registered
print(app.middleware_stack)  # Should show TenantContextMiddleware

# Check Authorization header in request
print(request.headers.get("Authorization"))

# Use auth dependency instead (recommended)
current_user = Depends(get_current_active_user)
tenant_id = current_user.tenant_id
```

---

### Issue: Public routes return 401 errors

**Possible Cause:** Using auth dependency on public routes.

**Solution:**
```python
# Public route - no auth dependency
@router.get("/health")
async def health_check():
    return {"status": "healthy"}

# Protected route - use auth dependency
@router.get("/documents")
async def list_documents(current_user: User = Depends(get_current_active_user)):
    return {"documents": []}
```

---

## Advanced Usage

### Custom Middleware for Tenant-Specific Logging

```python
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class TenantLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with tenant context."""

    async def dispatch(self, request: Request, call_next):
        tenant_id = get_tenant_id(request)
        user_id = get_user_id(request)

        # Add tenant context to log
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "tenant_id": str(tenant_id) if tenant_id else None,
                "user_id": str(user_id) if user_id else None
            }
        )

        response = await call_next(request)
        return response

# Register after TenantContextMiddleware
app.add_middleware(TenantContextMiddleware)
app.add_middleware(TenantLoggingMiddleware)
```

---

### Automatic Query Filtering (Future Enhancement)

You can extend the middleware to automatically filter queries by tenant:

```python
from sqlalchemy import event
from sqlalchemy.orm import Session

@event.listens_for(Session, "after_attach")
def receive_after_attach(session, instance):
    """Automatically set tenant_id on new instances."""
    if hasattr(instance, "tenant_id") and not instance.tenant_id:
        # Get tenant_id from request context (requires threading.local or contextvars)
        instance.tenant_id = current_tenant_id.get()
```

**Note:** This is an advanced pattern - implement only if you have many tenant-scoped queries.

---

## Related Documentation

- [Auth Dependencies Usage Guide](./2025-11-02-auth-dependencies-usage.md)
- [Multi-Tenancy Architecture](../architecture/2025-11-02-multi-tenancy.md)
- [FastAPI Middleware Documentation](https://fastapi.tiangolo.com/tutorial/middleware/)

---

**Last Updated:** 2025-11-02
