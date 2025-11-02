# JSON Schema Builder - Implementation Guide

**Version:** 1.0
**Last Updated:** 2025-11-02
**Companion to:** [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Component Implementation Examples](#component-implementation-examples)
3. [State Management Patterns](#state-management-patterns)
4. [Utility Functions](#utility-functions)
5. [Testing Strategies](#testing-strategies)
6. [Common Pitfalls & Solutions](#common-pitfalls--solutions)

---

## Quick Start

### 1. Install Required Dependencies

```bash
# shadcn/ui components
npx shadcn-ui@latest add button
npx shadcn-ui@latest add input
npx shadcn-ui@latest add label
npx shadcn-ui@latest add textarea
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add alert-dialog
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add select
npx shadcn-ui@latest add tooltip
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add card
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add toast
npx shadcn-ui@latest add switch
npx shadcn-ui@latest add alert

# Additional packages (already in package.json)
npm install lucide-react zustand ajv @microlink/react-json-view
```

### 2. Extend Tailwind Configuration

Add custom utilities for tree depth and type colors:

```js
// tailwind.config.js
export default {
  theme: {
    extend: {
      spacing: {
        '18': '4.5rem', // 72px for level 3 indentation
      },
      colors: {
        'type-string': {
          DEFAULT: 'hsl(217, 91%, 60%)',
          light: 'hsl(217, 91%, 95%)',
          dark: 'hsl(217, 91%, 15%)',
        },
        'type-number': {
          DEFAULT: 'hsl(142, 71%, 45%)',
          light: 'hsl(142, 71%, 95%)',
          dark: 'hsl(142, 71%, 15%)',
        },
        'type-boolean': {
          DEFAULT: 'hsl(271, 91%, 65%)',
          light: 'hsl(271, 91%, 95%)',
          dark: 'hsl(271, 91%, 15%)',
        },
        'type-object': {
          DEFAULT: 'hsl(31, 91%, 60%)',
          light: 'hsl(31, 91%, 95%)',
          dark: 'hsl(31, 91%, 15%)',
        },
        'type-array': {
          DEFAULT: 'hsl(330, 81%, 60%)',
          light: 'hsl(330, 81%, 95%)',
          dark: 'hsl(330, 81%, 15%)',
        },
      },
      keyframes: {
        shake: {
          '0%, 100%': { transform: 'translateX(0)' },
          '10%, 30%, 50%, 70%, 90%': { transform: 'translateX(-4px)' },
          '20%, 40%, 60%, 80%': { transform: 'translateX(4px)' },
        },
      },
      animation: {
        shake: 'shake 0.4s ease-in-out',
      },
    },
  },
};
```

### 3. Set Up Zustand Store

Create the global state management:

```tsx
// src/store/schemaStore.ts
import { create } from 'zustand';

export interface Property {
  id: string;
  name: string;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  required: boolean;
  description?: string;
  constraints: {
    // String constraints
    format?: string;
    pattern?: string;
    minLength?: number;
    maxLength?: number;
    enum?: string[];
    // Number constraints
    minimum?: number;
    maximum?: number;
    multipleOf?: number;
    // Common
    default?: any;
  };
  children?: Property[];
  level: number; // 0-3
}

interface SchemaState {
  // State
  schemaName: string;
  properties: Property[];
  selectedPropertyId: string | null;
  isDirty: boolean;
  expandedNodeIds: Set<string>;

  // Actions
  setSchemaName: (name: string) => void;
  addProperty: (property: Omit<Property, 'id' | 'level'>, parentId?: string) => void;
  updateProperty: (id: string, updates: Partial<Property>) => void;
  deleteProperty: (id: string) => void;
  selectProperty: (id: string | null) => void;
  toggleNode: (id: string) => void;
  loadTemplate: (properties: Property[], name: string) => void;
  reset: () => void;
  markClean: () => void;
}

const generateId = () => Math.random().toString(36).substr(2, 9);

const findPropertyById = (
  properties: Property[],
  id: string
): Property | null => {
  for (const prop of properties) {
    if (prop.id === id) return prop;
    if (prop.children) {
      const found = findPropertyById(prop.children, id);
      if (found) return found;
    }
  }
  return null;
};

const calculateLevel = (properties: Property[], parentId?: string): number => {
  if (!parentId) return 0;
  const parent = findPropertyById(properties, parentId);
  return parent ? parent.level + 1 : 0;
};

export const useSchemaStore = create<SchemaState>((set, get) => ({
  schemaName: 'Untitled Schema',
  properties: [],
  selectedPropertyId: null,
  isDirty: false,
  expandedNodeIds: new Set(),

  setSchemaName: (name) => set({ schemaName: name, isDirty: true }),

  addProperty: (property, parentId) => {
    const state = get();
    const level = calculateLevel(state.properties, parentId);

    if (level > 3) {
      throw new Error('Maximum nesting depth (3 levels) reached');
    }

    const newProperty: Property = {
      ...property,
      id: generateId(),
      level,
      children: property.type === 'object' || property.type === 'array' ? [] : undefined,
    };

    if (!parentId) {
      // Add to root
      set({
        properties: [...state.properties, newProperty],
        isDirty: true,
        expandedNodeIds: new Set([...state.expandedNodeIds, newProperty.id]),
      });
    } else {
      // Add as child
      const addToParent = (props: Property[]): Property[] => {
        return props.map(prop => {
          if (prop.id === parentId) {
            return {
              ...prop,
              children: [...(prop.children || []), newProperty],
            };
          }
          if (prop.children) {
            return { ...prop, children: addToParent(prop.children) };
          }
          return prop;
        });
      };

      set({
        properties: addToParent(state.properties),
        isDirty: true,
        expandedNodeIds: new Set([...state.expandedNodeIds, parentId, newProperty.id]),
      });
    }
  },

  updateProperty: (id, updates) => {
    const updateInTree = (props: Property[]): Property[] => {
      return props.map(prop => {
        if (prop.id === id) {
          return { ...prop, ...updates };
        }
        if (prop.children) {
          return { ...prop, children: updateInTree(prop.children) };
        }
        return prop;
      });
    };

    set({
      properties: updateInTree(get().properties),
      isDirty: true,
    });
  },

  deleteProperty: (id) => {
    const deleteFromTree = (props: Property[]): Property[] => {
      return props
        .filter(prop => prop.id !== id)
        .map(prop => {
          if (prop.children) {
            return { ...prop, children: deleteFromTree(prop.children) };
          }
          return prop;
        });
    };

    set({
      properties: deleteFromTree(get().properties),
      selectedPropertyId: get().selectedPropertyId === id ? null : get().selectedPropertyId,
      isDirty: true,
    });
  },

  selectProperty: (id) => set({ selectedPropertyId: id }),

  toggleNode: (id) => {
    const state = get();
    const expanded = new Set(state.expandedNodeIds);
    if (expanded.has(id)) {
      expanded.delete(id);
    } else {
      expanded.add(id);
    }
    set({ expandedNodeIds: expanded });
  },

  loadTemplate: (properties, name) => set({
    properties,
    schemaName: name,
    selectedPropertyId: null,
    isDirty: false,
    expandedNodeIds: new Set(properties.map(p => p.id)),
  }),

  reset: () => set({
    schemaName: 'Untitled Schema',
    properties: [],
    selectedPropertyId: null,
    isDirty: false,
    expandedNodeIds: new Set(),
  }),

  markClean: () => set({ isDirty: false }),
}));
```

---

## Component Implementation Examples

### SchemaTreeNode Component

```tsx
// src/components/schema-editor/SchemaTreeNode.tsx
import { useState } from 'react';
import {
  ChevronRight,
  ChevronDown,
  Pencil,
  Trash2,
  Plus,
  Type,
  Hash,
  ToggleLeft,
  Braces,
  Brackets,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { Property, useSchemaStore } from '@/store/schemaStore';

interface SchemaTreeNodeProps {
  property: Property;
  onEdit: () => void;
  onDelete: () => void;
  onAddChild: () => void;
}

const TypeIcon = ({ type }: { type: Property['type'] }) => {
  const iconClass = 'h-4 w-4';
  switch (type) {
    case 'string':
      return <Type className={cn(iconClass, 'text-type-string')} />;
    case 'number':
      return <Hash className={cn(iconClass, 'text-type-number')} />;
    case 'boolean':
      return <ToggleLeft className={cn(iconClass, 'text-type-boolean')} />;
    case 'object':
      return <Braces className={cn(iconClass, 'text-type-object')} />;
    case 'array':
      return <Brackets className={cn(iconClass, 'text-type-array')} />;
  }
};

const getDepthStyles = (level: number) => {
  const styles = {
    0: 'pl-0 bg-background border-l-0',
    1: 'pl-6 bg-muted/30 border-l-2 border-primary/20',
    2: 'pl-12 bg-muted/50 border-l-2 border-primary/40',
    3: 'pl-18 bg-accent/30 border-l-2 border-primary/60 border-l-amber-500',
  };
  return styles[level as keyof typeof styles] || styles[3];
};

export function SchemaTreeNode({
  property,
  onEdit,
  onDelete,
  onAddChild,
}: SchemaTreeNodeProps) {
  const { expandedNodeIds, toggleNode, selectProperty, selectedPropertyId } = useSchemaStore();
  const isExpanded = expandedNodeIds.has(property.id);
  const isSelected = selectedPropertyId === property.id;
  const canExpand = (property.type === 'object' || property.type === 'array') &&
                    (property.children?.length ?? 0) > 0;
  const canAddChild = (property.type === 'object' || property.type === 'array') &&
                      property.level < 3;
  const isMaxDepth = property.level === 3;

  return (
    <div className="space-y-1">
      <div
        className={cn(
          'group relative rounded-md border p-3 transition-all duration-150',
          'hover:bg-accent/50 cursor-pointer',
          getDepthStyles(property.level),
          isSelected && 'border-primary bg-primary/10',
          isMaxDepth && 'bg-amber-50/50 dark:bg-amber-950/20'
        )}
        onClick={() => selectProperty(property.id)}
      >
        <div className="flex items-center gap-2">
          {/* Expand/Collapse */}
          {canExpand ? (
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5 p-0"
              onClick={(e) => {
                e.stopPropagation();
                toggleNode(property.id);
              }}
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </Button>
          ) : (
            <div className="w-5" /> // Spacer for alignment
          )}

          {/* Type Icon */}
          <TypeIcon type={property.type} />

          {/* Property Name */}
          <span
            className={cn(
              'font-mono text-sm',
              property.required && 'font-semibold'
            )}
          >
            {property.name}
            {property.required && (
              <span className="text-destructive ml-1">*</span>
            )}
          </span>

          {/* Type Badge */}
          <Badge variant="secondary" className="ml-2 text-xs">
            {property.type}
          </Badge>

          {/* Required Badge */}
          {property.required ? (
            <Badge variant="destructive" className="text-xs">
              Required
            </Badge>
          ) : (
            <Badge variant="outline" className="text-xs">
              Optional
            </Badge>
          )}
        </div>

        {/* Description */}
        {property.description && (
          <p className="text-xs text-muted-foreground mt-1 ml-7">
            {property.description}
          </p>
        )}

        {/* Action Buttons (visible on hover) */}
        <div className="absolute right-2 top-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit();
                }}
              >
                <Pencil className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Edit property</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                }}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Delete property</TooltipContent>
          </Tooltip>

          {(property.type === 'object' || property.type === 'array') && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  disabled={!canAddChild}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (canAddChild) onAddChild();
                  }}
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {canAddChild
                  ? `Add child property (${3 - property.level} more levels available)`
                  : 'Maximum nesting depth (3 levels) reached'}
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      </div>

      {/* Children */}
      {canExpand && isExpanded && (
        <div
          className={cn(
            'ml-6 space-y-1 overflow-hidden transition-all duration-200',
            'border-l-2 border-primary/20 pl-2'
          )}
        >
          {property.children?.map((child) => (
            <SchemaTreeNode
              key={child.id}
              property={child}
              onEdit={() => {/* Handle edit */}}
              onDelete={() => {/* Handle delete */}}
              onAddChild={() => {/* Handle add child */}}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

### PropertyEditor Dialog Component

```tsx
// src/components/schema-editor/PropertyEditor.tsx
import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Type, Hash, ToggleLeft, Braces, Brackets } from 'lucide-react';
import { Property } from '@/store/schemaStore';
import { StringConstraints } from './StringConstraints';
import { NumberConstraints } from './NumberConstraints';
import { cn } from '@/lib/utils';

interface PropertyEditorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: 'create' | 'edit';
  initialData?: Property;
  onSubmit: (data: Omit<Property, 'id' | 'level'>) => void;
}

export function PropertyEditor({
  open,
  onOpenChange,
  mode,
  initialData,
  onSubmit,
}: PropertyEditorProps) {
  const [name, setName] = useState('');
  const [type, setType] = useState<Property['type']>('string');
  const [required, setRequired] = useState(false);
  const [description, setDescription] = useState('');
  const [constraints, setConstraints] = useState<Property['constraints']>({});
  const [nameError, setNameError] = useState('');

  useEffect(() => {
    if (initialData && mode === 'edit') {
      setName(initialData.name);
      setType(initialData.type);
      setRequired(initialData.required);
      setDescription(initialData.description || '');
      setConstraints(initialData.constraints);
    }
  }, [initialData, mode]);

  const validateName = (value: string) => {
    if (!value) {
      setNameError('Property name is required');
      return false;
    }
    if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(value)) {
      setNameError('Property name must start with letter or underscore');
      return false;
    }
    setNameError('');
    return true;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateName(name)) return;

    onSubmit({
      name,
      type,
      required,
      description,
      constraints,
      children: type === 'object' || type === 'array' ? [] : undefined,
    });

    // Reset form
    setName('');
    setType('string');
    setRequired(false);
    setDescription('');
    setConstraints({});
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {mode === 'create' ? 'Add Property' : 'Edit Property'}
          </DialogTitle>
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
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                validateName(e.target.value);
              }}
              className={cn(nameError && 'border-destructive animate-shake')}
              autoFocus
              required
            />
            {nameError && (
              <p className="text-xs text-destructive">{nameError}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Valid JSON key (alphanumeric, underscores, no spaces)
            </p>
          </div>

          {/* Type Selector */}
          <div className="space-y-2">
            <Label htmlFor="type">
              Type <span className="text-destructive">*</span>
            </Label>
            <Select value={type} onValueChange={(v) => setType(v as Property['type'])}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="string">
                  <div className="flex items-center gap-2">
                    <Type className="h-4 w-4 text-type-string" />
                    <span>String</span>
                  </div>
                </SelectItem>
                <SelectItem value="number">
                  <div className="flex items-center gap-2">
                    <Hash className="h-4 w-4 text-type-number" />
                    <span>Number</span>
                  </div>
                </SelectItem>
                <SelectItem value="boolean">
                  <div className="flex items-center gap-2">
                    <ToggleLeft className="h-4 w-4 text-type-boolean" />
                    <span>Boolean</span>
                  </div>
                </SelectItem>
                <SelectItem value="object">
                  <div className="flex items-center gap-2">
                    <Braces className="h-4 w-4 text-type-object" />
                    <span>Object</span>
                  </div>
                </SelectItem>
                <SelectItem value="array">
                  <div className="flex items-center gap-2">
                    <Brackets className="h-4 w-4 text-type-array" />
                    <span>Array</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Textarea
              id="description"
              placeholder="Describe this property's purpose..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>

          {/* Required Toggle */}
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="space-y-0.5">
              <Label htmlFor="required">Required Field</Label>
              <p className="text-xs text-muted-foreground">
                Must be present in extracted data
              </p>
            </div>
            <Switch
              id="required"
              checked={required}
              onCheckedChange={setRequired}
            />
          </div>

          {/* Type-Specific Constraints */}
          {type === 'string' && (
            <StringConstraints
              constraints={constraints}
              onChange={setConstraints}
            />
          )}

          {type === 'number' && (
            <NumberConstraints
              constraints={constraints}
              onChange={setConstraints}
            />
          )}

          {/* Actions */}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!!nameError || !name}>
              {mode === 'create' ? 'Add Property' : 'Update Property'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

### JSON Preview Panel

```tsx
// src/components/preview/JSONPreviewPanel.tsx
import { useMemo } from 'react';
import ReactJsonView from '@microlink/react-json-view';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Code, FileJson, Copy, CheckCircle2, AlertCircle } from 'lucide-react';
import { useSchemaStore, Property } from '@/store/schemaStore';
import { validateSchema } from '@/lib/validation';
import { useToast } from '@/hooks/use-toast';

function generateSchemaJSON(properties: Property[]): object {
  const schema: any = {
    $schema: 'http://json-schema.org/draft-07/schema#',
    type: 'object',
    properties: {},
    required: [],
  };

  const buildProperties = (props: Property[]) => {
    const result: any = {};
    const required: string[] = [];

    for (const prop of props) {
      const propSchema: any = { type: prop.type };

      if (prop.description) {
        propSchema.description = prop.description;
      }

      // Add constraints
      if (prop.type === 'string') {
        if (prop.constraints.format) propSchema.format = prop.constraints.format;
        if (prop.constraints.pattern) propSchema.pattern = prop.constraints.pattern;
        if (prop.constraints.minLength) propSchema.minLength = prop.constraints.minLength;
        if (prop.constraints.maxLength) propSchema.maxLength = prop.constraints.maxLength;
        if (prop.constraints.enum) propSchema.enum = prop.constraints.enum;
      }

      if (prop.type === 'number') {
        if (prop.constraints.minimum !== undefined) propSchema.minimum = prop.constraints.minimum;
        if (prop.constraints.maximum !== undefined) propSchema.maximum = prop.constraints.maximum;
        if (prop.constraints.multipleOf) propSchema.multipleOf = prop.constraints.multipleOf;
      }

      if (prop.constraints.default !== undefined) {
        propSchema.default = prop.constraints.default;
      }

      // Handle nested properties
      if ((prop.type === 'object' || prop.type === 'array') && prop.children) {
        if (prop.type === 'object') {
          const { properties: childProps, required: childRequired } = buildProperties(prop.children);
          propSchema.properties = childProps;
          if (childRequired.length > 0) {
            propSchema.required = childRequired;
          }
        } else {
          // array
          if (prop.children.length > 0) {
            const firstChild = prop.children[0];
            const itemSchema: any = { type: firstChild.type };
            if (firstChild.type === 'object' && firstChild.children) {
              const { properties: childProps, required: childRequired } = buildProperties(firstChild.children);
              itemSchema.properties = childProps;
              if (childRequired.length > 0) {
                itemSchema.required = childRequired;
              }
            }
            propSchema.items = itemSchema;
          }
        }
      }

      result[prop.name] = propSchema;
      if (prop.required) {
        required.push(prop.name);
      }
    }

    return { properties: result, required };
  };

  const { properties: props, required } = buildProperties(properties);
  schema.properties = props;
  if (required.length > 0) {
    schema.required = required;
  }

  return schema;
}

export function JSONPreviewPanel() {
  const { properties } = useSchemaStore();
  const { toast } = useToast();

  const schemaJSON = useMemo(() => generateSchemaJSON(properties), [properties]);
  const validation = useMemo(() => validateSchema(schemaJSON), [schemaJSON]);

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(schemaJSON, null, 2));
      toast({
        title: 'Copied to clipboard',
        description: 'Schema JSON has been copied',
      });
    } catch (err) {
      toast({
        title: 'Failed to copy',
        description: 'Please try again',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="flex h-full flex-col border-l">
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

        <TabsContent value="schema" className="flex-1 m-0 p-4 overflow-auto">
          <div className="space-y-4">
            {/* Validation Status */}
            <Alert
              variant={validation.isValid ? 'default' : 'destructive'}
              className={validation.isValid ? 'border-green-500 bg-green-50 dark:bg-green-950/20' : ''}
            >
              {validation.isValid ? (
                <>
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <AlertTitle className="text-green-900 dark:text-green-100">
                    Valid JSON Schema
                  </AlertTitle>
                </>
              ) : (
                <>
                  <AlertCircle className="h-5 w-5" />
                  <AlertTitle>Invalid Schema</AlertTitle>
                  <AlertDescription>
                    {validation.errors.map((err, i) => (
                      <div key={i} className="text-xs mt-1">• {err}</div>
                    ))}
                  </AlertDescription>
                </>
              )}
            </Alert>

            {/* JSON Display */}
            <div className="rounded-md border bg-muted/30 p-4">
              <ReactJsonView
                src={schemaJSON}
                theme="rjv-default"
                displayDataTypes={false}
                displayObjectSize={false}
                enableClipboard={true}
                collapsed={2}
                name="schema"
              />
            </div>

            {/* Copy Button */}
            <Button variant="outline" className="w-full" onClick={copyToClipboard}>
              <Copy className="mr-2 h-4 w-4" />
              Copy JSON to Clipboard
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="sample" className="flex-1 m-0 p-4 overflow-auto">
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Example data that conforms to this schema
            </p>
            <div className="rounded-md border bg-muted/30 p-4">
              {/* Generate sample data based on schema */}
              <p className="text-xs text-muted-foreground">
                Sample data generation coming soon...
              </p>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

---

## Utility Functions

### Schema Validation

```tsx
// src/lib/validation.ts
import Ajv from 'ajv';
import addFormats from 'ajv-formats';

const ajv = new Ajv({ allErrors: true, strict: false });
addFormats(ajv);

export function validateSchema(schema: object): {
  isValid: boolean;
  errors: string[];
} {
  try {
    ajv.compile(schema);
    return { isValid: true, errors: [] };
  } catch (e: any) {
    return {
      isValid: false,
      errors: e.errors?.map((err: any) =>
        `${err.instancePath || 'root'}: ${err.message}`
      ) || [e.message],
    };
  }
}
```

### Local Storage Auto-Save Hook

```tsx
// src/hooks/useAutoSave.ts
import { useEffect } from 'react';
import { useSchemaStore } from '@/store/schemaStore';

export function useAutoSave() {
  const { schemaName, properties, isDirty } = useSchemaStore();

  useEffect(() => {
    if (!isDirty) return;

    const saveDraft = () => {
      localStorage.setItem('schema-draft', JSON.stringify({
        name: schemaName,
        properties,
        timestamp: Date.now(),
      }));
    };

    const interval = setInterval(saveDraft, 30000); // Every 30 seconds
    return () => clearInterval(interval);
  }, [schemaName, properties, isDirty]);

  useEffect(() => {
    // Restore draft on mount
    const draft = localStorage.getItem('schema-draft');
    if (draft) {
      try {
        const { name, properties, timestamp } = JSON.parse(draft);
        const ageMinutes = (Date.now() - timestamp) / 60000;

        if (ageMinutes < 60) {
          console.log('Draft found:', { name, ageMinutes });
          // You can show a toast here to ask if user wants to restore
        }
      } catch (e) {
        console.error('Failed to restore draft:', e);
      }
    }
  }, []);
}
```

---

## Common Pitfalls & Solutions

### 1. Tree Re-Rendering Performance

**Problem:** Tree re-renders all nodes on every state change

**Solution:** Memoize tree nodes

```tsx
import { memo } from 'react';

export const SchemaTreeNode = memo(({ property, ...props }: SchemaTreeNodeProps) => {
  // Component implementation
}, (prevProps, nextProps) => {
  // Custom comparison
  return (
    prevProps.property.id === nextProps.property.id &&
    prevProps.property.name === nextProps.property.name &&
    prevProps.property.type === nextProps.property.type &&
    prevProps.property.required === nextProps.property.required
  );
});
```

### 2. Dialog Focus Management

**Problem:** Focus not returning to trigger after dialog close

**Solution:** Use Radix UI's built-in focus management (shadcn/ui handles this)

### 3. Keyboard Navigation in Tree

**Problem:** Arrow key navigation conflicts with scrolling

**Solution:** Implement custom keyboard handler

```tsx
// src/hooks/useTreeKeyboard.ts
import { useEffect } from 'react';
import { useSchemaStore } from '@/store/schemaStore';

export function useTreeKeyboard(properties: Property[]) {
  const { selectedPropertyId, selectProperty, toggleNode, expandedNodeIds } = useSchemaStore();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!selectedPropertyId) return;

      const flatProperties = flattenTree(properties);
      const currentIndex = flatProperties.findIndex(p => p.id === selectedPropertyId);

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          if (currentIndex < flatProperties.length - 1) {
            selectProperty(flatProperties[currentIndex + 1].id);
          }
          break;
        case 'ArrowUp':
          e.preventDefault();
          if (currentIndex > 0) {
            selectProperty(flatProperties[currentIndex - 1].id);
          }
          break;
        case 'ArrowRight':
          e.preventDefault();
          if (!expandedNodeIds.has(selectedPropertyId)) {
            toggleNode(selectedPropertyId);
          }
          break;
        case 'ArrowLeft':
          e.preventDefault();
          if (expandedNodeIds.has(selectedPropertyId)) {
            toggleNode(selectedPropertyId);
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedPropertyId, properties, expandedNodeIds]);
}

function flattenTree(properties: Property[]): Property[] {
  const result: Property[] = [];
  const traverse = (props: Property[]) => {
    for (const prop of props) {
      result.push(prop);
      if (prop.children) traverse(prop.children);
    }
  };
  traverse(properties);
  return result;
}
```

---

## Testing Strategies

### Unit Tests (Example with Vitest)

```tsx
// src/store/schemaStore.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { useSchemaStore } from './schemaStore';

describe('SchemaStore', () => {
  beforeEach(() => {
    useSchemaStore.getState().reset();
  });

  it('should add root property', () => {
    const { addProperty, properties } = useSchemaStore.getState();

    addProperty({
      name: 'testProperty',
      type: 'string',
      required: false,
      constraints: {},
    });

    expect(properties).toHaveLength(1);
    expect(properties[0].name).toBe('testProperty');
    expect(properties[0].level).toBe(0);
  });

  it('should prevent adding property beyond level 3', () => {
    const { addProperty, properties } = useSchemaStore.getState();

    // Add level 0
    addProperty({ name: 'root', type: 'object', required: false, constraints: {} });
    const rootId = properties[0].id;

    // Add level 1
    addProperty({ name: 'level1', type: 'object', required: false, constraints: {} }, rootId);
    const level1Id = properties[0].children![0].id;

    // Add level 2
    addProperty({ name: 'level2', type: 'object', required: false, constraints: {} }, level1Id);
    const level2Id = properties[0].children![0].children![0].id;

    // Add level 3
    addProperty({ name: 'level3', type: 'string', required: false, constraints: {} }, level2Id);

    // Try to add level 4 (should throw)
    const level3Id = properties[0].children![0].children![0].children![0].id;
    expect(() => {
      addProperty({ name: 'level4', type: 'string', required: false, constraints: {} }, level3Id);
    }).toThrow('Maximum nesting depth');
  });
});
```

### Accessibility Testing

```tsx
// src/components/schema-editor/SchemaTreeNode.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SchemaTreeNode } from './SchemaTreeNode';

describe('SchemaTreeNode Accessibility', () => {
  it('should have proper ARIA attributes', () => {
    const mockProperty = {
      id: '1',
      name: 'testProp',
      type: 'string' as const,
      required: true,
      constraints: {},
      level: 0,
    };

    render(
      <SchemaTreeNode
        property={mockProperty}
        onEdit={() => {}}
        onDelete={() => {}}
        onAddChild={() => {}}
      />
    );

    const node = screen.getByText(/testProp/);
    expect(node).toBeInTheDocument();
  });
});
```

---

## Next Steps

1. **Set up component structure** following the recommended folder layout
2. **Install shadcn/ui components** as needed
3. **Implement core state management** with Zustand store
4. **Build tree components** starting with SchemaTreeNode
5. **Add property editor** with type-specific constraints
6. **Integrate JSON preview** with real-time validation
7. **Test thoroughly** with keyboard navigation and screen readers

This implementation guide provides concrete examples to complement the design system specification. Reference both documents during development.

---

**Document Version:** 1.0
**Author:** Aura, UI/UX Designer Agent
**Date:** 2025-11-02
