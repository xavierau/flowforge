# Deprecation Fixes & Migration Guide

**Date:** 2025-12-03
**Status:** Implemented
**Applies to:** All Python code in `app/`

---

## Overview

This guide documents fixes for deprecation warnings including:
- Pydantic V2 `ConfigDict` migration
- FastAPI lifespan events migration
- SQLAlchemy 2.0 imports
- Third-party warning suppression

---

## Quick Reference

### Before (Deprecated - DO NOT USE)

```python
from pydantic import BaseModel, Field

class MyModel(BaseModel):
    name: str = Field(..., description="Name")

    class Config:
        from_attributes = True
        json_schema_extra = {"example": {"name": "test"}}
```

### After (Required Pattern)

```python
from pydantic import BaseModel, ConfigDict, Field

class MyModel(BaseModel):
    """Model description."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"name": "test"}}
    )

    name: str = Field(..., description="Name")
```

---

## ConfigDict Options Reference

| Option | Purpose | Example |
|--------|---------|---------|
| `from_attributes=True` | Enable ORM mode (SQLAlchemy models) | Response models |
| `populate_by_name=True` | Allow both field name and alias | Alias support |
| `use_enum_values=True` | Serialize enums as their values | Enum fields |
| `json_schema_extra={...}` | OpenAPI examples | API documentation |
| `ser_json_by_alias=False` | Serialize using field name, not alias | Override alias in output |

---

## Common Patterns

### 1. Simple Response Model (ORM)

```python
from pydantic import BaseModel, ConfigDict, Field

class UserResponse(BaseModel):
    """User response model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    is_active: bool
```

### 2. Request Model with Examples

```python
from pydantic import BaseModel, ConfigDict, Field

class CreateUserRequest(BaseModel):
    """Create user request."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }
    )

    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="Password")
```

### 3. Model with Aliases (camelCase API)

```python
from pydantic import BaseModel, ConfigDict, Field

class WorkflowResponse(BaseModel):
    """Workflow response with camelCase aliases."""

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )

    id: UUID
    workflow_id: UUID = Field(alias="workflowId")
    created_at: datetime = Field(alias="createdAt")
```

### 4. Model with Enums

```python
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import JobStatus

class JobResponse(BaseModel):
    """Job response with enum serialization."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True
    )

    id: UUID
    status: JobStatus  # Serializes as string value, not enum
```

### 5. Combined Options

```python
from pydantic import BaseModel, ConfigDict, Field

class ComplexResponse(BaseModel):
    """Complex response with all options."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed"
            }
        }
    )

    id: UUID
    status: str
```

---

## Validators Migration

### Before (Deprecated)

```python
from pydantic import BaseModel, validator

class MyModel(BaseModel):
    value: int

    @validator('value')
    def validate_value(cls, v):
        if v < 0:
            raise ValueError("Must be non-negative")
        return v
```

### After (Required Pattern)

```python
from pydantic import BaseModel, ConfigDict, field_validator

class MyModel(BaseModel):
    model_config = ConfigDict()

    value: int

    @field_validator('value')
    @classmethod
    def validate_value(cls, v):
        if v < 0:
            raise ValueError("Must be non-negative")
        return v
```

**Key changes:**
- `@validator` → `@field_validator`
- Must add `@classmethod` decorator
- Import from `pydantic` directly

---

## File Structure Convention

Place `model_config` at the top of the class, before field definitions:

```python
class MyModel(BaseModel):
    """Docstring first."""

    model_config = ConfigDict(...)  # Config second

    # Fields third
    field_one: str
    field_two: int

    # Validators last
    @field_validator('field_one')
    @classmethod
    def validate_field_one(cls, v):
        return v
```

---

## Migration Checklist

When creating or updating schemas:

- [ ] Import `ConfigDict` from pydantic
- [ ] Replace `class Config:` with `model_config = ConfigDict(...)`
- [ ] Move config to top of class (after docstring)
- [ ] Replace `@validator` with `@field_validator` + `@classmethod`
- [ ] Use keyword arguments in ConfigDict (not class attributes)
- [ ] Test import: `python -c "from app.schemas.mymodule import MyModel"`

---

## Files Updated (2025-12-03)

| File | Models Updated |
|------|----------------|
| `app/schemas/document.py` | DocumentResponse, DocumentUploadResponse, DocumentListResponse |
| `app/schemas/credits.py` | CreditBalanceResponse, CreditTransactionResponse, CreditTopUpResponse |
| `app/schemas/workflow.py` | BaseNodeData, ExtractionNodeConfig, HttpRequestNodeConfig, WorkflowNode, WorkflowEdge, WorkflowUpdateRequest, WorkflowVersionResponse, WorkflowResponse, WorkflowListResponse, ExecuteWorkflowRequest, WorkflowNodeExecutionResponse, WorkflowExecutionResponse, WorkflowExecutionListResponse, WorkflowWebhookRequest |
| `app/schemas/extraction.py` | ModelConfig, ParseRequest, ParseResponse, ExtractRequest, ExtractResponse, DocumentPageResponse |
| `app/schemas/job.py` | JobProgress, JobStatusResponse, ExtractionMetadata, JobResultResponse, JobListItem, JobListResponse |
| `app/schemas/schema_definition.py` | SchemaDefinitionCreate, SchemaDefinitionUpdate, SchemaDefinitionResponse, SchemaDefinitionListResponse |
| `app/schemas/admin.py` | PlatformStatistics, TenantListItem, TenantSubscriptionInfo, UserListItem, ApiTokenListItem, AuditLogEntry, UpdateTenantStatusRequest, UpdateUserStatusRequest, RevokeApiTokenRequest, AddTenantCreditsRequest, PlatformSettingResponse, UpdatePlatformSettingRequest, TopTenantItem |
| `app/schemas/review.py` | CorrectionCreate, CorrectionResponse, ReviewRequestCreate, ReviewRequestResponse, ReviewAssignRequest, ReviewEscalateRequest, ReviewSubmitRequest, ReviewQueueFilter, ReviewQueueResponse, ReviewMetricsResponse |
| `app/schemas/error.py` | ErrorDetail |

---

## FastAPI Lifespan Migration

### Before (Deprecated)

```python
from fastapi import FastAPI

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    print("Starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down...")
```

### After (Required Pattern)

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    # Startup code here
    print("Starting up...")

    yield  # Application runs here

    # Shutdown code here
    print("Shutting down...")

app = FastAPI(
    title="My API",
    lifespan=lifespan,  # Pass lifespan to FastAPI
)
```

**File updated:** `app/main.py`

---

## SQLAlchemy 2.0 Migration

**File:** `app/database.py`

```python
# Before (deprecated)
from sqlalchemy.ext.declarative import declarative_base

# After
from sqlalchemy.orm import declarative_base
```

---

## Third-Party Warning Suppression

Some warnings come from third-party packages we cannot modify. These are suppressed in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
filterwarnings = [
    # Ignore deprecation warnings from third-party packages
    "ignore::pydantic.PydanticDeprecatedSince20:litellm.*",
    "ignore::pydantic.PydanticDeprecatedSince212:google.genai.*",
    "ignore::DeprecationWarning:litellm.*",
    "ignore::DeprecationWarning:importlib_resources.*",
    # Convert our own deprecation warnings to errors
    "error::DeprecationWarning:app.*",
]
```

### Known Third-Party Warnings (Cannot Fix)

| Package | Warning | Reason |
|---------|---------|--------|
| `litellm` | Pydantic `class Config` | Upstream issue |
| `litellm` | `importlib_resources.open_text` | Upstream issue |
| `google-genai` | `@model_validator` classmethod | Upstream issue |

**Action:** Monitor package updates and remove filters when fixed upstream.

---

## Summary of All Fixes (2025-12-03)

| File | Issue | Fix |
|------|-------|-----|
| `app/database.py` | SQLAlchemy 2.0 import | `sqlalchemy.orm.declarative_base` |
| `app/main.py` | FastAPI `on_event` deprecated | `lifespan` context manager |
| `app/schemas/*.py` (9 files) | Pydantic `class Config` | `model_config = ConfigDict(...)` |
| `app/schemas/admin.py` | `@validator` deprecated | `@field_validator` + `@classmethod` |
| `pyproject.toml` | Third-party warnings | `filterwarnings` config |

---

## References

- [Pydantic V2 Migration Guide](https://docs.pydantic.dev/latest/concepts/migration/)
- [ConfigDict Documentation](https://docs.pydantic.dev/latest/api/config/)
- [Field Validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
