# JWT Authentication and Multi-Tenancy Architecture

**Date:** 2025-11-03
**Status:** Implemented
**Author:** System Architect

## Executive Summary

This document describes the JWT-based authentication and multi-tenancy architecture for the AI Document Processing SaaS platform. The implementation follows Clean Architecture principles, SOLID design patterns, and FastAPI best practices.

## Architecture Overview

### Core Components

1. **Auth Dependencies** (`app/dependencies/auth.py`)
   - JWT token validation and user authentication
   - Role-Based Access Control (RBAC)
   - Permission-Based Access Control (PBAC)
   - Composite permission checks

2. **Auth Service** (`app/services/auth_service.py`)
   - JWT token creation and verification
   - Password hashing and verification
   - Token lifecycle management

3. **Permission Service** (`app/services/permission_service.py`)
   - User permission aggregation (role + custom)
   - Permission checking logic
   - Permission grant/revoke operations

4. **Tenant Context Middleware** (`app/middleware/tenant_context.py`)
   - Tenant ID extraction from JWT tokens
   - Request-scoped tenant context
   - Multi-tenant data isolation

5. **Auth Exceptions** (`app/exceptions/auth.py`)
   - HTTP-compliant error responses
   - Granular exception types
   - OAuth2 WWW-Authenticate headers

## Authentication Flow

### 1. Token Creation

```python
# User logs in → AuthService creates access + refresh tokens
access_token = auth_service.create_access_token(
    user_id=str(user.id),
    tenant_id=str(user.tenant_id),
    additional_claims={"role": user.role.name}
)
```

**JWT Payload Structure:**
```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "exp": 1699123456,
  "type": "access",
  "role": "admin"  // Optional additional claims
}
```

### 2. Token Validation

```python
# Route handler with authentication
@router.get("/protected")
async def protected_route(
    current_user: User = Depends(get_current_active_user)
):
    return {"user": current_user.email}
```

**Validation Steps:**
1. OAuth2PasswordBearer extracts token from `Authorization: Bearer <token>`
2. `get_current_user` dependency validates JWT signature and expiration
3. User is queried from database using `sub` claim
4. `get_current_active_user` checks `user.is_active`
5. User object is injected into route handler

### 3. Token Error Handling

| Error Type | HTTP Status | Exception Class | Scenario |
|------------|-------------|-----------------|----------|
| Missing token | 401 | `AuthenticationError` | No Authorization header |
| Invalid token | 401 | `InvalidTokenError` | Malformed JWT or wrong type |
| Expired token | 401 | `ExpiredTokenError` | Token past `exp` claim |
| User not found | 404 | `UserNotFoundError` | User deleted after token issued |
| Inactive user | 403 | `InactiveUserError` | User deactivated |

## Authorization Flow

### Permission-Based Access Control (PBAC)

**Permission Naming Convention:**
```
<resource>:<action>[:<scope>]

Examples:
- documents:create
- documents:read:own
- documents:update:all
- schemas:delete
- admin:users:manage
```

**Permission Sources:**
1. **Role Permissions** - Granted to all users with a specific role
2. **Custom User Permissions** - Individual grants or revocations

**Aggregation Logic:**
```python
def get_user_permissions(user: User) -> Set[str]:
    permissions = set()

    # 1. Add all role-based permissions
    if user.role:
        permissions.update(get_role_permissions(user.role_id))

    # 2. Apply custom user permissions (grants and revocations)
    for perm, granted in get_user_custom_permissions(user.id):
        if granted:
            permissions.add(perm)
        else:
            permissions.discard(perm)  # Revoke

    return permissions
```

### Role-Based Access Control (RBAC)

**Standard Roles:**
- `owner` - Full access to tenant
- `admin` - Administrative access
- `member` - Standard user access
- `viewer` - Read-only access

**Usage Example:**
```python
@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: UUID,
    current_user: User = Depends(require_role("owner"))
):
    # Only tenant owners can delete tenants
    pass
```

## Multi-Tenancy Implementation

### Tenant Context Middleware

The `TenantContextMiddleware` runs on **ALL requests** (including public routes) and:

1. Extracts JWT token from `Authorization` header (if present)
2. Decodes token to get `tenant_id` claim
3. Stores `tenant_id` and `user_id` in `request.state`
4. **Gracefully handles missing/invalid tokens** (no blocking)

**Middleware Execution Order:**
```
Request → CORS → TenantContext → Route Handler
```

### Accessing Tenant Context

**Option 1: Via Request State**
```python
from fastapi import Request
from app.middleware.tenant_context import get_tenant_id

@router.get("/documents")
async def list_documents(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    tenant_id = get_tenant_id(request)  # From middleware

    # Query with tenant filtering
    documents = (
        db.query(Document)
        .filter(Document.tenant_id == tenant_id)
        .all()
    )
    return documents
```

**Option 2: Via Current User**
```python
@router.get("/documents")
async def list_documents(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # User object contains tenant_id
    tenant_id = current_user.tenant_id

    documents = (
        db.query(Document)
        .filter(Document.tenant_id == tenant_id)
        .all()
    )
    return documents
```

### Tenant Data Isolation

**Database Pattern:**
```python
# ALWAYS filter by tenant_id in multi-tenant queries
documents = (
    db.query(Document)
    .filter(Document.tenant_id == current_user.tenant_id)  # CRITICAL
    .all()
)
```

**Security Rule:**
> Every query that accesses tenant-specific data MUST include a `tenant_id` filter to prevent cross-tenant data leakage.

## Dependency Hierarchy

```
OAuth2PasswordBearer (token extraction)
    ↓
get_current_user (JWT validation + user query)
    ↓
get_current_active_user (active status check)
    ↓
require_permission/require_role (authorization check)
```

### Dependency Composition

**Use Case 1: Basic Authentication**
```python
@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_active_user)
):
    return {"email": current_user.email}
```

**Use Case 2: Permission Check**
```python
@router.post("/documents")
async def create_document(
    current_user: User = Depends(require_permission("documents:create")),
    db: Session = Depends(get_db)
):
    # User has "documents:create" permission
    pass
```

**Use Case 3: Role Check**
```python
@router.get("/admin/analytics")
async def get_analytics(
    current_user: User = Depends(require_role("admin"))
):
    # User has "admin" role
    pass
```

**Use Case 4: Multiple Permissions (OR Logic)**
```python
@router.put("/documents/{doc_id}")
async def update_document(
    doc_id: UUID,
    current_user: User = Depends(
        require_any_permission([
            "documents:update:own",
            "documents:update:all"
        ])
    )
):
    # User has at least one permission
    pass
```

**Use Case 5: Multiple Permissions (AND Logic)**
```python
@router.post("/schemas/{schema_id}/publish")
async def publish_schema(
    schema_id: UUID,
    current_user: User = Depends(
        require_all_permissions([
            "schemas:read",
            "schemas:publish"
        ])
    )
):
    # User has both permissions
    pass
```

**Use Case 6: Email Verification**
```python
@router.post("/documents/extract")
async def extract_document(
    current_user: User = Depends(require_verified_email())
):
    # User has verified email
    pass
```

## Security Considerations

### Token Security

1. **Secret Key Management**
   - `JWT_SECRET_KEY` must be cryptographically random (32+ bytes)
   - Use `openssl rand -hex 32` to generate
   - Never commit secrets to version control

2. **Token Expiration**
   - Access tokens: 15 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
   - Refresh tokens: 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)

3. **Token Validation**
   - Signature verification using HS256 algorithm
   - Expiration check (`exp` claim)
   - Token type validation (`type` claim)

### Password Security

1. **Hashing Algorithm**
   - bcrypt with automatic salt generation
   - Configurable work factor (default: 12 rounds)

2. **Password Reset Flow**
   - Time-limited reset tokens (6 hours)
   - Single-use tokens (invalidated after use)
   - Secure random token generation (`secrets.token_urlsafe`)

### Multi-Tenancy Security

1. **Tenant Isolation**
   - All tenant-specific queries MUST filter by `tenant_id`
   - Use database row-level security (RLS) as additional layer
   - Never trust tenant_id from client requests

2. **Cross-Tenant Prevention**
   - Validate resource ownership before mutations
   - Check `document.tenant_id == current_user.tenant_id`
   - Log suspicious cross-tenant access attempts

## Configuration

### Environment Variables

```bash
# JWT Settings
JWT_SECRET_KEY=your-secret-key-here-use-openssl-rand-hex-32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Frontend URL (for email links)
FRONTEND_URL=http://localhost:3002
```

### Production Hardening

1. **HTTPS Only**
   - Enforce HTTPS in production
   - Set `Secure` cookie flag for tokens

2. **CORS Configuration**
   - Replace `allow_origins=["*"]` with specific domains
   - Enable `allow_credentials=True` for cookie-based auth

3. **Rate Limiting**
   - Implement rate limiting on auth endpoints
   - Use slowloris protection

4. **Audit Logging**
   - Log all authentication events (success/failure)
   - Log permission denial events
   - Include tenant_id and user_id in logs

## Testing Strategy

### Unit Tests

```python
# Test JWT token creation and validation
def test_create_access_token():
    token = auth_service.create_access_token(
        user_id="test-user-id",
        tenant_id="test-tenant-id"
    )
    assert token is not None

    payload = auth_service.verify_token(token)
    assert payload["sub"] == "test-user-id"
    assert payload["tenant_id"] == "test-tenant-id"

# Test permission aggregation
def test_user_permissions_with_custom_grant():
    user = create_test_user(role="member")
    grant_custom_permission(user.id, "documents:delete")

    perms = permission_service.get_user_permissions(user)
    assert "documents:delete" in perms
```

### Integration Tests

```python
# Test authenticated endpoint
async def test_protected_endpoint_with_valid_token():
    token = create_access_token_for_user(test_user)

    response = client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == test_user.email

# Test tenant isolation
async def test_tenant_isolation():
    user1 = create_user(tenant_id=tenant1.id)
    user2 = create_user(tenant_id=tenant2.id)

    doc = create_document(tenant_id=tenant1.id)

    token2 = create_access_token_for_user(user2)
    response = client.get(
        f"/api/v1/documents/{doc.id}",
        headers={"Authorization": f"Bearer {token2}"}
    )

    # User from tenant2 cannot access tenant1's document
    assert response.status_code == 404
```

### Security Tests

```python
# Test expired token
async def test_expired_token_rejected():
    token = create_expired_token(test_user)

    response = client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()

# Test insufficient permissions
async def test_insufficient_permissions():
    user = create_user(role="viewer")  # No delete permission
    token = create_access_token_for_user(user)

    response = client.delete(
        f"/api/v1/documents/{doc.id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403
```

## Migration Guide

### Adding Auth to Existing Endpoints

**Before:**
```python
@router.get("/documents")
async def list_documents(db: Session = Depends(get_db)):
    documents = db.query(Document).all()
    return documents
```

**After:**
```python
@router.get("/documents")
async def list_documents(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # CRITICAL: Filter by tenant_id
    documents = (
        db.query(Document)
        .filter(Document.tenant_id == current_user.tenant_id)
        .all()
    )
    return documents
```

### Adding Permission Checks

**Step 1: Define Permissions**
```sql
INSERT INTO permissions (id, name, description, category)
VALUES
  (uuid_generate_v4(), 'documents:create', 'Create documents', 'documents'),
  (uuid_generate_v4(), 'documents:read', 'Read documents', 'documents'),
  (uuid_generate_v4(), 'documents:update', 'Update documents', 'documents'),
  (uuid_generate_v4(), 'documents:delete', 'Delete documents', 'documents');
```

**Step 2: Assign to Roles**
```sql
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'member'
  AND p.name IN ('documents:create', 'documents:read', 'documents:update');
```

**Step 3: Use in Routes**
```python
@router.post("/documents")
async def create_document(
    current_user: User = Depends(require_permission("documents:create")),
    db: Session = Depends(get_db)
):
    # Only users with "documents:create" permission can access
    pass
```

## Common Patterns

### Pattern 1: Resource Ownership Check

```python
@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Query document
    document = db.query(Document).filter(Document.id == doc_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # CRITICAL: Verify tenant ownership
    if document.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    db.delete(document)
    db.commit()

    return {"message": "Document deleted"}
```

### Pattern 2: Conditional Permission Check

```python
@router.put("/documents/{doc_id}")
async def update_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == doc_id).first()

    if not document:
        raise HTTPException(status_code=404)

    # Check if user can update this document
    permission_service = PermissionService(db)

    # Option 1: User owns the document and has "update:own" permission
    can_update_own = (
        document.created_by == current_user.id and
        permission_service.user_has_permission(current_user, "documents:update:own")
    )

    # Option 2: User has "update:all" permission
    can_update_all = permission_service.user_has_permission(
        current_user, "documents:update:all"
    )

    if not (can_update_own or can_update_all):
        raise HTTPException(status_code=403, detail="Cannot update this document")

    # Perform update
    pass
```

### Pattern 3: Tenant Admin Operations

```python
@router.post("/tenants/{tenant_id}/users")
async def invite_user(
    tenant_id: UUID,
    invite: UserInviteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Verify user belongs to tenant
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check permission
    permission_service = PermissionService(db)
    if not permission_service.user_has_permission(current_user, "users:invite"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Invite user to tenant
    pass
```

## Troubleshooting

### Issue 1: "Could not validate credentials"

**Cause:** Invalid JWT token or missing Authorization header

**Solution:**
```python
# Ensure token is sent correctly
headers = {
    "Authorization": f"Bearer {access_token}"
}
```

### Issue 2: "Token has expired"

**Cause:** Access token expired (default: 15 minutes)

**Solution:** Implement refresh token flow
```python
# Use refresh token to get new access token
POST /api/v1/auth/refresh
{
    "refresh_token": "..."
}
```

### Issue 3: "User not found"

**Cause:** User was deleted after token was issued

**Solution:**
- Implement token revocation on user deletion
- Force logout on user deletion via WebSocket/SSE

### Issue 4: "Insufficient permissions"

**Cause:** User lacks required permission

**Solution:**
```sql
-- Grant permission to user's role
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'member'
  AND p.name = 'documents:create';

-- OR grant custom permission to specific user
INSERT INTO user_permissions (user_id, permission_id, granted)
VALUES ('user-uuid', 'permission-uuid', true);
```

## Future Enhancements

1. **OAuth2 Social Login**
   - Google, GitHub, Microsoft authentication
   - Account linking for existing users

2. **API Key Authentication**
   - Long-lived API keys for service-to-service auth
   - Scoped API keys with limited permissions

3. **Audit Logging**
   - Track all authentication events
   - Permission denial logging
   - Suspicious activity detection

4. **Rate Limiting**
   - Per-user and per-tenant rate limits
   - Adaptive rate limiting based on behavior

5. **WebAuthn/Passkeys**
   - Passwordless authentication
   - Biometric authentication support

## References

- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [OAuth2 Password Bearer Flow](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [Multi-Tenancy Patterns](https://docs.microsoft.com/en-us/azure/architecture/patterns/multi-tenancy)

---

**Last Updated:** 2025-11-03
**Version:** 1.0
