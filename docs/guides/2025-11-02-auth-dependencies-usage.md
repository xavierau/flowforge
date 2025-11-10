# Authentication Dependencies - Usage Guide

**Date:** 2025-11-02
**Status:** Active
**Author:** System Architecture

---

## Overview

This guide provides practical examples for using authentication and authorization dependencies in FastAPI routes. The auth system provides JWT-based authentication with Role-Based Access Control (RBAC).

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Basic Authentication](#basic-authentication)
3. [Permission-Based Access](#permission-based-access)
4. [Role-Based Access](#role-based-access)
5. [Complex Authorization](#complex-authorization)
6. [Tenant Context](#tenant-context)
7. [Error Handling](#error-handling)
8. [Testing](#testing)

---

## Quick Reference

### Available Dependencies

| Dependency | Purpose | HTTP Status on Failure |
|------------|---------|----------------------|
| `get_current_user` | Authenticate user via JWT | 401 |
| `get_current_active_user` | Authenticate + verify active status | 401, 403 |
| `require_permission(perm)` | Check specific permission | 403 |
| `require_role(role)` | Check specific role | 403 |
| `require_any_permission(perms)` | Check at least one permission | 403 |
| `require_all_permissions(perms)` | Check all permissions | 403 |
| `require_verified_email()` | Check email verification | 403 |

### Import Statements

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

## Basic Authentication

### Any Authenticated User

Use `get_current_user` when you only need to verify the user has a valid token:

```python
from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_user
from app.models import User

router = APIRouter()

@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile - no additional checks."""
    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "tenant_id": str(current_user.tenant_id),
        "is_active": current_user.is_active
    }
```

**When to use:**
- Profile endpoints
- Account settings
- Routes that should work for inactive users (e.g., "activate account" endpoint)

---

### Active Users Only

Use `get_current_active_user` for most authenticated routes:

```python
@router.post("/documents")
async def create_document(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a document - requires active account."""
    # Only active users can create documents
    document = Document(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id
    )
    db.add(document)
    db.commit()
    return {"document_id": str(document.id)}
```

**When to use:**
- Document creation/modification
- Most application functionality
- Any operation that requires an active subscription

---

## Permission-Based Access

### Single Permission Check

Use `require_permission()` for fine-grained access control:

```python
@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(require_permission("documents:delete")),
    db: Session = Depends(get_db)
):
    """Delete a document - requires documents:delete permission."""
    document = db.query(Document).filter(Document.id == doc_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Additional tenant isolation check
    if document.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    db.delete(document)
    db.commit()
    return {"status": "deleted"}
```

**Common Permissions:**
- `documents:create` - Create documents
- `documents:read` - View documents
- `documents:update` - Modify documents
- `documents:delete` - Delete documents
- `schemas:create` - Create extraction schemas
- `schemas:publish` - Publish schemas
- `billing:manage` - Manage billing/subscriptions
- `users:manage` - Manage team members

---

### Multiple Permission Check (OR Logic)

Use `require_any_permission()` when user needs at least one permission:

```python
@router.put("/documents/{doc_id}")
async def update_document(
    doc_id: str,
    current_user: User = Depends(
        require_any_permission([
            "documents:update:own",    # Can update own documents
            "documents:update:all"     # Can update any document
        ])
    ),
    db: Session = Depends(get_db)
):
    """Update a document - requires either update:own OR update:all."""
    document = db.query(Document).filter(Document.id == doc_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check ownership if user only has "update:own" permission
    user_permissions = PermissionService(db).get_user_permissions(current_user)
    if "documents:update:all" not in user_permissions:
        # User only has update:own - verify ownership
        if document.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Can only update own documents")

    # Perform update
    db.commit()
    return {"status": "updated"}
```

**When to use:**
- Owner vs admin permissions
- Read-only vs full access
- Different permission tiers

---

### Multiple Permission Check (AND Logic)

Use `require_all_permissions()` when user needs all permissions:

```python
@router.post("/schemas/{schema_id}/publish")
async def publish_schema(
    schema_id: str,
    current_user: User = Depends(
        require_all_permissions([
            "schemas:read",       # Must be able to read schemas
            "schemas:publish"     # Must be able to publish
        ])
    ),
    db: Session = Depends(get_db)
):
    """Publish a schema - requires both schemas:read AND schemas:publish."""
    schema = db.query(SchemaDefinition).filter(
        SchemaDefinition.id == schema_id
    ).first()

    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    schema.is_published = True
    db.commit()
    return {"status": "published"}
```

**When to use:**
- Complex operations requiring multiple capabilities
- Workflows with multiple steps
- Safety-critical operations

---

## Role-Based Access

### Single Role Check

Use `require_role()` for simple role-based access:

```python
@router.get("/admin/users")
async def list_all_users(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """List all users - admin only."""
    users = db.query(User).all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "role": u.role.name
        }
        for u in users
    ]
```

**System Roles:**
- `admin` - Full access to tenant resources
- `member` - Standard user access
- `viewer` - Read-only access

---

### Custom Role Combinations

You can combine role and permission checks:

```python
@router.post("/admin/tenants")
async def create_tenant(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Create a tenant - admin only."""
    # Additional permission check for extra security
    permission_service = PermissionService(db)
    if not permission_service.user_has_permission(current_user, "tenants:create"):
        raise HTTPException(status_code=403, detail="Missing tenants:create permission")

    # Create tenant logic
    pass
```

---

## Complex Authorization

### Email Verification Requirement

Use `require_verified_email()` for operations requiring verified emails:

```python
@router.post("/documents/{doc_id}/extract")
async def extract_document(
    doc_id: str,
    current_user: User = Depends(require_verified_email()),
    db: Session = Depends(get_db)
):
    """Extract data from document - requires verified email."""
    # Only users with verified emails can use VLLM extraction
    pass
```

---

### Multiple Dependency Layers

You can stack multiple checks:

```python
@router.post("/premium/documents/batch-extract")
async def batch_extract(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Batch extract - requires active account, verified email, and premium permission."""

    # Check email verification
    if not current_user.is_verified:
        raise HTTPException(status_code=403, detail="Email verification required")

    # Check premium permission
    permission_service = PermissionService(db)
    if not permission_service.user_has_permission(current_user, "documents:batch_extract"):
        raise HTTPException(status_code=403, detail="Premium feature - upgrade required")

    # Check credit balance
    if current_user.tenant.credit_balance < 100:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    # Perform batch extraction
    pass
```

**Note:** For complex checks, consider creating a custom dependency function.

---

## Tenant Context

### Accessing Tenant Context from Middleware

The `TenantContextMiddleware` automatically extracts tenant context from JWT tokens:

```python
from fastapi import Request
from app.middleware import get_tenant_id, get_user_id

@router.get("/documents")
async def list_documents(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List documents for current tenant."""
    # Get tenant context from middleware
    tenant_id = get_tenant_id(request)

    # Query documents filtered by tenant
    documents = db.query(Document).filter(
        Document.tenant_id == tenant_id
    ).all()

    return [{"id": str(d.id), "filename": d.filename} for d in documents]
```

---

### Tenant Isolation Pattern

Always enforce tenant isolation in queries:

```python
@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get document by ID - with tenant isolation."""
    document = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id  # CRITICAL: Tenant isolation
    ).first()

    if not document:
        # Don't reveal if document exists in other tenants
        raise HTTPException(status_code=404, detail="Document not found")

    return document
```

**Security Best Practice:**
- ALWAYS filter by tenant_id in queries
- Use `current_user.tenant_id` for filtering
- Don't expose whether resources exist in other tenants

---

## Error Handling

### Standard Error Responses

The auth dependencies automatically return appropriate HTTP errors:

**401 Unauthorized:**
```json
{
  "detail": "Could not validate credentials"
}
```

**403 Forbidden (Inactive User):**
```json
{
  "detail": "User account is inactive"
}
```

**403 Forbidden (Missing Permission):**
```json
{
  "detail": "Missing required permission: documents:delete"
}
```

**403 Forbidden (Missing Role):**
```json
{
  "detail": "Required role: admin"
}
```

---

### Custom Error Handling

You can catch and customize errors:

```python
from app.exceptions.auth import InsufficientPermissionsError

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, current_user: User = Depends(get_current_active_user)):
    try:
        # Check permission manually
        permission_service = PermissionService(db)
        if not permission_service.user_has_permission(current_user, "documents:delete"):
            raise InsufficientPermissionsError("documents:delete")
    except InsufficientPermissionsError:
        # Custom handling
        raise HTTPException(
            status_code=403,
            detail="Document deletion requires premium subscription"
        )
```

---

## Testing

### Testing with Dependency Overrides

Override auth dependencies in tests:

```python
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies.auth import get_current_user

# Create test user
test_user = User(
    id="123e4567-e89b-12d3-a456-426614174000",
    email="test@example.com",
    tenant_id="tenant-123",
    is_active=True
)

# Override dependency
app.dependency_overrides[get_current_user] = lambda: test_user

# Make request
client = TestClient(app)
response = client.get("/api/v1/profile")
assert response.status_code == 200
```

---

### Testing Permission Checks

Mock PermissionService for testing:

```python
from unittest.mock import Mock
from app.services.permission_service import PermissionService

def test_delete_document_with_permission(client, test_db):
    # Mock permission service
    mock_permission_service = Mock(spec=PermissionService)
    mock_permission_service.user_has_permission.return_value = True

    # Inject mock
    app.dependency_overrides[PermissionService] = lambda: mock_permission_service

    # Test endpoint
    response = client.delete("/api/v1/documents/doc-123")
    assert response.status_code == 200
```

---

## Best Practices

### 1. Choose the Right Dependency

- **Public routes:** No dependency
- **Authenticated routes:** `get_current_user` or `get_current_active_user`
- **Fine-grained access:** `require_permission()`
- **Simple role checks:** `require_role()`

### 2. Always Enforce Tenant Isolation

```python
# GOOD: Tenant-isolated query
documents = db.query(Document).filter(
    Document.tenant_id == current_user.tenant_id
).all()

# BAD: No tenant filter (data leak!)
documents = db.query(Document).all()
```

### 3. Use Permissions for Features, Roles for Hierarchies

- **Permissions:** `documents:create`, `schemas:publish`, `billing:manage`
- **Roles:** `admin`, `member`, `viewer`

### 4. Don't Expose Sensitive Information in Errors

```python
# GOOD: Generic error
raise HTTPException(status_code=404, detail="Document not found")

# BAD: Reveals existence
raise HTTPException(status_code=403, detail="Document exists but belongs to another tenant")
```

### 5. Log Security Events

```python
import logging

logger = logging.getLogger(__name__)

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, current_user: User = Depends(require_permission("documents:delete"))):
    logger.info(f"User {current_user.id} deleting document {doc_id}")
    # Delete logic
```

---

## Troubleshooting

### "Could not validate credentials"

**Cause:** Token is missing, expired, or invalid.

**Solution:**
- Check Authorization header: `Authorization: Bearer <token>`
- Verify token hasn't expired (15 minutes for access tokens)
- Use refresh token to get new access token

---

### "User account is inactive"

**Cause:** User's `is_active` flag is False.

**Solution:**
- Check user status in database
- Activate user account or subscription
- Use `get_current_user` instead of `get_current_active_user` if inactive users should access this route

---

### "Missing required permission"

**Cause:** User lacks the specified permission.

**Solution:**
- Grant permission via role or custom permission
- Check user's role in database
- Verify permission name matches exactly (case-sensitive)

---

### "Required role: admin"

**Cause:** User doesn't have the specified role.

**Solution:**
- Assign correct role to user
- Use permission-based check instead if role is too restrictive
- Create custom role with needed permissions

---

## Related Documentation

- [Authentication Service](../architecture/2025-11-02-auth-service.md)
- [Permission System](../architecture/2025-11-02-rbac-permissions.md)
- [Tenant Context Middleware](../architecture/2025-11-02-tenant-middleware.md)
- [API Testing Guide](../guides/2025-11-02-api-testing.md)

---

**Last Updated:** 2025-11-02
