# JSON Schema Builder - Design System & UI/UX Specification

**Version:** 1.0
**Last Updated:** 2025-11-02
**Target:** React + TypeScript + Vite + Tailwind CSS + shadcn/ui

---

## Table of Contents

1. [Primary Job-to-be-Done (JTBD)](#1-primary-job-to-be-done-jtbd)
2. [Optimal Task Flow Analysis](#2-optimal-task-flow-analysis)
3. [Layout & Information Architecture](#3-layout--information-architecture)
4. [Visual Hierarchy](#4-visual-hierarchy)
5. [Component Specifications](#5-component-specifications)
6. [Color System & Theming](#6-color-system--theming)
7. [Typography Scale](#7-typography-scale)
8. [Spacing & Layout Grid](#8-spacing--layout-grid)
9. [Iconography](#9-iconography)
10. [Accessibility Requirements](#10-accessibility-requirements)
11. [Interaction Patterns](#11-interaction-patterns)
12. [Micro-interactions & Animations](#12-micro-interactions--animations)
13. [Error Prevention & Recovery](#13-error-prevention--recovery)
14. [Implementation Notes](#14-implementation-notes)
15. [User Flow Diagrams](#15-user-flow-diagrams)

---

## 1. Primary Job-to-be-Done (JTBD)

### When...
A developer or technical user needs to define a structured data extraction schema for documents (invoices, resumes, forms)

### I want to...
Visually create and edit JSON Schema specifications without memorizing syntax rules or worrying about validation errors

### So I can...
- Configure document extraction pipelines quickly and accurately
- Ensure data structure consistency across document types
- Reduce implementation errors and debugging time
- Reuse and adapt existing schema templates efficiently

### Core Functionality

- **Visual Schema Tree Editor** - Hierarchical representation of schema structure (max 3 nesting levels)
- **Type-Safe Property Definition** - Select from string, number, boolean, object, array with appropriate constraints
- **Real-Time Validation** - Immediate feedback on schema validity using AJV
- **Live JSON Preview** - Side-by-side view of generated JSON Schema
- **Template Management** - Load, modify, save pre-built schemas (Invoice, Resume)
- **Constraint Configuration** - Format, pattern, min/max, enum, default values per property type
- **Required Field Management** - Mark properties as required/optional
- **Export/Import** - Download JSON, upload existing schemas

---

## 2. Optimal Task Flow Analysis

### Creating a Schema from Scratch

**Trigger:** User clicks "New Schema" or starts with blank canvas

**Step 1:** Name the schema
- UI: Single text input with autofocus, "Create" button
- Validation: Non-empty name required

**Step 2:** Add root-level properties
- Action: Click "Add Property" button
- UI: Opens Property Editor dialog
- Elements: Name input, Type selector, Required toggle, Constraint fields (conditional)

**Step 3:** Define property details
- Input: Property name (validates for valid JSON keys)
- Select: Type (string/number/boolean/object/array)
- Configure: Type-specific constraints appear dynamically
- Toggle: Required field checkbox

**Step 4:** Add nested properties (for object/array types)
- Action: Click "Add Child" icon on object/array nodes
- Validation: Prevent adding children beyond level 3
- Feedback: Visual indicator shows current depth, disable if max depth reached

**Step 5:** Review live preview
- Real-time: JSON preview updates on every change
- Validation: AJV validates schema, shows errors inline

**Step 6:** Save or export
- Save: Store to backend API with metadata
- Export: Download as .json file

**Goal Achieved:** Valid JSON Schema ready for use in extraction pipeline

---

### Loading and Modifying a Template

**Trigger:** User selects "Templates" from toolbar

**Step 1:** Browse template gallery
- UI: Card-based grid showing Invoice, Resume, custom templates
- Preview: Hover shows schema structure summary

**Step 2:** Confirm template load
- Condition: If unsaved work exists, show confirmation dialog
- Action: Load selected template into editor

**Step 3:** Modify template
- Edit existing properties (click tree node → Edit dialog)
- Add new properties (follows standard flow)
- Delete properties (with confirmation for nodes with children)

**Step 4:** Save as new schema or update template
- Save As: New schema name, preserves original template
- Update: Overwrites template (if user has permission)

**Goal Achieved:** Customized schema based on proven template

---

### Adding Nested Objects with Validation

**Trigger:** User wants to add nested structure (e.g., invoice.lineItems.productDetails)

**Step 1:** Add object/array property at root level
- Name: "lineItems", Type: "array"

**Step 2:** Add child to lineItems
- Click "Add Child" on lineItems node
- System enforces: Currently at Level 1 → can add Level 2

**Step 3:** Add child to Level 2 object
- Click "Add Child" on Level 2 node
- System enforces: Currently at Level 2 → can add Level 3

**Step 4:** Attempt to add Level 4 (prevented)
- Click "Add Child" on Level 3 node
- Feedback: Button disabled + tooltip "Maximum nesting depth (3 levels) reached"
- Visual: Level 3 nodes have subtle warning background

**Goal Achieved:** User understands nesting limits before encountering errors

---

## 3. Layout & Information Architecture

### Overall Application Layout

```
┌────────────────────────────────────────────────────────────────┐
│  HEADER (fixed, h-16)                                          │
│  [Logo] JSON Schema Builder    [Templates ▾] [Save] [Export]  │
└────────────────────────────────────────────────────────────────┘
┌──────────────────────────┬─────────────────────────────────────┐
│                          │                                     │
│  SCHEMA TREE PANEL       │  LIVE PREVIEW PANEL                 │
│  (Left, 50% width)       │  (Right, 50% width)                 │
│  ┌────────────────────┐  │  ┌───────────────────────────────┐  │
│  │ Schema: "Invoice"  │  │  │ [Schema JSON] [Sample Data]   │  │
│  ├────────────────────┤  │  ├───────────────────────────────┤  │
│  │ + Add Property     │  │  │                               │  │
│  │                    │  │  │  {                            │  │
│  │ ▼ invoiceNumber    │  │  │    "type": "object",          │  │
│  │   Type: string     │  │  │    "properties": {            │  │
│  │   [Edit] [Delete]  │  │  │      "invoiceNumber": {       │  │
│  │                    │  │  │        "type": "string"       │  │
│  │ ▼ customer         │  │  │      },                       │  │
│  │   Type: object     │  │  │      ...                      │  │
│  │   [Edit] [Del] [+] │  │  │    }                          │  │
│  │   ▼ name           │  │  │  }                            │  │
│  │     Type: string   │  │  │                               │  │
│  │                    │  │  │  ✓ Valid Schema               │  │
│  └────────────────────┘  │  └───────────────────────────────┘  │
│                          │                                     │
└──────────────────────────┴─────────────────────────────────────┘
```

### Responsive Breakpoints

| Breakpoint | Layout Behavior |
|------------|-----------------|
| **≥1400px (2xl)** | Default 50/50 split, comfortable spacing |
| **≥1024px (lg)** | 50/50 split, reduced spacing |
| **≥768px (md)** | Vertical stack: Tree on top, Preview below (scrollable) |
| **<768px (sm)** | Vertical stack + Tabs: [Editor] [Preview] for mobile |

### Structure Rationale

**Why 2-Column Grid?**
- Immediate visual feedback reduces errors (Jakob's Law: users spend time on other sites with JSON editors)
- Developers expect side-by-side view from IDEs and code editors
- Reduces cognitive load: no need to switch tabs to validate changes

**Why Fixed Header?**
- Primary actions (Save, Export, Templates) always accessible
- Prevents scrolling frustration during deep tree navigation

---

## 4. Visual Hierarchy

### Nesting Level Representation

**Visual Strategy:** Progressive depth indicators using indentation + subtle background color shifts

```
Level 0 (Root Properties)
├─ Indentation: 0px
├─ Background: bg-background (white/dark)
└─ Border-left: none

  Level 1 (First Nesting)
  ├─ Indentation: 24px
  ├─ Background: bg-muted/30 (very subtle)
  └─ Border-left: 2px border-primary/20

    Level 2 (Second Nesting)
    ├─ Indentation: 48px
    ├─ Background: bg-muted/50
    └─ Border-left: 2px border-primary/40

      Level 3 (Maximum Nesting)
      ├─ Indentation: 72px
      ├─ Background: bg-accent/30
      └─ Border-left: 2px border-primary/60
      └─ Warning: Amber border when attempting to add children
```

### Property Type Visual Differentiation

**Icon + Color Strategy:**

| Type | Icon (Lucide) | Color | Background Badge |
|------|---------------|-------|------------------|
| **string** | `Type` | `text-blue-600` | `bg-blue-50 dark:bg-blue-950` |
| **number** | `Hash` | `text-green-600` | `bg-green-50 dark:bg-green-950` |
| **boolean** | `ToggleLeft` | `text-purple-600` | `bg-purple-50 dark:bg-purple-950` |
| **object** | `Braces` | `text-orange-600` | `bg-orange-50 dark:bg-orange-950` |
| **array** | `Brackets` | `text-pink-600` | `bg-pink-50 dark:bg-pink-950` |

### Required vs. Optional Indicators

**Visual Treatment:**

- **Required Fields:**
  - Red asterisk `*` after property name
  - Badge: `<Badge variant="destructive" size="sm">Required</Badge>`
  - Higher visual weight (font-semibold)

- **Optional Fields:**
  - No asterisk
  - Badge: `<Badge variant="outline" size="sm">Optional</Badge>`
  - Normal font weight

### Level Depth Indicators

**When approaching max depth:**

- **Level 2 nodes:** Show subtle info icon with tooltip "1 more level available"
- **Level 3 nodes:**
  - Amber left border (`border-l-2 border-amber-500`)
  - "Add Child" button disabled
  - Tooltip: "Maximum nesting depth (3 levels) reached"
  - Background: `bg-amber-50/50 dark:bg-amber-950/20`

---

## 5. Component Specifications

### 5.1 Schema Tree Node

**Component:** `SchemaTreeNode.tsx`

**Functional Purpose:** Represent a single property in the schema tree with expansion, editing, and child management

**Visual Structure:**

```tsx
<div className={cn(
  "group relative rounded-md border p-3 transition-colors",
  "hover:bg-accent/50",
  getDepthStyles(level) // Returns indentation and background based on level
)}>
  {/* Left: Expand/Collapse + Type Icon */}
  <div className="flex items-center gap-2">
    {isExpandable && (
      <Button variant="ghost" size="icon" className="h-5 w-5">
        {isExpanded ? <ChevronDown /> : <ChevronRight />}
      </Button>
    )}
    <TypeIcon type={property.type} className="h-4 w-4" />

    {/* Property Name + Required Indicator */}
    <span className={cn(
      "font-mono text-sm",
      property.required && "font-semibold"
    )}>
      {property.name}
      {property.required && <span className="text-destructive ml-1">*</span>}
    </span>

    {/* Type Badge */}
    <Badge variant="secondary" className="ml-2">
      {property.type}
    </Badge>
  </div>

  {/* Right: Action Buttons (visible on hover) */}
  <div className="absolute right-2 top-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
    <Button variant="ghost" size="icon" onClick={onEdit}>
      <Pencil className="h-4 w-4" />
    </Button>
    <Button variant="ghost" size="icon" onClick={onDelete}>
      <Trash2 className="h-4 w-4" />
    </Button>
    {canAddChild && (
      <Button variant="ghost" size="icon" onClick={onAddChild}>
        <Plus className="h-4 w-4" />
      </Button>
    )}
  </div>

  {/* Child Properties (if expanded) */}
  {isExpanded && children.length > 0 && (
    <div className="mt-2 space-y-2 border-l-2 border-primary/20 pl-4">
      {children.map(child => <SchemaTreeNode key={child.id} {...child} />)}
    </div>
  )}
</div>
```

**States:**

1. **Default:**
   - Border: `border-border`
   - Background: Based on depth level
   - Actions hidden

2. **Hover:**
   - Background: `bg-accent/50`
   - Action buttons fade in
   - Cursor: pointer

3. **Expanded:**
   - Icon: `ChevronDown` rotated
   - Children visible with left border connector

4. **Collapsed:**
   - Icon: `ChevronRight`
   - Children hidden

5. **Max Depth Warning (Level 3):**
   - Border: `border-l-2 border-amber-500`
   - Background: `bg-amber-50/50 dark:bg-amber-950/20`
   - Add Child button disabled

6. **Selected/Active:**
   - Border: `border-primary`
   - Background: `bg-primary/10`

**Rationale:**
- Hover-based actions reduce visual clutter (Fitts's Law: larger targets on demand)
- Group indentation visually connects parent-child relationships
- Type badges provide instant recognition without reading code
- Disabled "Add Child" at max depth prevents errors before they occur

---

### 5.2 Property Editor Dialog

**Component:** `PropertyEditorDialog.tsx` (uses shadcn/ui `Dialog`)

**Functional Purpose:** Modal form for creating or editing schema properties

**Layout:**

```tsx
<Dialog>
  <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
    <DialogHeader>
      <DialogTitle>{mode === 'create' ? 'Add Property' : 'Edit Property'}</DialogTitle>
      <DialogDescription>
        Define the property name, type, and constraints
      </DialogDescription>
    </DialogHeader>

    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Property Name */}
      <div className="space-y-2">
        <Label htmlFor="name">
          Property Name <span className="text-destructive">*</span>
        </Label>
        <Input
          id="name"
          placeholder="e.g., invoiceNumber"
          autoFocus
          pattern="^[a-zA-Z_][a-zA-Z0-9_]*$"
          required
        />
        <p className="text-xs text-muted-foreground">
          Valid JSON key (alphanumeric, underscores, no spaces)
        </p>
      </div>

      {/* Type Selector */}
      <div className="space-y-2">
        <Label htmlFor="type">
          Type <span className="text-destructive">*</span>
        </Label>
        <Select value={type} onValueChange={setType}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="string">
              <div className="flex items-center gap-2">
                <Type className="h-4 w-4 text-blue-600" />
                <span>String</span>
              </div>
            </SelectItem>
            <SelectItem value="number">
              <div className="flex items-center gap-2">
                <Hash className="h-4 w-4 text-green-600" />
                <span>Number</span>
              </div>
            </SelectItem>
            {/* ... other types */}
          </SelectContent>
        </Select>
      </div>

      {/* Required Toggle */}
      <div className="flex items-center justify-between rounded-lg border p-4">
        <div className="space-y-0.5">
          <Label htmlFor="required">Required Field</Label>
          <p className="text-xs text-muted-foreground">
            Must be present in extracted data
          </p>
        </div>
        <Switch id="required" checked={required} onCheckedChange={setRequired} />
      </div>

      {/* Conditional Constraint Fields */}
      {type === 'string' && (
        <StringConstraints
          format={format}
          pattern={pattern}
          minLength={minLength}
          maxLength={maxLength}
          enum={enumValues}
          defaultValue={defaultValue}
          onChange={updateConstraints}
        />
      )}

      {type === 'number' && (
        <NumberConstraints
          minimum={minimum}
          maximum={maximum}
          multipleOf={multipleOf}
          defaultValue={defaultValue}
          onChange={updateConstraints}
        />
      )}

      {/* ... other type-specific constraints */}

      {/* Actions */}
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={!isValid}>
          {mode === 'create' ? 'Add Property' : 'Update Property'}
        </Button>
      </DialogFooter>
    </form>
  </DialogContent>
</Dialog>
```

**States:**

1. **Create Mode:**
   - Title: "Add Property"
   - Empty form fields
   - Submit button: "Add Property"

2. **Edit Mode:**
   - Title: "Edit Property"
   - Pre-filled form with existing values
   - Submit button: "Update Property"

3. **Validation Error:**
   - Invalid fields: Red border + error message below
   - Submit button: Disabled
   - Example: "Property name must start with a letter or underscore"

4. **Loading/Submitting:**
   - Submit button: Loading spinner + disabled
   - Form: Semi-transparent overlay prevents interaction

**Rationale:**
- Autofocus on name field reduces clicks (Hick's Law: minimize choices to start)
- Inline validation provides immediate feedback (reduce error correction time)
- Conditional constraint fields prevent information overload (progressive disclosure)
- Switch for "Required" is more intuitive than checkbox for binary state

---

### 5.3 Type-Specific Constraint Editors

**Component:** `StringConstraints.tsx`

**Functional Purpose:** Configure string-specific validation rules

```tsx
<div className="space-y-4 rounded-lg border p-4 bg-muted/30">
  <h4 className="font-medium text-sm">String Constraints</h4>

  {/* Format Selector */}
  <div className="space-y-2">
    <Label htmlFor="format">Format</Label>
    <Select value={format} onValueChange={setFormat}>
      <SelectTrigger>
        <SelectValue placeholder="None" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="">None</SelectItem>
        <SelectItem value="email">Email Address</SelectItem>
        <SelectItem value="date">Date (YYYY-MM-DD)</SelectItem>
        <SelectItem value="uri">URL/URI</SelectItem>
        <SelectItem value="uuid">UUID</SelectItem>
      </SelectContent>
    </Select>
  </div>

  {/* Pattern (Regex) */}
  <div className="space-y-2">
    <Label htmlFor="pattern">Pattern (Regex)</Label>
    <Input
      id="pattern"
      placeholder="^[A-Z]{2}-\d{4}$"
      value={pattern}
      onChange={e => setPattern(e.target.value)}
      className="font-mono text-xs"
    />
    <p className="text-xs text-muted-foreground">
      Optional regular expression for custom validation
    </p>
  </div>

  {/* Length Constraints */}
  <div className="grid grid-cols-2 gap-4">
    <div className="space-y-2">
      <Label htmlFor="minLength">Min Length</Label>
      <Input
        id="minLength"
        type="number"
        min="0"
        placeholder="0"
        value={minLength}
        onChange={e => setMinLength(Number(e.target.value))}
      />
    </div>
    <div className="space-y-2">
      <Label htmlFor="maxLength">Max Length</Label>
      <Input
        id="maxLength"
        type="number"
        min="0"
        placeholder="Unlimited"
        value={maxLength}
        onChange={e => setMaxLength(Number(e.target.value))}
      />
    </div>
  </div>

  {/* Enum Values */}
  <div className="space-y-2">
    <Label htmlFor="enum">Allowed Values (Enum)</Label>
    <Textarea
      id="enum"
      placeholder="Enter one value per line"
      rows={4}
      value={enumValues.join('\n')}
      onChange={e => setEnumValues(e.target.value.split('\n').filter(Boolean))}
    />
    <p className="text-xs text-muted-foreground">
      Restrict to specific values only
    </p>
  </div>

  {/* Default Value */}
  <div className="space-y-2">
    <Label htmlFor="default">Default Value</Label>
    <Input
      id="default"
      placeholder="Optional default"
      value={defaultValue}
      onChange={e => setDefaultValue(e.target.value)}
    />
  </div>
</div>
```

**Component:** `NumberConstraints.tsx`

```tsx
<div className="space-y-4 rounded-lg border p-4 bg-muted/30">
  <h4 className="font-medium text-sm">Number Constraints</h4>

  {/* Min/Max */}
  <div className="grid grid-cols-2 gap-4">
    <div className="space-y-2">
      <Label htmlFor="minimum">Minimum</Label>
      <Input
        id="minimum"
        type="number"
        step="any"
        placeholder="No minimum"
        value={minimum}
        onChange={e => setMinimum(Number(e.target.value))}
      />
    </div>
    <div className="space-y-2">
      <Label htmlFor="maximum">Maximum</Label>
      <Input
        id="maximum"
        type="number"
        step="any"
        placeholder="No maximum"
        value={maximum}
        onChange={e => setMaximum(Number(e.target.value))}
      />
    </div>
  </div>

  {/* Multiple Of */}
  <div className="space-y-2">
    <Label htmlFor="multipleOf">Multiple Of</Label>
    <Input
      id="multipleOf"
      type="number"
      step="any"
      placeholder="Any value"
      value={multipleOf}
      onChange={e => setMultipleOf(Number(e.target.value))}
    />
    <p className="text-xs text-muted-foreground">
      E.g., 0.01 for currency (two decimal places)
    </p>
  </div>

  {/* Default Value */}
  <div className="space-y-2">
    <Label htmlFor="default">Default Value</Label>
    <Input
      id="default"
      type="number"
      step="any"
      placeholder="Optional default"
      value={defaultValue}
      onChange={e => setDefaultValue(Number(e.target.value))}
    />
  </div>
</div>
```

**Rationale:**
- Grouped constraints reduce cognitive load (related fields together)
- Placeholders provide examples (reduce documentation lookups)
- Progressive disclosure: only show relevant constraints per type
- Helper text explains technical concepts (multipleOf, regex)

---

### 5.4 Toolbar

**Component:** `Toolbar.tsx`

**Functional Purpose:** Primary actions for schema management

```tsx
<header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
  <div className="container flex h-16 items-center justify-between px-4">
    {/* Left: Branding */}
    <div className="flex items-center gap-2">
      <Braces className="h-6 w-6 text-primary" />
      <h1 className="text-xl font-bold">JSON Schema Builder</h1>
    </div>

    {/* Center: Schema Name (editable) */}
    <div className="flex items-center gap-2">
      <Input
        value={schemaName}
        onChange={e => setSchemaName(e.target.value)}
        className="w-64 font-mono"
        placeholder="Untitled Schema"
      />
    </div>

    {/* Right: Actions */}
    <div className="flex items-center gap-2">
      {/* Template Selector */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline">
            <FileText className="mr-2 h-4 w-4" />
            Templates
            <ChevronDown className="ml-2 h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel>Load Template</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => loadTemplate('invoice')}>
            <FileText className="mr-2 h-4 w-4" />
            Invoice Schema
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => loadTemplate('resume')}>
            <FileText className="mr-2 h-4 w-4" />
            Resume Schema
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={openTemplateManager}>
            <FolderOpen className="mr-2 h-4 w-4" />
            Manage Templates...
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Save */}
      <Button onClick={handleSave} disabled={!hasChanges || isSaving}>
        {isSaving ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Save className="mr-2 h-4 w-4" />
        )}
        Save
      </Button>

      {/* Export */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export
            <ChevronDown className="ml-2 h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => exportSchema('json')}>
            <FileJson className="mr-2 h-4 w-4" />
            Export as JSON
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => exportSchema('typescript')}>
            <Code className="mr-2 h-4 w-4" />
            Export TypeScript Types
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Import */}
      <Button variant="outline" onClick={handleImport}>
        <Upload className="mr-2 h-4 w-4" />
        Import
      </Button>

      {/* Theme Toggle (optional) */}
      <Button variant="ghost" size="icon" onClick={toggleTheme}>
        <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
        <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
      </Button>
    </div>
  </div>
</header>
```

**States:**

1. **Default:**
   - Save button disabled if no changes
   - All actions accessible

2. **Unsaved Changes:**
   - Save button enabled + primary color
   - Visual indicator (dot) next to schema name

3. **Saving:**
   - Save button: Loading spinner + disabled
   - Success: Toast notification "Schema saved successfully"
   - Error: Toast with error message + retry option

4. **Loading Template:**
   - Confirmation dialog if unsaved changes exist
   - "You have unsaved changes. Continue?" with [Cancel] [Load Template]

**Rationale:**
- Fixed header ensures actions always accessible (reduce scrolling)
- Disabled save button when no changes prevents unnecessary API calls
- Grouped export options reduce toolbar clutter (Hick's Law)
- Visual loading states provide feedback (reduce perceived wait time)

---

### 5.5 JSON Preview Panel

**Component:** `JSONPreviewPanel.tsx`

**Functional Purpose:** Real-time JSON Schema preview with validation feedback

```tsx
<div className="flex h-full flex-col border-l">
  {/* Tab Bar */}
  <Tabs defaultValue="schema" className="flex-1 flex flex-col">
    <TabsList className="w-full justify-start rounded-none border-b bg-muted/30">
      <TabsTrigger value="schema" className="gap-2">
        <Code className="h-4 w-4" />
        Schema JSON
      </TabsTrigger>
      <TabsTrigger value="sample" className="gap-2">
        <FileJson className="h-4 w-4" />
        Sample Data
      </TabsTrigger>
    </TabsList>

    {/* Schema JSON Tab */}
    <TabsContent value="schema" className="flex-1 m-0 p-4 overflow-auto">
      <div className="space-y-4">
        {/* Validation Status */}
        <div className={cn(
          "flex items-center gap-2 rounded-md border p-3",
          isValid
            ? "border-green-500 bg-green-50 dark:bg-green-950/20"
            : "border-destructive bg-destructive/10"
        )}>
          {isValid ? (
            <>
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              <span className="font-medium text-green-900 dark:text-green-100">
                Valid JSON Schema
              </span>
            </>
          ) : (
            <>
              <AlertCircle className="h-5 w-5 text-destructive" />
              <div className="flex-1">
                <p className="font-medium text-destructive">Invalid Schema</p>
                <p className="text-xs text-muted-foreground mt-1">{validationError}</p>
              </div>
            </>
          )}
        </div>

        {/* JSON Display (using react-json-view) */}
        <div className="rounded-md border bg-muted/30 p-4">
          <ReactJsonView
            src={schemaJSON}
            theme={isDarkMode ? "monokai" : "rjv-default"}
            displayDataTypes={false}
            displayObjectSize={false}
            enableClipboard={true}
            collapsed={2}
            name="schema"
          />
        </div>

        {/* Copy Button */}
        <Button
          variant="outline"
          className="w-full"
          onClick={copyToClipboard}
        >
          <Copy className="mr-2 h-4 w-4" />
          Copy JSON to Clipboard
        </Button>
      </div>
    </TabsContent>

    {/* Sample Data Tab */}
    <TabsContent value="sample" className="flex-1 m-0 p-4 overflow-auto">
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Example data that conforms to this schema
        </p>
        <div className="rounded-md border bg-muted/30 p-4">
          <ReactJsonView
            src={sampleData}
            theme={isDarkMode ? "monokai" : "rjv-default"}
            displayDataTypes={false}
            displayObjectSize={false}
            enableClipboard={true}
            collapsed={false}
            name="data"
          />
        </div>
      </div>
    </TabsContent>
  </Tabs>
</div>
```

**States:**

1. **Valid Schema:**
   - Green checkmark icon
   - "Valid JSON Schema" message
   - JSON displayed with syntax highlighting

2. **Invalid Schema:**
   - Red alert icon
   - Error message from AJV validation
   - JSON still displayed (for debugging)

3. **Empty Schema:**
   - Placeholder message: "Add properties to see JSON Schema"

4. **Copy Success:**
   - Toast notification: "Copied to clipboard"
   - Button momentarily shows checkmark

**Rationale:**
- Real-time validation prevents accumulation of errors
- Syntax highlighting improves readability (reduce cognitive load)
- Collapsible JSON tree allows quick navigation of large schemas
- Sample data tab helps users understand schema usage

---

### 5.6 Template Selector

**Component:** `TemplateSelector.tsx` (Dialog with card grid)

**Functional Purpose:** Browse and load pre-built schema templates

```tsx
<Dialog>
  <DialogContent className="max-w-4xl">
    <DialogHeader>
      <DialogTitle>Schema Templates</DialogTitle>
      <DialogDescription>
        Start with a pre-built schema or create from scratch
      </DialogDescription>
    </DialogHeader>

    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 py-4">
      {/* Blank Template */}
      <Card className="cursor-pointer hover:border-primary transition-colors" onClick={createBlank}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FilePlus className="h-5 w-5" />
            Blank Schema
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Start with an empty schema
          </p>
        </CardContent>
      </Card>

      {/* Invoice Template */}
      <Card className="cursor-pointer hover:border-primary transition-colors" onClick={() => loadTemplate('invoice')}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Invoice
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-3">
            Invoice number, dates, customer, line items, totals
          </p>
          <div className="flex flex-wrap gap-1">
            <Badge variant="secondary" className="text-xs">15 fields</Badge>
            <Badge variant="secondary" className="text-xs">2 levels</Badge>
          </div>
        </CardContent>
      </Card>

      {/* Resume Template */}
      <Card className="cursor-pointer hover:border-primary transition-colors" onClick={() => loadTemplate('resume')}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Resume
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-3">
            Personal info, experience, education, skills
          </p>
          <div className="flex flex-wrap gap-1">
            <Badge variant="secondary" className="text-xs">20 fields</Badge>
            <Badge variant="secondary" className="text-xs">3 levels</Badge>
          </div>
        </CardContent>
      </Card>

      {/* Custom Templates (from API) */}
      {customTemplates.map(template => (
        <Card key={template.id} className="cursor-pointer hover:border-primary transition-colors" onClick={() => loadTemplate(template.id)}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileJson className="h-5 w-5" />
              {template.name}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-3">
              {template.description}
            </p>
            <div className="flex flex-wrap gap-1">
              <Badge variant="secondary" className="text-xs">
                {template.fieldCount} fields
              </Badge>
              <Badge variant="secondary" className="text-xs">
                {template.maxDepth} levels
              </Badge>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>

    <DialogFooter>
      <Button variant="outline" onClick={onClose}>Cancel</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

**Rationale:**
- Card-based layout allows quick visual scanning
- Metadata badges (field count, depth) help users make informed choices
- Hover state provides affordance (clickable)
- Blank template option reduces steps for advanced users

---

## 6. Color System & Theming

### FlowForge Color System

**Complete color documentation:** [COLOR_GUIDE.md](./COLOR_GUIDE.md)

**Base Colors:**

```css
/* Primary Colors - FlowForge Brand */
--color-primary: 200 61% 26%;           /* #1A4B6B - Dark Blue/Teal */
--color-primary-foreground: 0 0% 100%;  /* #FFFFFF - White text */
--color-primary-mid: 168 46% 44%;       /* #3BA08D - Mid Blue/Green */
--color-primary-light: 168 46% 69%;     /* #90D3C3 - Light Blue/Green */

/* Accent Colors */
--color-accent: 146 48% 60%;            /* #65C695 - Vibrant Green */
--color-accent-foreground: 0 0% 20%;    /* #333333 - Dark text */
--color-secondary: 27 100% 68%;         /* #FFA05B - Subtle Orange */
--color-secondary-foreground: 0 0% 20%; /* #333333 - Dark text */

/* Neutral Colors */
--color-background: 0 0% 97%;           /* #F8F8F8 - Off-White */
--color-foreground: 0 0% 20%;           /* #333333 - Dark Gray */
--color-card: 0 0% 100%;                /* #FFFFFF - White */
--color-border: 0 0% 67%;               /* #AAAAAA - Mid Gray */
--color-muted-foreground: 0 0% 67%;     /* #AAAAAA - Secondary text */

/* Status Colors */
--color-destructive: 0 84.2% 60.2%;     /* #ef4444 - Error Red */
```

### FlowForge Extended Palette (Tailwind Config)

**Direct color references (when you need exact hex values):**

```js
// tailwind.config.js - extend.colors
extend: {
  colors: {
    // ... existing color mappings ...
    flowforge: {
      'primary-dark': '#1A4B6B',
      'primary-mid': '#3BA08D',
      'primary-light': '#90D3C3',
      'accent-green': '#65C695',
      'accent-orange': '#FFA05B',
      'neutral-bg': '#F8F8F8',
      'neutral-dark': '#333333',
      'neutral-light': '#FFFFFF',
      'neutral-border': '#AAAAAA',
    },
  }
}
```

### Usage Examples

```tsx
// Primary button with FlowForge brand color
<Button className="bg-primary text-primary-foreground hover:bg-primary-mid">
  Save Changes
</Button>

// Success state with accent green
<Badge className="bg-accent text-accent-foreground">
  Completed
</Badge>

// Warning state with accent orange
<Badge className="bg-secondary text-secondary-foreground">
  Pending
</Badge>

// Standard card with FlowForge background
<Card className="bg-white border-border">
  <CardContent className="text-foreground">
    Content
  </CardContent>
</Card>
```

### Depth Level Backgrounds

**Progressive transparency for nesting:**

```tsx
// utils/getDepthStyles.ts
export function getDepthStyles(level: number) {
  const styles = {
    0: 'pl-0 bg-background border-l-0',
    1: 'pl-6 bg-muted/30 border-l-2 border-primary/20',
    2: 'pl-12 bg-muted/50 border-l-2 border-primary/40',
    3: 'pl-18 bg-accent/30 border-l-2 border-primary/60',
  };
  return styles[level] || styles[3];
}
```

### State-Based Color Usage (FlowForge)

| State | Background | Border | Text | Icon |
|-------|-----------|--------|------|------|
| **Default** | `bg-background` (#F8F8F8) | `border-border` (#AAAAAA) | `text-foreground` (#333333) | `text-muted-foreground` (#AAAAAA) |
| **Hover** | `bg-primary-light/30` | `border-primary-mid` | `text-foreground` | `text-primary` |
| **Active/Selected** | `bg-primary` (#1A4B6B) | `border-primary` | `text-primary-foreground` (#FFFFFF) | `text-primary-foreground` |
| **Disabled** | `bg-muted` (#F8F8F8) | `border-border` | `text-muted-foreground` (#AAAAAA) | `text-muted-foreground` |
| **Error** | `bg-destructive/10` | `border-destructive` | `text-destructive` | `text-destructive` |
| **Success** | `bg-accent` (#65C695) | `border-accent` | `text-accent-foreground` (#333333) | `text-accent-foreground` |
| **Warning** | `bg-secondary` (#FFA05B) | `border-secondary` | `text-secondary-foreground` (#333333) | `text-secondary-foreground` |
| **Info** | `bg-primary-mid` (#3BA08D) | `border-primary-mid` | `text-white` | `text-white` |

---

## 7. Typography Scale

### Font Families

```css
/* Base configuration (already in index.css) */
:root {
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}

body {
  font-family: var(--font-sans);
}

code, pre, .font-mono {
  font-family: var(--font-mono);
}
```

### Type Scale

| Element | Tailwind Class | Size | Weight | Line Height | Usage |
|---------|---------------|------|--------|-------------|--------|
| **H1 (App Title)** | `text-xl font-bold` | 20px | 700 | 28px | Header branding |
| **H2 (Section)** | `text-lg font-semibold` | 18px | 600 | 28px | Panel titles |
| **H3 (Dialog Title)** | `text-base font-semibold` | 16px | 600 | 24px | Dialog headers |
| **Body Large** | `text-base` | 16px | 400 | 24px | Default text |
| **Body Small** | `text-sm` | 14px | 400 | 20px | Property names, labels |
| **Caption** | `text-xs` | 12px | 400 | 16px | Helper text, metadata |
| **Code** | `text-xs font-mono` | 12px | 400 | 18px | JSON, property names |
| **Button Text** | `text-sm font-medium` | 14px | 500 | 20px | All buttons |
| **Badge Text** | `text-xs font-medium` | 11px | 500 | 16px | Type badges |

### Responsive Typography

```tsx
// Mobile adjustments (apply at breakpoint md:)
<h1 className="text-lg md:text-xl font-bold">
<p className="text-sm md:text-base">
```

---

## 8. Spacing & Layout Grid

### Spacing Scale (Tailwind Default)

| Token | Value | Tailwind | Usage |
|-------|-------|----------|--------|
| **xs** | 4px | `space-1` | Icon gaps, tight padding |
| **sm** | 8px | `space-2` | Component internal spacing |
| **md** | 12px | `space-3` | Small gaps between elements |
| **base** | 16px | `space-4` | Default spacing |
| **lg** | 24px | `space-6` | Section spacing |
| **xl** | 32px | `space-8` | Large section gaps |
| **2xl** | 48px | `space-12` | Major layout divisions |

### Component-Specific Spacing

**Tree Node Indentation:**
- Level 0: `pl-0`
- Level 1: `pl-6` (24px)
- Level 2: `pl-12` (48px)
- Level 3: `pl-18` (72px) - Custom utility: `pl-18: 4.5rem`

**Add to Tailwind config:**
```js
extend: {
  spacing: {
    '18': '4.5rem', // 72px for level 3 indentation
  }
}
```

**Dialog Padding:**
- Content: `p-6` (24px)
- Form groups: `space-y-6` (24px vertical gap)

**Panel Padding:**
- Tree Panel: `p-4` (16px)
- Preview Panel: `p-4` (16px)

### Grid Layouts

**Template Selector Grid:**
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
```

**Form Two-Column:**
```tsx
<div className="grid grid-cols-2 gap-4">
  {/* Min/Max inputs side by side */}
</div>
```

---

## 9. Iconography

### Icon Library: Lucide React

**All icons from `lucide-react` package**

### Icon Mapping

#### Property Types

| Type | Icon | Component |
|------|------|-----------|
| **string** | `Type` | `<Type className="h-4 w-4 text-blue-600" />` |
| **number** | `Hash` | `<Hash className="h-4 w-4 text-green-600" />` |
| **boolean** | `ToggleLeft` | `<ToggleLeft className="h-4 w-4 text-purple-600" />` |
| **object** | `Braces` | `<Braces className="h-4 w-4 text-orange-600" />` |
| **array** | `Brackets` | `<Brackets className="h-4 w-4 text-pink-600" />` |

#### Actions

| Action | Icon | Component |
|--------|------|-----------|
| **Add Property** | `Plus` | `<Plus className="h-4 w-4" />` |
| **Edit** | `Pencil` | `<Pencil className="h-4 w-4" />` |
| **Delete** | `Trash2` | `<Trash2 className="h-4 w-4" />` |
| **Save** | `Save` | `<Save className="h-4 w-4" />` |
| **Export** | `Download` | `<Download className="h-4 w-4" />` |
| **Import** | `Upload` | `<Upload className="h-4 w-4" />` |
| **Copy** | `Copy` | `<Copy className="h-4 w-4" />` |

#### UI Controls

| Control | Icon | Component |
|---------|------|-----------|
| **Expand** | `ChevronRight` | `<ChevronRight className="h-4 w-4" />` |
| **Collapse** | `ChevronDown` | `<ChevronDown className="h-4 w-4" />` |
| **Close Dialog** | `X` | `<X className="h-4 w-4" />` |
| **Dropdown** | `ChevronDown` | `<ChevronDown className="h-4 w-4" />` |

#### Status Indicators

| Status | Icon | Component |
|--------|------|-----------|
| **Valid/Success** | `CheckCircle2` | `<CheckCircle2 className="h-5 w-5 text-green-600" />` |
| **Error** | `AlertCircle` | `<AlertCircle className="h-5 w-5 text-destructive" />` |
| **Warning** | `AlertTriangle` | `<AlertTriangle className="h-5 w-5 text-amber-600" />` |
| **Info** | `Info` | `<Info className="h-4 w-4 text-blue-600" />` |
| **Loading** | `Loader2` | `<Loader2 className="h-4 w-4 animate-spin" />` |

#### Templates & Files

| Item | Icon | Component |
|------|------|-----------|
| **Template** | `FileText` | `<FileText className="h-5 w-5" />` |
| **JSON File** | `FileJson` | `<FileJson className="h-5 w-5" />` |
| **Folder** | `FolderOpen` | `<FolderOpen className="h-5 w-5" />` |
| **New File** | `FilePlus` | `<FilePlus className="h-5 w-5" />` |

### Icon Sizing

| Context | Size Class | Pixel Size |
|---------|-----------|------------|
| **Tree node type** | `h-4 w-4` | 16px |
| **Action buttons** | `h-4 w-4` | 16px |
| **Toolbar buttons** | `h-5 w-5` | 20px |
| **Status indicators** | `h-5 w-5` | 20px |
| **App logo** | `h-6 w-6` | 24px |

---

## 10. Accessibility Requirements

### Keyboard Navigation

**Global Shortcuts:**

| Key | Action |
|-----|--------|
| `Ctrl/Cmd + S` | Save schema |
| `Ctrl/Cmd + E` | Export schema |
| `Ctrl/Cmd + I` | Import schema |
| `Ctrl/Cmd + N` | New property |
| `Esc` | Close dialog/dropdown |

**Tree Navigation:**

| Key | Action |
|-----|--------|
| `↑ / ↓` | Navigate between tree nodes |
| `→` | Expand collapsed node |
| `←` | Collapse expanded node |
| `Enter` | Edit selected node |
| `Delete` | Delete selected node |
| `Tab` | Move to next focusable element |
| `Shift + Tab` | Move to previous focusable element |

**Dialog Navigation:**

| Key | Action |
|-----|--------|
| `Tab` | Move to next field |
| `Shift + Tab` | Move to previous field |
| `Enter` | Submit form |
| `Esc` | Close dialog |

### ARIA Attributes

**Tree Component:**

```tsx
<div
  role="tree"
  aria-label="Schema property tree"
>
  <div
    role="treeitem"
    aria-expanded={isExpanded}
    aria-level={level}
    aria-setsize={siblings.length}
    aria-posinset={index + 1}
    tabIndex={isSelected ? 0 : -1}
  >
    {/* Node content */}
  </div>
</div>
```

**Dialogs:**

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

**Form Fields:**

```tsx
<div>
  <Label htmlFor="propertyName">
    Property Name
    <span className="sr-only">required</span>
  </Label>
  <Input
    id="propertyName"
    aria-required="true"
    aria-invalid={hasError}
    aria-describedby={hasError ? "name-error" : undefined}
  />
  {hasError && (
    <p id="name-error" role="alert" className="text-destructive text-sm">
      {errorMessage}
    </p>
  )}
</div>
```

**Buttons:**

```tsx
<Button
  aria-label="Add child property"
  disabled={level >= 3}
  aria-disabled={level >= 3}
>
  <Plus className="h-4 w-4" />
  <span className="sr-only">Add child property</span>
</Button>
```

### Focus Management

**Dialog Focus Trap:**
- On open: Focus first interactive element (property name input)
- On close: Return focus to trigger element
- Tab cycles within dialog only

**Tree Focus:**
- Maintain focus on current node during keyboard navigation
- Visible focus indicator: `focus:ring-2 focus:ring-primary focus:ring-offset-2`

### Color Contrast (WCAG 2.1 AA)

**Minimum Ratios:**
- Normal text: 4.5:1
- Large text (18px+): 3:1
- UI components: 3:1

**Verification:**

| Element | Foreground | Background | Ratio | Pass |
|---------|-----------|------------|-------|------|
| Body text | `#020817` | `#FFFFFF` | 19.8:1 | ✓ |
| Muted text | `#64748b` | `#FFFFFF` | 4.6:1 | ✓ |
| Primary button | `#f8fafc` | `#1e293b` | 14.2:1 | ✓ |
| Error text | `#ef4444` | `#FFFFFF` | 3.9:1 | ✓ (large text) |

### Screen Reader Considerations

**Status Announcements:**

```tsx
// Live region for schema validation status
<div
  role="status"
  aria-live="polite"
  aria-atomic="true"
  className="sr-only"
>
  {isValid ? "Schema is valid" : `Schema error: ${validationError}`}
</div>
```

**Tree Structure Announcement:**

```tsx
// Announce node details on selection
<span className="sr-only">
  {property.name}, {property.type},
  {property.required ? "required" : "optional"},
  level {level},
  {children.length} children
</span>
```

---

## 11. Interaction Patterns

### 11.1 Adding a New Property

**Flow:**

1. **Trigger:** User clicks "Add Property" button (root level) or "Add Child" icon (nested)
2. **Action:** Property Editor Dialog opens with autofocus on name field
3. **Validation:**
   - Name must be valid JSON key (alphanumeric, underscores, no spaces)
   - Inline validation shows error immediately
4. **Type Selection:** User selects type from dropdown with icons
5. **Constraint Configuration:** Conditional fields appear based on type
6. **Submit:** Click "Add Property" button
7. **Feedback:**
   - Dialog closes
   - New node appears in tree (expanded by default)
   - Tree scrolls to show new node
   - Toast: "Property added successfully"

**Error Handling:**
- Duplicate name: "Property with this name already exists at this level"
- Invalid name: "Property name must start with letter or underscore"
- Max depth exceeded: "Cannot add children beyond 3 levels of nesting"

---

### 11.2 Editing a Property

**Flow:**

1. **Trigger:** User clicks "Edit" icon on tree node OR presses `Enter` with node selected
2. **Action:** Property Editor Dialog opens with pre-filled values
3. **Modification:** User changes values
4. **Type Change Handling:**
   - If type changes (e.g., string → object):
     - Show warning: "Changing type will reset all constraints. Continue?"
     - If confirmed: Clear existing constraints, show new constraint fields
     - If has children and changing to non-container type: "This property has children. Remove children first."
5. **Submit:** Click "Update Property"
6. **Feedback:**
   - Dialog closes
   - Tree node updates immediately
   - JSON preview updates
   - Toast: "Property updated successfully"

**Validation:**
- Cannot change object/array to primitive type if children exist
- Name uniqueness validated within same parent scope

---

### 11.3 Deleting a Property

**Flow:**

1. **Trigger:** User clicks "Delete" icon OR presses `Delete` key with node selected
2. **Confirmation:**
   - If node has no children: Confirm dialog "Delete property '{name}'?"
   - If node has children: Stronger warning "Delete '{name}' and {count} nested properties?"
3. **Action:** User confirms
4. **Effect:**
   - Node removed from tree (with animation)
   - Focus moves to previous sibling or parent
   - JSON preview updates
   - Toast: "Property deleted"
5. **Undo (optional):** Toast includes "Undo" button (5 second timeout)

**Keyboard:**
- `Esc` to cancel confirmation
- `Enter` to confirm deletion

---

### 11.4 Changing Property Type

**Flow:**

1. **Trigger:** User selects different type from dropdown in Property Editor
2. **Constraint Reset Logic:**

   | From Type | To Type | Action |
   |-----------|---------|--------|
   | Primitive | Primitive | Reset constraints, show new fields |
   | Primitive | Object/Array | Clear constraints, prepare for children |
   | Object/Array | Primitive | **Blocked if has children** |
   | Object/Array | Object/Array | Preserve children, swap type |

3. **Warning Dialog (if has constraints):**
   ```
   Changing type will reset these constraints:
   - Pattern: ^[A-Z]{2}$
   - Min Length: 2

   Continue?
   ```

4. **Feedback:**
   - Constraint fields update immediately
   - Helper text changes to match new type
   - Default values cleared

---

### 11.5 Nesting Validation

**Max Depth Enforcement:**

**Visual Indicators:**

- **Level 0-1:** Green "Add Child" button (no warnings)
- **Level 2:** Info icon + tooltip "1 more level of nesting available"
- **Level 3:**
  - "Add Child" button disabled
  - Amber border on node
  - Amber background tint
  - Tooltip: "Maximum nesting depth (3 levels) reached"

**Attempted Action at Max Depth:**
- Click on disabled button: Tooltip appears
- Keyboard attempt: Toast notification "Cannot add children beyond level 3"

**Example Visual Feedback:**

```tsx
{level === 3 ? (
  <Tooltip>
    <TooltipTrigger asChild>
      <Button variant="ghost" size="icon" disabled>
        <Plus className="h-4 w-4 text-muted-foreground" />
      </Button>
    </TooltipTrigger>
    <TooltipContent>
      <p>Maximum nesting depth (3 levels) reached</p>
    </TooltipContent>
  </Tooltip>
) : (
  <Button variant="ghost" size="icon" onClick={onAddChild}>
    <Plus className="h-4 w-4" />
  </Button>
)}
```

---

### 11.6 Template Loading

**Flow:**

1. **Trigger:** User clicks "Templates" dropdown → selects template
2. **Unsaved Changes Check:**
   - If no changes: Load immediately
   - If unsaved changes: Confirmation dialog
     ```
     You have unsaved changes to "Current Schema"

     Loading a template will discard these changes.

     [Cancel] [Save & Load] [Discard & Load]
     ```
3. **Loading State:**
   - Loading spinner in tree panel
   - Disabled toolbar buttons
4. **Loaded:**
   - Tree populates with template structure
   - Schema name updates
   - JSON preview updates
   - Toast: "Loaded Invoice Template (15 fields)"

**Error Handling:**
- Template load failure: "Failed to load template. Please try again."
- Malformed template: "Template is invalid. Contact support."

---

### 11.7 Schema Export

**Flow:**

1. **Trigger:** User clicks "Export" dropdown → selects format
2. **Validation:**
   - If schema invalid: Block export, show validation errors
   - If valid: Proceed
3. **Export Options:**

   | Format | File Extension | Content |
   |--------|---------------|---------|
   | **JSON** | `.json` | Raw JSON Schema |
   | **TypeScript** | `.d.ts` | TypeScript interface definitions |

4. **Download:**
   - Browser triggers file download
   - Filename: `{schemaName}_schema.json` or `{schemaName}.d.ts`
   - Toast: "Schema exported successfully"

**Example TypeScript Export:**

```typescript
// invoice_schema.d.ts
export interface Invoice {
  invoiceNumber: string;
  customer: {
    name: string;
    email: string;
  };
  lineItems: Array<{
    description: string;
    quantity: number;
    unitPrice: number;
  }>;
  total: number;
}
```

---

### 11.8 Error States

**Validation Error Display:**

**In Tree Node:**
```tsx
{hasError && (
  <div className="flex items-center gap-1 text-destructive text-xs mt-1">
    <AlertCircle className="h-3 w-3" />
    <span>{errorMessage}</span>
  </div>
)}
```

**In JSON Preview:**
```tsx
{!isValid && (
  <Alert variant="destructive">
    <AlertCircle className="h-4 w-4" />
    <AlertTitle>Invalid Schema</AlertTitle>
    <AlertDescription>
      {validationErrors.map((err, i) => (
        <div key={i}>• {err.message} at {err.path}</div>
      ))}
    </AlertDescription>
  </Alert>
)}
```

**Common Error Messages:**

| Error | Message | Recovery Action |
|-------|---------|----------------|
| Duplicate property name | "Property 'name' already exists at this level" | Change name or delete duplicate |
| Invalid property name | "Property name must start with letter/underscore" | Fix name pattern |
| Empty required field | "Property name is required" | Fill field |
| Max depth exceeded | "Cannot add children beyond 3 levels" | Restructure schema |
| Invalid constraint | "Minimum cannot be greater than maximum" | Fix constraint values |

---

## 12. Micro-interactions & Animations

### Animation Principles

- **Duration:** 150-250ms for UI feedback (feels instant)
- **Easing:** `ease-out` for entrances, `ease-in-out` for state changes
- **Purpose:** Every animation must reduce cognitive load or provide feedback

### Component Animations

**Tree Node Expand/Collapse:**

```tsx
<div className={cn(
  "overflow-hidden transition-all duration-200 ease-in-out",
  isExpanded ? "max-h-[1000px] opacity-100" : "max-h-0 opacity-0"
)}>
  {children}
</div>
```

**Tree Node Hover:**

```tsx
<div className={cn(
  "transition-colors duration-150",
  "hover:bg-accent/50"
)}>
```

**Button Hover:**

```tsx
<Button className="transition-transform active:scale-95">
```

**Dialog Enter/Exit:**

Uses Radix UI (shadcn/ui) default animations:
- Enter: Fade in + scale from 95% to 100% (150ms)
- Exit: Fade out + scale to 95% (100ms)

**Loading State:**

```tsx
<Loader2 className="h-4 w-4 animate-spin" />
```

**Success Feedback:**

```tsx
// Button state change on successful action
<Button
  onClick={handleSave}
  className={cn(
    "transition-colors duration-200",
    isSaved && "bg-green-600 hover:bg-green-700"
  )}
>
  {isSaved ? (
    <><CheckCircle2 className="mr-2 h-4 w-4" />Saved</>
  ) : (
    <><Save className="mr-2 h-4 w-4" />Save</>
  )}
</Button>
```

**Toast Notifications:**

Uses shadcn/ui Toast component with default slide-in animation:
- Enter: Slide from right + fade in (150ms)
- Exit: Slide to right + fade out (100ms)
- Duration: 3000ms (3 seconds) default
- Action buttons: No auto-dismiss (manual close)

**Add Property Animation:**

```tsx
// New tree node appears with fade-in
<div className="animate-in fade-in duration-300">
  <SchemaTreeNode {...newProperty} />
</div>
```

**Delete Property Animation:**

```tsx
// Node fades out before removal
<div className="animate-out fade-out slide-out-to-right duration-200">
  <SchemaTreeNode {...property} />
</div>
```

**Validation Error Shake:**

```tsx
// Add to Tailwind config
keyframes: {
  shake: {
    '0%, 100%': { transform: 'translateX(0)' },
    '10%, 30%, 50%, 70%, 90%': { transform: 'translateX(-4px)' },
    '20%, 40%, 60%, 80%': { transform: 'translateX(4px)' },
  }
}
animation: {
  shake: 'shake 0.4s ease-in-out'
}

// Apply on validation error
<Input className={cn(hasError && "animate-shake border-destructive")} />
```

---

## 13. Error Prevention & Recovery

### Inline Validation

**Real-Time Validation:**

- **Property Name:** Validate on `onChange` with 300ms debounce
  ```tsx
  const validateName = useMemo(
    () => debounce((name: string) => {
      if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name)) {
        setError("Invalid property name");
      } else if (isDuplicate(name)) {
        setError("Property already exists");
      } else {
        setError(null);
      }
    }, 300),
    [existingNames]
  );
  ```

- **Numeric Constraints:** Validate min/max relationship on blur
  ```tsx
  const validateMinMax = () => {
    if (minimum !== null && maximum !== null && minimum > maximum) {
      setError("Minimum cannot be greater than maximum");
    }
  };
  ```

### Smart Defaults

**Reduce Decision Fatigue:**

| Field | Default Value | Rationale |
|-------|--------------|-----------|
| **Type** | `string` | Most common type in document extraction |
| **Required** | `false` | Prevents over-constraining schemas |
| **Format** | None | Avoid false positives |
| **Min/Max** | None | Allow any value unless explicitly restricted |

### Confirmation Dialogs

**Destructive Actions:**

```tsx
<AlertDialog>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>Delete Property</AlertDialogTitle>
      <AlertDialogDescription>
        Are you sure you want to delete "{property.name}"?
        {children.length > 0 && (
          <span className="block mt-2 text-destructive font-medium">
            This will also delete {children.length} nested properties.
          </span>
        )}
      </AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel>Cancel</AlertDialogCancel>
      <AlertDialogAction onClick={handleDelete} className="bg-destructive">
        Delete
      </AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

### Autosave to localStorage

**Draft Backup Strategy:**

```tsx
// Save draft every 30 seconds or on significant change
useEffect(() => {
  const saveDraft = () => {
    localStorage.setItem('schema-draft', JSON.stringify({
      name: schemaName,
      properties: schemaTree,
      timestamp: Date.now()
    }));
  };

  const interval = setInterval(saveDraft, 30000);
  return () => clearInterval(interval);
}, [schemaName, schemaTree]);

// Restore draft on load
useEffect(() => {
  const draft = localStorage.getItem('schema-draft');
  if (draft) {
    const { name, properties, timestamp } = JSON.parse(draft);
    const ageMinutes = (Date.now() - timestamp) / 60000;

    if (ageMinutes < 60) {
      showToast({
        title: "Draft Found",
        description: `Restore unsaved work from ${ageMinutes.toFixed(0)} minutes ago?`,
        action: <Button onClick={() => loadDraft(properties)}>Restore</Button>
      });
    }
  }
}, []);
```

### Helpful Error Messages

**Not This:**
- "Invalid input"
- "Error 400"
- "Validation failed"

**Do This:**
- "Property name must start with a letter or underscore (e.g., customer_name)"
- "Minimum value (10) cannot be greater than maximum value (5)"
- "Maximum nesting depth reached. Consider flattening your schema or using fewer levels."

### Undo Capability (Optional Enhancement)

**Command Pattern Implementation:**

```tsx
// Store action history
const [history, setHistory] = useState<Command[]>([]);
const [historyIndex, setHistoryIndex] = useState(-1);

// Undo action
const undo = () => {
  if (historyIndex >= 0) {
    history[historyIndex].undo();
    setHistoryIndex(historyIndex - 1);
  }
};

// Redo action
const redo = () => {
  if (historyIndex < history.length - 1) {
    history[historyIndex + 1].execute();
    setHistoryIndex(historyIndex + 1);
  }
};

// Keyboard shortcuts
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
      e.preventDefault();
      if (e.shiftKey) {
        redo();
      } else {
        undo();
      }
    }
  };

  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, [history, historyIndex]);
```

---

## 14. Implementation Notes

### shadcn/ui Components to Use

| Feature | shadcn/ui Component | Installation Command |
|---------|-------------------|---------------------|
| **Buttons** | `Button` | `npx shadcn-ui@latest add button` |
| **Forms** | `Input`, `Label`, `Textarea` | `npx shadcn-ui@latest add input label textarea` |
| **Dialogs** | `Dialog`, `AlertDialog` | `npx shadcn-ui@latest add dialog alert-dialog` |
| **Dropdowns** | `DropdownMenu`, `Select` | `npx shadcn-ui@latest add dropdown-menu select` |
| **Tooltips** | `Tooltip` | `npx shadcn-ui@latest add tooltip` |
| **Badges** | `Badge` | `npx shadcn-ui@latest add badge` |
| **Cards** | `Card` | `npx shadcn-ui@latest add card` |
| **Tabs** | `Tabs` | `npx shadcn-ui@latest add tabs` |
| **Toast** | `Toast` | `npx shadcn-ui@latest add toast` |
| **Switch** | `Switch` | `npx shadcn-ui@latest add switch` |

### Recommended Component Structure

```
src/
├── components/
│   ├── ui/                          # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── dialog.tsx
│   │   └── ...
│   ├── schema-editor/
│   │   ├── SchemaTree.tsx           # Main tree container
│   │   ├── SchemaTreeNode.tsx       # Recursive node component
│   │   ├── PropertyEditor.tsx       # Add/Edit dialog
│   │   ├── StringConstraints.tsx    # Type-specific constraint editors
│   │   ├── NumberConstraints.tsx
│   │   ├── BooleanConstraints.tsx
│   │   ├── ObjectConstraints.tsx
│   │   └── ArrayConstraints.tsx
│   ├── preview/
│   │   ├── JSONPreviewPanel.tsx     # Right panel container
│   │   └── ValidationStatus.tsx     # Validation indicator
│   ├── templates/
│   │   └── TemplateSelector.tsx     # Template gallery dialog
│   └── layout/
│       ├── Header.tsx               # App header with toolbar
│       └── MainLayout.tsx           # 2-column grid layout
├── lib/
│   ├── utils.ts                     # cn() helper (from shadcn)
│   ├── validation.ts                # AJV schema validation
│   └── schema-helpers.ts            # Schema manipulation utilities
├── hooks/
│   ├── useSchemaTree.ts             # Tree state management
│   ├── useSchemaValidation.ts       # Real-time validation
│   └── useAutoSave.ts               # localStorage draft saving
├── types/
│   ├── schema.ts                    # Schema type definitions
│   └── property.ts                  # Property type definitions
└── store/
    └── schemaStore.ts               # Zustand global state
```

### Tailwind CSS Utility Patterns

**Common Patterns:**

```tsx
// Consistent padding for sections
className="space-y-4"

// Form field container
className="space-y-2"

// Flex row with gap
className="flex items-center gap-2"

// Grid two columns
className="grid grid-cols-2 gap-4"

// Card with hover
className="rounded-lg border p-4 hover:border-primary transition-colors cursor-pointer"

// Icon with text
className="flex items-center gap-2"

// Disabled state
className={cn(
  "transition-opacity",
  disabled && "opacity-50 cursor-not-allowed"
)}

// Focus visible (keyboard navigation)
className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
```

### State Management with Zustand

**Example Schema Store:**

```tsx
// store/schemaStore.ts
import { create } from 'zustand';

interface Property {
  id: string;
  name: string;
  type: string;
  required: boolean;
  constraints: Record<string, any>;
  children?: Property[];
}

interface SchemaState {
  // State
  schemaName: string;
  properties: Property[];
  selectedPropertyId: string | null;
  isDirty: boolean;

  // Actions
  setSchemaName: (name: string) => void;
  addProperty: (property: Property, parentId?: string) => void;
  updateProperty: (id: string, updates: Partial<Property>) => void;
  deleteProperty: (id: string) => void;
  selectProperty: (id: string) => void;
  loadTemplate: (template: any) => void;
  reset: () => void;
}

export const useSchemaStore = create<SchemaState>((set) => ({
  schemaName: 'Untitled Schema',
  properties: [],
  selectedPropertyId: null,
  isDirty: false,

  setSchemaName: (name) => set({ schemaName: name, isDirty: true }),

  addProperty: (property, parentId) => set((state) => {
    // Implementation details...
    return { properties: newProperties, isDirty: true };
  }),

  // ... other actions
}));
```

### JSON Schema Validation with AJV

```tsx
// lib/validation.ts
import Ajv from 'ajv';
import addFormats from 'ajv-formats';

const ajv = new Ajv({ allErrors: true });
addFormats(ajv);

export function validateSchema(schema: object): {
  isValid: boolean;
  errors: string[]
} {
  try {
    ajv.compile(schema);
    return { isValid: true, errors: [] };
  } catch (e: any) {
    return {
      isValid: false,
      errors: e.errors?.map((err: any) =>
        `${err.instancePath || 'root'}: ${err.message}`
      ) || [e.message]
    };
  }
}
```

### Performance Optimization

**Virtualization for Large Trees:**

If schemas exceed 50 properties, consider virtualizing the tree:

```tsx
import { useVirtualizer } from '@tanstack/react-virtual';

// In SchemaTree component
const virtualizer = useVirtualizer({
  count: flattenedProperties.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 48, // Average node height
  overscan: 5
});
```

**Memoization:**

```tsx
// Expensive schema JSON generation
const schemaJSON = useMemo(() => {
  return generateSchemaJSON(properties);
}, [properties]);

// Property validation
const isPropertyValid = useMemo(() => {
  return validatePropertyName(name, existingNames);
}, [name, existingNames]);
```

---

## 15. User Flow Diagrams

### Flow 1: Creating Schema from Scratch

```
┌─────────────────────────────────────────────────────────────────┐
│ START: User opens application                                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
         ┌────────────────────────┐
         │ Empty schema canvas    │
         │ "Add Property" button  │
         └────────┬───────────────┘
                  │ Click "Add Property"
                  ▼
      ┌───────────────────────────┐
      │ Property Editor Dialog    │
      │ - Name: [autofocus]       │
      │ - Type: [string default]  │
      │ - Required: [unchecked]   │
      └───────┬───────────────────┘
              │ Enter details
              ▼
    ┌──────────────────────────────┐
    │ Conditional Constraints      │
    │ (based on selected type)     │
    └───────┬──────────────────────┘
            │ Click "Add Property"
            ▼
  ┌──────────────────────────────────┐
  │ Tree updates (fade-in animation) │
  │ JSON preview updates              │
  │ Toast: "Property added"           │
  └───────┬──────────────────────────┘
          │
          ▼
    ┌─────────────────┐
    │ Need to nest?   │◄──────┐
    └────┬────────────┘       │
         │ Yes                │ No, add more
         ▼                    │
┌──────────────────────┐      │
│ Click "Add Child" on │      │
│ object/array node    │      │
└────┬─────────────────┘      │
     │                        │
     ▼                        │
┌──────────────────────┐      │
│ Repeat property      │      │
│ editor flow          │      │
│ (max 3 levels)       │      │
└────┬─────────────────┘      │
     │                        │
     └────────────────────────┘
              │
              ▼
      ┌───────────────┐
      │ Schema valid? │
      └───┬───────────┘
          │ Yes
          ▼
  ┌──────────────────┐
  │ Click "Save"     │
  └───┬──────────────┘
      │
      ▼
┌─────────────────────┐
│ Schema saved to DB  │
│ Toast: "Saved!"     │
└─────────────────────┘
```

---

### Flow 2: Loading and Modifying Template

```
┌──────────────────────────────────────┐
│ START: User wants to use template    │
└────────────────┬─────────────────────┘
                 │
                 ▼
     ┌────────────────────────┐
     │ Click "Templates" ▾    │
     └────────┬───────────────┘
              │
              ▼
   ┌──────────────────────────┐
   │ Dropdown menu appears    │
   │ - Invoice                │
   │ - Resume                 │
   │ - Custom templates       │
   └────────┬─────────────────┘
            │ Select "Invoice"
            ▼
  ┌──────────────────────────────┐
  │ Unsaved changes?             │
  └────┬────────────────┬────────┘
       │ No             │ Yes
       │                ▼
       │      ┌─────────────────────────┐
       │      │ Confirmation Dialog     │
       │      │ "Discard changes?"      │
       │      │ [Cancel] [Discard]      │
       │      └────┬────────────────────┘
       │           │ Discard
       │           ▼
       └──────►┌──────────────────────┐
               │ Loading spinner      │
               └──────┬───────────────┘
                      │
                      ▼
            ┌──────────────────────────┐
            │ Tree populates with      │
            │ template structure       │
            │ - invoiceNumber (string) │
            │ - customer (object)      │
            │   - name (string)        │
            │   - email (string)       │
            │ - lineItems (array)      │
            │   - description (string) │
            │   - quantity (number)    │
            │   - unitPrice (number)   │
            │ - total (number)         │
            └──────┬───────────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │ User modifies:      │
         │ - Edit properties   │
         │ - Add new fields    │
         │ - Delete unneeded   │
         └─────┬───────────────┘
               │
               ▼
      ┌──────────────────────┐
      │ Save as new schema   │
      │ OR                   │
      │ Update template      │
      └──────────────────────┘
```

---

### Flow 3: Nesting Validation & Max Depth

```
┌────────────────────────────────────┐
│ START: Adding nested structure     │
└──────────────┬─────────────────────┘
               │
               ▼
   ┌────────────────────────────┐
   │ Add "lineItems" (array)    │
   │ at Level 0 (root)          │
   └──────────┬─────────────────┘
              │
              ▼
┌──────────────────────────────────┐
│ Click "Add Child" on lineItems  │
│ Current: Level 0 → Adding Level 1│
│ ✓ Allowed (green button)         │
└──────────┬───────────────────────┘
           │
           ▼
  ┌─────────────────────────────┐
  │ Add "product" (object)      │
  │ at Level 1                  │
  └──────────┬──────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ Click "Add Child" on product    │
│ Current: Level 1 → Adding Level 2│
│ ✓ Allowed                        │
│ ℹ️ Tooltip: "1 more level avail."│
└──────────┬───────────────────────┘
           │
           ▼
  ┌─────────────────────────────┐
  │ Add "details" (object)      │
  │ at Level 2                  │
  └──────────┬──────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ Click "Add Child" on details    │
│ Current: Level 2 → Adding Level 3│
│ ✓ Allowed (last level)           │
│ ⚠️ Node gets amber border        │
└──────────┬───────────────────────┘
           │
           ▼
  ┌─────────────────────────────┐
  │ Add "specification" (string)│
  │ at Level 3 (MAX)            │
  └──────────┬──────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ Try "Add Child" on specification│
│ ❌ Button DISABLED               │
│ ⚠️ Amber background on node     │
│ 🛈 Tooltip: "Max depth reached"  │
└──────────┬───────────────────────┘
           │ Click anyway
           ▼
  ┌─────────────────────────────┐
  │ Toast notification:         │
  │ "Cannot add children beyond │
  │  3 levels of nesting"       │
  └─────────────────────────────┘
```

---

## Accessibility Checklist

Use this checklist during implementation to ensure compliance:

### Keyboard Navigation
- [ ] All interactive elements accessible via Tab
- [ ] Logical tab order (left to right, top to bottom)
- [ ] Tree navigable with arrow keys
- [ ] Enter/Space activate buttons and toggles
- [ ] Escape closes dialogs and dropdowns
- [ ] Shortcuts documented and discoverable (Ctrl+S, etc.)

### ARIA Implementation
- [ ] Tree has `role="tree"` and proper ARIA attributes
- [ ] Tree items have `role="treeitem"`, `aria-level`, `aria-expanded`
- [ ] Dialogs have `role="dialog"`, `aria-labelledby`, `aria-describedby`
- [ ] Form fields have associated labels (for/id or aria-label)
- [ ] Error messages use `role="alert"` for live announcements
- [ ] Status indicators use `aria-live="polite"`

### Visual Accessibility
- [ ] Color contrast meets WCAG AA (4.5:1 for text)
- [ ] Focus indicators visible on all interactive elements
- [ ] Focus ring: 2px, high contrast, offset from element
- [ ] No information conveyed by color alone
- [ ] Icons paired with text or aria-label

### Screen Reader Support
- [ ] Screen reader tested with NVDA/JAWS (Windows) and VoiceOver (Mac)
- [ ] All images have alt text (or aria-hidden if decorative)
- [ ] Live regions announce important changes
- [ ] Hidden content (sr-only) provides context
- [ ] Tree structure announced with level and position

### Forms & Validation
- [ ] Required fields marked with aria-required
- [ ] Error states communicated with aria-invalid
- [ ] Error messages programmatically associated (aria-describedby)
- [ ] Success/error feedback announced to screen readers
- [ ] Form submission errors clearly listed and focused

---

## Conclusion

This design system prioritizes **task efficiency**, **error prevention**, and **accessibility** while maintaining a clean, modern aesthetic aligned with shadcn/ui and Tailwind CSS conventions.

**Key Design Decisions:**

1. **2-Column Real-Time Feedback:** Reduces errors by showing immediate JSON output
2. **Progressive Depth Indicators:** Prevents max nesting errors before they occur
3. **Type-Specific Constraint Editors:** Reduces cognitive load through progressive disclosure
4. **Keyboard-First Navigation:** Optimizes for power users and accessibility
5. **Inline Validation:** Catches errors at input time, not submission time

**Implementation Priority:**

1. **Phase 1:** Core tree editor, property CRUD, basic validation
2. **Phase 2:** Constraint editors, template loading, JSON preview
3. **Phase 3:** Advanced features (export formats, undo, autosave)
4. **Phase 4:** Performance optimization (virtualization for large schemas)

**Next Steps:**

1. Review this specification with stakeholders
2. Set up component library (shadcn/ui installation)
3. Implement core state management (Zustand store)
4. Build foundational components (SchemaTree, PropertyEditor)
5. Iterate based on usability testing

This design system is a living document. Update it as new requirements emerge or usability testing reveals improvements.

---

**Document Version:** 1.0
**Author:** Aura, UI/UX Designer Agent
**Date:** 2025-11-02
**Status:** Ready for Implementation
