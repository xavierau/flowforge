import { useMemo } from 'react';
import ReactJson from '@microlink/react-json-view';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useSchemaStore } from '@/store/schemaStore';
import { propertiesToJsonSchema } from '@/lib/schema-converter';
import { generateSampleData } from '@/lib/template-loader';

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
    <Card className="h-full flex flex-col">
      <Tabs defaultValue="schema" className="h-full flex flex-col">
        <div className="p-4 border-b">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="schema">JSON Schema</TabsTrigger>
            <TabsTrigger value="sample">Sample Data</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="schema" className="flex-1 overflow-auto p-4 mt-0">
          <ReactJson
            src={jsonSchema}
            theme="rjv-default"
            collapsed={2}
            displayDataTypes={false}
            displayObjectSize={false}
            enableClipboard={true}
            name={false}
            style={{
              fontSize: '13px',
              fontFamily: 'monospace',
            }}
          />
        </TabsContent>

        <TabsContent value="sample" className="flex-1 overflow-auto p-4 mt-0">
          {Object.keys(sampleData).length > 0 ? (
            <ReactJson
              src={sampleData}
              theme="rjv-default"
              collapsed={2}
              displayDataTypes={false}
              displayObjectSize={false}
              enableClipboard={true}
              name={false}
              style={{
                fontSize: '13px',
                fontFamily: 'monospace',
              }}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <p>No properties defined yet. Add properties to see sample data.</p>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </Card>
  );
}
