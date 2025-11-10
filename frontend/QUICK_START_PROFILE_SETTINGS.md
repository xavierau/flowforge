# Quick Start: Profile & Settings Pages

## Accessing the Pages

### Via Sidebar Navigation
- Click **"Profile"** in the sidebar → User profile page
- Click **"Settings"** in the sidebar → Settings page with tabs

### Direct URLs
- Profile: `http://localhost:3002/profile`
- Settings: `http://localhost:3002/settings`

---

## File Locations Reference

### Need to modify Profile page?
**`/Users/xavierau/Code/python/ai_document_processing/frontend/src/pages/Profile.tsx`**

### Need to modify Settings tabs?
**`/Users/xavierau/Code/python/ai_document_processing/frontend/src/components/settings/`**
- `UserInvitationTab.tsx` - Team invitation management
- `SubscriptionTab.tsx` - Billing and plan management
- `AccountSettingsTab.tsx` - Account settings and preferences

### Need to modify API calls?
**`/Users/xavierau/Code/python/ai_document_processing/frontend/src/services/`**
- `user.service.ts` - User profile and invitation APIs
- `subscription.service.ts` - Subscription and billing APIs

### Need to modify types?
**`/Users/xavierau/Code/python/ai_document_processing/frontend/src/types/profile.ts`**

---

## Component Usage Examples

### Using the Profile Page Component
```tsx
import { Profile } from '@/pages/Profile';

// Already integrated in App.tsx at /profile route
<Route path="/profile" element={<Profile />} />
```

### Using the Settings Page Component
```tsx
import { Settings } from '@/pages/Settings';

// Already integrated in App.tsx at /settings route
<Route path="/settings" element={<Settings />} />
```

### Using Individual Settings Tabs
```tsx
import {
  UserInvitationTab,
  SubscriptionTab,
  AccountSettingsTab
} from '@/components/settings';

// Use in custom layouts if needed
<UserInvitationTab />
```

---

## Service Function Examples

### Fetch Current User
```tsx
import { getCurrentUser } from '@/services/user.service';

const profile = await getCurrentUser();
// Returns: UserProfile object
```

### Update User Profile
```tsx
import { updateAccount } from '@/services/user.service';

const updated = await updateAccount({
  full_name: 'John Doe',
  email: 'john@example.com'
});
```

### Send User Invitation
```tsx
import { createInvitation } from '@/services/user.service';

const invitation = await createInvitation({
  email: 'newuser@example.com',
  role: 'user'
});
```

### Get Subscription Data
```tsx
import { getCurrentSubscription } from '@/services/subscription.service';

const subscription = await getCurrentSubscription();
// Returns: Subscription object with credits, plan, etc.
```

### Change Subscription Plan
```tsx
import { changePlan } from '@/services/subscription.service';

const updated = await changePlan('pro');
// Upgrades/downgrades to specified plan
```

---

## Common Tasks

### Add a New Field to Profile
1. Update type in `/types/profile.ts`:
   ```tsx
   export interface UserProfile {
     // ... existing fields
     phone_number?: string; // Add new field
   }
   ```

2. Update display in `/pages/Profile.tsx`:
   ```tsx
   <div className="flex items-center gap-3">
     <Phone className="h-4 w-4 text-muted-foreground" />
     <div className="flex-1">
       <p className="text-sm font-medium">Phone</p>
       <p className="text-sm text-muted-foreground">
         {profile.phone_number || 'Not provided'}
       </p>
     </div>
   </div>
   ```

3. Update form in `/components/settings/AccountSettingsTab.tsx`

### Add a New Notification Preference
1. Update type in `/types/profile.ts`:
   ```tsx
   export interface NotificationPreferences {
     // ... existing fields
     email_on_new_feature: boolean; // Add new preference
   }
   ```

2. Update UI in `/components/settings/AccountSettingsTab.tsx`:
   ```tsx
   // Add to preferences object in render
   {Object.entries({
     // ... existing entries
     email_on_new_feature: 'New feature announcements',
   }).map(...)}
   ```

### Add a New Subscription Plan
1. Update plan data (backend provides this via API)
2. Component automatically renders new plans in comparison grid
3. No frontend changes needed if using API data

---

## Troubleshooting

### "Failed to load profile" error
**Cause:** Backend API not responding or endpoint missing
**Solution:**
1. Check backend is running: `http://localhost:8000/health`
2. Verify API endpoint exists: `GET /api/v1/users/me`
3. Check authentication token is valid

### Forms not submitting
**Cause:** Validation errors or API errors
**Solution:**
1. Check browser console for error messages
2. Verify form fields match validation rules
3. Check network tab for failed API calls

### Tabs not switching
**Cause:** React state issue
**Solution:**
1. Clear browser cache
2. Check console for errors
3. Verify Tabs component is properly imported

### Data not updating after API call
**Cause:** State not refreshing
**Solution:**
1. Check if API call succeeded (network tab)
2. Verify state update logic in component
3. Check for race conditions (component unmounted before update)

---

## Backend Integration Checklist

Before the pages work with real data, implement these backend endpoints:

### User Endpoints
- [ ] `GET /api/v1/users/me` - Current user profile
- [ ] `PATCH /api/v1/users/me` - Update profile
- [ ] `POST /api/v1/users/me/password` - Change password
- [ ] `DELETE /api/v1/users/me` - Delete account
- [ ] `GET /api/v1/users/me/notifications/preferences`
- [ ] `PUT /api/v1/users/me/notifications/preferences`

### Invitation Endpoints
- [ ] `GET /api/v1/invitations` - List invitations
- [ ] `POST /api/v1/invitations` - Create invitation
- [ ] `POST /api/v1/invitations/:id/resend`
- [ ] `DELETE /api/v1/invitations/:id`

### Subscription Endpoints
- [ ] `GET /api/v1/subscriptions/current`
- [ ] `GET /api/v1/subscriptions/plans`
- [ ] `GET /api/v1/subscriptions/usage`
- [ ] `POST /api/v1/subscriptions/change-plan`
- [ ] `POST /api/v1/subscriptions/cancel`
- [ ] `POST /api/v1/subscriptions/credits`

---

## Development Workflow

### Making Changes
1. Edit component files in `src/pages/` or `src/components/settings/`
2. Dev server auto-reloads (`npm run dev`)
3. Check browser console for errors
4. Test functionality manually

### Adding New Features
1. Define types in `src/types/profile.ts`
2. Add service function in `src/services/`
3. Update component to use new service
4. Test with mock data if backend not ready

### Testing
1. Start dev server: `npm run dev`
2. Navigate to pages via sidebar
3. Test all forms and buttons
4. Verify loading states
5. Test error scenarios (disconnect network)

---

## Architecture Decisions

### Why Three Separate Tab Components?
- **Single Responsibility:** Each tab has one clear purpose
- **Reusability:** Tabs can be used in other contexts
- **Maintainability:** Easier to update individual features
- **Testing:** Can test each tab independently

### Why Service Layer?
- **Separation of Concerns:** API logic separate from UI
- **Reusability:** Services used across multiple components
- **Error Handling:** Centralized error management
- **Type Safety:** Typed API responses

### Why react-hook-form?
- **Performance:** Minimizes re-renders
- **Validation:** Built-in validation rules
- **Developer Experience:** Clean API
- **Accessibility:** Proper error handling

---

## Performance Notes

### Current Optimizations
✅ useEffect cleanup prevents memory leaks
✅ AbortController cancels in-flight requests
✅ Optimistic UI updates for better UX
✅ Form validation prevents unnecessary API calls

### Future Optimizations
- Consider memoizing expensive computations with `useMemo`
- Add `useCallback` for event handlers passed to children
- Implement virtual scrolling for long invitation lists
- Add React Query for caching and background refetch

---

## Support

For questions or issues:
1. Check `/frontend/PROFILE_AND_SETTINGS_IMPLEMENTATION.md` for detailed docs
2. Review component source code (well-commented)
3. Check browser console for error messages
4. Verify backend API is running and endpoints exist
