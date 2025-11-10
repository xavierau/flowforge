# Authentication Implementation Guide

**Date:** 2025-11-03
**Status:** Complete
**Audience:** Developers implementing auth-protected routes

## Quick Start

### 1. Protect a Route with Authentication

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models import User

router = APIRouter()

@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Protected route - requires valid JWT token.
    Returns current user's profile information.
    """
    return {
        "email": current_user.email,
        "full_name": current_user.full_name,
        "tenant_id": str(current_user.tenant_id),
        "role": current_user.role.name
    }
```

**What you get:**
- ✅ JWT token validation (signature + expiration)
- ✅ User existence check
- ✅ Active user verification
- ✅ User object injected into handler
- ❌ Returns 401 if token is invalid/expired
- ❌ Returns 403 if user is inactive

### 2. Add Permission-Based Authorization

```python
from app.dependencies.auth import require_permission

@router.post("/documents")
async def create_document(
    current_user: User = Depends(require_permission("documents:create")),
    db: Session = Depends(get_db)
):
    """
    Protected route - requires "documents:create" permission.
    User must have permission via role or custom grant.
    """
    # User has "documents:create" permission - proceed
    document = Document(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        # ...
    )
    db.add(document)
    db.commit()

    return {"document_id": str(document.id)}
```

**What you get:**
- ✅ All authentication checks from `get_current_active_user`
- ✅ Permission check (role-based + custom)
- ❌ Returns 403 if user lacks permission

### 3. Add Role-Based Authorization

```python
from app.dependencies.auth import require_role

@router.get("/admin/analytics")
async def get_analytics(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """
    Protected route - requires "admin" role.
    Only users with admin role can access.
    """
    # User has admin role - proceed with sensitive operation
    pass
```

### 4. Multi-Tenant Data Filtering

```python
from uuid import UUID
from fastapi import Request
from app.middleware.tenant_context import get_tenant_id

@router.get("/documents")
async def list_documents(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List documents for current user's tenant.
    CRITICAL: Always filter by tenant_id.
    """
    # Option 1: Get tenant_id from middleware
    tenant_id = get_tenant_id(request)

    # Option 2: Get tenant_id from current_user (recommended)
    tenant_id = current_user.tenant_id

    # CRITICAL: Filter by tenant_id to prevent data leakage
    documents = (
        db.query(Document)
        .filter(Document.tenant_id == tenant_id)
        .all()
    )

    return {"documents": documents}
```

## Common Use Cases

### Use Case 1: Public + Protected Endpoints

```python
# Public endpoint (no authentication)
@router.get("/health")
async def health_check():
    return {"status": "ok"}

# Protected endpoint (authentication required)
@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_active_user)
):
    return {"email": current_user.email}
```

### Use Case 2: Optional Authentication

```python
from typing import Optional
from app.dependencies.auth import get_current_user

@router.get("/public-data")
async def get_public_data(
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Endpoint accessible to both authenticated and anonymous users.
    Behavior changes based on authentication status.
    """
    if current_user:
        # Return personalized data for authenticated users
        return {"data": "personalized", "user": current_user.email}
    else:
        # Return generic data for anonymous users
        return {"data": "generic"}
```

**Note:** This requires modifying `oauth2_scheme` to use `auto_error=False`:
```python
# In app/dependencies/auth.py
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False  # Don't raise error if token is missing
)
```

### Use Case 3: Resource Ownership Check

```python
from fastapi import HTTPException

@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a document - verify tenant ownership before deletion.
    """
    # Query document
    document = (
        db.query(Document)
        .filter(Document.id == doc_id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # CRITICAL: Verify tenant ownership
    if document.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this document"
        )

    # Delete document
    db.delete(document)
    db.commit()

    return {"message": "Document deleted successfully"}
```

### Use Case 4: Multiple Permissions (OR Logic)

```python
from app.dependencies.auth import require_any_permission

@router.put("/documents/{doc_id}")
async def update_document(
    doc_id: UUID,
    update_data: DocumentUpdate,
    current_user: User = Depends(
        require_any_permission([
            "documents:update:own",  # Can update own documents
            "documents:update:all"   # Can update all documents
        ])
    ),
    db: Session = Depends(get_db)
):
    """
    Update a document - user needs at least one permission.
    """
    document = db.query(Document).filter(Document.id == doc_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Additional check for "update:own" permission
    permission_service = PermissionService(db)
    has_update_all = permission_service.user_has_permission(
        current_user, "documents:update:all"
    )

    if not has_update_all:
        # User only has "update:own" - verify ownership
        if document.created_by != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only update your own documents"
            )

    # Update document
    document.name = update_data.name
    db.commit()

    return {"message": "Document updated"}
```

### Use Case 5: Multiple Permissions (AND Logic)

```python
from app.dependencies.auth import require_all_permissions

@router.post("/schemas/{schema_id}/publish")
async def publish_schema(
    schema_id: UUID,
    current_user: User = Depends(
        require_all_permissions([
            "schemas:read",    # Must be able to read schemas
            "schemas:publish"  # Must be able to publish schemas
        ])
    ),
    db: Session = Depends(get_db)
):
    """
    Publish a schema - user needs both permissions.
    """
    schema = db.query(SchemaDefinition).filter(
        SchemaDefinition.id == schema_id,
        SchemaDefinition.tenant_id == current_user.tenant_id
    ).first()

    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Publish schema
    schema.is_published = True
    schema.published_at = datetime.utcnow()
    db.commit()

    return {"message": "Schema published"}
```

### Use Case 6: Email Verification Required

```python
from app.dependencies.auth import require_verified_email

@router.post("/documents/extract")
async def extract_document(
    doc_id: UUID,
    current_user: User = Depends(require_verified_email()),
    db: Session = Depends(get_db)
):
    """
    Extract document data - requires verified email.
    """
    # User has verified email - proceed with extraction
    pass
```

### Use Case 7: Admin-Only Operations

```python
from app.dependencies.auth import require_role

@router.post("/tenants/{tenant_id}/users/{user_id}/suspend")
async def suspend_user(
    tenant_id: UUID,
    user_id: UUID,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """
    Suspend a user - admin only.
    """
    # Verify admin belongs to tenant
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Find user to suspend
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == tenant_id
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Suspend user
    user.is_active = False
    db.commit()

    return {"message": "User suspended"}
```

## Testing Your Implementation

### 1. Create Test Users

```python
# tests/conftest.py
import pytest
from app.services.auth_service import auth_service

@pytest.fixture
def test_user(db):
    """Create a test user with access token."""
    from app.models import User, Tenant, Role

    tenant = Tenant(name="Test Tenant", slug="test-tenant")
    db.add(tenant)
    db.commit()

    role = Role(name="member", description="Standard member")
    db.add(role)
    db.commit()

    user = User(
        email="test@example.com",
        hashed_password=auth_service.hash_password("password123"),
        tenant_id=tenant.id,
        role_id=role.id,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    db.commit()

    return user

@pytest.fixture
def auth_headers(test_user):
    """Create authorization headers with valid token."""
    token = auth_service.create_access_token(
        user_id=str(test_user.id),
        tenant_id=str(test_user.tenant_id)
    )
    return {"Authorization": f"Bearer {token}"}
```

### 2. Test Authenticated Endpoints

```python
# tests/test_auth.py
def test_protected_endpoint_with_valid_token(client, auth_headers):
    """Test accessing protected endpoint with valid token."""
    response = client.get(
        "/api/v1/profile",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert "email" in response.json()

def test_protected_endpoint_without_token(client):
    """Test accessing protected endpoint without token."""
    response = client.get("/api/v1/profile")

    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]

def test_protected_endpoint_with_expired_token(client, test_user):
    """Test accessing protected endpoint with expired token."""
    # Create expired token
    import jwt
    from datetime import datetime, timedelta
    from app.config import settings

    expired_token = jwt.encode(
        {
            "sub": str(test_user.id),
            "tenant_id": str(test_user.tenant_id),
            "exp": datetime.utcnow() - timedelta(minutes=10),
            "type": "access"
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    response = client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {expired_token}"}
    )

    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()
```

### 3. Test Permission Checks

```python
def test_permission_required_endpoint_with_permission(client, test_user, db, auth_headers):
    """Test accessing permission-protected endpoint with required permission."""
    from app.models import Permission, UserPermission

    # Grant permission to user
    permission = Permission(name="documents:create", description="Create documents")
    db.add(permission)
    db.commit()

    user_perm = UserPermission(
        user_id=test_user.id,
        permission_id=permission.id,
        granted=True
    )
    db.add(user_perm)
    db.commit()

    response = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        json={"name": "test.pdf"}
    )

    assert response.status_code in [200, 201]

def test_permission_required_endpoint_without_permission(client, auth_headers):
    """Test accessing permission-protected endpoint without required permission."""
    response = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        json={"name": "test.pdf"}
    )

    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()
```

### 4. Test Tenant Isolation

```python
def test_tenant_isolation(client, db):
    """Test that users can only access their own tenant's data."""
    from app.models import User, Tenant, Document

    # Create two tenants
    tenant1 = Tenant(name="Tenant 1", slug="tenant1")
    tenant2 = Tenant(name="Tenant 2", slug="tenant2")
    db.add_all([tenant1, tenant2])
    db.commit()

    # Create users for each tenant
    user1 = create_user(tenant_id=tenant1.id, email="user1@example.com")
    user2 = create_user(tenant_id=tenant2.id, email="user2@example.com")

    # Create document for tenant1
    doc = Document(tenant_id=tenant1.id, name="tenant1-doc.pdf")
    db.add(doc)
    db.commit()

    # User2 tries to access tenant1's document
    token2 = create_access_token_for_user(user2)
    response = client.get(
        f"/api/v1/documents/{doc.id}",
        headers={"Authorization": f"Bearer {token2}"}
    )

    # Should return 404 (not 403) to avoid leaking document existence
    assert response.status_code == 404
```

## Error Handling

### Client-Side Error Handling

```typescript
// Frontend example (React/TypeScript)
const fetchProtectedData = async () => {
  try {
    const response = await fetch('/api/v1/profile', {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    if (response.status === 401) {
      // Token expired or invalid - try refresh
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        // Retry with new token
        return fetchProtectedData();
      } else {
        // Refresh failed - redirect to login
        window.location.href = '/login';
      }
    }

    if (response.status === 403) {
      // Insufficient permissions - show error
      showError('You do not have permission to access this resource');
      return;
    }

    return await response.json();
  } catch (error) {
    console.error('Request failed:', error);
    showError('An error occurred');
  }
};
```

### Server-Side Error Responses

| Status Code | Error Type | Response Body | Client Action |
|-------------|------------|---------------|---------------|
| 401 | Missing token | `{"detail": "Not authenticated"}` | Redirect to login |
| 401 | Invalid token | `{"detail": "Invalid authentication token"}` | Clear token, redirect to login |
| 401 | Expired token | `{"detail": "Authentication token has expired"}` | Try refresh token flow |
| 403 | Inactive user | `{"detail": "User account is inactive"}` | Show error, contact support |
| 403 | Missing permission | `{"detail": "Missing required permission: documents:create"}` | Show error, request access |
| 403 | Missing role | `{"detail": "Required role: admin"}` | Show error, request role |
| 404 | User not found | `{"detail": "User not found"}` | Clear token, redirect to login |

## Best Practices

### 1. Always Filter by Tenant ID

```python
# ❌ BAD: No tenant filtering
documents = db.query(Document).all()

# ✅ GOOD: Filter by current user's tenant
documents = (
    db.query(Document)
    .filter(Document.tenant_id == current_user.tenant_id)
    .all()
)
```

### 2. Verify Resource Ownership

```python
# ❌ BAD: Trust doc_id from URL without verification
document = db.query(Document).filter(Document.id == doc_id).first()
db.delete(document)

# ✅ GOOD: Verify tenant ownership before mutation
document = db.query(Document).filter(
    Document.id == doc_id,
    Document.tenant_id == current_user.tenant_id
).first()

if not document:
    raise HTTPException(status_code=404, detail="Document not found")

db.delete(document)
```

### 3. Use Specific Permissions

```python
# ❌ BAD: Overly broad permission
@router.delete("/documents/{doc_id}")
async def delete_document(
    current_user: User = Depends(require_permission("admin"))
):
    pass

# ✅ GOOD: Specific, granular permission
@router.delete("/documents/{doc_id}")
async def delete_document(
    current_user: User = Depends(require_permission("documents:delete"))
):
    pass
```

### 4. Layer Security Checks

```python
# ✅ GOOD: Multiple layers of security
@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: UUID,
    current_user: User = Depends(require_permission("documents:delete")),
    db: Session = Depends(get_db)
):
    # Layer 1: Permission check (via dependency)

    # Layer 2: Tenant ownership check
    document = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id
    ).first()

    if not document:
        raise HTTPException(status_code=404)

    # Layer 3: Business logic check (e.g., can't delete if in use)
    if document.extraction_jobs:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete document with active extraction jobs"
        )

    db.delete(document)
    db.commit()
```

### 5. Don't Leak Information

```python
# ❌ BAD: Reveals existence of cross-tenant resource
if document.tenant_id != current_user.tenant_id:
    raise HTTPException(status_code=403, detail="Access denied")

# ✅ GOOD: Returns 404 for cross-tenant access
document = db.query(Document).filter(
    Document.id == doc_id,
    Document.tenant_id == current_user.tenant_id
).first()

if not document:
    # Could be missing OR belong to another tenant
    raise HTTPException(status_code=404, detail="Document not found")
```

## Migration Checklist

When adding authentication to existing endpoints:

- [ ] Add `current_user: User = Depends(get_current_active_user)` parameter
- [ ] Add tenant filtering: `.filter(Model.tenant_id == current_user.tenant_id)`
- [ ] Add permission check if needed: `Depends(require_permission("..."))`
- [ ] Verify resource ownership before mutations
- [ ] Update tests to include authentication
- [ ] Update API documentation with security requirements
- [ ] Test with different roles and permissions
- [ ] Test tenant isolation (cross-tenant access blocked)

## Quick Reference

### Dependency Cheat Sheet

```python
# Basic authentication (active user)
current_user: User = Depends(get_current_active_user)

# Permission check
current_user: User = Depends(require_permission("documents:create"))

# Role check
current_user: User = Depends(require_role("admin"))

# At least one permission (OR)
current_user: User = Depends(require_any_permission(["perm1", "perm2"]))

# All permissions (AND)
current_user: User = Depends(require_all_permissions(["perm1", "perm2"]))

# Email verification required
current_user: User = Depends(require_verified_email())
```

### Token Structure

```json
{
  "sub": "user-uuid",           // User ID
  "tenant_id": "tenant-uuid",   // Tenant ID
  "exp": 1699123456,            // Expiration timestamp
  "type": "access"              // Token type
}
```

### HTTP Status Codes

- `200` - Success
- `401` - Authentication failed (invalid/missing token)
- `403` - Authorization failed (insufficient permissions)
- `404` - Resource not found (or cross-tenant access)

---

**Last Updated:** 2025-11-03
**Version:** 1.0
