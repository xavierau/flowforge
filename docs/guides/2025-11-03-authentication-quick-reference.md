# Authentication API Quick Reference

**Last Updated:** 2025-11-03

Quick reference guide for the authentication API implementation.

## Files Overview

```
app/
├── api/auth.py                    # 8 API endpoints
├── schemas/auth.py                # Request/response schemas
├── models/                        # Database models (existing)
│   ├── user.py
│   ├── tenant.py
│   ├── role.py
│   └── permission.py
├── services/                      # Business logic (existing)
│   ├── auth_service.py
│   └── permission_service.py
└── dependencies/auth.py           # Auth dependencies (existing)

tests/
├── conftest.py                    # Test fixtures
├── unit/schemas/
│   └── test_auth_schemas.py       # Schema validation tests
└── integration/api/
    └── test_auth_api.py           # API endpoint tests
```

## Quick Command Reference

### Testing

```bash
# Run all auth tests
pytest tests/ -v -k auth

# Run schema validation tests only
pytest tests/unit/schemas/test_auth_schemas.py -v

# Run API integration tests only
pytest tests/integration/api/test_auth_api.py -v

# Run with coverage report
pytest tests/ --cov=app.api.auth --cov=app.schemas.auth --cov-report=html
open htmlcov/index.html  # View coverage report

# Run specific test
pytest tests/integration/api/test_auth_api.py::TestRegisterEndpoint::test_register_with_new_tenant -v
```

### Development

```bash
# Start API server
uvicorn app.main:app --reload --port 8000

# Access API docs
open http://localhost:8000/docs

# Check Python syntax
python -m py_compile app/api/auth.py app/schemas/auth.py

# Format code (if using black)
black app/api/auth.py app/schemas/auth.py tests/

# Lint code (if using ruff)
ruff check app/api/auth.py app/schemas/auth.py
```

## API Endpoints Cheat Sheet

### 1. Register

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123",
    "full_name": "John Doe",
    "tenant_name": "Acme Corp"
  }'
```

**Response (201):**
```json
{
  "user": {...},
  "tenant": {...},
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123"
  }'
```

**Response (200):** Same as register

### 3. Refresh Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGc..."
  }'
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### 4. Logout

```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response (200):**
```json
{
  "message": "Logged out successfully"
}
```

### 5. Forgot Password

```bash
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

**Response (200):**
```json
{
  "message": "If the email exists, a password reset link has been sent"
}
```

### 6. Reset Password

```bash
curl -X POST http://localhost:8000/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "reset-token-from-email",
    "new_password": "NewSecurePass456"
  }'
```

**Response (200):**
```json
{
  "message": "Password reset successfully"
}
```

### 7. Verify Email

```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{
    "token": "verification-token-from-email"
  }'
```

**Response (200):**
```json
{
  "message": "Email verified successfully"
}
```

### 8. Get Current User

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

**Response (200):**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "is_verified": true,
    "locale": "en",
    "role_id": "uuid",
    "tenant_id": "uuid",
    "created_at": "2025-11-03T10:00:00Z",
    "last_login": "2025-11-03T12:30:00Z"
  },
  "tenant": {
    "id": "uuid",
    "name": "Acme Corp",
    "slug": "acme-corp",
    "status": "active",
    "subscription_plan": "pro",
    "credit_balance": 1000
  },
  "permissions": [
    "documents:create",
    "documents:read",
    "schemas:create",
    "schemas:read"
  ]
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid or expired reset token"
}
```

### 401 Unauthorized
```json
{
  "detail": "Incorrect email or password"
}
```

### 404 Not Found
```json
{
  "detail": "User not found"
}
```

### 409 Conflict
```json
{
  "detail": "Email already registered"
}
```

### 422 Unprocessable Entity (Validation Error)
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "password"],
      "msg": "Password must contain at least one uppercase letter",
      "input": "weakpass123"
    }
  ]
}
```

## Common Code Patterns

### Using Auth Headers in Tests

```python
def test_protected_endpoint(client, auth_headers):
    """Test endpoint with authentication."""
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
```

### Creating Test Users

```python
def test_something(client, test_user, db_session):
    """Test with pre-created user."""
    # test_user is already created and committed
    assert test_user.email == "testuser@example.com"
```

### Seeding Roles and Permissions

```python
def test_with_permissions(client, seed_roles, seed_permissions, seed_role_permissions):
    """Test with full RBAC setup."""
    # All roles, permissions, and mappings are ready
    pass
```

### Generating Tokens Manually

```python
from app.services.auth_service import auth_service

# Generate access token
access_token = auth_service.create_access_token(
    user_id=str(user.id),
    tenant_id=str(tenant.id)
)

# Generate refresh token
refresh_token = auth_service.create_refresh_token(
    user_id=str(user.id)
)

# Verify token
payload = auth_service.verify_token(access_token, token_type="access")
```

## Password Validation Rules

Enforced by Pydantic validators in `RegisterRequest` and `ResetPasswordRequest`:

- ✅ Minimum 8 characters
- ✅ At least 1 uppercase letter (A-Z)
- ✅ At least 1 number (0-9)
- ❌ No maximum length (reasonable limit: 128 chars)
- ❌ No special character requirement (optional)

**Valid Examples:**
- `SecurePass123`
- `MyPassword1`
- `Test1234`

**Invalid Examples:**
- `short` (too short)
- `nouppercase123` (no uppercase)
- `NoNumbers` (no number)

## Email Validation Rules

Enforced by Pydantic validators in all request schemas:

- ✅ Valid email format (`user@domain.com`)
- ✅ Automatically normalized to lowercase
- ✅ Maximum 255 characters

**Valid Examples:**
- `user@example.com`
- `john.doe+tag@company.co.uk`
- `USER@EXAMPLE.COM` (normalized to lowercase)

**Invalid Examples:**
- `notanemail`
- `@example.com`
- `user@`

## Token Configuration

Defined in `app/config.py` (Settings):

```python
# JWT settings
jwt_secret_key: str = "change-this-in-production"
jwt_algorithm: str = "HS256"
access_token_expire_minutes: int = 15
refresh_token_expire_days: int = 7
```

**Production Settings:**
```bash
# .env
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## Database Schema

### Key Columns

**users table:**
- `id` (UUID, PK)
- `email` (String, unique, indexed)
- `hashed_password` (String)
- `is_active` (Boolean, default=True)
- `is_verified` (Boolean, default=False)
- `refresh_token` (String, nullable)
- `password_reset_token` (String, nullable)
- `password_reset_expires` (DateTime, nullable)
- `email_verification_token` (String, nullable)
- `last_login` (DateTime, nullable)
- `role_id` (UUID, FK to roles)
- `tenant_id` (UUID, FK to tenants)

**tenants table:**
- `id` (UUID, PK)
- `name` (String)
- `slug` (String, unique, indexed)
- `status` (String: active/suspended/cancelled)
- `subscription_plan` (String: free/starter/pro/enterprise)
- `credit_balance` (Integer)

**roles table:**
- `id` (UUID, PK)
- `name` (String, unique: admin/member/viewer)
- `display_name` (String)
- `is_system` (Boolean)

**permissions table:**
- `id` (UUID, PK)
- `name` (String, unique: "documents:create")
- `resource` (String: "documents")
- `action` (String: "create")

## Debugging Tips

### Issue: "Default role 'member' not found"

**Solution:** Seed roles in database:
```sql
INSERT INTO roles (id, name, display_name, is_system) VALUES
  (gen_random_uuid(), 'admin', 'Administrator', true),
  (gen_random_uuid(), 'member', 'Member', true),
  (gen_random_uuid(), 'viewer', 'Viewer', true);
```

Or use test fixtures:
```python
def test_something(client, seed_roles):  # Add seed_roles fixture
    pass
```

### Issue: JWT token invalid

**Symptom:** 401 Unauthorized with "Invalid authentication token"

**Causes:**
1. Wrong secret key (JWT_SECRET_KEY mismatch)
2. Expired token
3. Token type mismatch (refresh vs access)

**Solution:**
```python
# Verify token manually
from app.services.auth_service import auth_service

try:
    payload = auth_service.verify_token(token, token_type="access")
    print(f"Token valid: {payload}")
except Exception as e:
    print(f"Token error: {e}")
```

### Issue: Email already exists in tests

**Symptom:** 409 Conflict when creating test users

**Solution:** Use unique emails or function-scoped fixtures:
```python
@pytest.fixture(scope="function")  # Fresh DB each test
def db_session(db_engine):
    # ...
```

### Issue: Tests pass individually but fail together

**Symptom:** `pytest tests/integration/api/test_auth_api.py::TestClass::test1` passes, but `pytest tests/integration/api/test_auth_api.py` fails

**Cause:** Shared database state between tests

**Solution:** Ensure fixtures have correct scope:
```python
@pytest.fixture(scope="function")  # NOT "module" or "session"
```

## Security Checklist

### Development
- ✅ Use placeholder JWT_SECRET_KEY
- ✅ Use HTTP (localhost only)
- ✅ Test with fake emails
- ✅ Use in-memory database for tests

### Staging
- ✅ Use strong JWT_SECRET_KEY (32+ bytes)
- ✅ Use HTTPS
- ✅ Configure SMTP for real emails
- ✅ Use PostgreSQL database
- ✅ Test rate limiting
- ✅ Test with real email providers

### Production
- ✅ Rotate JWT_SECRET_KEY regularly
- ✅ Enforce HTTPS only
- ✅ Enable rate limiting (5 req/15min per IP)
- ✅ Monitor failed login attempts
- ✅ Set up audit logging
- ✅ Configure backup SMTP provider
- ✅ Enable database connection pooling
- ✅ Set up error monitoring (Sentry)

## Environment Variables

Required for production:

```bash
# JWT Configuration
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email Configuration
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=<sendgrid-api-key>
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=Your App Name
SMTP_USE_TLS=true

# Frontend URL (for email links)
FRONTEND_URL=https://app.yourdomain.com

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
```

## Next Steps

1. **Implement Email Service**
   - Choose provider (SendGrid, AWS SES, Mailgun)
   - Create email templates
   - Implement send functions in `app/services/email_service.py`
   - Update TODO comments in `app/api/auth.py`

2. **Add Rate Limiting**
   - Install slowapi: `uv add slowapi`
   - Add rate limiter to endpoints
   - Configure limits: 5 failed logins per 15 min

3. **Set Up Monitoring**
   - Install Sentry: `uv add sentry-sdk`
   - Configure error tracking
   - Add performance monitoring

4. **Deploy to Staging**
   - Configure environment variables
   - Run database migrations
   - Test all endpoints
   - Verify email delivery

## Resources

- **Architecture Doc:** `docs/architecture/2025-11-03-authentication-api-design.md`
- **Implementation Summary:** `AUTHENTICATION_IMPLEMENTATION_SUMMARY.md`
- **API Documentation:** http://localhost:8000/docs (when running)
- **Test Coverage:** Run `pytest --cov` and open `htmlcov/index.html`

---

**Quick Reference Version:** 1.0
**Last Updated:** 2025-11-03
