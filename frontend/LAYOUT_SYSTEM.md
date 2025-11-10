# Layout System Architecture

**Complete Guide to the Composable Page Layout System**

---

## Overview

This document describes the layout component architecture for the AI Document Processing SaaS application. The system is built on **composition principles** where small, focused components combine to create consistent, maintainable page layouts.

**Design Goals:**
- **Consistency** - All pages share the same structure and spacing
- **Composability** - Small components combine for flexibility
- **Maintainability** - Change layout in one place, affects all pages
- **Accessibility** - Built-in ARIA patterns and semantic HTML
- **Developer Experience** - Simple, intuitive API

---

## Component Hierarchy

```
AuthenticatedLayout (App shell with sidebar + navbar)
└── Page (Top-level page container)
    ├── PageHeader (Breadcrumb, title, subtitle)
    │   └── Breadcrumb (Navigation trail)
    └── PageContent (Main content wrapper)
        └── {children} (Your page-specific content)
```

**Visual Layout:**
```
┌─────────────────────────────────────────────────────┐
│  Navbar                                       [JD]  │
├────────┬────────────────────────────────────────────┤
│        │  Breadcrumb: Home > Schema Builder        │
│ Side-  │  ──────────────────────────────────────── │
│ bar    │  Page Title                               │
│        │  Optional subtitle/description            │
│        │  ──────────────────────────────────────── │
│        │                                            │
│        │  Page Content                             │
│        │  (Your components here)                   │
│        │                                            │
│        │                                            │
└────────┴────────────────────────────────────────────┘
```

---

## Core Components

### 1. AuthenticatedLayout

**Purpose:** Main application shell for all authenticated pages. Manages sidebar and navbar state.

**Location:** `src/components/layout/AuthenticatedLayout.tsx`

**Features:**
- Collapseable sidebar (280px → 80px)
- Mobile-responsive overlay menu
- Sidebar state persisted to localStorage
- User menu in navbar
- Logout functionality

**Props:** None (wraps entire authenticated app)

**Example:**
```tsx
import { AuthenticatedLayout } from '@/components/layout';

function App() {
  return (
    <AuthenticatedLayout>
      {/* Your page components */}
    </AuthenticatedLayout>
  );
}
```

---

### 2. Page

**Purpose:** Top-level container for page content. Provides consistent spacing and structure.

**Location:** `src/components/layout/Page.tsx`

**Props:**
```tsx
interface PageProps {
  children: React.ReactNode;
  className?: string;  // Optional: override default styling
}
```

**Default Styling:**
- Padding: `p-6` (24px)
- Spacing: `space-y-6` (24px vertical gap between children)
- Full width container

**Example:**
```tsx
import { Page } from '@/components/layout';

export function MyPage() {
  return (
    <Page>
      <PageHeader ... />
      <PageContent>...</PageContent>
    </Page>
  );
}
```

**When to Use:**
- Use for EVERY authenticated page
- Wraps PageHeader + PageContent
- Provides consistent spacing

**When NOT to Use:**
- Public pages (login, signup, landing)
- Pages with custom full-screen layouts

---

### 3. PageHeader

**Purpose:** Standardized page header with breadcrumb navigation, title, and optional subtitle.

**Location:** `src/components/layout/PageHeader.tsx`

**Props:**
```tsx
interface PageHeaderProps {
  breadcrumbs?: BreadcrumbItem[];  // Optional navigation trail
  title: string;                   // Page title (required)
  subtitle?: string;               // Optional description
  className?: string;              // Optional: override styling
}

interface BreadcrumbItem {
  label: string;      // Display text
  href?: string;      // Optional link (last item typically has no href)
}
```

**Default Styling:**
- Spacing: `space-y-4` (16px vertical gap)
- Title: `text-3xl font-bold` (30px, bold)
- Subtitle: `mt-2 text-muted-foreground` (gray text)

**Example:**
```tsx
<PageHeader
  breadcrumbs={[
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Schema Builder' }  // Current page - no href
  ]}
  title="Schema Builder"
  subtitle="Create and manage your JSON schemas"
/>
```

**Output:**
```
Dashboard > Schema Builder

Schema Builder
Create and manage your JSON schemas
```

**Accessibility:**
- Title uses semantic `<h1>` tag
- Breadcrumb uses `<nav>` with proper ARIA labels
- Subtitle uses semantic `<p>` tag

---

### 4. Breadcrumb

**Purpose:** Navigation breadcrumb trail showing user's current location.

**Location:** `src/components/layout/Breadcrumb.tsx`

**Props:**
```tsx
interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

interface BreadcrumbItem {
  label: string;      // Display text
  href?: string;      // Optional link
}
```

**Features:**
- Integrates with React Router (`Link` component)
- Automatic active/inactive state styling
- Proper ARIA labels for accessibility
- Semantic `<nav>` element

**Example:**
```tsx
<Breadcrumb
  items={[
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Documents', href: '/documents' },
    { label: 'Invoice #123' }  // Current page
  ]}
/>
```

**Styling:**
- Uses shadcn/ui `Breadcrumb` components
- Active link: Blue, underline on hover
- Inactive (current page): Gray, no link

**Accessibility:**
- `<nav aria-label="breadcrumb">`
- Screen reader friendly separators
- Keyboard navigable links

---

### 5. PageContent

**Purpose:** Wrapper for main page content with consistent spacing.

**Location:** `src/components/layout/PageContent.tsx`

**Props:**
```tsx
interface PageContentProps {
  children: React.ReactNode;
  className?: string;  // Optional: override styling
}
```

**Default Styling:**
- Spacing: `space-y-6` (24px vertical gap)
- Semantic `<section>` element
- ARIA label: "Page content"

**Example:**
```tsx
<PageContent>
  <div className="grid gap-6 md:grid-cols-3">
    <StatCard title="Documents" value={42} />
    <StatCard title="Schemas" value={12} />
    <StatCard title="Jobs" value={5} />
  </div>
</PageContent>
```

**When to Use:**
- Use for ALL page content below PageHeader
- Contains your page-specific components
- Provides consistent spacing between sections

---

### 6. Sidebar

**Purpose:** Collapseable navigation sidebar with route links.

**Location:** `src/components/layout/Sidebar.tsx`

**Props:**
```tsx
interface SidebarProps {
  isCollapsed: boolean;           // Collapsed state (80px vs 280px)
  onToggleCollapse: () => void;   // Toggle callback
  isMobileOpen: boolean;          // Mobile overlay state
  onMobileClose: () => void;      // Close mobile menu
}
```

**Features:**
- Desktop: Collapseable (280px → 80px with icons only)
- Mobile: Overlay menu with backdrop
- Navigation items with icons and active state
- Collapse toggle button
- State persisted to localStorage

**Navigation Items:**
```tsx
const navItems = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Schema Builder', href: '/schema-builder', icon: FileJson },
  { label: 'Documents', href: '/documents', icon: FileText },
  { label: 'Settings', href: '/settings', icon: Settings },
];
```

**State Management:**
- Managed by AuthenticatedLayout
- localStorage key: `'sidebar-collapsed'`
- Mobile state is ephemeral (not persisted)

**Styling:**
- Expanded: 280px width, text + icons
- Collapsed: 80px width, icons only
- Active route: Blue background
- Hover: Light gray background

---

### 7. Navbar

**Purpose:** Top navigation bar with user menu and mobile toggle.

**Location:** `src/components/layout/Navbar.tsx`

**Props:**
```tsx
interface NavbarProps {
  user: User;                     // User data for display
  onMobileMenuToggle: () => void; // Mobile sidebar toggle
}

interface User {
  full_name: string;
  email: string;
  avatar_url?: string;
}
```

**Features:**
- Application title/logo
- Mobile menu toggle button
- User avatar with dropdown menu
- Logout functionality

**User Menu Items:**
- Profile (placeholder)
- Settings (placeholder)
- Logout (clears tokens, redirects to login)

**Styling:**
- Fixed height: 64px
- Border bottom
- Flexbox layout
- Avatar uses shadcn/ui components

---

## Usage Patterns

### Standard Page Layout

**Pattern:** Breadcrumb → Title → Subtitle → Content

```tsx
import { Page, PageHeader, PageContent } from '@/components/layout';

export function MyPage() {
  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'My Page' }
        ]}
        title="My Page"
        subtitle="Description of what this page does"
      />
      <PageContent>
        {/* Your page content */}
        <div>Content goes here</div>
      </PageContent>
    </Page>
  );
}
```

---

### Dashboard Layout

**Pattern:** Stats cards in grid

```tsx
export function Dashboard() {
  return (
    <Page>
      <PageHeader
        breadcrumbs={[{ label: 'Dashboard' }]}
        title="Dashboard"
        subtitle="Welcome to your AI Document Processing dashboard"
      />
      <PageContent>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <StatCard title="Documents Processed" value={0} />
          <StatCard title="Active Schemas" value={0} />
          <StatCard title="Processing Jobs" value={0} />
        </div>
      </PageContent>
    </Page>
  );
}
```

---

### Custom Layout Page

**Pattern:** Override default spacing for custom layouts

```tsx
export function SchemaBuilder() {
  return (
    <Page className="h-full flex flex-col p-0">
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Schema Builder' }
        ]}
        title="Schema Builder"
        className="px-6 py-4 border-b"
      />

      {/* Custom split-panel layout */}
      <div className="flex-1 flex overflow-hidden">
        <div className="w-1/2 border-r">
          <SchemaTree />
        </div>
        <div className="w-1/2">
          <JsonPreview />
        </div>
      </div>
    </Page>
  );
}
```

---

### Page with No Breadcrumbs

**Pattern:** Top-level page (e.g., Dashboard)

```tsx
export function Dashboard() {
  return (
    <Page>
      <PageHeader
        title="Dashboard"
        subtitle="Welcome to your dashboard"
        // No breadcrumbs - top-level page
      />
      <PageContent>
        {/* Content */}
      </PageContent>
    </Page>
  );
}
```

---

### Page with Actions in Header

**Pattern:** Add action buttons to header

```tsx
export function DocumentsPage() {
  return (
    <Page>
      <div className="flex items-center justify-between">
        <PageHeader
          breadcrumbs={[
            { label: 'Dashboard', href: '/dashboard' },
            { label: 'Documents' }
          ]}
          title="Documents"
          subtitle="Manage your uploaded documents"
        />
        <div className="flex gap-2">
          <Button variant="outline">
            <Upload className="h-4 w-4 mr-2" />
            Upload
          </Button>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            New Document
          </Button>
        </div>
      </div>
      <PageContent>
        {/* Document list */}
      </PageContent>
    </Page>
  );
}
```

---

## Design Principles

### 1. Composition Over Configuration

**Why:** More flexible, easier to understand, better TypeScript support

**Example:**
```tsx
// ✅ Good - Composition
<Page>
  <PageHeader title="My Page" />
  <PageContent>
    <MyContent />
  </PageContent>
</Page>

// ❌ Bad - Configuration
<Page
  header={{ title: "My Page" }}
  content={<MyContent />}
/>
```

**Benefits:**
- Each component does one thing well
- Easy to test in isolation
- Familiar React patterns
- TypeScript auto-completion

---

### 2. Single Responsibility Principle

**Why:** Each component has one clear purpose

**Components:**
- `Page` - Container with spacing
- `PageHeader` - Display title/breadcrumbs
- `PageContent` - Content wrapper
- `Breadcrumb` - Navigation trail

**Benefits:**
- Easy to understand
- Simple to modify
- Minimal coupling
- Reusable across pages

---

### 3. Consistent Spacing

**Why:** Visual harmony and predictability

**Spacing Scale:**
- `p-6` (24px) - Page padding
- `space-y-6` (24px) - Content vertical spacing
- `space-y-4` (16px) - Header vertical spacing
- `gap-6` (24px) - Grid gap

**Benefits:**
- Professional appearance
- Easy to scan
- Consistent rhythm
- Accessible (proper whitespace)

---

### 4. Accessibility First

**Why:** Inclusive design, legal compliance, better UX for all

**Features:**
- Semantic HTML (`<nav>`, `<h1>`, `<section>`)
- ARIA labels (breadcrumb, content)
- Keyboard navigation (sidebar, menu)
- Focus indicators (visible outlines)

**Benefits:**
- Screen reader support
- Keyboard-only users
- WCAG 2.1 AA compliance
- Better SEO

---

## Complete Example: Building a New Page

**Scenario:** Create a "Settings" page with tabs

```tsx
import { Page, PageHeader, PageContent } from '@/components/layout';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export function SettingsPage() {
  return (
    <Page>
      {/* Header with breadcrumb navigation */}
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Settings' }
        ]}
        title="Settings"
        subtitle="Manage your account and preferences"
      />

      {/* Main content */}
      <PageContent>
        <Tabs defaultValue="profile">
          <TabsList>
            <TabsTrigger value="profile">Profile</TabsTrigger>
            <TabsTrigger value="security">Security</TabsTrigger>
            <TabsTrigger value="notifications">Notifications</TabsTrigger>
          </TabsList>

          <TabsContent value="profile" className="space-y-6">
            <div className="rounded-lg border bg-card p-6">
              <h3 className="text-lg font-semibold mb-4">Profile Information</h3>
              {/* Profile form */}
            </div>
          </TabsContent>

          <TabsContent value="security" className="space-y-6">
            <div className="rounded-lg border bg-card p-6">
              <h3 className="text-lg font-semibold mb-4">Password & Security</h3>
              {/* Security settings */}
            </div>
          </TabsContent>

          <TabsContent value="notifications" className="space-y-6">
            <div className="rounded-lg border bg-card p-6">
              <h3 className="text-lg font-semibold mb-4">Notification Preferences</h3>
              {/* Notification settings */}
            </div>
          </TabsContent>
        </Tabs>
      </PageContent>
    </Page>
  );
}
```

**App.tsx Integration:**
```tsx
<Route
  path="/settings"
  element={
    <ProtectedRoute>
      <AuthenticatedLayout>
        <SettingsPage />
      </AuthenticatedLayout>
    </ProtectedRoute>
  }
/>
```

**Result:**
```
Sidebar | Dashboard > Settings
        |
        | Settings
        | Manage your account and preferences
        | ─────────────────────────────────
        |
        | [Profile] [Security] [Notifications]
        |
        | ┌─────────────────────────────────┐
        | │ Profile Information             │
        | │                                 │
        | │ [Profile form here]             │
        | └─────────────────────────────────┘
```

---

## Props Reference

### Page
```tsx
interface PageProps {
  children: React.ReactNode;  // Required: Page content
  className?: string;         // Optional: Override default styles
}
```

### PageHeader
```tsx
interface PageHeaderProps {
  breadcrumbs?: BreadcrumbItem[];  // Optional: Navigation trail
  title: string;                   // Required: Page title
  subtitle?: string;               // Optional: Description
  className?: string;              // Optional: Override styles
}

interface BreadcrumbItem {
  label: string;      // Display text
  href?: string;      // Optional link (omit for current page)
}
```

### PageContent
```tsx
interface PageContentProps {
  children: React.ReactNode;  // Required: Content
  className?: string;         // Optional: Override styles
}
```

### Breadcrumb
```tsx
interface BreadcrumbProps {
  items: BreadcrumbItem[];  // Required: Breadcrumb trail
}
```

### AuthenticatedLayout
```tsx
interface AuthenticatedLayoutProps {
  children: React.ReactNode;  // Required: Page components
}
```

### Navbar
```tsx
interface NavbarProps {
  user: User;                     // Required: User data
  onMobileMenuToggle: () => void; // Required: Mobile toggle callback
}
```

### Sidebar
```tsx
interface SidebarProps {
  isCollapsed: boolean;           // Required: Collapse state
  onToggleCollapse: () => void;   // Required: Toggle callback
  isMobileOpen: boolean;          // Required: Mobile state
  onMobileClose: () => void;      // Required: Close callback
}
```

---

## Accessibility

### Keyboard Navigation

**Sidebar:**
- `Tab` - Navigate through menu items
- `Enter` - Activate menu item / Navigate to route
- `Escape` - Close mobile menu

**Breadcrumb:**
- `Tab` - Navigate through breadcrumb links
- `Enter` - Follow link

**User Menu:**
- `Tab` - Focus dropdown trigger
- `Enter/Space` - Open dropdown
- `Arrow Up/Down` - Navigate menu items
- `Enter` - Select menu item
- `Escape` - Close dropdown

### ARIA Attributes

**Breadcrumb:**
```tsx
<nav aria-label="Breadcrumb">
  <ol>
    <li><a href="...">Dashboard</a></li>
    <li aria-current="page">Settings</li>
  </ol>
</nav>
```

**PageContent:**
```tsx
<section aria-label="Page content">
  {/* Content */}
</section>
```

**Sidebar:**
```tsx
<nav aria-label="Main navigation">
  <button aria-expanded={isOpen} aria-controls="nav-menu">
    Menu
  </button>
</nav>
```

### Screen Reader Support

**Announcements:**
- Page title changes announced via `<h1>` focus
- Breadcrumb location announced via ARIA labels
- Menu state changes announced via `aria-expanded`

---

## File Locations

```
src/components/layout/
├── AuthenticatedLayout.tsx  # Main app shell
├── Navbar.tsx               # Top navigation
├── Sidebar.tsx              # Side navigation
├── Breadcrumb.tsx           # Breadcrumb component
├── PageHeader.tsx           # Page header
├── PageContent.tsx          # Content wrapper
├── Page.tsx                 # Page container
└── index.ts                 # Export all components
```

**Import Pattern:**
```tsx
import {
  Page,
  PageHeader,
  PageContent,
  AuthenticatedLayout
} from '@/components/layout';
```

---

## Best Practices

### ✅ Do

- Use `Page` for every authenticated page
- Include breadcrumbs for nested pages
- Provide descriptive subtitles
- Use `PageContent` for main content
- Override `className` for custom layouts
- Test keyboard navigation
- Verify ARIA labels with screen reader

### ❌ Don't

- Skip `PageHeader` (inconsistent UX)
- Nest `Page` components
- Put content outside `PageContent`
- Hardcode spacing (use components)
- Forget breadcrumbs on deep pages
- Override without good reason

---

## Common Patterns

### Pattern 1: Simple Content Page
```tsx
<Page>
  <PageHeader title="Page" />
  <PageContent>
    <div>Content</div>
  </PageContent>
</Page>
```

### Pattern 2: Page with Breadcrumbs
```tsx
<Page>
  <PageHeader
    breadcrumbs={[{ label: 'Home', href: '/' }, { label: 'Page' }]}
    title="Page"
  />
  <PageContent>
    <div>Content</div>
  </PageContent>
</Page>
```

### Pattern 3: Page with Grid Layout
```tsx
<Page>
  <PageHeader title="Dashboard" />
  <PageContent>
    <div className="grid gap-6 md:grid-cols-3">
      <Card />
      <Card />
      <Card />
    </div>
  </PageContent>
</Page>
```

### Pattern 4: Custom Full-Height Page
```tsx
<Page className="h-full flex flex-col p-0">
  <PageHeader title="Editor" className="px-6 py-4 border-b" />
  <div className="flex-1 overflow-hidden">
    {/* Custom layout */}
  </div>
</Page>
```

---

## Migration Guide

**Before (Old Pattern):**
```tsx
export function Dashboard() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="mt-2 text-muted-foreground">
          Welcome to your dashboard
        </p>
      </div>
      <div className="grid gap-6 md:grid-cols-3">
        {/* Content */}
      </div>
    </div>
  );
}
```

**After (New Pattern):**
```tsx
export function Dashboard() {
  return (
    <Page>
      <PageHeader
        breadcrumbs={[{ label: 'Dashboard' }]}
        title="Dashboard"
        subtitle="Welcome to your dashboard"
      />
      <PageContent>
        <div className="grid gap-6 md:grid-cols-3">
          {/* Content */}
        </div>
      </PageContent>
    </Page>
  );
}
```

**Benefits:**
- ✅ Consistent structure
- ✅ Breadcrumb navigation
- ✅ Semantic HTML
- ✅ ARIA labels
- ✅ Easier to maintain

---

## Troubleshooting

### Issue: Breadcrumb links not working

**Problem:** Clicking breadcrumb doesn't navigate

**Solution:** Ensure React Router is set up correctly
```tsx
// App.tsx
import { BrowserRouter } from 'react-router-dom';

function App() {
  return (
    <BrowserRouter>
      {/* Routes */}
    </BrowserRouter>
  );
}
```

---

### Issue: Sidebar state not persisting

**Problem:** Sidebar resets to expanded on page refresh

**Solution:** Check localStorage implementation in AuthenticatedLayout
```tsx
// Verify localStorage key
const SIDEBAR_COLLAPSE_KEY = 'sidebar-collapsed';

// Check read
const stored = localStorage.getItem(SIDEBAR_COLLAPSE_KEY);

// Check write
localStorage.setItem(SIDEBAR_COLLAPSE_KEY, String(isCollapsed));
```

---

### Issue: Custom layout not working

**Problem:** Page doesn't fill viewport height

**Solution:** Override default padding
```tsx
<Page className="h-full flex flex-col p-0">
  {/* Custom layout */}
</Page>
```

---

## Version History

**Version 1.0** (2025-11-03)
- Initial layout system implementation
- Page, PageHeader, PageContent components
- AuthenticatedLayout with sidebar and navbar
- Breadcrumb navigation
- Complete documentation

---

## See Also

- [Component Reference](./COMPONENT_REFERENCE.md) - Quick reference for all components
- [Auth Implementation](./AUTH_IMPLEMENTATION.md) - Authentication and protected routes
- [Design System Summary](./DESIGN_SYSTEM_SUMMARY.md) - Overall design philosophy

---

**Last Updated:** 2025-11-03
**Version:** 1.0
**Status:** ✅ Complete and Production-Ready
