# API Token Management - Frontend Implementation

**Implementation Date:** 2025-11-04

## Overview

Complete frontend implementation for API token management following React best practices, including proper component composition, effect management, and state handling.

## Architecture

### Component Structure

```
frontend/src/
├── types/
│   └── api-token.ts                    # Type definitions and constants
├── services/
│   └── api-token.service.ts            # API service layer
├── components/
│   └── api-tokens/
│       ├── ApiTokenList.tsx            # Token list table
│       ├── CreateTokenDialog.tsx       # Create token form
│       ├── TokenCreatedDialog.tsx      # Display new token (once)
│       └── index.ts                    # Exports
├── pages/
│   └── ApiTokens.tsx                   # Main page component
└── App.tsx                             # Routes (updated)
```

### Design Principles Applied

#### 1. **Component Composition**
- Small, focused components with single responsibilities
- ApiTokenList only displays tokens
- CreateTokenDialog only handles form
- TokenCreatedDialog only shows created token
- ApiTokens page orchestrates all components

#### 2. **State Management**
- Local state with useState for component-specific data
- No prop drilling - callbacks passed down appropriately
- State colocation - keep state close to where it's used

#### 3. **Effect Management**
- Proper useEffect cleanup in ApiTokens page
- Dependencies array correctly specified
- Form reset on dialog close using useEffect
- No infinite loops or missing dependencies

#### 4. **Error Handling**
- Try/catch blocks in all async operations
- User-friendly error messages with toast notifications
- Error propagation to parent components when needed

## Files Created

### 1. Types (`types/api-token.ts`)

**Purpose:** Type definitions and constants for API tokens

**Key Exports:**
- `ApiToken` - Token data structure
- `ApiTokenCreateRequest` - Create request payload
- `ApiTokenCreateResponse` - Create response (includes full token)
- `AVAILABLE_SCOPES` - All available permission scopes
- `EXPIRATION_OPTIONS` - Token expiration options

**Scopes Defined:**
```typescript
Documents: read, create, update, delete
Schemas:   read, create, update, delete
Jobs:      read
```

**Expiration Options:**
- 30 days
- 60 days
- 90 days
- 1 year
- Never

### 2. Service Layer (`services/api-token.service.ts`)

**Purpose:** API communication for token operations

**Methods:**
- `createToken(data)` - Create new token
- `listTokens()` - Get all tokens
- `getToken(id)` - Get specific token
- `updateToken(id, data)` - Update token name/scopes
- `revokeToken(id)` - Delete token

**Features:**
- Centralized auth header injection
- 401 handling with redirect to login
- Consistent error handling
- Uses existing apiFetch pattern

### 3. ApiTokenList Component

**Purpose:** Display tokens in a table with revoke functionality

**Props:**
```typescript
{
  tokens: ApiToken[];
  onRevoke: (tokenId: string) => Promise<void>;
}
```

**Features:**
- shadcn/ui Table component
- Displays: name, prefix, scopes (badges), expiration, last used
- Revoke button with confirmation dialog
- Empty state when no tokens
- Expired token highlighting
- Scope badges (shows first 3 + count)

**React Best Practices:**
- Single responsibility (only displays)
- No side effects (parent fetches data)
- Controlled confirmation dialog state
- Proper button disabled states

### 4. CreateTokenDialog Component

**Purpose:** Form dialog for creating new tokens

**Props:**
```typescript
{
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: ApiTokenCreateRequest) => Promise<void>;
}
```

**Features:**
- Form fields: name, scopes (checkboxes), expiration (select)
- Grouped scopes by resource type
- Validation: name required, at least one scope
- Auto-reset form on dialog close
- Loading states during submission

**React Best Practices:**
- Controlled component (open state from parent)
- useEffect for form cleanup (no memory leaks)
- Proper dependency array [open]
- Form validation before submit
- Error handling with visual feedback

### 5. TokenCreatedDialog Component

**Purpose:** Display newly created token exactly once

**Props:**
```typescript
{
  token: string;
  tokenName: string;
  open: boolean;
  onClose: () => void;
}
```

**Features:**
- Full token display (ONLY TIME SHOWN)
- Copy to clipboard with visual feedback
- Security warning alert
- Usage example code snippet
- Best practices guide
- "I've saved my token" confirmation button

**Security UX:**
- Prominent warning that token won't be shown again
- Copy button for easy saving
- Clear usage instructions
- No persistence of token value

### 6. ApiTokens Page

**Purpose:** Main page orchestrating token management

**Features:**
- Page/PageHeader/PageContent layout
- "Create Token" button in header
- Token list with loading state
- Dialog state management
- Data fetching with proper cleanup

**State:**
```typescript
const [tokens, setTokens] = useState<ApiToken[]>([]);
const [isLoading, setIsLoading] = useState(true);
const [createDialogOpen, setCreateDialogOpen] = useState(false);
const [createdToken, setCreatedToken] = useState<ApiTokenCreateResponse | null>(null);
```

**React Best Practices:**
- useEffect with cleanup function
- isMounted flag to prevent state updates after unmount
- Proper dependency arrays
- Error handling with toast
- State updates after successful operations

**useEffect Pattern:**
```typescript
useEffect(() => {
  let isMounted = true;

  const fetchTokens = async () => {
    try {
      const data = await apiTokenService.listTokens();
      if (isMounted) {
        setTokens(data);
      }
    } catch (error) {
      if (isMounted) {
        toast.error('Failed to load API tokens');
      }
    } finally {
      if (isMounted) {
        setIsLoading(false);
      }
    }
  };

  fetchTokens();

  return () => {
    isMounted = false; // Cleanup
  };
}, []); // Empty deps - run once on mount
```

## User Flow

### Create Token Flow

1. User clicks "Create Token" button
2. CreateTokenDialog opens with form
3. User fills:
   - Name (e.g., "Production API Key")
   - Scopes (checkboxes grouped by resource)
   - Expiration (select dropdown)
4. User submits form
5. CreateTokenDialog closes on success
6. TokenCreatedDialog opens with full token
7. User copies token to clipboard
8. User clicks "I've saved my token"
9. TokenCreatedDialog closes
10. Token appears in list (prefix only)

### Revoke Token Flow

1. User clicks trash icon on token row
2. Confirmation dialog appears
3. User confirms revocation
4. Token is deleted from backend
5. Token is removed from list
6. Success toast appears

## Security Considerations

### Token Display
- **Full token shown ONLY ONCE** in TokenCreatedDialog
- List shows prefix only (e.g., "sk_live_abc12345...")
- No way to retrieve full token after creation

### Warnings
- Prominent alert in TokenCreatedDialog
- Clear messaging about one-time display
- Best practices guide included

### Storage
- Tokens NOT stored in frontend state/localStorage
- Only stored temporarily during creation flow
- Cleared when TokenCreatedDialog closes

## Integration Points

### Routes (App.tsx)
```typescript
<Route
  path="/tokens"
  element={
    <ProtectedRoute>
      <AuthenticatedLayout>
        <ApiTokens />
      </AuthenticatedLayout>
    </ProtectedRoute>
  }
/>
```

### Navigation (Sidebar.tsx)
```typescript
{
  name: 'API Tokens',
  path: '/tokens',
  icon: Key,
}
```

## API Endpoints Used

All endpoints are prefixed with `/api/v1/tokens`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/tokens` | Create token (returns full token) |
| GET | `/tokens` | List all tokens |
| GET | `/tokens/{id}` | Get token details |
| PATCH | `/tokens/{id}` | Update token name/scopes |
| DELETE | `/tokens/{id}` | Revoke token |

## Testing Checklist

### Component Rendering
- [ ] ApiTokenList renders empty state
- [ ] ApiTokenList renders tokens table
- [ ] CreateTokenDialog form validation
- [ ] TokenCreatedDialog displays token
- [ ] ApiTokens page loads tokens

### User Interactions
- [ ] Create token button opens dialog
- [ ] Form validation prevents empty submission
- [ ] Token creation shows success
- [ ] Copy button works in TokenCreatedDialog
- [ ] Revoke button shows confirmation
- [ ] Token removal updates list

### Error Handling
- [ ] Network errors show toast
- [ ] 401 redirects to login
- [ ] Form errors display inline
- [ ] API errors don't break UI

### State Management
- [ ] Dialog state resets on close
- [ ] Token list updates after create
- [ ] Token list updates after revoke
- [ ] No memory leaks on unmount

## Known Issues

None - all TypeScript errors are pre-existing in other files.

## Future Enhancements

1. **Token Usage Analytics**
   - Show usage count per token
   - Graph of API calls over time
   - Most used endpoints per token

2. **Token Rotation**
   - Schedule automatic rotation
   - Generate new token, revoke old
   - Grace period for transition

3. **IP Whitelisting**
   - Add allowed IP ranges per token
   - Additional security layer

4. **Rate Limiting Display**
   - Show rate limit per token
   - Current usage vs limit
   - Reset time

5. **Audit Log**
   - Track token creation/revocation
   - Show who created each token
   - Export audit logs

## References

- Backend API docs: `/docs/guides/2025-11-04-api-tokens-implementation.md` (if exists)
- React best practices: Project's CLAUDE.md
- shadcn/ui components: https://ui.shadcn.com/
- Layout system: `frontend/LAYOUT_SYSTEM.md`

---

**Implementation Status:** ✅ Complete

**Last Updated:** 2025-11-04

**Implemented By:** Claude Code (following React best practices)
