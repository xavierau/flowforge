# JSON Schema Builder - Quick Reference Card

**Print this page and keep it at your desk during implementation**

---

## Component Mapping

| UI Element | shadcn/ui Component | File Location |
|------------|-------------------|---------------|
| Schema Tree | Custom + `Button` | `src/components/schema-editor/SchemaTreeNode.tsx` |
| Property Editor | `Dialog` + `Input` + `Select` | `src/components/schema-editor/PropertyEditor.tsx` |
| Toolbar | `DropdownMenu` + `Button` | `src/components/layout/Header.tsx` |
| JSON Preview | `Tabs` + `@microlink/react-json-view` | `src/components/preview/JSONPreviewPanel.tsx` |
| Type Selector | `Select` with icons | `PropertyEditor.tsx` |
| Constraint Editors | `Input` + `Textarea` + `Select` | `src/components/schema-editor/*Constraints.tsx` |
| Template Gallery | `Dialog` + `Card` | `src/components/templates/TemplateSelector.tsx` |
| Validation Status | `Alert` + icons | `JSONPreviewPanel.tsx` |
| Tooltips | `Tooltip` | Throughout |
| Toast Notifications | `Toast` (shadcn/ui) | Throughout |

---

## Color Palette Reference

### Semantic Colors (from CSS variables)

```tsx
// Use these Tailwind classes
bg-background       // Main background
bg-foreground       // Main text color
bg-primary          // Primary actions (save button)
bg-secondary        // Secondary actions
bg-destructive      // Delete, errors
bg-muted            // Subtle backgrounds
bg-accent           // Hover states
border-border       // Default borders
text-muted-foreground // Helper text
```

### Type-Specific Colors

```tsx
// Import and use these classes
text-type-string    // Blue #3b82f6
text-type-number    // Green #10b981
text-type-boolean   // Purple #a855f7
text-type-object    // Orange #f97316
text-type-array     // Pink #ec4899

// With backgrounds
bg-type-string-light dark:bg-type-string-dark
```

---

## Spacing Scale (Tailwind)

| Token | Value | Tailwind | Common Use |
|-------|-------|----------|------------|
| xs | 4px | `gap-1` `p-1` | Icon gaps |
| sm | 8px | `gap-2` `p-2` | Tight padding |
| md | 12px | `gap-3` `p-3` | Component spacing |
| base | 16px | `gap-4` `p-4` | Default spacing |
| lg | 24px | `gap-6` `p-6` | Section spacing |
| xl | 32px | `gap-8` `p-8` | Large gaps |

---

## Tree Depth Styling

```tsx
// Copy-paste this helper function
export function getDepthStyles(level: number) {
  const styles = {
    0: 'pl-0 bg-background border-l-0',
    1: 'pl-6 bg-muted/30 border-l-2 border-primary/20',
    2: 'pl-12 bg-muted/50 border-l-2 border-primary/40',
    3: 'pl-18 bg-accent/30 border-l-2 border-primary/60 border-l-amber-500',
  };
  return styles[level as keyof typeof styles] || styles[3];
}
```

---

## Icon Mapping (Lucide React)

```tsx
import {
  // Property Types
  Type,          // string
  Hash,          // number
  ToggleLeft,    // boolean
  Braces,        // object
  Brackets,      // array

  // Actions
  Plus,          // add
  Pencil,        // edit
  Trash2,        // delete
  Save,          // save
  Download,      // export
  Upload,        // import
  Copy,          // copy

  // UI Controls
  ChevronRight,  // collapsed
  ChevronDown,   // expanded
  X,             // close

  // Status
  CheckCircle2,  // success
  AlertCircle,   // error
  AlertTriangle, // warning
  Info,          // info
  Loader2,       // loading
} from 'lucide-react';
```

---

## Common Tailwind Patterns

### Flex Row with Gap
```tsx
className="flex items-center gap-2"
```

### Form Field Container
```tsx
className="space-y-2"
```

### Section Spacing
```tsx
className="space-y-4"
```

### Grid Two Columns
```tsx
className="grid grid-cols-2 gap-4"
```

### Hover Effect
```tsx
className="hover:bg-accent/50 transition-colors"
```

### Focus Ring (Accessibility)
```tsx
className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
```

### Disabled State
```tsx
className={cn(
  "transition-opacity",
  disabled && "opacity-50 cursor-not-allowed"
)}
```

---

## State Management (Zustand)

### Access State
```tsx
import { useSchemaStore } from '@/store/schemaStore';

const { properties, schemaName, isDirty } = useSchemaStore();
```

### Modify State
```tsx
const { addProperty, updateProperty, deleteProperty } = useSchemaStore();

addProperty({
  name: 'newProperty',
  type: 'string',
  required: false,
  constraints: {},
});
```

---

## Validation Pattern

```tsx
import { validateSchema } from '@/lib/validation';

const schemaJSON = generateSchemaJSON(properties);
const { isValid, errors } = validateSchema(schemaJSON);

if (!isValid) {
  console.error('Schema validation errors:', errors);
}
```

---

## ARIA Patterns (Copy-Paste)

### Tree Node
```tsx
<div
  role="treeitem"
  aria-expanded={isExpanded}
  aria-level={level}
  aria-setsize={siblings.length}
  aria-posinset={index + 1}
  tabIndex={isSelected ? 0 : -1}
>
```

### Button with Icon
```tsx
<Button aria-label="Edit property">
  <Pencil className="h-4 w-4" />
  <span className="sr-only">Edit property</span>
</Button>
```

### Input with Error
```tsx
<Input
  id="name"
  aria-required="true"
  aria-invalid={hasError}
  aria-describedby={hasError ? "name-error" : undefined}
/>
{hasError && (
  <p id="name-error" role="alert" className="text-destructive text-sm">
    {errorMessage}
  </p>
)}
```

### Dialog
```tsx
<Dialog>
  <DialogContent
    role="dialog"
    aria-labelledby="dialog-title"
    aria-describedby="dialog-description"
  >
    <DialogTitle id="dialog-title">Add Property</DialogTitle>
    <DialogDescription id="dialog-description">
      Define the property name, type, and constraints
    </DialogDescription>
  </DialogContent>
</Dialog>
```

---

## Keyboard Shortcuts (Implement These)

| Key | Action | Implementation |
|-----|--------|----------------|
| `Tab` | Navigate forward | Default browser behavior |
| `Shift + Tab` | Navigate backward | Default browser behavior |
| `↑ / ↓` | Navigate tree nodes | Custom handler in `useTreeKeyboard` |
| `→` | Expand node | Custom handler |
| `←` | Collapse node | Custom handler |
| `Enter` | Edit selected node | Custom handler |
| `Delete` | Delete selected node | Custom handler |
| `Esc` | Close dialog | Default shadcn/ui behavior |
| `Ctrl/Cmd + S` | Save schema | Custom handler |

```tsx
// Keyboard handler example
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 's') {
      e.preventDefault();
      handleSave();
    }
  };
  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, []);
```

---

## Testing Quick Commands

```bash
# Install dependencies
npm install

# Run dev server
npm run dev

# Type check
npm run build

# Lint
npm run lint

# Test (if configured)
npm run test
```

---

## Common Mistakes to Avoid

### ❌ Don't Do This
```tsx
// Missing label
<Input placeholder="Enter name" />

// Icon-only button without label
<Button><Pencil /></Button>

// Color-only information
<div className="text-red-500">Error</div>

// Hardcoded level styles
<div className="pl-48">
```

### ✅ Do This Instead
```tsx
// Proper label
<Label htmlFor="name">Name</Label>
<Input id="name" placeholder="e.g., customer" />

// Icon button with label
<Button aria-label="Edit property">
  <Pencil />
  <span className="sr-only">Edit</span>
</Button>

// Error with icon + text
<div className="flex items-center gap-1 text-destructive">
  <AlertCircle className="h-4 w-4" />
  <span>Error message</span>
</div>

// Dynamic depth styles
<div className={getDepthStyles(level)}>
```

---

## Property Type Defaults

| Type | Default Constraints | Rationale |
|------|-------------------|-----------|
| `string` | No format, no pattern | Prevent false positives |
| `number` | No min/max | Allow any number |
| `boolean` | None | N/A |
| `object` | Empty children array | Allow nesting |
| `array` | Empty children array | Allow nesting |

---

## File Structure (Quick Reference)

```
src/
├── components/
│   ├── ui/                  # shadcn/ui components (auto-generated)
│   ├── schema-editor/
│   │   ├── SchemaTree.tsx
│   │   ├── SchemaTreeNode.tsx
│   │   ├── PropertyEditor.tsx
│   │   ├── StringConstraints.tsx
│   │   ├── NumberConstraints.tsx
│   │   └── ...
│   ├── preview/
│   │   └── JSONPreviewPanel.tsx
│   ├── templates/
│   │   └── TemplateSelector.tsx
│   └── layout/
│       ├── Header.tsx
│       └── MainLayout.tsx
├── store/
│   └── schemaStore.ts       # Zustand state
├── lib/
│   ├── utils.ts             # cn() helper
│   └── validation.ts        # AJV validation
├── hooks/
│   ├── useAutoSave.ts
│   └── useTreeKeyboard.ts
└── types/
    ├── schema.ts
    └── property.ts
```

---

## Useful VS Code Snippets

Add to `.vscode/snippets.json`:

```json
{
  "Schema Property Type": {
    "prefix": "sprop",
    "body": [
      "interface ${1:PropertyName} {",
      "  id: string;",
      "  name: string;",
      "  type: 'string' | 'number' | 'boolean' | 'object' | 'array';",
      "  required: boolean;",
      "  constraints: Record<string, any>;",
      "  children?: ${1:PropertyName}[];",
      "  level: number;",
      "}"
    ]
  },
  "ARIA Tree Item": {
    "prefix": "atree",
    "body": [
      "<div",
      "  role=\"treeitem\"",
      "  aria-expanded={${1:isExpanded}}",
      "  aria-level={${2:level}}",
      "  aria-setsize={${3:siblings.length}}",
      "  aria-posinset={${4:index + 1}}",
      "  tabIndex={${5:isSelected} ? 0 : -1}",
      ">",
      "  ${0}",
      "</div>"
    ]
  }
}
```

---

## Emergency Debugging

### Tree Not Updating?
1. Check Zustand store: `console.log(useSchemaStore.getState())`
2. Verify property IDs are unique
3. Check for mutation (should use spread operator)

### Focus Not Working?
1. Verify `tabIndex` is set correctly
2. Check for CSS `pointer-events: none`
3. Ensure element is not `display: none` when focusing

### Validation Errors?
1. Check AJV validation: `validateSchema(schemaJSON)`
2. Verify JSON structure matches JSON Schema spec
3. Console log the generated schema

### Keyboard Navigation Broken?
1. Check event listeners are attached
2. Verify `e.preventDefault()` is called
3. Test focus indicators are visible

---

**Print and Keep This Card Handy!**

For full details, see:
- [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)
- [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)
- [ACCESSIBILITY_CHECKLIST.md](./ACCESSIBILITY_CHECKLIST.md)

---

**Version:** 1.0
**Date:** 2025-11-02
