import type { Property } from '@/store/schemaStore';
import type { Template } from '@/types/template';
import { jsonSchemaToProperties } from './schema-converter';

/**
 * Load a template and convert it to the Property format used by the store
 */
export function loadTemplateAsProperties(template: Template): {
  properties: Property[];
  name: string;
} {
  const properties = jsonSchemaToProperties(template.schema);

  return {
    properties,
    name: template.name,
  };
}

/**
 * Create a sample data object from properties (for JSON preview)
 */
export function generateSampleData(properties: Property[]): Record<string, any> {
  const sample: Record<string, any> = {};

  properties.forEach(prop => {
    sample[prop.name] = generateSampleValue(prop);
  });

  return sample;
}

function generateSampleValue(property: Property): any {
  switch (property.type) {
    case 'string':
      if (property.constraints.enum && property.constraints.enum.length > 0) {
        return property.constraints.enum[0];
      }
      if (property.constraints.format === 'email') {
        return 'example@email.com';
      }
      if (property.constraints.format === 'date') {
        return '2025-01-01';
      }
      if (property.constraints.format === 'date-time') {
        return '2025-01-01T00:00:00Z';
      }
      if (property.constraints.default !== undefined) {
        return property.constraints.default;
      }
      return `Sample ${property.name}`;

    case 'number':
      if (property.constraints.default !== undefined) {
        return property.constraints.default;
      }
      if (property.constraints.minimum !== undefined) {
        return property.constraints.minimum;
      }
      return 0;

    case 'boolean':
      if (property.constraints.default !== undefined) {
        return property.constraints.default;
      }
      return true;

    case 'object':
      if (!property.children || property.children.length === 0) {
        return {};
      }
      const objValue: Record<string, any> = {};
      property.children.forEach(child => {
        objValue[child.name] = generateSampleValue(child);
      });
      return objValue;

    case 'array':
      if (!property.children || property.children.length === 0) {
        return [];
      }
      // Generate 1-2 sample items
      const itemsSchema = property.children[0];
      const minItems = property.constraints.minItems || 1;
      const sampleCount = Math.max(minItems, 1);

      return Array.from({ length: sampleCount }, () =>
        generateSampleValue(itemsSchema)
      );

    default:
      return null;
  }
}
