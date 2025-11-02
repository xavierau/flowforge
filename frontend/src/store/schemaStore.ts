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
    // Array constraints
    minItems?: number;
    maxItems?: number;
    uniqueItems?: boolean;
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
