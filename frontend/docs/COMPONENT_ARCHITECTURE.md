# JSON Schema Builder - Component Architecture

**Visual guide to component hierarchy and data flow**

---

## Application Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│                          HEADER (Header.tsx)                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ [Logo] JSON Schema Builder  [Templates▾] [Save] [Export]    │   │
│  │                              ^             ^        ^         │   │
│  │                              │             │        │         │   │
│  │                           Zustand Store Actions               │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│                      MAIN LAYOUT (MainLayout.tsx)                   │
│  ┌────────────────────────────┬──────────────────────────────────┐  │
│  │  SCHEMA TREE PANEL         │  JSON PREVIEW PANEL              │  │
│  │  (SchemaTree.tsx)          │  (JSONPreviewPanel.tsx)          │  │
│  │                            │                                  │  │
│  │  ┌──────────────────────┐  │  ┌────────────────────────────┐  │  │
│  │  │ [+ Add Property]     │  │  │ [Schema JSON | Sample]     │  │  │
│  │  ├──────────────────────┤  │  ├────────────────────────────┤  │  │
│  │  │                      │  │  │                            │  │  │
│  │  │ SchemaTreeNode (x3)  │◄─┼──│ ReactJsonView              │  │  │
│  │  │   ├─ Child Node      │  │  │                            │  │  │
│  │  │   └─ Child Node      │  │  │ Validation Status (AJV)    │  │  │
│  │  │                      │  │  │                            │  │  │
│  │  └──────────────────────┘  │  └────────────────────────────┘  │  │
│  │           ▲                │              ▲                   │  │
│  │           │                │              │                   │  │
│  │           └────────────────┴──────────────┘                   │  │
│  │                    Zustand Store                              │  │
│  │              (schemaStore.ts)                                 │  │
│  └────────────────────────────┴──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

DIALOGS (rendered at root level):
┌─────────────────────────────────┐
│ PropertyEditor.tsx              │
│  ├─ StringConstraints.tsx       │
│  ├─ NumberConstraints.tsx       │
│  └─ BooleanConstraints.tsx      │
└─────────────────────────────────┘
┌─────────────────────────────────┐
│ TemplateSelector.tsx            │
│  └─ TemplateCard (x multiple)   │
└─────────────────────────────────┘
```

---

## Component Hierarchy Tree

```
App.tsx
├── MainLayout.tsx
│   ├── Header.tsx
│   │   ├── SchemaNameInput
│   │   ├── TemplatesDropdown
│   │   │   └── TemplateSelector (Dialog)
│   │   │       └── TemplateCard[]
│   │   ├── SaveButton
│   │   ├── ExportDropdown
│   │   └── ImportButton
│   │
│   ├── SchemaTree.tsx
│   │   ├── AddPropertyButton
│   │   └── SchemaTreeNode (recursive)
│   │       ├── TypeIcon
│   │       ├── PropertyName
│   │       ├── TypeBadge
│   │       ├── RequiredBadge
│   │       ├── ActionButtons
│   │       │   ├── EditButton → PropertyEditor (Dialog)
│   │       │   ├── DeleteButton
│   │       │   └── AddChildButton
│   │       └── SchemaTreeNode[] (children)
│   │
│   └── JSONPreviewPanel.tsx
│       ├── Tabs
│       │   ├── SchemaJSONTab
│       │   │   ├── ValidationStatus
│       │   │   ├── ReactJsonView
│       │   │   └── CopyButton
│       │   └── SampleDataTab
│       │       └── ReactJsonView
│       └── ExportOptions
│
├── PropertyEditor.tsx (Dialog)
│   ├── PropertyNameInput
│   ├── TypeSelector
│   ├── DescriptionTextarea
│   ├── RequiredSwitch
│   ├── StringConstraints (conditional)
│   │   ├── FormatSelector
│   │   ├── PatternInput
│   │   ├── MinLengthInput
│   │   ├── MaxLengthInput
│   │   ├── EnumTextarea
│   │   └── DefaultValueInput
│   ├── NumberConstraints (conditional)
│   │   ├── MinimumInput
│   │   ├── MaximumInput
│   │   ├── MultipleOfInput
│   │   └── DefaultValueInput
│   └── BooleanConstraints (conditional)
│       └── DefaultValueCheckbox
│
└── ToastProvider
    └── Toast (shadcn/ui)
```

---

## Data Flow Diagram

### Adding a Property

```
User Action: Click "Add Property"
        │
        ▼
┌───────────────────────┐
│ SchemaTree.tsx        │
│ onClick={() =>        │
│   setDialogOpen(true) │
│ }                     │
└───────┬───────────────┘
        │
        ▼
┌───────────────────────────────────┐
│ PropertyEditor.tsx (Dialog opens) │
│ - Autofocus on name input         │
│ - Default type: "string"          │
│ - Required: false                 │
└───────┬───────────────────────────┘
        │
        │ User fills form
        ▼
┌────────────────────────────────────┐
│ Form Submit Handler                │
│ onSubmit={(data) => {              │
│   addProperty(data, parentId)      │
│ }}                                 │
└────────┬───────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│ Zustand Store (schemaStore.ts)    │
│ addProperty: (prop, parentId) => { │
│   - Generate ID                    │
│   - Calculate level                │
│   - Validate max depth             │
│   - Update state                   │
│   - Set isDirty = true             │
│ }                                  │
└────────┬───────────────────────────┘
         │
         ├──────────────────────┬────────────────────┐
         ▼                      ▼                    ▼
┌────────────────┐   ┌──────────────────┐   ┌─────────────────┐
│ SchemaTree     │   │ JSONPreviewPanel │   │ Header          │
│ - Re-renders   │   │ - Regenerates    │   │ - Save enabled  │
│ - Shows new    │   │   schema JSON    │   │   (isDirty)     │
│   node         │   │ - Validates      │   │                 │
│ - Expands      │   │ - Updates view   │   │                 │
└────────────────┘   └──────────────────┘   └─────────────────┘
```

---

### Editing a Property

```
User Action: Click "Edit" icon on tree node
        │
        ▼
┌───────────────────────────────────────┐
│ SchemaTreeNode.tsx                    │
│ onClick={() => {                      │
│   selectProperty(property.id)         │
│   openPropertyEditor(property)        │
│ }}                                    │
└───────┬───────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────┐
│ PropertyEditor.tsx (Dialog opens)      │
│ - Pre-filled with existing values      │
│ - Mode: "edit"                         │
└────────┬───────────────────────────────┘
         │
         │ User modifies values
         ▼
┌─────────────────────────────────────────┐
│ Form Submit Handler                     │
│ onSubmit={(data) => {                   │
│   updateProperty(property.id, data)     │
│ }}                                      │
└─────────┬───────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────┐
│ Zustand Store (schemaStore.ts)          │
│ updateProperty: (id, updates) => {       │
│   - Find property in tree                │
│   - Merge updates                        │
│   - Set isDirty = true                   │
│   - Trigger re-render                    │
│ }                                        │
└──────────┬───────────────────────────────┘
           │
           ├────────────────────┬────────────────────┐
           ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐
│ SchemaTreeNode   │  │ JSONPreviewPanel │  │ Header          │
│ - Updates        │  │ - Re-validates   │  │ - Save enabled  │
│   display        │  │ - Updates JSON   │  │                 │
└──────────────────┘  └──────────────────┘  └─────────────────┘
```

---

### Deleting a Property

```
User Action: Click "Delete" icon
        │
        ▼
┌──────────────────────────────────────┐
│ Confirmation Dialog                  │
│ "Delete 'propertyName'?"             │
│ (If has children: warn about count)  │
└────────┬─────────────────────────────┘
         │ User confirms
         ▼
┌─────────────────────────────────────────┐
│ Zustand Store (schemaStore.ts)          │
│ deleteProperty: (id) => {               │
│   - Remove from tree                    │
│   - Remove children (if any)            │
│   - Clear selection if was selected     │
│   - Set isDirty = true                  │
│ }                                       │
└─────────┬───────────────────────────────┘
          │
          ├────────────────────┬────────────────────┐
          ▼                    ▼                    ▼
┌───────────────────┐  ┌──────────────────┐  ┌─────────────────┐
│ SchemaTree        │  │ JSONPreviewPanel │  │ Toast           │
│ - Removes node    │  │ - Re-validates   │  │ "Property       │
│   (fade out)      │  │ - Updates JSON   │  │  deleted"       │
│ - Focus prev      │  │                  │  │                 │
└───────────────────┘  └──────────────────┘  └─────────────────┘
```

---

## State Management (Zustand Store)

### Store Structure

```typescript
interface SchemaState {
  // Data
  schemaName: string;
  properties: Property[];
  selectedPropertyId: string | null;
  expandedNodeIds: Set<string>;
  isDirty: boolean;

  // Actions
  setSchemaName: (name: string) => void;
  addProperty: (property, parentId?) => void;
  updateProperty: (id, updates) => void;
  deleteProperty: (id) => void;
  selectProperty: (id) => void;
  toggleNode: (id) => void;
  loadTemplate: (properties, name) => void;
  reset: () => void;
  markClean: () => void;
}
```

### Store Subscribers

```
┌──────────────────────────────────────┐
│         Zustand Store                │
│       (schemaStore.ts)               │
└──────────┬───────────────────────────┘
           │
           ├─────────────────┬──────────────────┬──────────────────┐
           ▼                 ▼                  ▼                  ▼
┌──────────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐
│ SchemaTree       │  │ JSONPreview   │  │ Header       │  │ AutoSave     │
│                  │  │               │  │              │  │  Hook        │
│ const {          │  │ const {       │  │ const {      │  │              │
│   properties,    │  │   properties  │  │   isDirty,   │  │ useEffect(() │
│   expandedIds,   │  │ } = store();  │  │   name       │  │   => {       │
│   selectedId     │  │               │  │ } = store(); │  │   if(isDirty)│
│ } = store();     │  │ regenerate    │  │              │  │     save()   │
│                  │  │   schemaJSON  │  │ Enable/      │  │ }, [isDirty])│
└──────────────────┘  └───────────────┘  │ disable Save │  └──────────────┘
                                         └──────────────┘
```

---

## shadcn/ui Component Mapping

### Core UI Components

| UI Element | shadcn/ui Component | Custom Logic |
|------------|-------------------|--------------|
| **Tree Node** | `Button` (icons) + custom wrapper | Tree traversal, depth calculation |
| **Property Editor** | `Dialog` + `Input` + `Select` + `Switch` | Form validation, constraint logic |
| **Type Selector** | `Select` with custom rendering | Icon + text items |
| **Constraint Editors** | `Input` + `Textarea` + `Select` | Conditional rendering by type |
| **Toolbar Dropdown** | `DropdownMenu` | Template loading, export options |
| **JSON Preview** | `Tabs` + `@microlink/react-json-view` | Schema generation, AJV validation |
| **Validation Status** | `Alert` | Real-time validation feedback |
| **Toast Notifications** | `Toast` (shadcn/ui) | Success/error messages |
| **Tooltips** | `Tooltip` | Help text, disabled button reasons |
| **Template Cards** | `Card` | Template metadata display |
| **Confirmation** | `AlertDialog` | Destructive action confirmation |

---

## Key Integration Points

### 1. AJV Validation Integration

```
┌──────────────────────────────────┐
│ JSONPreviewPanel.tsx             │
│                                  │
│ const schemaJSON = useMemo(() => │
│   generateSchemaJSON(properties) │
│ , [properties]);                 │
│                                  │
│ const validation = useMemo(() => │
│   validateSchema(schemaJSON)     │───┐
│ , [schemaJSON]);                 │   │
└──────────────────────────────────┘   │
                                       │
                                       ▼
                         ┌──────────────────────────┐
                         │ lib/validation.ts        │
                         │                          │
                         │ import Ajv from 'ajv';   │
                         │ const ajv = new Ajv();   │
                         │                          │
                         │ export function          │
                         │   validateSchema(schema) │
                         │ {                        │
                         │   try {                  │
                         │     ajv.compile(schema); │
                         │     return { valid: true}│
                         │   } catch (e) {          │
                         │     return {             │
                         │       valid: false,      │
                         │       errors: [...]      │
                         │     }                    │
                         │   }                      │
                         │ }                        │
                         └──────────────────────────┘
```

---

### 2. Keyboard Navigation Integration

```
┌──────────────────────────────────────┐
│ SchemaTree.tsx                       │
│                                      │
│ useTreeKeyboard(properties)          │───┐
│                                      │   │
│ <div onKeyDown={handleKeyDown}>     │   │
│   {properties.map(prop =>           │   │
│     <SchemaTreeNode                 │   │
│       tabIndex={selected ? 0 : -1}  │   │
│     />                               │   │
│   )}                                 │   │
│ </div>                               │   │
└──────────────────────────────────────┘   │
                                           │
                                           ▼
                         ┌──────────────────────────────┐
                         │ hooks/useTreeKeyboard.ts     │
                         │                              │
                         │ export function              │
                         │   useTreeKeyboard(props) {   │
                         │                              │
                         │   useEffect(() => {          │
                         │     const handler = (e) => { │
                         │       switch(e.key) {        │
                         │         case 'ArrowDown':    │
                         │           selectNext();      │
                         │         case 'ArrowUp':      │
                         │           selectPrev();      │
                         │         case 'Enter':        │
                         │           editSelected();    │
                         │       }                      │
                         │     };                       │
                         │     window.addEventListener( │
                         │       'keydown', handler     │
                         │     );                       │
                         │   }, []);                    │
                         │ }                            │
                         └──────────────────────────────┘
```

---

### 3. Auto-Save Integration

```
┌──────────────────────────────────────┐
│ App.tsx                              │
│                                      │
│ useAutoSave()                        │───┐
│                                      │   │
└──────────────────────────────────────┘   │
                                           │
                                           ▼
                         ┌──────────────────────────────────┐
                         │ hooks/useAutoSave.ts             │
                         │                                  │
                         │ export function useAutoSave() {  │
                         │   const { name, props, isDirty } │
                         │     = useSchemaStore();          │
                         │                                  │
                         │   useEffect(() => {              │
                         │     if (!isDirty) return;        │
                         │                                  │
                         │     const save = () => {         │
                         │       localStorage.setItem(      │
                         │         'schema-draft',          │
                         │         JSON.stringify({         │
                         │           name, props,           │
                         │           timestamp: Date.now()  │
                         │         })                       │
                         │       );                         │
                         │     };                           │
                         │                                  │
                         │     const interval =             │
                         │       setInterval(save, 30000);  │
                         │                                  │
                         │     return () =>                 │
                         │       clearInterval(interval);   │
                         │   }, [name, props, isDirty]);    │
                         │ }                                │
                         └──────────────────────────────────┘
```

---

## Responsive Layout Adaptation

### Desktop (≥1024px)

```
┌────────────────────────────────────────────────────────┐
│                      HEADER                            │
├────────────────────────┬───────────────────────────────┤
│                        │                               │
│   SCHEMA TREE (50%)    │   JSON PREVIEW (50%)          │
│                        │                               │
│   Full features        │   Full features               │
│   All actions visible  │   Tabs: Schema / Sample       │
│                        │                               │
└────────────────────────┴───────────────────────────────┘
```

### Tablet (768px-1023px)

```
┌────────────────────────────────────────────────────────┐
│                      HEADER                            │
├────────────────────────────────────────────────────────┤
│                                                        │
│   SCHEMA TREE (100%, scrollable)                       │
│   Actions on hover                                     │
│                                                        │
├────────────────────────────────────────────────────────┤
│                                                        │
│   JSON PREVIEW (100%, below tree)                      │
│   Sticky tabs                                          │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### Mobile (<768px)

```
┌──────────────────────────────────┐
│           HEADER                 │
│  (Hamburger menu for actions)    │
├──────────────────────────────────┤
│ [Editor Tab] [Preview Tab]       │
├──────────────────────────────────┤
│                                  │
│  TAB CONTENT (100%)              │
│  - Editor: Tree view             │
│  - Preview: JSON view            │
│                                  │
│  Touch-optimized (44px targets)  │
│                                  │
└──────────────────────────────────┘
```

---

## Performance Considerations

### Tree Virtualization (Optional, if >50 properties)

```
┌─────────────────────────────────────┐
│ SchemaTree.tsx                      │
│                                     │
│ import { useVirtualizer }           │
│   from '@tanstack/react-virtual';   │
│                                     │
│ const flatProperties =              │
│   flattenTree(properties);          │
│                                     │
│ const virtualizer = useVirtualizer({│
│   count: flatProperties.length,     │
│   getScrollElement: () => parentRef,│
│   estimateSize: () => 48, // px     │
│   overscan: 5                       │
│ });                                 │
│                                     │
│ // Render only visible items        │
│ virtualizer.getVirtualItems()       │
│   .map(item => <SchemaTreeNode />)  │
└─────────────────────────────────────┘
```

### Memoization Strategy

```typescript
// Expensive calculations
const schemaJSON = useMemo(
  () => generateSchemaJSON(properties),
  [properties]
);

const validation = useMemo(
  () => validateSchema(schemaJSON),
  [schemaJSON]
);

// Component memoization
export const SchemaTreeNode = memo(
  ({ property, ...props }) => { /* ... */ },
  (prev, next) => prev.property.id === next.property.id
);
```

---

## Error Boundaries

```
App.tsx
├── ErrorBoundary (Top Level)
│   ├── MainLayout
│   │   ├── ErrorBoundary (Tree Panel)
│   │   │   └── SchemaTree
│   │   │       └── SchemaTreeNode[]
│   │   │
│   │   └── ErrorBoundary (Preview Panel)
│   │       └── JSONPreviewPanel
│   │
│   └── ErrorBoundary (Dialogs)
│       ├── PropertyEditor
│       └── TemplateSelector
```

---

## Testing Architecture

### Unit Tests

```
src/
├── store/
│   └── schemaStore.test.ts       # Zustand actions
├── lib/
│   ├── validation.test.ts        # AJV integration
│   └── utils.test.ts             # Helper functions
└── components/
    └── schema-editor/
        ├── SchemaTreeNode.test.tsx    # Component rendering
        └── PropertyEditor.test.tsx    # Form validation
```

### Integration Tests

```
tests/
├── tree-operations.test.tsx      # Add/edit/delete flows
├── keyboard-navigation.test.tsx  # Arrow keys, Enter, Delete
└── template-loading.test.tsx     # Load and modify templates
```

### Accessibility Tests

```
tests/
├── a11y/
│   ├── keyboard.test.tsx         # Full keyboard navigation
│   ├── screen-reader.test.tsx    # ARIA attributes
│   └── contrast.test.tsx         # Color contrast ratios
```

---

## Deployment Architecture

```
┌────────────────────────────────────────┐
│          Vite Build Process            │
│                                        │
│  src/ → dist/                          │
│  ├── index.html                        │
│  ├── assets/                           │
│  │   ├── index-[hash].js (minified)    │
│  │   └── index-[hash].css (purged)     │
│  └── ...                               │
└────────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────────┐
│       Static File Server               │
│       (Nginx / Vercel / Netlify)       │
│                                        │
│  Serves: dist/                         │
│  Routes: /* → index.html (SPA)         │
└────────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────────┐
│         Backend API                    │
│         (FastAPI)                      │
│                                        │
│  POST /api/v1/schemas (save)           │
│  GET  /api/v1/schemas (list)           │
│  GET  /api/v1/schemas/:id (load)       │
│  GET  /api/v1/templates (list)         │
└────────────────────────────────────────┘
```

---

## Summary

This component architecture provides:

1. **Clear separation of concerns** (UI, state, validation, API)
2. **Unidirectional data flow** (Zustand → Components)
3. **Performance optimization** (memoization, virtualization)
4. **Accessibility first** (keyboard, ARIA, focus management)
5. **Developer experience** (TypeScript, shadcn/ui, clear patterns)

**Next Steps:**
1. Set up folder structure per this architecture
2. Implement Zustand store first
3. Build SchemaTreeNode (recursive component)
4. Add PropertyEditor dialog
5. Integrate JSONPreviewPanel
6. Test keyboard navigation and accessibility

---

**Document Version:** 1.0
**Last Updated:** 2025-11-02
**Designed by:** Aura, UI/UX Designer Agent
