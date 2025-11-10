# API Security Implementation Summary

**Date:** 2025-11-03
**Type:** Implementation Guide
**Status:** Completed

---

## Overview

This document summarizes the changes made to secure all API endpoints with JWT authentication and tenant-level data isolation. All existing API endpoints have been updated to prevent unauthorized access and ensure complete tenant segregation.

---

## Files Modified

### 1. `/app/api/documents.py`

**Changes:**
- Added imports: `User` model, `require_permission`, `get_current_active_user`
- Updated 4 endpoints with authentication and tenant filtering

| Endpoint | Permission | Changes |
|----------|-----------|---------|
| `POST /documents/upload` | `documents:create` | Sets `tenant_id` on create |
| `POST /documents/{id}/parse` | `documents:create` | Validates tenant ownership before parsing |
| `GET /documents` | `documents:read` | Filters by `tenant_id` |
| `GET /documents/{id}` | `documents:read` | Validates tenant ownership |

**Key Security Patterns:**

```python
# CREATE: Set tenant_id from current user
document = Document(
    tenant_id=current_user.tenant_id,  # ← Auto-assign
    filename=file.filename,
    ...
)

# READ: Filter by tenant_id FIRST
document = (
    db.query(Document)
    .filter(Document.tenant_id == current_user.tenant_id)  # ← FIRST
    .filter(Document.id == document_id)                    # ← SECOND
    .first()
)
```

---

### 2. `/app/api/jobs.py`

**Changes:**
- Added imports: `User` model, `require_permission`
- Updated 2 endpoints with authentication and tenant filtering via JOIN

| Endpoint | Permission | Changes |
|----------|-----------|---------|
| `GET /jobs/{id}/status` | `documents:read` | Validates via Document JOIN |
| `GET /jobs/{id}/result` | `documents:read` | Validates via Document JOIN |

**Key Security Pattern:**

```python
# ExtractionJob doesn't have tenant_id directly
# Use JOIN through Document to validate tenant ownership
job = (
    db.query(ExtractionJob)
    .join(Document)
    .filter(Document.tenant_id == current_user.tenant_id)
    .filter(ExtractionJob.id == job_id)
    .first()
)
```

**Why this works:**
- ExtractionJob has `document_id` foreign key to Document
- Document has `tenant_id`
- JOIN ensures we only access jobs for our tenant's documents
- No duplicate tenant_id storage (normalized schema)

---

### 3. `/app/api/schemas.py`

**Changes:**
- Added imports: `User` model, `require_permission`
- Updated 6 endpoints with authentication and tenant filtering

| Endpoint | Permission | Changes |
|----------|-----------|---------|
| `POST /schemas` | `schemas:create` | Sets `tenant_id` on create |
| `GET /schemas` | `schemas:read` | Filters by `tenant_id` |
| `GET /schemas/{id}` | `schemas:read` | Validates tenant ownership |
| `GET /schemas/name/{name}` | `schemas:read` | Validates tenant ownership |
| `PUT /schemas/{id}` | `schemas:update` | Validates tenant ownership before update |
| `DELETE /schemas/{id}` | `schemas:delete` | Validates tenant ownership before delete |

**Key Security Patterns:**

```python
# CREATE: Set tenant_id from current user
schema_def = SchemaDefinition(
    tenant_id=current_user.tenant_id,  # ← Multi-tenancy
    name=request.name,
    definitions=request.definitions,
)

# UPDATE/DELETE: Validate ownership BEFORE modification
schema_def = (
    db.query(SchemaDefinition)
    .filter(SchemaDefinition.tenant_id == current_user.tenant_id)
    .filter(SchemaDefinition.id == schema_id)
    .first()
)
if not schema_def:
    raise HTTPException(404, "Schema not found")  # ← Don't reveal existence
```

---

## Permission Mapping

All endpoints now use these seeded permissions:

### Documents Resource
- `documents:create` - Upload and initiate parsing
- `documents:read` - List, get, and check job status/results
- `documents:update` - (Reserved for future use)
- `documents:delete` - (Reserved for future use)
- `documents:share` - (Reserved for future use)
- `documents:export` - (Reserved for future use)

### Schemas Resource
- `schemas:create` - Create schema definitions
- `schemas:read` - List and get schemas
- `schemas:update` - Update schema definitions
- `schemas:delete` - Delete schema definitions
- `schemas:share` - (Reserved for future use)

### Role Assignments (from seed data)

| Role | Permissions |
|------|-------------|
| `platform_admin` | ALL permissions |
| `tenant_admin` | ALL documents + schemas + users + tenant management |
| `member` | documents: create, read, update, share, export<br>schemas: create, read, update |
| `viewer` | documents: read, export<br>schemas: read |

---

## Security Guarantees

### 1. Zero Unauthenticated Access

**Before:**
```python
@router.post("/documents/upload")
async def upload_document(file: UploadFile, db: Session = Depends(get_db)):
    # Anyone could upload
```

**After:**
```python
@router.post("/documents/upload")
async def upload_document(
    file: UploadFile,
    current_user: User = Depends(require_permission("documents:create")),  # ← Required
    db: Session = Depends(get_db)
):
    # Only authenticated users with permission can upload
```

---

### 2. Complete Tenant Isolation

**Before:**
```python
# Could see ALL documents
documents = db.query(Document).all()
```

**After:**
```python
# Only see own tenant's documents
documents = (
    db.query(Document)
    .filter(Document.tenant_id == current_user.tenant_id)  # ← Isolated
    .all()
)
```

---

### 3. No Information Disclosure

**Before:**
```python
document = db.query(Document).filter(Document.id == doc_id).first()
if not document:
    raise HTTPException(404, "Document not found")
# Could determine if document exists in another tenant by trying many IDs
```

**After:**
```python
# Tenant filter FIRST - cannot determine existence in other tenants
document = (
    db.query(Document)
    .filter(Document.tenant_id == current_user.tenant_id)  # ← Filter FIRST
    .filter(Document.id == doc_id)
    .first()
)
if not document:
    # Returns 404 whether document doesn't exist OR belongs to another tenant
    raise HTTPException(404, "Document not found")
```

---

## Error Responses

### Authentication Errors

```bash
# No token provided
HTTP 401 Unauthorized
{
  "detail": "Not authenticated"
}

# Invalid or expired token
HTTP 401 Unauthorized
{
  "detail": "Token validation failed: ..."
}

# Inactive user account
HTTP 403 Forbidden
{
  "detail": "User account is not active"
}
```

### Authorization Errors

```bash
# User lacks required permission
HTTP 403 Forbidden
{
  "detail": "Insufficient permissions: documents:create required"
}

# Resource doesn't exist OR belongs to different tenant (intentionally ambiguous)
HTTP 404 Not Found
{
  "detail": "Document not found"
}
```

---

## Testing Examples

### 1. Test Authentication

```bash
# Upload without authentication → 401
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@invoice.pdf"

# Expected: 401 Unauthorized

# Upload with valid token → 201
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@invoice.pdf"

# Expected: 201 Created with document_id
```

### 2. Test Permission Enforcement

```bash
# Login as viewer (read-only permissions)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"viewer@example.com","password":"ViewerPass123!"}'
# → Get TOKEN

# Attempt to upload (requires documents:create) → 403
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@invoice.pdf"

# Expected: 403 Forbidden (user has documents:read, not documents:create)
```

### 3. Test Tenant Isolation

**Setup:**
1. Create Tenant A with User A
2. Create Tenant B with User B
3. User A uploads document → doc_a_id

**Test:**
```bash
# Login as User B
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"userb@tenantb.com","password":"..."}'
# → Get TOKEN_B

# Attempt to access User A's document → 404
curl http://localhost:8000/api/v1/documents/$doc_a_id \
  -H "Authorization: Bearer $TOKEN_B"

# Expected: 404 Not Found (doesn't reveal existence)
```

---

## Database Queries (Before vs After)

### List Documents

**Before (INSECURE):**
```sql
SELECT * FROM documents
ORDER BY created_at DESC
LIMIT 20;

-- Returns ALL documents across ALL tenants
```

**After (SECURE):**
```sql
SELECT * FROM documents
WHERE tenant_id = '00000000-0000-0000-0000-000000000001'  -- User's tenant
ORDER BY created_at DESC
LIMIT 20;

-- Uses index: idx_documents_tenant_id
```

### Get Single Document

**Before (INSECURE):**
```sql
SELECT * FROM documents
WHERE id = 'some-uuid';

-- Could access any document
```

**After (SECURE):**
```sql
SELECT * FROM documents
WHERE tenant_id = '00000000-0000-0000-0000-000000000001'  -- FIRST
  AND id = 'some-uuid';                                    -- SECOND

-- Composite index scan: idx_documents_tenant_id + primary key
```

### Get Job Status (via JOIN)

**Before (INSECURE):**
```sql
SELECT * FROM extraction_jobs
WHERE id = 'job-uuid';

-- Could access any job
```

**After (SECURE):**
```sql
SELECT ej.* FROM extraction_jobs ej
INNER JOIN documents d ON ej.document_id = d.id
WHERE d.tenant_id = '00000000-0000-0000-0000-000000000001'
  AND ej.id = 'job-uuid';

-- Uses: idx_documents_tenant_id + foreign key index
```

---

## Performance Impact

### Database Indexes

All tenant-scoped queries benefit from these indexes:

```sql
-- Already exists (from migration)
CREATE INDEX idx_documents_tenant_id ON documents(tenant_id);
CREATE INDEX idx_schema_definitions_tenant_id ON schema_definitions(tenant_id);

-- Composite indexes for common queries (recommended)
CREATE INDEX idx_documents_tenant_id_created_at
  ON documents(tenant_id, created_at DESC);

CREATE INDEX idx_schema_definitions_tenant_id_created_at
  ON schema_definitions(tenant_id, created_at DESC);
```

### Query Performance

- **List Queries:** Tenant filter + index = O(log n) instead of O(n)
- **Single Item Queries:** Tenant filter first = immediate index hit
- **JOIN Queries:** Foreign key indexes optimize Document → ExtractionJob joins

**Expected Query Times:**
- List documents: < 10ms (indexed scan)
- Get single document: < 5ms (index lookup)
- Get job status (with JOIN): < 15ms (two index lookups + join)

---

## Migration Checklist

### Pre-Deployment

- [x] Add `tenant_id` to Document model (nullable=True)
- [x] Add `tenant_id` to SchemaDefinition model (nullable=True)
- [x] Update all API endpoints with authentication
- [x] Update all API endpoints with tenant filtering
- [x] Create architecture documentation
- [ ] Write unit tests for authentication
- [ ] Write unit tests for tenant isolation
- [ ] Write integration tests
- [ ] Run security audit

### Deployment Steps

1. **Deploy Code Changes:**
   ```bash
   git add app/api/documents.py app/api/jobs.py app/api/schemas.py
   git commit -m "feat: add authentication and multi-tenancy to API endpoints"
   git push
   ```

2. **Run Migrations (if new):**
   ```bash
   alembic upgrade head
   ```

3. **Seed Permissions and Roles:**
   ```bash
   python -m app.db.seed
   ```

4. **Verify:**
   ```bash
   # Test unauthenticated access (should fail)
   curl http://localhost:8000/api/v1/documents

   # Test authenticated access (should succeed)
   curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/documents
   ```

### Post-Deployment

- [ ] Monitor error rates (expect spike in 401s from old clients)
- [ ] Check slow query logs for missing indexes
- [ ] Verify no cross-tenant data access in logs
- [ ] Update API documentation (Swagger)
- [ ] Update client SDKs with authentication
- [ ] Notify users to obtain JWTs

---

## Breaking Changes

### For API Clients

**All endpoints now require authentication:**

```diff
# Before
- curl http://localhost:8000/api/v1/documents

# After
+ curl -H "Authorization: Bearer $TOKEN" \
+   http://localhost:8000/api/v1/documents
```

**How to obtain a JWT:**

```bash
# Login endpoint
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'

# Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

# Use access_token in Authorization header
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
curl -H "Authorization: Bearer $TOKEN" ...
```

---

## Troubleshooting

### Issue: 401 Unauthorized

**Cause:** No token or invalid token

**Solution:**
1. Obtain JWT via `/api/v1/auth/login`
2. Include in header: `Authorization: Bearer $TOKEN`
3. Check token hasn't expired (default: 30 minutes)

---

### Issue: 403 Forbidden

**Cause:** User lacks required permission

**Solution:**
1. Check user's role: `GET /api/v1/users/me`
2. Verify role has required permission
3. Grant permission or upgrade role

```sql
-- Check user's permissions
SELECT p.name, p.resource, p.action
FROM permissions p
JOIN role_permissions rp ON p.id = rp.permission_id
JOIN users u ON u.role_id = rp.role_id
WHERE u.email = 'user@example.com';
```

---

### Issue: 404 Not Found (but resource exists)

**Cause:** Resource belongs to different tenant

**Solution:**
- Verify you're logged in with correct tenant account
- Check resource actually exists in your tenant

```sql
-- Admin query to verify tenant ownership
SELECT d.id, d.filename, d.tenant_id, t.name AS tenant_name
FROM documents d
JOIN tenants t ON d.tenant_id = t.id
WHERE d.id = 'document-uuid';
```

---

### Issue: Query Performance Degraded

**Cause:** Missing or unused indexes

**Solution:**
```sql
-- Check if indexes are being used
EXPLAIN ANALYZE
SELECT * FROM documents
WHERE tenant_id = '...' AND id = '...';

-- Should show: Index Scan using idx_documents_tenant_id
-- Should NOT show: Seq Scan

-- Create missing indexes if needed
CREATE INDEX idx_documents_tenant_id_created_at
  ON documents(tenant_id, created_at DESC);
```

---

## Security Best Practices

### 1. Always Filter by tenant_id FIRST

```python
# CORRECT
query = (
    db.query(Model)
    .filter(Model.tenant_id == current_user.tenant_id)  # FIRST
    .filter(Model.id == entity_id)                      # SECOND
)

# WRONG - allows information disclosure
query = db.query(Model).filter(Model.id == entity_id)
if query.first().tenant_id != current_user.tenant_id:
    raise HTTPException(403)  # Too late - already revealed existence
```

### 2. Never Cache Without tenant_id in Key

```python
# CORRECT
cache_key = f"document:{current_user.tenant_id}:{document_id}"

# WRONG - cache poisoning across tenants
cache_key = f"document:{document_id}"
```

### 3. Use Generic 404 Messages

```python
# CORRECT - doesn't reveal existence
if not document:
    raise HTTPException(404, "Document not found")

# WRONG - information disclosure
if not document:
    if db.query(Document).filter(Document.id == doc_id).first():
        raise HTTPException(403, "Access denied to this tenant")
    raise HTTPException(404, "Document not found")
```

### 4. Log Security Events

```python
# Log failed access attempts
if not document:
    logger.warning(
        "document_access_denied",
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        document_id=document_id,
        reason="not_found_or_wrong_tenant"
    )
```

---

## Next Steps

### Immediate (Before Production)

1. **Write Tests:**
   - Unit tests for each endpoint
   - Integration tests for auth flow
   - Security tests for cross-tenant access

2. **Backfill Data:**
   - Assign tenant_id to existing Documents
   - Assign tenant_id to existing SchemaDefinitions

3. **Update Models:**
   - Change `nullable=True` → `nullable=False`
   - Create Alembic migration for NOT NULL constraint

### Short-term (First Week)

1. **Monitoring:**
   - Set up alerts for 401/403 errors
   - Monitor slow queries
   - Track permission denial rates

2. **Documentation:**
   - Update API docs (Swagger)
   - Create migration guide for clients
   - Write deployment runbook

### Long-term (First Month)

1. **Enhancements:**
   - Implement audit logging
   - Add rate limiting per tenant
   - Consider PostgreSQL Row-Level Security (RLS)

2. **Security:**
   - External security audit
   - Penetration testing
   - OWASP compliance verification

---

## References

- [Architecture Document](/Users/xavierau/Code/python/ai_document_processing/docs/architecture/2025-11-03-api-authentication-multi-tenancy.md)
- [Auth Dependencies](/Users/xavierau/Code/python/ai_document_processing/app/dependencies/auth.py)
- [Database Seed Script](/Users/xavierau/Code/python/ai_document_processing/app/db/seed.py)

---

**Implementation Completed:** 2025-11-03
**All API Endpoints Secured:** ✅
**Tenant Isolation Enforced:** ✅
**Production Ready:** Pending tests and data migration
