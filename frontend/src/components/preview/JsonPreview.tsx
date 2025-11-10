import { useMemo } from 'react';
import { useSchemaStore } from '@/store/schemaStore';
import { propertiesToJsonSchema } from '@/lib/schema-converter';
import { generateSampleData } from '@/lib/template-loader';
import { SchemaJsonViewer } from './SchemaJsonViewer';

/**
 * JsonPreview component for Schema Builder
 *
 * Displays JSON schema and sample data based on the current
 * properties in the Zustand store.
 */
export function JsonPreview() {
  const { properties, schemaName } = useSchemaStore();

  // Convert properties to JSON Schema
  const jsonSchema = useMemo(() => {
    return propertiesToJsonSchema(properties, schemaName);
  }, [properties, schemaName]);

  // Generate sample data
  const sampleData = useMemo(() => {
    return generateSampleData(properties);
  }, [properties]);

  return (
    <SchemaJsonViewer
      schema={jsonSchema}
      sampleData={sampleData}
      showTabs={true}
      collapsedLevel={2}
    />
  );
}
