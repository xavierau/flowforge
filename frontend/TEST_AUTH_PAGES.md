# Testing Authentication Pages

## Manual Testing Guide

### 1. Start the Development Server
```bash
cd frontend
npm run dev
```

### 2. Test Login Page

**URL:** http://localhost:3002/login

**Visual Checks:**
- [ ] Card is centered on gradient background
- [ ] LogIn icon is displayed in a colored circle
- [ ] "Welcome back" title is visible
- [ ] Email field has mail icon on left
- [ ] Password field has lock icon on left
- [ ] "Remember me" checkbox is functional
- [ ] "Forgot password?" link is present
- [ ] "Sign in" button is styled correctly
- [ ] "Sign up" link at bottom works

**Functionality Tests:**
1. **Valid Login:**
   - Enter: test@example.com / password123
   - Click "Sign in"
   - Should show loading spinner
   - Should redirect to /schema-builder on success
   - Should show success toast

2. **Invalid Email:**
   - Enter: invalid-email
   - Tab to next field
   - Should show "Invalid email address" error

3. **Empty Fields:**
   - Click "Sign in" without filling fields
   - Should show "Email is required" and "Password is required"

4. **Wrong Credentials (if API is running):**
   - Enter: wrong@email.com / wrongpass
   - Click "Sign in"
   - Should show "Invalid credentials" toast

### 3. Test Signup Page

**URL:** http://localhost:3002/signup

**Visual Checks:**
- [ ] Card is centered on gradient background
- [ ] UserPlus icon is displayed
- [ ] "Create an account" title is visible
- [ ] All 5 input fields are present with icons
- [ ] Password strength indicator appears when typing password
- [ ] Terms acceptance checkbox with links
- [ ] "Create account" button is disabled until terms accepted
- [ ] "Sign in" link at bottom works

**Functionality Tests:**
1. **Password Strength Indicator:**
   - Type: "pass" → Should show "Weak" (red)
   - Type: "password1" → Should show "Fair" (orange)
   - Type: "Password1" → Should show "Good" (yellow)
   - Type: "P@ssw0rd!" → Should show "Strong" (green)

2. **Password Matching:**
   - Password: "Test1234"
   - Confirm: "Test5678"
   - Should show "Passwords do not match"

3. **Terms Acceptance:**
   - Leave checkbox unchecked
   - Button should be disabled
   - Check checkbox
   - Button should be enabled

4. **Valid Signup (if API is running):**
   - Full Name: "John Doe"
   - Email: "john@example.com"
   - Company: "Acme Inc"
   - Password: "Test1234!"
   - Confirm Password: "Test1234!"
   - Check terms
   - Click "Create account"
   - Should auto-login and redirect to /schema-builder

5. **Existing Email (if API is running):**
   - Use email that already exists
   - Should show "Email already registered" toast

### 4. Navigation Tests

1. **Login → Signup:**
   - On /login page
   - Click "Sign up" link
   - Should navigate to /signup

2. **Signup → Login:**
   - On /signup page
   - Click "Sign in" link
   - Should navigate to /login

### 5. Loading States

1. **Login Loading:**
   - Fill valid credentials
   - Click "Sign in"
   - Button should show "Signing in..." with spinner
   - All fields should be disabled during loading

2. **Signup Loading:**
   - Fill all fields
   - Click "Create account"
   - Button should show "Creating account..." with spinner
   - All fields should be disabled during loading

### 6. Accessibility Tests

1. **Keyboard Navigation:**
   - Press Tab to move between fields
   - All fields should be reachable
   - Focus indicators should be visible

2. **Screen Reader:**
   - Use screen reader to verify:
     - Labels are announced
     - Error messages are linked to inputs
     - Loading states are announced

## Browser Console Checks

Open DevTools (F12) and check:

1. **No Console Errors:**
   ```
   Should have no red error messages
   ```

2. **Network Tab (when submitting):**
   ```
   POST http://localhost:8000/api/v1/auth/login
   POST http://localhost:8000/api/v1/auth/register
   ```

3. **LocalStorage (after successful login):**
   ```
   access_token: "eyJ..."
   refresh_token: "eyJ..."
   ```

## Expected API Responses

### Login Success (200):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "123",
    "email": "test@example.com",
    "full_name": "Test User",
    "tenant_id": "456",
    "is_active": true,
    "created_at": "2025-11-03T...",
    "updated_at": "2025-11-03T..."
  }
}
```

### Login Error (401):
```json
{
  "detail": "Invalid credentials"
}
```

### Signup Error (409):
```json
{
  "detail": "Email already registered"
}
```

## Notes

- If backend API is not running, network errors will be caught and shown
- All form validations work client-side without API
- Toast notifications use Sonner library (should appear top-right)
- Background is gradient from slate-50 to slate-100
