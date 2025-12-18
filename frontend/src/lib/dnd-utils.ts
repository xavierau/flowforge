import type { Property } from '@/store/schemaStore';
import { findPropertyById } from '@/store/schemaStore';
import { SCHEMA_CONFIG } from '@/config';

/**
 * Result of a move validation check
 */
export interface ValidationResult {
  valid: boolean;
  reason?: string;
}

/**
 * Drop position relative to an element
 */
export type DropPosition = 'before' | 'after' | 'inside' | null;

/**
 * Check if targetId is a descendant of ancestorId in the property tree
 *
 * @param properties - The root property array
 * @param targetId - The ID to check if it's a descendant
 * @param ancestorId - The potential ancestor ID
 * @returns true if targetId is a descendant of ancestorId
 */
export function isDescendantOf(
  properties: Property[],
  targetId: string,
  ancestorId: string
): boolean {
  const ancestor = findPropertyById(properties, ancestorId);
  if (!ancestor || !ancestor.children) {
    return false;
  }

  // Check direct children
  for (const child of ancestor.children) {
    if (child.id === targetId) {
      return true;
    }
    // Recursively check descendants
    if (child.children && isDescendantOf([child], targetId, child.id)) {
      return true;
    }
  }

  return false;
}

/**
 * Get the maximum depth of a property subtree
 * Returns 1 for a leaf node, higher for nested structures
 *
 * @param property - The property to calculate depth for
 * @returns The maximum depth of the subtree (1-based)
 */
export function getMaxDepth(property: Property): number {
  if (!property.children || property.children.length === 0) {
    return 1;
  }

  let maxChildDepth = 0;
  for (const child of property.children) {
    const childDepth = getMaxDepth(child);
    if (childDepth > maxChildDepth) {
      maxChildDepth = childDepth;
    }
  }

  return 1 + maxChildDepth;
}

/**
 * Check if a move operation is valid
 *
 * Validation rules:
 * 1. Cannot drop onto self (sourceId === destinationParentId)
 * 2. Cannot drop into own descendant (circular reference)
 * 3. Destination parent must be object/array type (or null for root)
 * 4. Resulting depth must not exceed MAX_NESTING_LEVEL
 *
 * @param sourceId - The ID of the property being moved
 * @param destinationParentId - The ID of the destination parent (null for root)
 * @param properties - The root property array
 * @returns ValidationResult with valid flag and optional reason
 */
export function canMoveProperty(
  sourceId: string,
  destinationParentId: string | null,
  properties: Property[]
): ValidationResult {
  // Rule 1: Cannot drop onto self
  if (sourceId === destinationParentId) {
    return {
      valid: false,
      reason: 'Cannot drop a property onto itself',
    };
  }

  // Find the source property
  const sourceProperty = findPropertyById(properties, sourceId);
  if (!sourceProperty) {
    return {
      valid: false,
      reason: 'Source property not found',
    };
  }

  // Rule 2: Cannot drop into own descendant (circular reference)
  if (destinationParentId !== null && isDescendantOf(properties, destinationParentId, sourceId)) {
    return {
      valid: false,
      reason: 'Cannot drop a property into its own descendant',
    };
  }

  // Rule 3: Destination parent must be object/array type (or null for root)
  if (destinationParentId !== null) {
    const destinationParent = findPropertyById(properties, destinationParentId);
    if (!destinationParent) {
      return {
        valid: false,
        reason: 'Destination parent not found',
      };
    }

    if (destinationParent.type !== 'object' && destinationParent.type !== 'array') {
      return {
        valid: false,
        reason: 'Can only nest inside object or array properties',
      };
    }
  }

  // Rule 4: Resulting depth must not exceed MAX_NESTING_LEVEL
  const destinationLevel = destinationParentId !== null
    ? (findPropertyById(properties, destinationParentId)?.level ?? -1) + 1
    : 0;

  const sourceSubtreeDepth = getMaxDepth(sourceProperty);
  const resultingMaxLevel = destinationLevel + sourceSubtreeDepth - 1;

  if (resultingMaxLevel > SCHEMA_CONFIG.MAX_NESTING_LEVEL) {
    return {
      valid: false,
      reason: `Would exceed maximum nesting depth of ${SCHEMA_CONFIG.MAX_NESTING_LEVEL} levels`,
    };
  }

  return { valid: true };
}

/**
 * Determine drop position based on cursor Y relative to element
 *
 * Position zones:
 * - Top 25% of element = 'before'
 * - Bottom 25% = 'after'
 * - Middle 50% = 'inside' (only if canNestInside is true)
 *
 * If canNestInside is false and cursor is in middle zone,
 * falls back to before/after based on cursor position relative to center.
 *
 * @param cursorY - The Y coordinate of the cursor
 * @param elementTop - The top Y coordinate of the element
 * @param elementHeight - The height of the element
 * @param canNestInside - Whether nesting inside this element is allowed
 * @returns The drop position or null if outside element bounds
 */
export function getDropPosition(
  cursorY: number,
  elementTop: number,
  elementHeight: number,
  canNestInside: boolean
): DropPosition {
  // Check if cursor is within element bounds
  if (cursorY < elementTop || cursorY > elementTop + elementHeight) {
    return null;
  }

  const relativeY = cursorY - elementTop;
  const topZone = elementHeight * 0.25;
  const bottomZone = elementHeight * 0.75;
  const centerY = elementHeight * 0.5;

  // Top 25% - before
  if (relativeY < topZone) {
    return 'before';
  }

  // Bottom 25% - after
  if (relativeY > bottomZone) {
    return 'after';
  }

  // Middle 50%
  if (canNestInside) {
    return 'inside';
  }

  // Cannot nest inside - fallback based on cursor position relative to center
  return relativeY < centerY ? 'before' : 'after';
}

/**
 * Find the parent ID of a property
 */
export function findParentId(
  properties: Property[],
  propertyId: string,
  parentId: string | null = null
): string | null {
  for (const prop of properties) {
    if (prop.id === propertyId) {
      return parentId;
    }
    if (prop.children) {
      const found = findParentId(prop.children, propertyId, prop.id);
      if (found !== undefined) {
        return found;
      }
    }
  }
  return null;
}

/**
 * Find the index of a property within its parent's children array
 */
export function findPropertyIndex(
  properties: Property[],
  propertyId: string
): number {
  for (let i = 0; i < properties.length; i++) {
    if (properties[i].id === propertyId) {
      return i;
    }
  }
  return -1;
}

/**
 * Get siblings of a property (properties at the same level)
 */
export function getSiblings(
  properties: Property[],
  propertyId: string
): Property[] | null {
  // Check root level
  for (const prop of properties) {
    if (prop.id === propertyId) {
      return properties;
    }
  }

  // Check nested levels
  for (const prop of properties) {
    if (prop.children) {
      const siblings = getSiblings(prop.children, propertyId);
      if (siblings) {
        return siblings;
      }
    }
  }

  return null;
}
