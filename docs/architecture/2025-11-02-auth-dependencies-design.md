# Auth Dependencies Architecture

**Date:** 2025-11-02
**Status:** Implemented
**Author:** System Architecture

---

## Context and Problem Statement

The AI Document Processing SaaS requires a robust authentication and authorization system to:

1. **Authenticate users** via JWT tokens
2. **Authorize access** based on roles and permissions (RBAC)
3. **Enforce multi-tenancy** to isolate tenant data
4. **Provide security** against common vulnerabilities
5. **Maintain testability** and clean architecture

The solution must integrate seamlessly with FastAPI's dependency injection system and existing services (AuthService, PermissionService).

---

## Decision Drivers

1. **Security First**: Protection against token tampering, unauthorized access, and data leaks
2. **Developer Experience**: Clear, declarative route protection with minimal boilerplate
3. **Performance**: Efficient token validation and database queries
4. **Flexibility**: Support various authorization patterns (roles, permissions, custom checks)
5. **Testability**: Easy to mock and test in isolation
6. **Clean Architecture**: Separation of concerns, no tight coupling

---

## Considered Options

### Option 1: Middleware-Based Authentication
**Description:** Validate tokens in middleware, attach user to request state.

**Pros:**
- Centralized auth logic
- All routes automatically authenticated
- Less code duplication

**Cons:**
- Can't have public routes without workarounds
- Less flexible per-route authorization
- Harder to compose different auth levels
- Doesn't leverage FastAPI's dependency system

**Verdict:** ❌ Rejected - Too inflexible for mixed public/private API

---

### Option 2: Decorator-Based Authorization
**Description:** Custom Python decorators to check auth before route handlers.

**Pros:**
- Familiar pattern for Python developers
- Can compose multiple decorators

**Cons:**
- Not idiomatic for FastAPI
- Doesn't integrate with OpenAPI docs
- Harder to override in tests
- Manual error handling in each decorator

**Verdict:** ❌ Rejected - Not FastAPI-native

---

### Option 3: FastAPI Dependency Injection (Selected)
**Description:** Use FastAPI's `Depends()` for auth checks, with dependency composition.

**Pros:**
- ✅ Native FastAPI pattern
- ✅ Automatic OpenAPI documentation
- ✅ Easy to test with dependency overrides
- ✅ Composable (dependencies depend on other dependencies)
- ✅ Clear, declarative syntax
- ✅ Proper error handling with HTTPException

**Cons:**
- Slightly verbose for simple cases (but more explicit)

**Verdict:** ✅ **SELECTED** - Best fit for FastAPI ecosystem

---

## Design Decisions

### Decision 1: Separate Token Validation from Active Check

**Rationale:**
- Some routes need authenticated users (e.g., profile, account settings)
- Other routes need active users only (e.g., document operations)
- Flexibility for edge cases (e.g., "activate account" endpoint for inactive users)

**Implementation:**
```python
get_current_user()        # Authenticated user (any status)
get_current_active_user() # Authenticated + active status
```

**Consequence:** More granular control, clearer route intent

---

### Decision 2: Factory Pattern for Permission/Role Checks

**Rationale:**
- Need to parameterize dependencies with permission strings
- FastAPI dependencies can't take parameters directly
- Factory functions return closures with captured parameters

**Implementation:**
```python
def require_permission(permission: str) -> Callable:
    async def permission_checker(...) -> User:
        # Check permission
    return permission_checker
```

**Usage:**
```python
@router.delete("/documents/{id}")
async def delete_document(
    current_user: User = Depends(require_permission("documents:delete"))
):
    pass
```

**Consequence:** Clean syntax, easy to add new check types

---

### Decision 3: Custom Exception Hierarchy

**Rationale:**
- Specific error types enable better logging and monitoring
- FastAPI automatically converts HTTPException to HTTP responses
- Semantic exceptions (InvalidTokenError vs ExpiredTokenError) aid debugging

**Implementation:**
```python
AuthenticationError (401)
├── InvalidTokenError
└── ExpiredTokenError

AuthorizationError (403)
├── InsufficientPermissionsError
├── InsufficientRoleError
└── InactiveUserError

UserNotFoundError (404)
```

**Consequence:** Better observability, clearer error semantics

---

### Decision 4: Optional Tenant Context Middleware

**Rationale:**
- Multi-tenant system requires tenant isolation
- Not all routes need tenant context (health check, login)
- Middleware approach provides global context without blocking public routes

**Implementation:**
- Middleware extracts `tenant_id` from JWT (if present)
- Stores in `request.state.tenant_id` for route handlers
- Gracefully handles missing/invalid tokens (doesn't raise errors)

**Consequence:**
- Tenant context available when needed
- No impact on public routes
- Can be extended for automatic query filtering

---

### Decision 5: OAuth2PasswordBearer for Token Extraction

**Rationale:**
- Standard OAuth2 pattern for bearer tokens
- FastAPI provides built-in `OAuth2PasswordBearer`
- Automatic OpenAPI documentation with "Authorize" button

**Implementation:**
```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Validate token
```

**Consequence:** Standard OAuth2 flow, automatic docs generation

---

## Security Considerations

### 1. Token Validation
**Threat:** Token tampering, expired tokens, wrong token type

**Mitigation:**
- JWT signature verification (HMAC-SHA256)
- Expiration check (built into `jwt.decode()`)
- Token type validation (`access` vs `refresh`)
- Constant-time password comparison (bcrypt in AuthService)

**Implementation:**
```python
payload = auth_service.verify_token(token, token_type="access")
if payload.get("type") != "access":
    raise InvalidTokenError("Wrong token type")
```

---

### 2. SQL Injection
**Threat:** Malicious input in queries

**Mitigation:**
- Use SQLAlchemy ORM (parameterized queries)
- No raw SQL concatenation
- UUID validation for user_id/tenant_id

**Implementation:**
```python
# SAFE: ORM query with parameterization
user = db.query(User).filter(User.id == user_id).first()

# UNSAFE: Raw SQL (NOT USED)
db.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
```

---

### 3. Tenant Isolation
**Threat:** Cross-tenant data access

**Mitigation:**
- Always filter by `tenant_id` in queries
- Use `current_user.tenant_id` for filtering
- Don't expose whether resources exist in other tenants

**Implementation:**
```python
# SAFE: Tenant-isolated query
document = db.query(Document).filter(
    Document.id == doc_id,
    Document.tenant_id == current_user.tenant_id
).first()
```

---

### 4. Information Disclosure
**Threat:** Error messages reveal sensitive information

**Mitigation:**
- Generic error messages (don't reveal internal details)
- Don't expose user existence in other tenants
- Log detailed errors server-side only

**Implementation:**
```python
# GOOD: Generic error
raise HTTPException(status_code=404, detail="Document not found")

# BAD: Reveals existence (NOT USED)
raise HTTPException(status_code=403, detail="Document exists in tenant X")
```

---

### 5. Replay Attacks
**Threat:** Stolen token reused by attacker

**Mitigation:**
- Short token lifetime (15 minutes for access tokens)
- Refresh token rotation (7 days)
- Token revocation via refresh token invalidation

**Implementation:**
- Access tokens expire after 15 minutes (configurable)
- Refresh tokens stored in database (can be revoked)
- Consider adding JTI (JWT ID) for token blacklisting

---

## SOLID Principles Applied

### Single Responsibility Principle (SRP)
Each dependency has one clear responsibility:
- `get_current_user`: Token validation → User
- `get_current_active_user`: Active status check
- `require_permission`: Permission validation
- `require_role`: Role validation

**Consequence:** Easy to understand, test, and modify

---

### Open/Closed Principle (OCP)
- Dependency factories are extensible without modification
- Can add new check types (e.g., `require_tenant_match()`) without changing existing code
- Custom exception hierarchy allows adding specific error types

**Example:**
```python
# Adding new dependency (no existing code changed)
def require_credit_balance(min_credits: int) -> Callable:
    async def checker(current_user: User = Depends(get_current_active_user)):
        if current_user.tenant.credit_balance < min_credits:
            raise HTTPException(402, "Insufficient credits")
        return current_user
    return checker
```

---

### Liskov Substitution Principle (LSP)
- All auth dependencies return `User` objects consistently
- Can substitute any auth dependency in route definitions
- Exception hierarchy maintains expected behavior

**Example:**
```python
# All return User - interchangeable
current_user: User = Depends(get_current_user)
current_user: User = Depends(get_current_active_user)
current_user: User = Depends(require_permission("documents:read"))
current_user: User = Depends(require_role("admin"))
```

---

### Interface Segregation Principle (ISP)
- Separate dependencies for different concerns
- Routes only depend on what they need
- No monolithic "auth check everything" dependency

**Example:**
```python
# Public route: No dependency
@router.get("/health")
async def health_check():
    pass

# Authenticated route: Basic auth
@router.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    pass

# Admin route: Role check
@router.get("/admin/users")
async def list_users(user: User = Depends(require_role("admin"))):
    pass
```

---

### Dependency Inversion Principle (DIP)
- Dependencies rely on abstractions (FastAPI's Depends, SQLAlchemy Session)
- No direct service instantiation
- Easy to mock for testing

**Example:**
```python
# Depends on abstraction (Session)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)  # Injected, not instantiated
) -> User:
    pass
```

---

## Testing Strategy

### Unit Tests

**Location:** `tests/unit/test_auth_dependencies.py`

**Coverage:**
1. Token validation (valid, invalid, expired, malformed)
2. Active user check (active, inactive)
3. Permission checks (granted, denied, custom grants/revocations)
4. Role checks (matching, non-matching)
5. Multiple permission checks (any, all)

**Mocking Strategy:**
- Mock `AuthService.verify_token()` for token validation
- Mock database session for user queries
- Mock `PermissionService` for RBAC checks

---

### Integration Tests

**Location:** `tests/integration/test_auth_flow.py`

**Scenarios:**
1. **End-to-End Auth Flow:**
   - Login → Get access token → Make authenticated request
   - Refresh token → Get new access token

2. **Multi-Tenancy:**
   - User A (Tenant 1) cannot access Tenant 2 resources
   - Tenant context correctly set in middleware

3. **RBAC Scenarios:**
   - Admin can access admin-only endpoints
   - Member can access member endpoints but not admin
   - Viewer can only read, not write

---

## Performance Considerations

### Token Validation Overhead
- JWT decode: ~0.1ms (negligible)
- Database user query: ~1-5ms (indexed lookup)
- Permission check: ~1-3ms (indexed joins)

**Total:** ~2-8ms per request (acceptable for API authentication)

---

### Caching Strategies

**Option 1: Cache User Object**
```python
# Cache user for 30 seconds to avoid repeated DB queries
@lru_cache(maxsize=1000)
def get_cached_user(user_id: str, cache_buster: int):
    # cache_buster = int(time.time() / 30) for 30-second TTL
    return db.query(User).filter(User.id == user_id).first()
```

**Option 2: Cache Permissions**
```python
# Cache user permissions for 60 seconds
@lru_cache(maxsize=1000)
def get_cached_permissions(user_id: str, cache_buster: int):
    return permission_service.get_user_permissions(user)
```

**Trade-offs:**
- ✅ Reduced database queries
- ❌ Stale data (permissions may not update immediately)
- ❌ Memory usage for cache

**Recommendation:** Implement if performance becomes an issue (profile first)

---

## Future Enhancements

### 1. API Key Authentication
Add support for API keys for machine-to-machine communication:

```python
async def get_current_user_or_api_key(
    api_key: Optional[str] = Header(None),
    token: Optional[str] = Depends(oauth2_scheme)
):
    if api_key:
        return validate_api_key(api_key)
    else:
        return get_current_user(token)
```

---

### 2. Automatic Tenant Filtering
Extend middleware to automatically filter queries by tenant:

```python
# Add tenant filter to all queries
@event.listens_for(Session, "before_flush")
def receive_before_flush(session, flush_context, instances):
    for instance in session.new:
        if hasattr(instance, "tenant_id") and not instance.tenant_id:
            instance.tenant_id = g.tenant_id
```

---

### 3. Token Blacklisting
Implement JWT ID (JTI) and blacklist for revoked tokens:

```python
# Add JTI to token claims
to_encode = {
    "sub": str(user_id),
    "jti": str(uuid.uuid4()),  # Unique token ID
    "exp": expire
}

# Check blacklist on validation
if redis.exists(f"blacklist:{jti}"):
    raise InvalidTokenError("Token has been revoked")
```

---

### 4. Rate Limiting
Add rate limiting per user/tenant:

```python
@limiter.limit("100/minute")
@router.post("/documents/extract")
async def extract_document(current_user: User = Depends(get_current_active_user)):
    pass
```

---

## Related Architectural Decisions

- [ADR-001: JWT Authentication](./2025-11-02-jwt-authentication.md)
- [ADR-002: RBAC Permission System](./2025-11-02-rbac-system.md)
- [ADR-003: Multi-Tenancy Design](./2025-11-02-multi-tenancy.md)

---

## References

- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [OAuth2 with Password (and hashing), Bearer with JWT tokens](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [JSON Web Token Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)

---

**Last Updated:** 2025-11-02
