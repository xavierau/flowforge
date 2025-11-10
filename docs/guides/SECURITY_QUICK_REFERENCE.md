# API Security Quick Reference

**Date:** 2025-11-03
**For:** All Backend Developers

---

## 🔐 Authentication Dependency

### Basic Authentication (Active Users Only)

```python
from app.dependencies.auth import get_current_active_user
from app.models import User

@router.get("/endpoint")
async def my_endpoint(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # current_user is authenticated and active
    # Use: current_user.tenant_id, current_user.email, etc.
```

### Permission-Based Authentication (RECOMMENDED)

```python
from app.dependencies.auth import require_permission

@router.post("/documents/upload")
async def upload_document(
    current_user: User = Depends(require_permission("documents:create")),
    db: Session = Depends(get_db)
):
    # current_user has "documents:create" permission
```

---

## 🏢 Tenant Isolation Patterns

### CREATE Operations

```python
# ✅ CORRECT: Auto-assign tenant_id from current user
document = Document(
    tenant_id=current_user.tenant_id,  # ← ALWAYS set this
    filename="example.pdf",
    # ... other fields
)
db.add(document)
db.commit()

# ❌ WRONG: Never allow client to set tenant_id
document = Document(
    tenant_id=request.tenant_id,  # ← SECURITY VULNERABILITY
    filename="example.pdf",
)
```

---

### READ Operations (Single Item)

```python
# ✅ CORRECT: Tenant filter FIRST
document = (
    db.query(Document)
    .filter(Document.tenant_id == current_user.tenant_id)  # ← FIRST
    .filter(Document.id == document_id)                    # ← SECOND
    .first()
)
if not document:
    raise HTTPException(404, "Document not found")  # Generic message

# ❌ WRONG: Missing tenant filter
document = db.query(Document).filter(Document.id == document_id).first()
if document.tenant_id != current_user.tenant_id:
    raise HTTPException(403)  # Too late - revealed existence
```

---

### READ Operations (List)

```python
# ✅ CORRECT: Filter by tenant_id in base query
query = db.query(Document).filter(Document.tenant_id == current_user.tenant_id)

# Apply additional filters
if status:
    query = query.filter(Document.status == status)

# Pagination
documents = query.order_by(Document.created_at.desc()).limit(20).all()

# ❌ WRONG: No tenant filter
documents = db.query(Document).all()  # Returns ALL tenants' data
```

---

### UPDATE Operations

```python
# ✅ CORRECT: Validate ownership BEFORE update
document = (
    db.query(Document)
    .filter(Document.tenant_id == current_user.tenant_id)  # ← Validate
    .filter(Document.id == document_id)
    .first()
)
if not document:
    raise HTTPException(404, "Document not found")

# Now safe to update
document.filename = "new_name.pdf"
db.commit()

# ❌ WRONG: Update without validation
document = db.query(Document).filter(Document.id == document_id).first()
document.filename = "new_name.pdf"  # Modifies other tenant's data!
db.commit()
```

---

### DELETE Operations

```python
# ✅ CORRECT: Validate ownership BEFORE delete
document = (
    db.query(Document)
    .filter(Document.tenant_id == current_user.tenant_id)  # ← Validate
    .filter(Document.id == document_id)
    .first()
)
if not document:
    raise HTTPException(404, "Document not found")

db.delete(document)
db.commit()

# ❌ WRONG: Delete without validation
document = db.query(Document).filter(Document.id == document_id).first()
db.delete(document)  # Deletes other tenant's data!
db.commit()
```

---

### JOIN Operations (for related entities without tenant_id)

```python
# Example: ExtractionJob doesn't have tenant_id, but Document does

# ✅ CORRECT: JOIN through Document to validate tenant
job = (
    db.query(ExtractionJob)
    .join(Document)
    .filter(Document.tenant_id == current_user.tenant_id)  # ← Tenant check
    .filter(ExtractionJob.id == job_id)
    .first()
)

# ❌ WRONG: Direct query without tenant validation
job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
```

---

## 🛡️ Error Messages (Security)

### Generic 404 (No Information Disclosure)

```python
# ✅ CORRECT: Don't reveal if resource exists in another tenant
if not document:
    raise HTTPException(404, "Document not found")

# ❌ WRONG: Reveals existence
if not document:
    if db.query(Document).filter(Document.id == doc_id).first():
        raise HTTPException(403, "You don't have access to this document")
    raise HTTPException(404, "Document not found")
```

---

## 📋 Available Permissions

### Documents
- `documents:create` - Upload and parse
- `documents:read` - List and get
- `documents:update` - Modify
- `documents:delete` - Delete
- `documents:share` - Share with others
- `documents:export` - Export data

### Schemas
- `schemas:create` - Create schema definitions
- `schemas:read` - List and get schemas
- `schemas:update` - Modify schemas
- `schemas:delete` - Delete schemas
- `schemas:share` - Share schemas

### Users
- `users:invite` - Invite new users
- `users:read` - View user info
- `users:update` - Modify users
- `users:delete` - Delete users

### Tenant
- `tenant:manage` - Manage tenant settings
- `tenant:billing` - Manage billing

---

## 🎯 Common Patterns

### Pattern 1: Simple CRUD Endpoint

```python
@router.post("/items")
async def create_item(
    request: ItemCreate,
    current_user: User = Depends(require_permission("items:create")),
    db: Session = Depends(get_db)
):
    item = Item(
        tenant_id=current_user.tenant_id,  # ← Auto-assign
        name=request.name,
    )
    db.add(item)
    db.commit()
    return item

@router.get("/items/{item_id}")
async def get_item(
    item_id: UUID,
    current_user: User = Depends(require_permission("items:read")),
    db: Session = Depends(get_db)
):
    item = (
        db.query(Item)
        .filter(Item.tenant_id == current_user.tenant_id)
        .filter(Item.id == item_id)
        .first()
    )
    if not item:
        raise HTTPException(404, "Item not found")
    return item
```

### Pattern 2: List with Pagination

```python
@router.get("/items")
async def list_items(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("items:read")),
    db: Session = Depends(get_db)
):
    # Base query with tenant filter
    query = db.query(Item).filter(Item.tenant_id == current_user.tenant_id)

    # Get total count
    total = query.count()

    # Get paginated results
    items = query.order_by(Item.created_at.desc()).limit(limit).offset(offset).all()

    return {"items": items, "total": total, "limit": limit, "offset": offset}
```

### Pattern 3: Related Entity via JOIN

```python
@router.get("/parent/{parent_id}/children")
async def list_children(
    parent_id: UUID,
    current_user: User = Depends(require_permission("children:read")),
    db: Session = Depends(get_db)
):
    # Validate parent ownership
    parent = (
        db.query(Parent)
        .filter(Parent.tenant_id == current_user.tenant_id)
        .filter(Parent.id == parent_id)
        .first()
    )
    if not parent:
        raise HTTPException(404, "Parent not found")

    # Get children (no need to check tenant again - FK ensures same tenant)
    children = db.query(Child).filter(Child.parent_id == parent.id).all()

    return children
```

---

## ⚠️ Common Mistakes

### Mistake 1: Checking tenant_id AFTER query

```python
# ❌ WRONG
document = db.query(Document).filter(Document.id == doc_id).first()
if document.tenant_id != current_user.tenant_id:
    raise HTTPException(403)  # Already revealed existence!

# ✅ CORRECT
document = (
    db.query(Document)
    .filter(Document.tenant_id == current_user.tenant_id)
    .filter(Document.id == doc_id)
    .first()
)
if not document:
    raise HTTPException(404)  # Generic message
```

### Mistake 2: Allowing client to set tenant_id

```python
# ❌ WRONG
@router.post("/items")
async def create_item(request: ItemCreate):
    item = Item(
        tenant_id=request.tenant_id,  # ← CLIENT CONTROLS THIS
        name=request.name
    )

# ✅ CORRECT
@router.post("/items")
async def create_item(
    request: ItemCreate,
    current_user: User = Depends(require_permission("items:create"))
):
    item = Item(
        tenant_id=current_user.tenant_id,  # ← SERVER CONTROLS THIS
        name=request.name
    )
```

### Mistake 3: No authentication on "public" endpoints

```python
# ❌ WRONG (unless truly public like /health)
@router.get("/items")
async def list_items(db: Session = Depends(get_db)):
    return db.query(Item).all()  # Returns ALL tenants' data!

# ✅ CORRECT
@router.get("/items")
async def list_items(
    current_user: User = Depends(require_permission("items:read")),
    db: Session = Depends(get_db)
):
    return db.query(Item).filter(Item.tenant_id == current_user.tenant_id).all()
```

### Mistake 4: Revealing different error codes

```python
# ❌ WRONG
if not document:
    raise HTTPException(404, "Document not found")
if document.tenant_id != current_user.tenant_id:
    raise HTTPException(403, "Access denied")  # Reveals it exists!

# ✅ CORRECT
document = (
    db.query(Document)
    .filter(Document.tenant_id == current_user.tenant_id)
    .filter(Document.id == doc_id)
    .first()
)
if not document:
    raise HTTPException(404, "Document not found")  # One error for all cases
```

---

## 🧪 Testing Checklist

### For Every New Endpoint

- [ ] Unauthenticated request returns 401
- [ ] User without permission returns 403
- [ ] User with permission succeeds
- [ ] Tenant A cannot access Tenant B's data (returns 404, not 403)
- [ ] CREATE sets tenant_id correctly
- [ ] UPDATE/DELETE validate tenant ownership
- [ ] LIST endpoints filter by tenant_id
- [ ] No information disclosure in error messages

---

## 📚 Quick Links

- [Full Architecture Doc](/docs/architecture/2025-11-03-api-authentication-multi-tenancy.md)
- [Implementation Summary](/docs/guides/2025-11-03-api-security-implementation-summary.md)
- [Auth Dependencies](/app/dependencies/auth.py)
- [Seeded Permissions](/app/db/seed.py)

---

## 🆘 Need Help?

### Getting current user info

```python
# In endpoint handler
print(f"User: {current_user.email}")
print(f"Tenant: {current_user.tenant_id}")
print(f"Role: {current_user.role.name}")
```

### Checking user permissions

```python
from app.services.permission_service import PermissionService

permission_service = PermissionService(db)
has_perm = permission_service.user_has_permission(current_user, "documents:create")
```

### Debugging tenant isolation

```sql
-- Check what tenant owns a document
SELECT d.id, d.filename, d.tenant_id, t.name AS tenant_name
FROM documents d
JOIN tenants t ON d.tenant_id = t.id
WHERE d.id = 'document-uuid';
```

---

**Last Updated:** 2025-11-03
**Keep this handy when writing new endpoints!** 🚀
