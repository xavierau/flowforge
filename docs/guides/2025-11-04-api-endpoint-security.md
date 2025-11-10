# API Endpoint Security & Permission Control

**Created:** 2025-11-04
**Status:** Active
**Category:** Security, Backend Development

## Overview

This guide documents the complete security model for API endpoints, including authentication methods, permission control, and API token scoping. All backend developers MUST follow these patterns when creating or modifying endpoints.

---

## Table of Contents

1. [Authentication Methods](#authentication-methods)
2. [Permission System](#permission-system)
3. [API Token Scoping](#api-token-scoping)
4. [Endpoint Security Patterns](#endpoint-security-patterns)
5. [Security Decision Tree](#security-decision-tree)
6. [Common Mistakes](#common-mistakes)
7. [Testing Security](#testing-security)

---

## Authentication Methods

### 1. JWT Authentication (Web Sessions)

**Use Case:** User-facing operations via web interface
**Token Type:** Short-lived access tokens (15 min) + refresh tokens (7 days)
**Origin Restriction:** Only works from allowed frontend domains

```python
from app.dependencies.auth import get_current_user

@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    # JWT-only endpoint
    # Validates origin against JWT_ALLOWED_ORIGINS
    pass
```

**Security Features:**
- Origin validation (CORS-like protection)
- Short expiration time
- Automatic token refresh
- User session management

---

### 2. API Token Authentication (Server-to-Server)

**Use Case:** Programmatic API access from external systems
**Token Type:** Long-lived tokens with explicit scopes
**Format:** `sk_live_XXXXXXXXXXXXX` (32+ character random string)
**No Origin Restriction:** Can be used from any domain

```python
from app.dependencies.auth import get_current_user_from_api_token

@router.get("/data")
async def get_data(
    user_info: tuple = Depends(get_current_user_from_api_token)
):
    user, api_token = user_info
    # API token scopes available in request.state.api_token_scopes
    pass
```

**Security Features:**
- Scope-based access control (least privilege)
- Token prefix for fast lookup
- Bcrypt hashed storage
- Usage tracking (last_used_at, last_used_ip)
- Expiration support
- Revocation capability

---

### 3. Flexible Authentication (Recommended for APIs)

**Use Case:** Endpoints that support BOTH JWT and API tokens
**Best Practice:** Use this for all core API operations

```python
from app.dependencies.auth import get_current_user_flexible

@router.post("/documents/upload")
async def upload_document(
    current_user: User = Depends(get_current_user_flexible)
):
    # Accepts both JWT and API tokens
    # Automatically handles authentication logic
    pass
```

---

## Permission System

### Permission Structure

**Format:** `resource:action`
**Examples:** `documents:create`, `users:read`, `schemas:delete`

### Available Permissions

```python
# Document Operations
"documents:create"   # Upload documents
"documents:read"     # View/download documents
"documents:update"   # Update document metadata
"documents:delete"   # Delete documents
"documents:share"    # Share documents
"documents:export"   # Export document data

# Extraction & Jobs
"extraction:create"  # Create extraction jobs
"jobs:read"          # View job status and results

# Schema Management
"schemas:create"     # Create schema definitions
"schemas:read"       # View schema definitions
"schemas:update"     # Modify schema definitions
"schemas:delete"     # Delete schema definitions
"schemas:share"      # Share schemas

# User Management (JWT-only)
"users:invite"       # Invite new users
"users:read"         # View user information
"users:update"       # Modify user accounts
"users:delete"       # Delete user accounts

# Tenant Management (JWT-only)
"tenant:manage"      # Manage tenant settings
"tenant:billing"     # Manage billing
```

### Permission Enforcement

#### JWT-Only Permission Check

```python
from app.dependencies.auth import require_permission

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_permission("users:delete"))
):
    # ONLY accepts JWT tokens
    # Checks user's role-based permissions
    # Used for sensitive operations (user mgmt, billing)
    pass
```

#### Flexible Permission Check (JWT + API Token)

```python
from app.dependencies.auth import require_permission_flexible

@router.post("/documents/upload")
async def upload_document(
    current_user: User = Depends(require_permission_flexible("documents:create"))
):
    # Accepts BOTH JWT and API tokens
    # For API tokens: checks token scopes FIRST, then role permissions
    # For JWT: checks only role permissions
    pass
```

**CRITICAL:** `require_permission_flexible()` validates API token scopes BEFORE role permissions. This ensures tokens cannot bypass scope restrictions.

---

## API Token Scoping

### How Scoping Works

1. **Token Creation:** User creates token with specific scopes
2. **Scope Validation:** User must have permission for requested scopes
3. **Request Processing:** Token scopes are checked BEFORE role permissions
4. **Access Control:** Token can ONLY access operations within its scopes

### Scope Validation Flow

```
Request with API Token
  ↓
Extract token from Authorization header
  ↓
Query database and verify token hash
  ↓
Store scopes in request.state.api_token_scopes
  ↓
require_permission_flexible() checks:
  1. Is API token present? → Check token scopes FIRST
     - If scope missing → REJECT (403 Forbidden)
  2. Check user role permissions
     - If permission missing → REJECT (403 Forbidden)
  3. Both pass → ALLOW
```

### Example: API Token with Limited Scopes

```python
# Create token with only read access
token_scopes = ["documents:read", "jobs:read"]

# This token CAN:
✅ GET /documents           (requires documents:read)
✅ GET /documents/{id}      (requires documents:read)
✅ GET /jobs/{id}/status    (requires jobs:read)
✅ GET /jobs/{id}/result    (requires jobs:read)

# This token CANNOT:
❌ POST /documents/upload   (missing documents:create scope)
❌ POST /jobs/extract       (missing extraction:create scope)
❌ DELETE /documents/{id}   (missing documents:delete scope)
```

---

## Endpoint Security Patterns

### Pattern 1: Public Endpoints

**Use Case:** Health checks, landing pages
**Auth:** None

```python
@router.get("/health")
async def health_check():
    return {"status": "healthy"}
```

---

### Pattern 2: Self-Service Operations (JWT-Only, No Permission)

**Use Case:** User profile, password changes, notifications
**Auth:** JWT only, no explicit permission check
**Rationale:** Users should always be able to manage their own data

```python
from app.dependencies.auth import get_current_active_user

@router.get("/users/profile")
async def get_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # User can always view their own profile
    # No permission check needed
    return UserProfileResponse(...)
```

---

### Pattern 3: Sensitive Operations (JWT-Only, With Permission)

**Use Case:** User management, billing, tenant settings, API token management
**Auth:** JWT only, requires specific permission
**Rationale:** Too sensitive for API tokens

```python
from app.dependencies.auth import require_permission

@router.post("/users/invite")
async def invite_user(
    request: UserInviteRequest,
    current_user: User = Depends(require_permission("users:invite")),
    db: Session = Depends(get_db)
):
    # ONLY JWT tokens work
    # Requires users:invite permission
    pass
```

---

### Pattern 4: Core API Operations (Flexible Auth, With Permission)

**Use Case:** Documents, schemas, jobs, extraction
**Auth:** Both JWT and API tokens, requires specific permission
**Rationale:** External systems need programmatic access

```python
from app.dependencies.auth import require_permission_flexible

@router.post("/jobs/extract")
async def extract_from_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission_flexible("extraction:create")),
    db: Session = Depends(get_db)
):
    # Works with BOTH JWT and API tokens
    # API tokens: checks extraction:create in scopes
    # JWT: checks extraction:create in role permissions
    pass
```

---

## Security Decision Tree

```
Is this endpoint sensitive (user mgmt, billing, tokens)?
├─ YES → Use JWT-only auth
│   ├─ Needs permission check?
│   │   ├─ YES → Use require_permission("permission:name")
│   │   └─ NO  → Use get_current_active_user (profile operations)
│
└─ NO → Should external systems access this API?
    ├─ YES → Use flexible auth
    │   └─ Use require_permission_flexible("permission:name")
    │
    └─ NO → Determine if it's public or JWT-only
        ├─ Public (health checks) → No auth
        └─ User-facing only → Use require_permission("permission:name")
```

---

## Common Mistakes

### ❌ Mistake #1: Using wrong permission for endpoint

```python
# WRONG: Using documents:read for job endpoints
@router.get("/jobs/{job_id}/status")
async def get_job_status(
    current_user: User = Depends(require_permission("documents:read"))  # ❌
):
    pass

# CORRECT: Use jobs:read
@router.get("/jobs/{job_id}/status")
async def get_job_status(
    current_user: User = Depends(require_permission_flexible("jobs:read"))  # ✅
):
    pass
```

---

### ❌ Mistake #2: JWT-only when should be flexible

```python
# WRONG: Core API operation using JWT-only
@router.post("/documents/upload")
async def upload_document(
    current_user: User = Depends(require_permission("documents:create"))  # ❌
):
    # External systems can't use this!
    pass

# CORRECT: Use flexible auth for core APIs
@router.post("/documents/upload")
async def upload_document(
    current_user: User = Depends(require_permission_flexible("documents:create"))  # ✅
):
    # Works with both JWT and API tokens
    pass
```

---

### ❌ Mistake #3: No permission check on sensitive operations

```python
# WRONG: Missing permission check
@router.post("/invitations")
async def create_invitation(
    current_user: User = Depends(get_current_active_user)  # ❌
):
    # Anyone authenticated can invite users!
    pass

# CORRECT: Add permission check
@router.post("/invitations")
async def create_invitation(
    current_user: User = Depends(require_permission("users:invite"))  # ✅
):
    # Only users with users:invite permission can access
    pass
```

---

### ❌ Mistake #4: Forgetting tenant isolation

```python
# WRONG: No tenant filtering
document = db.query(Document).filter(Document.id == document_id).first()  # ❌

# CORRECT: Always filter by tenant FIRST
document = (
    db.query(Document)
    .filter(Document.tenant_id == current_user.tenant_id)  # ✅
    .filter(Document.id == document_id)
    .first()
)
```

---

## Testing Security

### Test Cases for API Token Scoping

```python
# Test 1: Token with correct scope can access
def test_api_token_with_correct_scope():
    token = create_api_token(scopes=["extraction:create"])
    response = client.post(
        "/api/v1/jobs/extract",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": test_file}
    )
    assert response.status_code == 202  # ✅ Accepted

# Test 2: Token with wrong scope is rejected
def test_api_token_with_wrong_scope():
    token = create_api_token(scopes=["jobs:read"])  # Missing extraction:create
    response = client.post(
        "/api/v1/jobs/extract",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": test_file}
    )
    assert response.status_code == 403  # ✅ Forbidden

# Test 3: JWT still works
def test_jwt_auth_still_works():
    jwt_token = login_and_get_jwt()
    response = client.post(
        "/api/v1/jobs/extract",
        headers={"Authorization": f"Bearer {jwt_token}"},
        files={"file": test_file}
    )
    assert response.status_code == 202  # ✅ Accepted
```

### Test Cases for Permission Checks

```python
# Test 1: User with permission can access
def test_user_with_permission():
    user = create_user(role="member")  # Has extraction:create
    token = get_jwt_for_user(user)
    response = client.post(
        "/api/v1/jobs/extract",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": test_file}
    )
    assert response.status_code == 202  # ✅

# Test 2: User without permission is rejected
def test_user_without_permission():
    user = create_user(role="viewer")  # Lacks extraction:create
    token = get_jwt_for_user(user)
    response = client.post(
        "/api/v1/jobs/extract",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": test_file}
    )
    assert response.status_code == 403  # ✅
```

### Test Cases for Tenant Isolation

```python
# Test: User cannot access another tenant's resources
def test_cross_tenant_access_blocked():
    tenant_a_user = create_user(tenant_id=tenant_a.id)
    tenant_b_document = create_document(tenant_id=tenant_b.id)

    token = get_jwt_for_user(tenant_a_user)
    response = client.get(
        f"/api/v1/documents/{tenant_b_document.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404  # ✅ Not found (don't reveal existence)
```

---

## Quick Reference

### When to Use Each Auth Method

| Endpoint Type | Auth Method | Example |
|---------------|-------------|---------|
| Public | None | `/health`, `/docs` |
| Self-service | `get_current_active_user` | `/users/profile`, `/users/password` |
| Sensitive (JWT-only) | `require_permission("...")` | `/users/invite`, `/tokens`, `/subscriptions` |
| Core API | `require_permission_flexible("...")` | `/documents/*`, `/schemas/*`, `/jobs/*` |

### Checklist for New Endpoints

- [ ] Determine sensitivity level (public, self-service, sensitive, core API)
- [ ] Choose appropriate auth method
- [ ] Add permission check if needed
- [ ] Verify correct permission is used (match resource:action)
- [ ] Add tenant isolation to all database queries
- [ ] Update documentation docstring with permission requirements
- [ ] Add comprehensive tests for:
  - [ ] Successful access with correct auth/permission
  - [ ] Rejection with wrong/missing permission
  - [ ] Tenant isolation (cross-tenant access blocked)
  - [ ] API token scope validation (if flexible auth)

---

## Related Documentation

- [JWT Authentication & Multi-Tenancy](../architecture/2025-11-03-jwt-authentication-and-multi-tenancy.md)
- [API Authentication Design](../architecture/2025-11-03-api-authentication-multi-tenancy.md)
- [Auth Dependencies Design](../architecture/2025-11-02-auth-dependencies-design.md)
- [Security Quick Reference](./SECURITY_QUICK_REFERENCE.md)

---

**Last Updated:** 2025-11-04
**Author:** System Architecture Team
