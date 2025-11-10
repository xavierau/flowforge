# Layout Components

Professional SaaS application layout components following React best practices and SOLID principles.

## Components

### AuthenticatedLayout

Main layout wrapper for authenticated pages. Composes `Navbar` and `Sidebar` components with proper state management.

**Features:**
- Collapseable sidebar with localStorage persistence
- Mobile-responsive with overlay menu
- User menu with logout functionality
- Proper TypeScript types throughout

**Usage:**

```tsx
import { AuthenticatedLayout } from '@/components/layout';

export function MyPage() {
  return (
    <AuthenticatedLayout>
      <h1>My Page Content</h1>
      {/* Your page content */}
    </AuthenticatedLayout>
  );
}
```

**State Management:**
- Sidebar collapse state: Persisted to `localStorage` as `sidebar-collapsed`
- Mobile menu state: Ephemeral (not persisted)
- User data: Currently mocked via `getMockUser()` (TODO: Replace with API call)

### Navbar

Top navigation bar component.

**Features:**
- App branding/logo
- User avatar with dropdown menu
- Profile and logout actions
- Mobile menu toggle button

**Props:**
```tsx
interface NavbarProps {
  user: User;                    // Current user data
  onMobileMenuToggle: () => void; // Mobile menu toggle handler
}
```

### Sidebar

Collapseable navigation sidebar.

**Features:**
- Collapseable: 280px expanded, 80px collapsed
- Smooth transitions (300ms)
- Active route highlighting
- Mobile overlay on small screens
- Responsive: Hidden on mobile by default

**Navigation Items:**
- Dashboard (`/`) - LayoutDashboard icon
- Schema Builder (`/schema-builder`) - FileJson icon
- Documents (`/documents`) - FileText icon
- Settings (`/settings`) - Settings icon

**Props:**
```tsx
interface SidebarProps {
  isCollapsed: boolean;         // Collapsed state
  onToggleCollapse: () => void; // Collapse toggle handler
  isMobileOpen: boolean;        // Mobile menu open state
  onMobileClose: () => void;    // Mobile menu close handler
}
```

## Design Principles

### Single Responsibility
Each component has a clear, focused purpose:
- `AuthenticatedLayout`: Layout structure and state orchestration
- `Navbar`: Top navigation concerns only
- `Sidebar`: Left navigation concerns only

### Composability
Components are designed to compose together naturally:
```tsx
<AuthenticatedLayout>
  ↳ <Sidebar />
  ↳ <div>
      ↳ <Navbar />
      ↳ <main>{children}</main>
    </div>
</AuthenticatedLayout>
```

### No useEffect Anti-patterns
- ✅ State updates handled through callbacks
- ✅ localStorage read once during initial state
- ✅ localStorage write happens synchronously in handlers
- ❌ No unnecessary effects for derived state
- ❌ No effect dependency issues

### Proper TypeScript Types
All components are fully typed:
- Props interfaces exported for reusability
- User type defined in `@/types/user.ts`
- No `any` types used

## Styling

Uses Tailwind CSS 4 with proper syntax:
- Responsive breakpoints: `md:` prefix for 768px+
- Smooth transitions: `transition-all duration-300`
- Theme colors via CSS variables: `hsl(var(--primary))`
- Mobile-first approach

## State Flow

```
AuthenticatedLayout (state owner)
  │
  ├─ isCollapsed (useState)
  │  ├─ Initial: getInitialCollapseState() from localStorage
  │  └─ Updates: handleToggleCollapse() → saveCollapseState()
  │
  ├─ isMobileOpen (useState)
  │  ├─ Initial: false (not persisted)
  │  └─ Updates: handleMobileMenuToggle() / handleMobileClose()
  │
  ├─ user (getMockUser)
  │  └─ TODO: Replace with API call
  │
  ├→ Sidebar
  │   ├─ isCollapsed (prop)
  │   ├─ onToggleCollapse (callback)
  │   ├─ isMobileOpen (prop)
  │   └─ onMobileClose (callback)
  │
  └→ Navbar
      ├─ user (prop)
      └─ onMobileMenuToggle (callback)
```

## File Structure

```
src/
├── components/
│   └── layout/
│       ├── AuthenticatedLayout.tsx  # Main layout component
│       ├── Navbar.tsx               # Top navigation
│       ├── Sidebar.tsx              # Left navigation
│       ├── index.ts                 # Exports
│       └── README.md                # This file
├── types/
│   └── user.ts                      # User type definitions
└── pages/
    └── Dashboard.tsx                # Example usage
```

## TODO Items

1. **User API Integration**
   - Replace `getMockUser()` with actual API call
   - Add user profile page route
   - Implement user data refresh mechanism

2. **Additional Pages**
   - Documents page (`/documents`)
   - Settings page (`/settings`)
   - User profile page

3. **Enhancements**
   - Add notifications dropdown to Navbar
   - Add search functionality
   - Add breadcrumbs to main content area
   - Add loading states for user data

## Testing

To test the layout components:

1. **Visual Testing:**
   ```bash
   npm run dev
   # Navigate to any protected route
   ```

2. **Responsive Testing:**
   - Desktop: Verify sidebar collapse/expand
   - Mobile: Verify mobile menu overlay
   - Tablet: Verify breakpoint transitions

3. **State Persistence:**
   - Toggle sidebar collapse
   - Refresh page
   - Verify state persisted

4. **Navigation:**
   - Click nav items
   - Verify active state highlighting
   - Verify mobile menu closes on navigation

## Dependencies

- `react-router-dom`: Navigation and routing
- `lucide-react`: Icons
- `@/components/ui`: shadcn/ui components
  - `Button`
  - `DropdownMenu`
  - `Avatar`
- `@/lib/utils`: `cn()` utility for class merging
- `@/services/auth.service`: `clearTokens()` for logout

## Browser Support

Targets modern browsers with:
- CSS Grid and Flexbox
- CSS Custom Properties (variables)
- localStorage API
- ES6+ JavaScript features
