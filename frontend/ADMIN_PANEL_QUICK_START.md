# Admin Panel - Quick Start Guide

## Accessing the Admin Panel

### Prerequisites
- User account with `platform_admin` role
- Valid JWT access token

### Test Credentials
```
Email: admin@platform.local
Password: AdminPass123!
```

### Navigation
After logging in as a platform admin, you'll see an "Administration" section in the sidebar with:
- **Admin Dashboard** - Platform statistics overview
- **Tenants** - Tenant management
- **Users** - Cross-tenant user management

## Feature Guide

### 1. Platform Dashboard (`/admin`)

**What you see:**
- Tenant metrics (total, active, suspended, new)
- User activity (total users, active users, jobs, API tokens)
- Job performance (total, completed, failed, success rate)
- Resource usage (documents, tokens, cost, credits)

**Actions:**
- Click "Refresh" to update statistics

### 2. Tenant Management (`/admin/tenants`)

**What you see:**
- Paginated list of all tenants (50 per page)
- For each tenant: name, status, plan, users, jobs, credits

**Filters:**
- **Search** - Filter by tenant name or slug
- **Status** - All/Active/Suspended/Cancelled
- **Plan** - All/Free/Starter/Professional/Enterprise

**Actions:**
- **View Details** (eye icon) - Navigate to tenant detail page
- **Suspend** (red button) - Suspend an active tenant
- **Activate** (green button) - Activate a suspended tenant

**Workflow for suspending a tenant:**
1. Click "Suspend" button
2. Review confirmation dialog
3. Optionally enter a reason (logged to audit trail)
4. Click "Confirm"
5. Tenant status updated immediately

### 3. Tenant Detail (`/admin/tenants/:tenantId`)

**What you see:**
- Tenant information (name, slug, plan, created date, last activity)
- Metrics cards (jobs, tokens, cost)
- Tabs:
  - **Users** - List of users in this tenant
  - **API Tokens** - List of API tokens in this tenant

**Actions:**
- **Suspend/Activate** - Change tenant status (same as tenant list)

**Navigation:**
- Breadcrumbs: Admin → Tenants → [Tenant Name]

### 4. User Management (`/admin/users`)

**What you see:**
- Paginated list of all users across all tenants (50 per page)
- For each user: email, name, tenant, role, status, last login

**Filters:**
- **Search** - Filter by email or name
- **Status** - All Users/Active/Inactive

**Actions:**
- **View Details** (eye icon) - View user details (placeholder)
- **Deactivate** (red button) - Deactivate an active user
- **Activate** (green button) - Activate an inactive user

**Workflow for deactivating a user:**
1. Click "Deactivate" button
2. Review confirmation dialog
3. Optionally enter a reason (logged to audit trail)
4. Click "Confirm"
5. User status updated immediately (user will be logged out)

## Status Badges

### Tenant Status
- **Active** (blue) - Tenant is active and accessible
- **Suspended** (red) - Tenant is suspended (users can't access)
- **Cancelled** (gray) - Tenant subscription cancelled

### User Status
- **Active** (blue) - User can log in and access system
- **Inactive** (red) - User account deactivated
- **Unverified** (gray) - User hasn't verified email

## Best Practices

### 1. Always Provide Reasons
When suspending tenants or deactivating users, provide clear reasons:
- "Payment overdue - 30 days past due"
- "Terms of service violation - spam detected"
- "User request - account closure"

Reasons are logged in the audit trail for compliance.

### 2. Check Before Acting
Before suspending a tenant:
1. Review tenant details (users, jobs, activity)
2. Check last activity date
3. Verify the reason for suspension

### 3. Monitor Impact
After suspending a tenant:
- All users in that tenant lose access immediately
- Running jobs may fail
- API tokens are still active but will fail auth

### 4. Use Search Effectively
- Search by **email** for specific users
- Search by **tenant name** for specific organizations
- Combine search with filters for best results

## Keyboard Shortcuts

None currently implemented. All interactions require mouse/touch.

## Pagination

- Default: 50 items per page
- Use "Previous"/"Next" buttons to navigate
- Page count shown at bottom

## Error Handling

### Common Errors

**"Unauthorized - Please log in again"**
- JWT token expired or invalid
- **Solution:** Log out and log back in

**"Network error. Please check your connection."**
- Backend API not responding
- **Solution:** Check if backend is running (`docker-compose up -d`)

**"Failed to load [resource]"**
- Backend error or permission issue
- **Solution:** Check browser console for details

### What to Do When Errors Occur

1. **Check console** - Open browser DevTools (F12) and check console
2. **Check network** - Check Network tab for failed requests
3. **Verify token** - Check if JWT token is valid (localStorage)
4. **Refresh page** - Sometimes fixes transient issues

## API Endpoints Reference

All admin endpoints require JWT with `platform_admin` role:

```
GET    /api/v1/admin/dashboard
GET    /api/v1/admin/tenants
GET    /api/v1/admin/tenants/{id}
GET    /api/v1/admin/tenants/{id}/users
GET    /api/v1/admin/tenants/{id}/tokens
PATCH  /api/v1/admin/tenants/{id}/status
GET    /api/v1/admin/users
GET    /api/v1/admin/users/{id}
PATCH  /api/v1/admin/users/{id}/status
DELETE /api/v1/admin/tokens/{id}
GET    /api/v1/admin/analytics/top-tenants
```

## Role Requirements

### Who Can Access?
- **Only** users with `role_name = "platform_admin"`
- Regular tenant admins **cannot** access admin panel
- Role checked on:
  - Frontend (route protection, sidebar visibility)
  - Backend (API middleware)

### What if I Don't Have Access?
If you try to access admin routes without proper role:
1. You'll be redirected to `/dashboard`
2. Admin section won't appear in sidebar
3. Backend will return 403 Forbidden

**Solution:** Contact existing platform admin to grant role.

## Troubleshooting

### Admin Section Not Showing in Sidebar

**Possible causes:**
1. Not logged in as platform_admin
2. JWT token doesn't contain `role_name: "platform_admin"`
3. Token expired or invalid

**Solution:**
1. Log out and log back in with admin credentials
2. Check localStorage for `access_token`
3. Decode JWT token to verify role (use jwt.io)

### Can't Suspend Tenant

**Possible causes:**
1. Tenant already suspended
2. Network error
3. Backend validation error

**Solution:**
1. Refresh page and check current status
2. Check browser console for errors
3. Check backend logs

### Users Still Accessing After Suspension

**Possible causes:**
1. Caching on frontend
2. Existing JWT tokens still valid
3. Suspension didn't complete

**Solution:**
1. Users need to refresh or re-login
2. Check tenant status in database
3. Suspended tenants fail middleware check

## Security Notes

### Client-Side vs Server-Side

**Client-side protection:**
- Hides admin UI from non-admins
- Prevents navigation to admin routes
- **NOT** a security boundary

**Server-side protection (ACTUAL security):**
- All admin endpoints check `platform_admin` role
- Middleware enforces permissions
- Audit logging on all actions

**Important:** Never rely on client-side checks for security!

### Audit Trail

All admin actions are logged with:
- User ID and email
- Action performed
- Resource affected
- Timestamp
- IP address
- User-provided reason

**Location:** Backend database (audit_logs table)

## Support

For issues or questions:
1. Check backend logs: `docker-compose logs -f api`
2. Check browser console: F12 → Console tab
3. Review implementation docs: `frontend/ADMIN_PANEL_IMPLEMENTATION.md`
4. Check API security guide: `docs/guides/2025-11-04-api-endpoint-security.md`

---

**Last Updated:** 2025-11-05
