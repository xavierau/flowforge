# Auth Dependencies - Quick Reference

**One-Page Reference for FastAPI Authentication & Authorization**

---

## Import Statement

```python
from fastapi import APIRouter, Depends, Request
from app.dependencies.auth import (
    get_current_user,
    get_current_active_user,
    require_permission,
    require_role,
    require_any_permission,
    require_all_permissions,
    require_verified_email,
)
from app.middleware import get_tenant_id, get_user_id
from app.models import User
```

---

## Dependencies Quick Reference

| Dependency | Use Case | Returns | Raises |
|------------|----------|---------|--------|
| `get_current_user` | Any authenticated user | `User` | 401, 404 |
| `get_current_active_user` | Active users only | `User` | 401, 403, 404 |
| `require_permission("perm")` | Specific permission | `User` | 401, 403 |
| `require_role("role")` | Specific role | `User` | 401, 403 |
| `require_any_permission([...])` | At least one permission | `User` | 401, 403 |
| `require_all_permissions([...])` | All permissions | `User` | 401, 403 |
| `require_verified_email()` | Email verified | `User` | 401, 403 |

---

## Common Patterns

### Public Route (No Auth)
```python
@router.get("/health")
async def health_check():
    return {"status": "ok"}
```

### Authenticated Route
```python
@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {"email": current_user.email}
```

### Active User Only
```python
@router.post("/documents")
async def create_document(current_user: User = Depends(get_current_active_user)):
    # Only active users
    pass
```

### Permission Check
```python
@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(require_permission("documents:delete"))
):
    pass
```

### Role Check
```python
@router.get("/admin/users")
async def list_users(current_user: User = Depends(require_role("admin"))):
    pass
```

### Multiple Permissions (OR)
```python
@router.put("/documents/{doc_id}")
async def update_document(
    doc_id: str,
    current_user: User = Depends(
        require_any_permission(["documents:update:own", "documents:update:all"])
    )
):
    pass
```

### Multiple Permissions (AND)
```python
@router.post("/schemas/{id}/publish")
async def publish_schema(
    id: str,
    current_user: User = Depends(
        require_all_permissions(["schemas:read", "schemas:publish"])
    )
):
    pass
```

---

## Tenant Isolation Pattern

**ALWAYS filter queries by tenant_id:**

```python
@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id  # CRITICAL
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document
```

---

## Tenant Context Middleware

### Access Tenant Context
```python
@router.get("/documents")
async def list_documents(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    # Option 1: From middleware (for logging)
    tenant_id = get_tenant_id(request)

    # Option 2: From current_user (RECOMMENDED)
    tenant_id = current_user.tenant_id
```

### Register Middleware (in `app/main.py`)
```python
from app.middleware import TenantContextMiddleware

app.add_middleware(TenantContextMiddleware)
```

---

## Error Responses

| Status | Error | Meaning |
|--------|-------|---------|
| 401 | `Could not validate credentials` | Invalid/expired token |
| 403 | `User account is inactive` | User is not active |
| 403 | `Missing required permission: X` | Lacks permission |
| 403 | `Required role: X` | Lacks role |
| 404 | `User not found` | User in token doesn't exist |

---

## Common Permissions

| Permission | Description |
|------------|-------------|
| `documents:create` | Create documents |
| `documents:read` | View documents |
| `documents:update` | Modify documents |
| `documents:delete` | Delete documents |
| `documents:update:own` | Update own documents only |
| `documents:update:all` | Update any document |
| `schemas:create` | Create schemas |
| `schemas:read` | View schemas |
| `schemas:publish` | Publish schemas |
| `billing:manage` | Manage billing |
| `users:manage` | Manage team members |

---

## System Roles

| Role | Description |
|------|-------------|
| `admin` | Full access to tenant resources |
| `member` | Standard user access |
| `viewer` | Read-only access |

---

## Testing

### Override Auth Dependency
```python
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies.auth import get_current_user

test_user = User(id="test-id", email="test@example.com", is_active=True)

app.dependency_overrides[get_current_user] = lambda: test_user

client = TestClient(app)
response = client.get("/api/v1/profile")
```

---

## Security Checklist

- ✅ Always use `Authorization: Bearer <token>` header
- ✅ Filter queries by `current_user.tenant_id`
- ✅ Use `get_current_active_user` for most routes
- ✅ Validate ownership before updates/deletes
- ✅ Don't expose internal details in errors
- ✅ Log security events (access denied, etc.)
- ❌ Never query without tenant filter
- ❌ Never trust client-provided tenant_id
- ❌ Never expose stack traces to clients

---

## Example Route Template

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import get_current_active_user, require_permission
from app.models import User, Document

router = APIRouter()

@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get document by ID with tenant isolation."""
    # Query with tenant isolation
    document = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": str(document.id),
        "filename": document.filename,
        "status": document.status
    }


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(require_permission("documents:delete")),
    db: Session = Depends(get_db)
):
    """Delete document - requires documents:delete permission."""
    document = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(document)
    db.commit()

    return {"status": "deleted", "document_id": str(document.id)}
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Could not validate credentials" | Check token format, expiration, and validity |
| "User account is inactive" | Activate user or use `get_current_user` |
| "Missing required permission" | Grant permission via role or custom grant |
| "Required role: admin" | Assign correct role or use permission check |
| `tenant_id` is `None` | Ensure middleware is registered and token is valid |

---

## Need More Details?

- **Full Guide:** [Auth Dependencies Usage](./2025-11-02-auth-dependencies-usage.md)
- **Architecture:** [Auth Dependencies Design](../architecture/2025-11-02-auth-dependencies-design.md)
- **Middleware:** [Middleware Integration](./2025-11-02-middleware-integration.md)

---

**Last Updated:** 2025-11-02
