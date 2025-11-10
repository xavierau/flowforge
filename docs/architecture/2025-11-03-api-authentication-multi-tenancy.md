# API Authentication and Multi-Tenancy Implementation

**Date:** 2025-11-03
**Status:** Implemented
**Type:** Security Enhancement

---

## Executive Summary

All API endpoints in the document processing system have been updated with JWT-based authentication and tenant-level data isolation. This ensures that:

1. **Zero Unauthenticated Access**: Every endpoint requires authentication
2. **Complete Tenant Isolation**: Users can only access data belonging to their tenant
3. **Permission-Based Authorization**: Fine-grained access control using RBAC permissions
4. **Security by Design**: No data leakage across tenant boundaries

---

## Architecture Overview

### Authentication Flow

```
Client Request
    ↓
[JWT Token in Authorization Header]
    ↓
[FastAPI Dependency: get_current_user]
    ↓
[Verify Token & Extract User ID]
    ↓
[Query User from Database]
    ↓
[Check is_active Status]
    ↓
[Check Permission via require_permission]
    ↓
[Endpoint Handler with tenant_id filtering]
    ↓
Response (tenant-scoped data only)
```

### Tenant Isolation Pattern

Every database query follows this critical pattern:

```python
# CORRECT: Tenant filter FIRST
db.query(Model)
  .filter(Model.tenant_id == current_user.tenant_id)  # ← FIRST
  .filter(Model.id == entity_id)                      # ← SECOND
  .first()

# WRONG: Risk of cross-tenant access
db.query(Model).filter(Model.id == entity_id).first()
```

**Why this matters:**
- Prevents information disclosure across tenants
- 404 errors don't reveal existence of resources in other tenants
- Database indexes optimize for tenant_id first (idx_documents_tenant_id, etc.)

---

## Updated API Endpoints

### 1. Documents API (`app/api/documents.py`)

#### POST /api/v1/documents/upload
- **Permission Required**: `documents:create`
- **Creates**: Document with `tenant_id = current_user.tenant_id`
- **Security**: Auto-assigns tenant, user cannot forge tenant_id

#### POST /api/v1/documents/{document_id}/parse
- **Permission Required**: `documents:create`
- **Validates**: Document belongs to user's tenant before parsing
- **Security**: Cannot trigger extraction jobs on other tenants' documents

#### GET /api/v1/documents
- **Permission Required**: `documents:read`
- **Filters**: `tenant_id == current_user.tenant_id`
- **Security**: List endpoint only shows tenant's documents

#### GET /api/v1/documents/{document_id}
- **Permission Required**: `documents:read`
- **Validates**: Document belongs to user's tenant
- **Security**: Returns 404 for documents in other tenants (doesn't reveal existence)

---

### 2. Jobs API (`app/api/jobs.py`)

#### GET /api/v1/jobs/{job_id}/status
- **Permission Required**: `documents:read`
- **Validates**: Job belongs to user's tenant (via Document JOIN)
- **Security**: Prevents status checks on other tenants' jobs

```python
# Join through Document to check tenant ownership
job = (
    db.query(ExtractionJob)
    .join(Document)
    .filter(Document.tenant_id == current_user.tenant_id)
    .filter(ExtractionJob.id == job_id)
    .first()
)
```

#### GET /api/v1/jobs/{job_id}/result
- **Permission Required**: `documents:read`
- **Validates**: Job belongs to user's tenant (via Document JOIN)
- **Security**: Cannot access extraction results from other tenants

---

### 3. Schemas API (`app/api/schemas.py`)

#### POST /api/v1/schemas
- **Permission Required**: `schemas:create`
- **Creates**: SchemaDefinition with `tenant_id = current_user.tenant_id`
- **Security**: Schema names scoped per tenant (tenant A and B can have same name)

#### GET /api/v1/schemas
- **Permission Required**: `schemas:read`
- **Filters**: `tenant_id == current_user.tenant_id`
- **Security**: Only shows tenant's schemas

#### GET /api/v1/schemas/{schema_id}
- **Permission Required**: `schemas:read`
- **Validates**: Schema belongs to user's tenant
- **Security**: Returns 404 for schemas in other tenants

#### GET /api/v1/schemas/name/{schema_name}
- **Permission Required**: `schemas:read`
- **Validates**: Schema belongs to user's tenant
- **Security**: Name lookup scoped to tenant

#### PUT /api/v1/schemas/{schema_id}
- **Permission Required**: `schemas:update`
- **Validates**: Schema belongs to user's tenant before updating
- **Security**: Cannot modify other tenants' schemas

#### DELETE /api/v1/schemas/{schema_id}
- **Permission Required**: `schemas:delete`
- **Validates**: Schema belongs to user's tenant before deletion
- **Security**: Cannot delete other tenants' schemas

---

## Permission Mapping

| Endpoint | HTTP Method | Permission Required | Resource Type |
|----------|-------------|---------------------|---------------|
| Upload Document | POST | `documents:create` | Document |
| Parse Document | POST | `documents:create` | Document |
| List Documents | GET | `documents:read` | Document |
| Get Document | GET | `documents:read` | Document |
| Job Status | GET | `documents:read` | Extraction Job |
| Job Result | GET | `documents:read` | Extraction Job |
| Create Schema | POST | `schemas:create` | Schema |
| List Schemas | GET | `schemas:read` | Schema |
| Get Schema | GET | `schemas:read` | Schema |
| Update Schema | PUT | `schemas:update` | Schema |
| Delete Schema | DELETE | `schemas:delete` | Schema |

---

## Security Guarantees

### 1. Authentication Enforcement

Every endpoint uses one of these dependencies:

```python
# For permission-based access
current_user: User = Depends(require_permission("resource:action"))

# For basic authenticated access (rarely used)
current_user: User = Depends(get_current_active_user)
```

**Exception Handling:**
- `401 Unauthorized`: No token or invalid token
- `403 Forbidden`: Authenticated but lacks permission
- `404 Not Found`: Resource doesn't exist OR belongs to different tenant

### 2. Tenant Isolation

**CREATE operations:**
```python
entity = Model(
    tenant_id=current_user.tenant_id,  # ALWAYS set from current user
    # ... other fields
)
```

**READ operations (single):**
```python
entity = (
    db.query(Model)
    .filter(Model.tenant_id == current_user.tenant_id)  # FIRST
    .filter(Model.id == entity_id)                      # SECOND
    .first()
)
if not entity:
    raise HTTPException(404, "Not found")  # Don't reveal existence
```

**READ operations (list):**
```python
query = db.query(Model).filter(Model.tenant_id == current_user.tenant_id)
# Apply additional filters...
results = query.all()
```

**UPDATE/DELETE operations:**
```python
entity = (
    db.query(Model)
    .filter(Model.tenant_id == current_user.tenant_id)  # FIRST
    .filter(Model.id == entity_id)
    .first()
)
if not entity:
    raise HTTPException(404, "Not found")
# Perform update/delete
```

### 3. No Information Disclosure

**CRITICAL:** Never reveal whether a resource exists in another tenant.

```python
# CORRECT: Generic 404 message
if not document:
    raise HTTPException(404, "Document not found")

# WRONG: Reveals existence in other tenant
if not document:
    if db.query(Document).filter(Document.id == doc_id).first():
        raise HTTPException(403, "Access denied")
    raise HTTPException(404, "Document not found")
```

---

## Database Schema Support

### Models with tenant_id

All tenant-scoped models include:

```python
tenant_id = Column(
    UUID(as_uuid=True),
    ForeignKey("tenants.id", ondelete="CASCADE"),
    nullable=True,  # Nullable for migration, will be False in production
    index=True
)
```

**Indexed for Performance:**
- `idx_documents_tenant_id`
- `idx_schema_definitions_tenant_id`

**Cascade Delete:**
- When a Tenant is deleted, all associated Documents and SchemaDefinitions are automatically deleted

### Relationship to ExtractionJob

ExtractionJob does NOT have tenant_id directly, but inherits it through Document:

```python
# Tenant-scoped job query via JOIN
job = (
    db.query(ExtractionJob)
    .join(Document)
    .filter(Document.tenant_id == current_user.tenant_id)
    .filter(ExtractionJob.id == job_id)
    .first()
)
```

This ensures:
- No duplicate tenant_id storage
- Automatic tenant isolation through foreign key relationship
- Database normalization

---

## Testing Strategy

### Unit Tests (to be implemented)

```python
def test_document_upload_requires_authentication():
    """Test that unauthenticated users cannot upload documents."""
    response = client.post("/api/v1/documents/upload", files={"file": ...})
    assert response.status_code == 401

def test_document_list_filtered_by_tenant():
    """Test that users only see documents from their tenant."""
    # Create documents for two different tenants
    # Login as tenant A user
    # Assert only tenant A documents returned

def test_cannot_access_other_tenant_document():
    """Test that accessing another tenant's document returns 404."""
    # Create document for tenant A
    # Login as tenant B user
    # Attempt to get tenant A's document
    # Assert 404 (not 403, to avoid information disclosure)
```

### Integration Tests

1. **Authentication Flow:**
   - Login with valid credentials → receive JWT
   - Use JWT to access protected endpoint → success
   - Use invalid JWT → 401
   - Use expired JWT → 401

2. **Tenant Isolation:**
   - Create resources as Tenant A
   - Attempt to read as Tenant B → 404
   - Attempt to update as Tenant B → 404
   - Attempt to delete as Tenant B → 404

3. **Permission Enforcement:**
   - User with `documents:read` → can list/get documents
   - User with `documents:read` → cannot create documents (403)
   - User with `documents:create` → can upload documents

---

## Migration Considerations

### Backward Compatibility

**CRITICAL:** The `tenant_id` column is currently `nullable=True` for migration.

**Migration Steps:**
1. ✅ Add `tenant_id` column as nullable
2. ✅ Update API endpoints to require authentication
3. 🔄 Backfill `tenant_id` for existing documents (if any)
4. 🔄 Change `nullable=False` in model
5. 🔄 Create Alembic migration for NOT NULL constraint

**Sample Backfill Script:**
```python
# Migration: Assign all existing documents to platform tenant
from app.models import Document, Tenant
from app.database import SessionLocal

db = SessionLocal()
platform_tenant = db.query(Tenant).filter(Tenant.slug == "platform").first()

db.query(Document).filter(Document.tenant_id == None).update({
    "tenant_id": platform_tenant.id
})
db.commit()
```

---

## Dependencies

### Required Models
- `User` (with `tenant_id`, `role_id`, `is_active`)
- `Tenant` (with `id`, `status`)
- `Role` (with permissions)
- `Permission` (with `name`, `resource`, `action`)
- `RolePermission` (junction table)

### Required Dependencies
- `app.dependencies.auth.get_current_user`
- `app.dependencies.auth.get_current_active_user`
- `app.dependencies.auth.require_permission`

### Required Services
- `app.services.auth_service` (JWT token verification)
- `app.services.permission_service` (permission checking)

---

## Security Checklist

### Before Deployment

- [x] All API endpoints require authentication
- [x] All queries filter by tenant_id
- [x] All CREATE operations set tenant_id from current_user
- [x] All READ operations validate tenant ownership
- [x] All UPDATE operations validate tenant ownership
- [x] All DELETE operations validate tenant ownership
- [x] 404 errors don't reveal existence in other tenants
- [x] Permission dependencies configured correctly
- [ ] Unit tests cover cross-tenant access attempts
- [ ] Integration tests validate authentication flow
- [ ] Load tests confirm performance with tenant filtering
- [ ] Security audit by external team
- [ ] Penetration testing completed

### Runtime Monitoring

- [ ] Log all 403 errors (potential unauthorized access attempts)
- [ ] Alert on unusual cross-tenant query patterns
- [ ] Monitor JWT token expiration and refresh patterns
- [ ] Track permission denial rates per user/role

---

## Performance Considerations

### Database Indexes

All tenant-scoped queries benefit from these indexes:

```sql
CREATE INDEX idx_documents_tenant_id ON documents(tenant_id);
CREATE INDEX idx_schema_definitions_tenant_id ON schema_definitions(tenant_id);
CREATE INDEX idx_documents_tenant_id_created_at ON documents(tenant_id, created_at DESC);
```

**Query Plan Example:**
```sql
EXPLAIN ANALYZE
SELECT * FROM documents
WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
  AND id = 'some-uuid';

-- Expected: Index Scan using idx_documents_tenant_id
-- Should NOT be: Sequential Scan
```

### Caching Considerations

**CRITICAL:** Never cache data without tenant_id in the cache key.

```python
# CORRECT: Include tenant_id in cache key
cache_key = f"document:{tenant_id}:{document_id}"

# WRONG: Risk of cross-tenant data leakage
cache_key = f"document:{document_id}"
```

---

## Known Limitations

1. **ExtractionJob Tenant Filtering:** Requires JOIN through Document table (slightly slower)
   - Mitigation: Indexed foreign key on `document_id`

2. **Nullable tenant_id:** Migration period allows NULL values
   - Mitigation: Deploy backfill script before enforcing NOT NULL

3. **No Row-Level Security (RLS):** Relies on application-level filtering
   - Mitigation: Consider PostgreSQL RLS policies for defense-in-depth

---

## Future Enhancements

### 1. Row-Level Security (PostgreSQL)

```sql
-- Enable RLS on documents table
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their tenant's documents
CREATE POLICY tenant_isolation ON documents
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### 2. Audit Logging

```python
# Log all data access attempts
@router.get("/documents/{document_id}")
async def get_document(...):
    audit_log.info(
        "document_access",
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        document_id=document_id,
        action="read"
    )
```

### 3. Rate Limiting per Tenant

```python
# Prevent one tenant from monopolizing resources
@limiter.limit("100/minute", key_func=lambda: current_user.tenant_id)
async def upload_document(...):
    ...
```

---

## References

- [Seeded Permissions](/Users/xavierau/Code/python/ai_document_processing/app/db/seed.py)
- [Auth Dependencies](/Users/xavierau/Code/python/ai_document_processing/app/dependencies/auth.py)
- [User Model](/Users/xavierau/Code/python/ai_document_processing/app/models/user.py)
- [Document Model](/Users/xavierau/Code/python/ai_document_processing/app/models/document.py)
- [OWASP API Security Top 10](https://owasp.org/API-Security/editions/2023/en/0x11-t10/)

---

## Conclusion

All API endpoints are now secured with:

1. **JWT-based authentication** - No unauthenticated access
2. **Permission-based authorization** - Fine-grained access control
3. **Tenant-level isolation** - Complete data segregation
4. **Security by design** - No information disclosure across tenants

The implementation follows industry best practices for multi-tenant SaaS applications and provides a solid foundation for production deployment.

**Next Steps:**
1. Implement comprehensive test suite
2. Backfill tenant_id for existing data
3. Enable NOT NULL constraint on tenant_id
4. Deploy to staging for security testing
5. Conduct penetration testing
6. Production deployment with monitoring

---

**Document Version:** 1.0
**Last Updated:** 2025-11-03
**Author:** AI Solution Architect (Claude Code)
