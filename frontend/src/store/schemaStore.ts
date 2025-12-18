import { create } from 'zustand';
import { SCHEMA_CONFIG } from '@/config';

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
  moveProperty: (sourceId: string, destinationParentId: string | null, destinationIndex: number) => void;
}

const generateId = () => Math.random().toString(36).substr(2, 9);

export const findPropertyById = (
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

    if (level > SCHEMA_CONFIG.MAX_NESTING_LEVEL) {
      throw new Error(`Maximum nesting depth (${SCHEMA_CONFIG.MAX_NESTING_LEVEL} levels) reached`);
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

  moveProperty: (sourceId, destinationParentId, destinationIndex) => {
    const state = get();

    // Find the source property
    const sourceProperty = findPropertyById(state.properties, sourceId);
    if (!sourceProperty) {
      console.error('Source property not found:', sourceId);
      return;
    }

    // Calculate new level based on destination parent
    const newLevel = destinationParentId
      ? (findPropertyById(state.properties, destinationParentId)?.level ?? -1) + 1
      : 0;

    // Validate nesting depth
    if (newLevel > SCHEMA_CONFIG.MAX_NESTING_LEVEL) {
      console.error('Cannot move: would exceed maximum nesting depth');
      return;
    }

    // Helper to recursively update levels for a property and its descendants
    const updateLevels = (prop: Property, baseLevel: number): Property => {
      const updated: Property = { ...prop, level: baseLevel };
      if (prop.children && prop.children.length > 0) {
        updated.children = prop.children.map(child =>
          updateLevels(child, baseLevel + 1)
        );
      }
      return updated;
    };

    // Helper to remove property from tree and return [remaining tree, removed property]
    const removeFromTree = (
      props: Property[],
      targetId: string
    ): [Property[], Property | null] => {
      let removed: Property | null = null;

      const remaining = props.reduce<Property[]>((acc, prop) => {
        if (prop.id === targetId) {
          removed = prop;
          return acc;
        }

        if (prop.children && prop.children.length > 0) {
          const [childRemaining, childRemoved] = removeFromTree(prop.children, targetId);
          if (childRemoved) {
            removed = childRemoved;
          }
          acc.push({ ...prop, children: childRemaining });
        } else {
          acc.push(prop);
        }

        return acc;
      }, []);

      return [remaining, removed];
    };

    // Helper to insert property at specific index in target location
    const insertIntoTree = (
      props: Property[],
      targetParentId: string | null,
      property: Property,
      index: number
    ): Property[] => {
      if (targetParentId === null) {
        // Insert at root level
        const result = [...props];
        const safeIndex = Math.min(Math.max(0, index), result.length);
        result.splice(safeIndex, 0, property);
        return result;
      }

      return props.map(prop => {
        if (prop.id === targetParentId) {
          const children = [...(prop.children || [])];
          const safeIndex = Math.min(Math.max(0, index), children.length);
          children.splice(safeIndex, 0, property);
          return { ...prop, children };
        }

        if (prop.children && prop.children.length > 0) {
          return {
            ...prop,
            children: insertIntoTree(prop.children, targetParentId, property, index),
          };
        }

        return prop;
      });
    };

    // Step 1: Remove source from its current location
    const [treeAfterRemoval, removedProperty] = removeFromTree(state.properties, sourceId);

    if (!removedProperty) {
      console.error('Failed to remove source property');
      return;
    }

    // Step 2: Update levels for the removed property and its descendants
    const updatedProperty = updateLevels(removedProperty, newLevel);

    // Step 3: Insert at destination
    const newProperties = insertIntoTree(
      treeAfterRemoval,
      destinationParentId,
      updatedProperty,
      destinationIndex
    );

    // Step 4: Auto-expand destination parent if nesting into a parent
    const newExpandedNodeIds = new Set(state.expandedNodeIds);
    if (destinationParentId) {
      newExpandedNodeIds.add(destinationParentId);
    }

    set({
      properties: newProperties,
      isDirty: true,
      expandedNodeIds: newExpandedNodeIds,
    });
  },
}));
