import type { Property } from '@/store/schemaStore';
import type { JSONSchema } from '@/types/schema';

const generateId = () => Math.random().toString(36).substr(2, 9);

/**
 * Convert JSON Schema to Property tree structure
 */
export function jsonSchemaToProperties(schema: JSONSchema): Property[] {
  const properties: Property[] = [];

  if (!schema.properties) return properties;

  Object.entries(schema.properties).forEach(([key, value]: [string, any]) => {
    const property = convertSchemaProperty(key, value, 0, schema.required?.includes(key) || false);
    if (property) {
      properties.push(property);
    }
  });

  return properties;
}

function convertSchemaProperty(
  name: string,
  schema: any,
  level: number,
  required: boolean
): Property | null {
  if (!schema.type) return null;

  const property: Property = {
    id: generateId(),
    name,
    type: schema.type as Property['type'],
    required,
    description: schema.description,
    level,
    constraints: {},
  };

  // String constraints
  if (schema.format) property.constraints.format = schema.format;
  if (schema.pattern) property.constraints.pattern = schema.pattern;
  if (schema.minLength !== undefined) property.constraints.minLength = schema.minLength;
  if (schema.maxLength !== undefined) property.constraints.maxLength = schema.maxLength;
  if (schema.enum) property.constraints.enum = schema.enum;

  // Number constraints
  if (schema.minimum !== undefined) property.constraints.minimum = schema.minimum;
  if (schema.maximum !== undefined) property.constraints.maximum = schema.maximum;
  if (schema.multipleOf !== undefined) property.constraints.multipleOf = schema.multipleOf;

  // Array constraints
  if (schema.minItems !== undefined) property.constraints.minItems = schema.minItems;
  if (schema.maxItems !== undefined) property.constraints.maxItems = schema.maxItems;
  if (schema.uniqueItems !== undefined) property.constraints.uniqueItems = schema.uniqueItems;

  // Default value
  if (schema.default !== undefined) property.constraints.default = schema.default;

  // Handle object properties
  if (schema.type === 'object' && schema.properties) {
    property.children = [];
    Object.entries(schema.properties).forEach(([childKey, childValue]: [string, any]) => {
      const childProperty = convertSchemaProperty(
        childKey,
        childValue,
        level + 1,
        schema.required?.includes(childKey) || false
      );
      if (childProperty) {
        property.children!.push(childProperty);
      }
    });
  }

  // Handle array items
  if (schema.type === 'array' && schema.items) {
    const itemsProperty = convertSchemaProperty(
      'items',
      schema.items,
      level + 1,
      false
    );
    if (itemsProperty) {
      property.children = [itemsProperty];
    }
  }

  return property;
}

/**
 * Convert Property tree to JSON Schema
 */
export function propertiesToJsonSchema(
  properties: Property[],
  schemaName: string,
  description?: string
): JSONSchema {
  const schema: JSONSchema = {
    $schema: 'http://json-schema.org/draft-07/schema#',
    title: schemaName,
    description: description || `Schema for ${schemaName}`,
    type: 'object',
    properties: {},
    required: [],
  };

  properties.forEach(prop => {
    const propSchema = convertPropertyToSchema(prop);
    if (propSchema) {
      schema.properties[prop.name] = propSchema;
      if (prop.required) {
        schema.required.push(prop.name);
      }
    }
  });

  return schema;
}

function convertPropertyToSchema(property: Property): any {
  const schema: any = {
    type: property.type,
  };

  if (property.description) {
    schema.description = property.description;
  }

  // String constraints
  if (property.constraints.format) schema.format = property.constraints.format;
  if (property.constraints.pattern) schema.pattern = property.constraints.pattern;
  if (property.constraints.minLength !== undefined) schema.minLength = property.constraints.minLength;
  if (property.constraints.maxLength !== undefined) schema.maxLength = property.constraints.maxLength;
  if (property.constraints.enum) schema.enum = property.constraints.enum;

  // Number constraints
  if (property.constraints.minimum !== undefined) schema.minimum = property.constraints.minimum;
  if (property.constraints.maximum !== undefined) schema.maximum = property.constraints.maximum;
  if (property.constraints.multipleOf !== undefined) schema.multipleOf = property.constraints.multipleOf;

  // Array constraints
  if (property.constraints.minItems !== undefined) schema.minItems = property.constraints.minItems;
  if (property.constraints.maxItems !== undefined) schema.maxItems = property.constraints.maxItems;
  if (property.constraints.uniqueItems !== undefined) schema.uniqueItems = property.constraints.uniqueItems;

  // Default value
  if (property.constraints.default !== undefined) schema.default = property.constraints.default;

  // Handle object properties
  if (property.type === 'object' && property.children && property.children.length > 0) {
    schema.properties = {};
    schema.required = [];

    property.children.forEach(child => {
      const childSchema = convertPropertyToSchema(child);
      if (childSchema) {
        schema.properties[child.name] = childSchema;
        if (child.required) {
          schema.required.push(child.name);
        }
      }
    });

    if (schema.required.length === 0) {
      delete schema.required;
    }
  }

  // Handle array items
  if (property.type === 'array' && property.children && property.children.length > 0) {
    // For arrays, we use the first child as the items schema
    const itemsProperty = property.children[0];
    schema.items = convertPropertyToSchema(itemsProperty);
  }

  return schema;
}

/**
 * Validate that properties don't exceed max nesting level
 */
export function validateNestingLevel(properties: Property[], maxLevel: number = 3): boolean {
  const checkLevel = (props: Property[]): boolean => {
    for (const prop of props) {
      if (prop.level > maxLevel) {
        return false;
      }
      if (prop.children && !checkLevel(prop.children)) {
        return false;
      }
    }
    return true;
  };

  return checkLevel(properties);
}

/**
 * Get all property IDs in a tree (for expanding all nodes)
 */
export function getAllPropertyIds(properties: Property[]): string[] {
  const ids: string[] = [];

  const collectIds = (props: Property[]) => {
    props.forEach(prop => {
      ids.push(prop.id);
      if (prop.children) {
        collectIds(prop.children);
      }
    });
  };

  collectIds(properties);
  return ids;
}
