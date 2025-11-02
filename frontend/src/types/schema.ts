/**
 * JSON Schema Type Definitions
 * Following the design system specifications
 */

export type JSONSchemaType =
  | 'object'
  | 'array'
  | 'string'
  | 'number'
  | 'boolean'
  | 'null';

/**
 * Internal representation of a schema node in the tree
 */
export interface SchemaNode {
  id: string;
  name: string;
  type: JSONSchemaType;
  description?: string;
  required: boolean;
  level: number; // 0-3 for max 3 levels
  parentId: string | null;

  // String constraints
  format?: string;
  pattern?: string;
  minLength?: number;
  maxLength?: number;

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
  enum?: string[];

  // Object properties
  properties?: SchemaNode[];

  // Array items
  items?: SchemaNode;
}

/**
 * Schema metadata (root level properties)
 */
export interface SchemaMetadata {
  title: string;
  description: string;
  $schema: string;
  required: string[];
}

/**
 * Complete JSON Schema output format
 */
export interface JSONSchema {
  $schema: string;
  title: string;
  description: string;
  type: 'object';
  properties: Record<string, any>;
  required: string[];
}

/**
 * String format options for the format constraint
 */
export const STRING_FORMATS = [
  'date',
  'date-time',
  'time',
  'email',
  'uri',
  'uuid',
  'hostname',
  'ipv4',
  'ipv6',
] as const;

export type StringFormat = typeof STRING_FORMATS[number];

/**
 * Helper type for property type icons (from Lucide React)
 */
export const TYPE_ICONS = {
  object: 'Braces',
  array: 'List',
  string: 'Type',
  number: 'Hash',
  boolean: 'ToggleLeft',
  null: 'Circle',
} as const;

/**
 * Level depth configuration
 */
export const MAX_NESTING_LEVEL = 3;

/**
 * Validation result type
 */
export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}
