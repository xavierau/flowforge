# JWT Origin Restrictions vs API Token Usage

**Date:** 2025-11-04
**Status:** Implemented
**Related:** Authentication, Security

## Overview

JWT tokens and API tokens now have different origin restrictions for enhanced security:

- **JWT tokens**: Only work from allowed domains (frontend applications)
- **API tokens (`sk_*`)**: Work from any domain (for server-to-server integrations)

## Configuration

### Environment Variable

Add to your `.env` file:

```bash
# JWT Domain Restrictions (comma-separated list)
JWT_ALLOWED_ORIGINS="http://localhost:3002,http://localhost:3000,https://yourdomain.com,https://app.yourdomain.com"
```

### Default Configuration

The default allowed origins are:
- `http://localhost:3002` (primary frontend)
- `http://localhost:3000` (alternate frontend port)

## How It Works

### JWT Token Authentication

**Allowed:**
```bash
# Request from allowed origin (http://localhost:3002)
curl -X POST http://localhost:8000/api/v1/jobs/extract \
  -H "Origin: http://localhost:3002" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -F "file=@document.pdf" \
  -F "model_provider=google" \
  -F "model_name=gemini-2.5-flash"
```

**Blocked:**
```bash
# Request from unauthorized origin (e.g., Postman without allowed origin)
curl -X POST http://localhost:8000/api/v1/jobs/extract \
  -H "Origin: http://unauthorized-domain.com" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -F "file=@document.pdf"

# Response:
# {
#   "detail": "JWT authentication not allowed from this origin. Please use an API token for server-to-server requests."
# }
```

### API Token Authentication

**Always Allowed (from any origin):**
```bash
# Works from Postman, curl, or any server
curl -X POST http://localhost:8000/api/v1/jobs/extract \
  -H "Authorization: Bearer sk_live_fkmxlgo0rcc5zufz5imkhas84uqq0mdt_55gbri9po3lq" \
  -F "file=@document.pdf" \
  -F "model_provider=google" \
  -F "model_name=gemini-2.5-flash"
```

## Use Cases

### JWT Tokens - Frontend Applications

Use JWT tokens for:
- Browser-based applications (React, Vue, Angular, etc.)
- Single-page applications (SPAs)
- Mobile apps with WebViews

**Example (React):**
```typescript
const response = await fetch('http://localhost:8000/api/v1/jobs/extract', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${jwtToken}`,
  },
  body: formData
});
```

### API Tokens - Server-to-Server

Use API tokens for:
- Server-to-server integrations
- CLI tools
- Batch processing scripts
- Third-party integrations
- Postman/testing tools

**Example (Python):**
```python
import requests

headers = {
    'Authorization': 'Bearer sk_live_fkmxlgo0rcc5zufz5imkhas84uqq0mdt_55gbri9po3lq'
}

files = {'file': open('document.pdf', 'rb')}
data = {
    'model_provider': 'google',
    'model_name': 'gemini-2.5-flash'
}

response = requests.post(
    'http://localhost:8000/api/v1/jobs/extract',
    headers=headers,
    files=files,
    data=data
)
```

## Security Benefits

1. **CSRF Protection**: JWT tokens are restricted to trusted origins, preventing cross-site request forgery attacks
2. **Separation of Concerns**: Frontend tokens and API tokens have different security profiles
3. **Audit Trail**: Different token types make it easier to trace the source of requests
4. **Granular Control**: You can revoke API tokens without affecting frontend users

## Implementation Details

### Code Location

- Configuration: `app/config.py:56`
- Origin validation: `app/dependencies/auth.py:68-88`
- Flexible auth: `app/dependencies/auth.py:424-478`

### How Origin is Validated

The system checks the `Origin` or `Referer` header against the configured allowed origins:

1. Extract origin from request headers
2. Compare against `JWT_ALLOWED_ORIGINS` list
3. If not matched, reject JWT authentication
4. API tokens bypass this check entirely

### Endpoint Behavior

Endpoints using `require_permission_flexible()` will:
1. Try JWT authentication first (with origin check)
2. Fall back to API token authentication (no origin check)
3. Return 401 if both fail

## Adding New Allowed Origins

### Development
Add to `.env`:
```bash
JWT_ALLOWED_ORIGINS="http://localhost:3002,http://localhost:3000,http://localhost:5173"
```

### Production
Add your production domains:
```bash
JWT_ALLOWED_ORIGINS="https://app.yourdomain.com,https://yourdomain.com"
```

**Note:** Always use the full URL including protocol (http/https)

## Troubleshooting

### JWT Token Rejected from Postman

**Symptom:**
```json
{
  "detail": "JWT authentication not allowed from this origin. Please use an API token for server-to-server requests."
}
```

**Solution:** Use an API token instead of JWT for Postman testing:
```bash
Authorization: Bearer sk_live_...
```

### Frontend CORS Errors

**Symptom:** CORS error in browser console

**Solution:** Ensure your frontend origin is in `JWT_ALLOWED_ORIGINS`:
```bash
JWT_ALLOWED_ORIGINS="http://localhost:3002,http://localhost:3000"
```

### Missing Origin Header

Some tools (like curl without `-H "Origin: ..."`) don't send origin headers. The system will reject JWT tokens without a valid origin header.

**Solution:** Use API tokens for CLI tools and curl.

## Best Practices

1. **Use JWT for browsers**: Keep JWT tokens for frontend applications
2. **Use API tokens for servers**: Use API tokens for all server-to-server communication
3. **Restrict origins tightly**: Only add trusted domains to `JWT_ALLOWED_ORIGINS`
4. **Separate production origins**: Use different allowed origins for dev/staging/production
5. **Rotate API tokens regularly**: Implement token rotation for long-lived API tokens

## Related Documentation

- [Auth Implementation Guide](2025-11-03-auth-implementation-guide.md)
- [API Token Management](2025-11-04-api-token-management.md) (if exists)
- [Security Quick Reference](SECURITY_QUICK_REFERENCE.md)
