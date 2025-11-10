# Component Quick Reference

**Fast lookup guide for all reusable components in the application**

---

## Table of Contents

1. [Layout Components](#layout-components)
2. [Authentication Components](#authentication-components)
3. [shadcn/ui Components](#shadcnui-components)
4. [Schema Builder Components](#schema-builder-components)
5. [Common Patterns](#common-patterns)

---

## Layout Components

### Page

**Purpose:** Top-level page container

**Import:**
```tsx
import { Page } from '@/components/layout';
```

**Props:**
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| children | ReactNode | ✅ | - | Page content |
| className | string | ❌ | - | Override styles |

**Example:**
```tsx
<Page>
  <PageHeader ... />
  <PageContent>...</PageContent>
</Page>
```

---

### PageHeader

**Purpose:** Standardized page header with breadcrumb, title, subtitle

**Import:**
```tsx
import { PageHeader } from '@/components/layout';
```

**Props:**
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| title | string | ✅ | - | Page title (h1) |
| breadcrumbs | BreadcrumbItem[] | ❌ | - | Navigation trail |
| subtitle | string | ❌ | - | Description |
| className | string | ❌ | - | Override styles |

**BreadcrumbItem:**
```tsx
interface BreadcrumbItem {
  label: string;    // Display text
  href?: string;    // Optional link (omit for current page)
}
```

**Example:**
```tsx
<PageHeader
  breadcrumbs={[
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Current Page' }
  ]}
  title="Page Title"
  subtitle="Optional description"
/>
```

---

### PageContent

**Purpose:** Main content wrapper with consistent spacing

**Import:**
```tsx
import { PageContent } from '@/components/layout';
```

**Props:**
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| children | ReactNode | ✅ | - | Content |
| className | string | ❌ | - | Override styles |

**Example:**
```tsx
<PageContent>
  <div className="grid gap-6 md:grid-cols-3">
    {/* Content */}
  </div>
</PageContent>
```

---

### Breadcrumb

**Purpose:** Navigation breadcrumb trail

**Import:**
```tsx
import { Breadcrumb } from '@/components/layout';
```

**Props:**
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| items | BreadcrumbItem[] | ✅ | - | Breadcrumb trail |

**Example:**
```tsx
<Breadcrumb
  items={[
    { label: 'Home', href: '/' },
    { label: 'Docs', href: '/docs' },
    { label: 'Current' }
  ]}
/>
```

---

### AuthenticatedLayout

**Purpose:** Main app shell with sidebar and navbar

**Import:**
```tsx
import { AuthenticatedLayout } from '@/components/layout';
```

**Props:**
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| children | ReactNode | ✅ | - | Page components |

**Example:**
```tsx
<AuthenticatedLayout>
  <Page>
    {/* Your pages */}
  </Page>
</AuthenticatedLayout>
```

**Note:** Used in App.tsx to wrap all authenticated routes.

---

### Sidebar

**Purpose:** Collapseable side navigation

**Location:** `src/components/layout/Sidebar.tsx`

**Managed by:** AuthenticatedLayout (don't use directly)

**Features:**
- Desktop: 280px expanded, 80px collapsed
- Mobile: Overlay menu
- State persists to localStorage
- Navigation items with icons

---

### Navbar

**Purpose:** Top navigation with user menu

**Location:** `src/components/layout/Navbar.tsx`

**Managed by:** AuthenticatedLayout (don't use directly)

**Features:**
- App title/logo
- Mobile menu toggle
- User avatar with dropdown
- Logout functionality

---

## Authentication Components

### ProtectedRoute

**Purpose:** Authentication guard for routes

**Import:**
```tsx
import { ProtectedRoute } from '@/components/layout';
```

**Props:**
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| children | ReactNode | ✅ | - | Protected content |

**Example:**
```tsx
<Route
  path="/dashboard"
  element={
    <ProtectedRoute>
      <AuthenticatedLayout>
        <Dashboard />
      </AuthenticatedLayout>
    </ProtectedRoute>
  }
/>
```

**Behavior:**
- Checks `isAuthenticated()` on mount
- Redirects to `/login` if not authenticated
- Returns `null` during redirect

---

## shadcn/ui Components

### Button

**Import:**
```tsx
import { Button } from '@/components/ui/button';
```

**Variants:** `default`, `destructive`, `outline`, `secondary`, `ghost`, `link`

**Sizes:** `default`, `sm`, `lg`, `icon`

**Example:**
```tsx
<Button variant="default" size="default">
  Click me
</Button>

<Button variant="outline" size="sm">
  <Icon className="h-4 w-4 mr-2" />
  With Icon
</Button>
```

---

### Card

**Import:**
```tsx
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter
} from '@/components/ui/card';
```

**Example:**
```tsx
<Card>
  <CardHeader>
    <CardTitle>Card Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
  <CardContent>
    {/* Content */}
  </CardContent>
  <CardFooter>
    {/* Footer actions */}
  </CardFooter>
</Card>
```

---

### Input

**Import:**
```tsx
import { Input } from '@/components/ui/input';
```

**Example:**
```tsx
<Input
  type="text"
  placeholder="Enter text"
  value={value}
  onChange={(e) => setValue(e.target.value)}
/>
```

---

### Label

**Import:**
```tsx
import { Label } from '@/components/ui/label';
```

**Example:**
```tsx
<div className="space-y-2">
  <Label htmlFor="email">Email</Label>
  <Input id="email" type="email" />
</div>
```

---

### Dialog

**Import:**
```tsx
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter
} from '@/components/ui/dialog';
```

**Example:**
```tsx
<Dialog>
  <DialogTrigger asChild>
    <Button>Open Dialog</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Dialog Title</DialogTitle>
      <DialogDescription>
        Description text
      </DialogDescription>
    </DialogHeader>
    {/* Content */}
    <DialogFooter>
      <Button>Save</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

---

### Dropdown Menu

**Import:**
```tsx
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from '@/components/ui/dropdown-menu';
```

**Example:**
```tsx
<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="outline">Menu</Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent>
    <DropdownMenuItem>Item 1</DropdownMenuItem>
    <DropdownMenuItem>Item 2</DropdownMenuItem>
    <DropdownMenuSeparator />
    <DropdownMenuItem>Item 3</DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

---

### Checkbox

**Import:**
```tsx
import { Checkbox } from '@/components/ui/checkbox';
```

**Example:**
```tsx
<div className="flex items-center space-x-2">
  <Checkbox
    id="terms"
    checked={accepted}
    onCheckedChange={(checked) => setAccepted(checked === true)}
  />
  <Label htmlFor="terms">Accept terms</Label>
</div>
```

---

### Avatar

**Import:**
```tsx
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
```

**Example:**
```tsx
<Avatar>
  <AvatarImage src={user.avatar} alt={user.name} />
  <AvatarFallback>{user.initials}</AvatarFallback>
</Avatar>
```

---

## Schema Builder Components

### SchemaTree

**Purpose:** Visual tree editor for schema structure

**Location:** `src/components/schema-builder/SchemaTree.tsx`

**Features:**
- Recursive tree rendering
- Add/edit/delete properties
- Max 3-level nesting
- Expand/collapse nodes

---

### PropertyEditor

**Purpose:** Dialog for editing property details

**Location:** `src/components/schema-builder/PropertyEditor.tsx`

**Features:**
- Type selection (string, number, boolean, object, array)
- Constraint editors per type
- Form validation
- Required field toggle

---

### JsonPreview

**Purpose:** Live JSON Schema preview

**Location:** `src/components/preview/JsonPreview.tsx`

**Features:**
- Syntax highlighting
- Tabs (Schema, Sample Data)
- Copy to clipboard
- Validation errors

---

### TemplateSelector

**Purpose:** Load pre-built schema templates

**Location:** `src/components/templates/TemplateSelector.tsx`

**Features:**
- Template library (Invoice, Resume)
- Load template into editor
- Preview template structure

---

## Common Patterns

### Standard Page Layout

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
        subtitle="Page description"
      />
      <PageContent>
        {/* Your content */}
      </PageContent>
    </Page>
  );
}
```

---

### Grid Layout

```tsx
<PageContent>
  <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
    <Card>...</Card>
    <Card>...</Card>
    <Card>...</Card>
  </div>
</PageContent>
```

---

### Form with Validation

```tsx
import { useForm } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export function MyForm() {
  const { register, handleSubmit, formState: { errors } } = useForm();

  const onSubmit = (data) => {
    console.log(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          {...register('email', {
            required: 'Email is required',
            pattern: {
              value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
              message: 'Invalid email address'
            }
          })}
        />
        {errors.email && (
          <p className="text-sm text-destructive">
            {errors.email.message}
          </p>
        )}
      </div>
      <Button type="submit">Submit</Button>
    </form>
  );
}
```

---

### Dialog with Form

```tsx
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export function MyDialog() {
  const [open, setOpen] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    // Handle form submission
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Open Dialog</Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Form Title</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input id="name" placeholder="Enter name" />
            </div>
          </div>
          <DialogFooter>
            <Button type="submit">Save</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

---

### Zustand Store Usage

```tsx
import { useSchemaStore } from '@/store/schemaStore';

export function MyComponent() {
  // Subscribe to specific state
  const schemaName = useSchemaStore((state) => state.schemaName);
  const setSchemaName = useSchemaStore((state) => state.setSchemaName);

  // Or use multiple values
  const { properties, addProperty } = useSchemaStore();

  return (
    <div>
      <Input
        value={schemaName}
        onChange={(e) => setSchemaName(e.target.value)}
      />
    </div>
  );
}
```

---

### Toast Notifications

```tsx
import { toast } from 'sonner';

// Success
toast.success('Schema saved successfully!', {
  description: 'Your schema has been saved to the database'
});

// Error
toast.error('Failed to save schema', {
  description: 'Please try again later'
});

// Info
toast.info('Processing...', {
  description: 'This may take a few moments'
});

// With action
toast.success('Schema saved', {
  action: {
    label: 'View',
    onClick: () => navigate('/schemas')
  }
});
```

---

### API Calls with Error Handling

```tsx
import { getAccessToken } from '@/services/auth.service';
import { toast } from 'sonner';

async function saveData() {
  try {
    const response = await fetch('/api/v1/data', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getAccessToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      if (response.status === 401) {
        toast.error('Authentication required');
        navigate('/login');
        return;
      }
      throw new Error('Failed to save');
    }

    const result = await response.json();
    toast.success('Saved successfully!');
  } catch (error) {
    toast.error('Failed to save', {
      description: error.message
    });
  }
}
```

---

### Protected Route Pattern

```tsx
// App.tsx
import { ProtectedRoute } from '@/components/layout';
import { AuthenticatedLayout } from '@/components/layout';

<Route
  path="/protected-page"
  element={
    <ProtectedRoute>
      <AuthenticatedLayout>
        <ProtectedPage />
      </AuthenticatedLayout>
    </ProtectedRoute>
  }
/>

// Public route (no protection)
<Route path="/login" element={<Login />} />
<Route path="/signup" element={<Signup />} />
```

---

## Keyboard Shortcuts

| Action | Shortcut | Component |
|--------|----------|-----------|
| Focus search | `/` | Global |
| Close dialog | `Esc` | Dialog |
| Open dropdown | `Enter/Space` | DropdownMenu |
| Navigate menu | `↑/↓` | DropdownMenu |
| Toggle sidebar | `Ctrl+B` | Sidebar (planned) |

---

## File Locations

### Layout Components
```
src/components/layout/
├── Page.tsx
├── PageHeader.tsx
├── PageContent.tsx
├── Breadcrumb.tsx
├── AuthenticatedLayout.tsx
├── Navbar.tsx
├── Sidebar.tsx
└── ProtectedRoute.tsx
```

### UI Components
```
src/components/ui/
├── button.tsx
├── card.tsx
├── input.tsx
├── label.tsx
├── dialog.tsx
├── dropdown-menu.tsx
├── checkbox.tsx
├── avatar.tsx
└── ... (more shadcn/ui components)
```

### Pages
```
src/pages/
├── Dashboard.tsx
├── SchemaBuilder.tsx
├── Login.tsx
├── Signup.tsx
└── LandingPage.tsx
```

---

## Installation Commands

### Add shadcn/ui Components

```bash
# Single component
npx shadcn@latest add button

# Multiple components
npx shadcn@latest add button card dialog

# All form components
npx shadcn@latest add button input label checkbox select textarea
```

### Install Peer Dependencies

```bash
npm install class-variance-authority @radix-ui/react-icons
```

---

## Quick Tips

1. **Always import from `@/components/layout`** for layout components
2. **Use `Page` for every authenticated page** for consistency
3. **Include breadcrumbs for nested pages** (depth > 1)
4. **Use `toast` for all user feedback** (success, error, info)
5. **Wrap protected routes** with both ProtectedRoute and AuthenticatedLayout
6. **Check `isAuthenticated()`** before making authenticated API calls
7. **Use `react-hook-form`** for all forms (better validation)
8. **Prefer composition over configuration** (combine small components)
9. **Test keyboard navigation** for accessibility
10. **Use Zustand** for global state, local state for component-specific data

---

## See Also

- [Layout System Guide](./LAYOUT_SYSTEM.md) - Complete layout documentation
- [Auth Implementation](./AUTH_IMPLEMENTATION.md) - Authentication patterns
- [shadcn/ui Documentation](https://ui.shadcn.com/) - Component library docs
- [React Hook Form](https://react-hook-form.com/) - Form validation
- [Zustand Documentation](https://zustand-demo.pmnd.rs/) - State management

---

**Last Updated:** 2025-11-03
**Version:** 1.0
