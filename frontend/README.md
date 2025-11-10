# AI Document Processing - Frontend Application

**React + TypeScript + Vite SaaS Application for AI-Powered Document Processing**

---

## Overview

Complete frontend application for the AI Document Processing SaaS platform. Features include JWT authentication, multi-tenancy support, visual JSON Schema builder, dashboard layouts, and document management.

---

## ✅ Current Status

### Completed Features

**Phase 1: Project Foundation** ✅
- Vite + React 19 + TypeScript 5.6+ setup
- Tailwind CSS 4 with shadcn/ui components
- Path aliases (`@/*` → `./src/*`)
- Dev server with API proxy

**Phase 2: Authentication & Authorization** ✅
- JWT authentication with refresh tokens
- Login and signup pages
- Protected routes
- User session management
- Password strength validation
- Form validation with react-hook-form

**Phase 3: Dashboard & Layout System** ✅
- AuthenticatedLayout with collapseable sidebar
- Page composition system (Page/PageHeader/PageContent)
- Breadcrumb navigation
- User menu with logout
- Mobile-responsive design

**Phase 4: JSON Schema Builder** ✅
- Visual tree-based schema editor
- 3-level nesting support
- Property type selector (string, number, boolean, object, array)
- Constraint editors (format, pattern, min/max, enum, default)
- Live JSON Schema preview
- Sample data generation
- Pre-built templates (Invoice, Resume)
- Save/load schemas via backend API
- Export as JSON file

---

## 🚀 Quick Start

### Development Server

```bash
# Install dependencies
npm install

# Start dev server (http://localhost:3002)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Variables

Create `.env` file:
```bash
VITE_API_URL=http://localhost:8000
```

---

## 🏗️ Architecture

### Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 19.1.1 | UI framework |
| **TypeScript** | 5.6+ | Type safety |
| **Vite** | 7 | Build tool & dev server |
| **Tailwind CSS** | 4 | Utility-first styling |
| **shadcn/ui** | Latest | Component library |
| **Zustand** | 5 | State management |
| **React Router** | 7 | Client-side routing |
| **react-hook-form** | 7.54+ | Form validation |
| **Lucide React** | Latest | Icon library |
| **Sonner** | Latest | Toast notifications |

### Key Features

✅ **Authentication**
- JWT token-based authentication
- Login/signup with validation
- Password strength indicator
- Auto-login after registration
- Token refresh mechanism

✅ **Layout System**
- Composable page components
- Collapseable sidebar (280px → 80px)
- Breadcrumb navigation
- User menu with avatar
- Mobile-responsive design

✅ **Protected Routes**
- Route guards checking authentication
- Automatic redirect to login
- Token validation

✅ **JSON Schema Builder**
- Visual tree editor
- Max 3-level nesting
- Type constraints
- Live preview
- Template library

✅ **Dashboard**
- Statistics overview
- Quick actions
- Navigation

---

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/                     # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   └── ...
│   │   ├── layout/                 # Layout system components
│   │   │   ├── AuthenticatedLayout.tsx
│   │   │   ├── Navbar.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Breadcrumb.tsx
│   │   │   ├── Page.tsx
│   │   │   ├── PageHeader.tsx
│   │   │   ├── PageContent.tsx
│   │   │   ├── ProtectedRoute.tsx
│   │   │   └── index.ts
│   │   ├── preview/                # JSON preview components
│   │   │   └── JsonPreview.tsx
│   │   ├── schema-builder/         # Schema tree & editors
│   │   │   ├── SchemaTree.tsx
│   │   │   ├── SchemaTreeNode.tsx
│   │   │   ├── PropertyEditor.tsx
│   │   │   └── ...
│   │   └── templates/              # Template selector
│   │       └── TemplateSelector.tsx
│   ├── pages/                      # Application pages
│   │   ├── Dashboard.tsx           # Main dashboard
│   │   ├── SchemaBuilder.tsx       # Schema creation page
│   │   ├── Login.tsx               # Login page
│   │   ├── Signup.tsx              # Registration page
│   │   └── LandingPage.tsx         # Public landing
│   ├── services/                   # API services
│   │   └── auth.service.ts         # Authentication API
│   ├── lib/
│   │   ├── utils.ts                # Utility functions (cn())
│   │   ├── api.ts                  # API client
│   │   ├── schema-converter.ts     # JSON Schema conversion
│   │   └── template-loader.ts      # Template utilities
│   ├── store/
│   │   └── schemaStore.ts          # Zustand state management
│   ├── types/
│   │   ├── schema.ts               # Schema type definitions
│   │   ├── auth.ts                 # Auth types
│   │   ├── user.ts                 # User types
│   │   └── template.ts             # Template types
│   ├── templates/                  # Pre-built schema templates
│   │   ├── invoice.ts
│   │   └── resume.ts
│   ├── App.tsx                     # Main app with routes
│   ├── main.tsx                    # Entry point
│   └── index.css                   # Global styles
├── public/                         # Static assets
├── package.json
├── vite.config.ts                  # Vite configuration
├── tsconfig.json                   # TypeScript configuration
├── tailwind.config.js              # Tailwind configuration
└── README.md                       # This file
```

---

## 🎯 Core Features

### 1. Authentication Flow

**Login:**
1. User enters email and password
2. Form validation (client-side)
3. API call to `/api/v1/auth/login`
4. Store JWT tokens in localStorage
5. Redirect to dashboard

**Signup:**
1. User fills registration form (name, email, company, password)
2. Password strength indicator
3. Password confirmation matching
4. Terms acceptance
5. API call to `/api/v1/auth/register`
6. Auto-login and redirect to dashboard

**Protected Routes:**
- Check `isAuthenticated()` before rendering
- Redirect to `/login` if not authenticated
- Token validation on page load

---

### 2. Layout System

**Component Hierarchy:**
```
AuthenticatedLayout
└── Page
    ├── PageHeader (Breadcrumb, Title, Subtitle)
    └── PageContent (Your content)
```

**Example Usage:**
```tsx
<Page>
  <PageHeader
    breadcrumbs={[
      { label: 'Dashboard', href: '/dashboard' },
      { label: 'Current Page' }
    ]}
    title="Page Title"
    subtitle="Optional description"
  />
  <PageContent>
    {/* Your page content */}
  </PageContent>
</Page>
```

**See:** [Layout System Documentation](./LAYOUT_SYSTEM.md)

---

### 3. JSON Schema Builder

**Features:**
- Visual tree editor with drag-and-drop (planned)
- Add/edit/delete properties
- Type selection (string, number, boolean, object, array)
- Constraint editors per type
- Max 3-level nesting enforcement
- Live JSON Schema preview
- Sample data generation
- Save to backend API
- Export as JSON file
- Import existing schemas
- Template library (Invoice, Resume)

**Usage:**
1. Navigate to `/schema-builder`
2. Add properties to schema
3. Configure constraints
4. Preview generated JSON Schema
5. Save or export

---

## 📚 Documentation

### Core Guides

- **[Layout System](./LAYOUT_SYSTEM.md)** - Complete layout architecture documentation
- **[Component Reference](./COMPONENT_REFERENCE.md)** - Quick reference for all components
- **[Auth Implementation](./AUTH_IMPLEMENTATION.md)** - Authentication and protected routes
- **[Testing Guide](./TESTING_GUIDE.md)** - Testing checklist and strategies
- **[Implementation Status](./IMPLEMENTATION_STATUS.md)** - Progress tracker

### Design System

- **[Design System Summary](./DESIGN_SYSTEM_SUMMARY.md)** - Overall design philosophy
- **[Test Auth Pages](./TEST_AUTH_PAGES.md)** - Auth testing guide

---

## 🔐 Authentication

### Token Management

**Storage:**
```typescript
// Store tokens after login/signup
storeTokens(accessToken, refreshToken);

// Get access token
const token = getAccessToken();

// Check authentication status
const isAuth = isAuthenticated();

// Clear tokens (logout)
clearTokens();
```

**API Integration:**

**CRITICAL: Always use the centralized API wrapper - NEVER use raw `fetch()` directly.**

```typescript
// ✅ CORRECT - Use apiFetch wrapper (defined in service files)
const response = await apiFetch('/api/v1/schemas', {
  headers: {
    'Content-Type': 'application/json'
  }
});

// ❌ INCORRECT - Do NOT use raw fetch
const response = await fetch('/api/v1/schemas', {
  headers: {
    'Authorization': `Bearer ${getAccessToken()}`,
    'Content-Type': 'application/json'
  }
});
```

**Why use apiFetch wrapper?**
- ✅ Automatic auth header injection
- ✅ 401 interceptor - auto-redirect to login on unauthorized
- ✅ Consistent error handling across all services
- ✅ Token management centralized

**Wrapper Pattern:**
```typescript
// Each service file should include this apiFetch function
async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem('access_token');
  const headers = new Headers(options.headers);

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Intercept 401 - clear tokens and redirect to login
  if (response.status === 401) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
    throw new Error('Unauthorized - Please log in again');
  }

  return response;
}
```

**See:**
- `src/lib/api.ts` - Main API service (schemas, jobs, documents)
- `src/services/user.service.ts` - User profile and invitations
- `src/services/subscription.service.ts` - Subscription management
- `src/services/auth.service.ts` - Authentication (login/signup)

---

## 🎨 Styling

### Tailwind CSS 4

**IMPORTANT:** Tailwind 4 has breaking changes from v3.

**Common Patterns:**
```tsx
// ✅ Use direct properties for CSS variables
<div style={{
  backgroundColor: 'hsl(var(--background))',
  color: 'hsl(var(--foreground))'
}} />

// ❌ Don't use @apply with custom properties
// @apply bg-background  (won't work in Tailwind 4)
```

**Color Variables:**
- `--background` - Page background
- `--foreground` - Text color
- `--primary` - Primary brand color
- `--destructive` - Error/danger color
- `--muted` - Muted/secondary color
- `--border` - Border color

---

## 🧪 Testing

### Manual Testing Checklist

**Authentication:**
- [ ] Login with valid credentials
- [ ] Login with invalid credentials
- [ ] Signup with valid data
- [ ] Signup with duplicate email
- [ ] Password strength indicator updates
- [ ] Token persists across page refresh
- [ ] Logout clears tokens

**Layout:**
- [ ] Sidebar collapses/expands
- [ ] Sidebar state persists to localStorage
- [ ] Mobile menu opens/closes
- [ ] Breadcrumb navigation works
- [ ] User menu dropdown works
- [ ] All routes accessible

**Schema Builder:**
- [ ] Add property
- [ ] Edit property
- [ ] Delete property
- [ ] Nesting works (max 3 levels)
- [ ] JSON preview updates
- [ ] Save to API
- [ ] Export JSON file
- [ ] Load template

---

## 🚧 Development Workflow

### Adding a New Page

1. **Create page component** in `src/pages/`
   ```tsx
   // src/pages/MyPage.tsx
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
           {/* Content */}
         </PageContent>
       </Page>
     );
   }
   ```

2. **Add route** in `App.tsx`
   ```tsx
   <Route
     path="/my-page"
     element={
       <ProtectedRoute>
         <AuthenticatedLayout>
           <MyPage />
         </AuthenticatedLayout>
       </ProtectedRoute>
     }
   />
   ```

3. **Add navigation** in `Sidebar.tsx`
   ```tsx
   { label: 'My Page', href: '/my-page', icon: MyIcon }
   ```

---

### Adding a shadcn/ui Component

```bash
# Install component
npx shadcn@latest add [component-name]

# Example: Add dialog component
npx shadcn@latest add dialog

# Manually install peer dependencies if needed
npm install class-variance-authority @radix-ui/react-icons
```

---

## 🔧 Configuration

### Vite Configuration

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3002,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

### TypeScript Path Aliases

```json
// tsconfig.json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### Tailwind Configuration

```javascript
// tailwind.config.js
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        // ... shadcn/ui theme
      },
    },
  },
};
```

---

## 🎯 Best Practices

### React Best Practices

1. **Use @agent-react-best-practices-expert** for ALL React implementation
2. **Single Responsibility** - Each component does one thing
3. **Composition over Inheritance** - Build complex UIs from simple components
4. **No Unnecessary useEffect** - Derived state, not effects
5. **TypeScript Strict Mode** - Ensure type safety

### API Communication

**MANDATORY: All remote API calls MUST use the centralized API wrapper.**

1. **NEVER use raw `fetch()` for API calls**
   - ❌ `fetch('/api/v1/users/profile', { headers: {...} })`
   - ✅ `apiFetch('/api/v1/users/profile', { headers: {...} })`

2. **Use apiFetch wrapper in service files**
   - Automatic auth header injection
   - Built-in 401 interceptor (auto-redirect to login)
   - Consistent error handling

3. **Service file pattern:**
   ```typescript
   // src/services/my.service.ts

   // Define apiFetch wrapper at the top
   async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
     const token = localStorage.getItem('access_token');
     const headers = new Headers(options.headers);

     if (token && !headers.has('Authorization')) {
       headers.set('Authorization', `Bearer ${token}`);
     }

     const response = await fetch(url, { ...options, headers });

     // 401 interceptor
     if (response.status === 401) {
       localStorage.removeItem('access_token');
       localStorage.removeItem('refresh_token');
       window.location.href = '/login';
       throw new Error('Unauthorized - Please log in again');
     }

     return response;
   }

   // Use in all API functions
   export async function getMyData(): Promise<MyData> {
     const response = await apiFetch(`${API_BASE_URL}/my-data`, {
       method: 'GET',
       headers: { 'Content-Type': 'application/json' }
     });
     // ... handle response
   }
   ```

4. **References:**
   - See `src/lib/api.ts` for complete implementation
   - See `src/services/user.service.ts` for example usage
   - See `src/services/subscription.service.ts` for example usage

### Component Patterns

1. **Prefer Composition:**
   ```tsx
   // ✅ Good
   <Page>
     <PageHeader title="..." />
     <PageContent>...</PageContent>
   </Page>

   // ❌ Bad
   <Page header="..." content="..." />
   ```

2. **Use Zustand for Global State:**
   ```tsx
   const { schemaName, setSchemaName } = useSchemaStore();
   ```

3. **Form Validation with react-hook-form:**
   ```tsx
   const { register, handleSubmit, formState: { errors } } = useForm();
   ```

---

## 🐛 Common Issues

### Issue: Tailwind styles not applying

**Solution:** Ensure Tailwind 4 syntax
```tsx
// ✅ Correct (Tailwind 4)
<div className="bg-background text-foreground" />

// ❌ Incorrect (custom variables need direct CSS)
<div style={{ backgroundColor: 'hsl(var(--background))' }} />
```

### Issue: shadcn/ui component not working

**Solution:** Install peer dependencies
```bash
npm install class-variance-authority @radix-ui/react-icons
```

### Issue: 401 Unauthorized on API calls

**Solution:** Use the API wrapper (apiFetch) instead of raw fetch
```tsx
// ❌ Wrong - manual token management
const token = getAccessToken();
const response = await fetch('/api/v1/data', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// ✅ Correct - use apiFetch wrapper
const response = await apiFetch('/api/v1/data', {
  headers: { 'Content-Type': 'application/json' }
});
```

**Why?** The apiFetch wrapper:
- Automatically adds Authorization header
- Handles 401 responses (clears tokens, redirects to login)
- Provides consistent error handling

---

## 📖 Further Reading

- [Vite Documentation](https://vitejs.dev/)
- [React 19 Documentation](https://react.dev/)
- [Tailwind CSS 4](https://tailwindcss.com/docs)
- [shadcn/ui Components](https://ui.shadcn.com/)
- [Zustand State Management](https://zustand-demo.pmnd.rs/)
- [React Router](https://reactrouter.com/)

---

## 🔄 Version History

**Version 1.4** (2025-11-04)
- ✅ Centralized API wrapper for all remote calls
- ✅ 401 interceptor with auto-redirect to login
- ✅ Automatic auth header injection
- ✅ Profile and Settings pages
- ✅ User invitation management (stub)
- ✅ Subscription management (stub)
- ✅ Updated documentation with API wrapper requirements

**Version 1.3** (2025-11-03)
- ✅ Added Layout System (Page, PageHeader, PageContent)
- ✅ Added Breadcrumb Navigation
- ✅ Added AuthenticatedLayout with Sidebar and Navbar
- ✅ Updated documentation

**Version 1.2** (2025-11-03)
- ✅ Added Authentication (Login/Signup)
- ✅ Added Protected Routes
- ✅ Added Dashboard

**Version 1.1** (2025-11-02)
- ✅ JSON Schema Builder complete
- ✅ Template library
- ✅ Save/Export functionality

**Version 1.0** (2025-11-02)
- ✅ Project foundation
- ✅ Tailwind + shadcn/ui setup
- ✅ Basic schema editor

---

**Last Updated:** 2025-11-04
**Status:** ✅ Production-Ready SaaS Frontend
