import { useState } from 'react';
import ReactJson from '@microlink/react-json-view';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';

interface SchemaJsonViewerProps {
  /**
   * JSON Schema object to display
   */
  schema: Record<string, any>;

  /**
   * Optional sample data to show in the second tab
   */
  sampleData?: Record<string, any>;

  /**
   * Whether to show the tabs or just the schema view
   * @default true
   */
  showTabs?: boolean;

  /**
   * Default collapsed level for the JSON tree
   * @default 2
   */
  collapsedLevel?: number;
}

/**
 * Reusable JSON Schema Viewer Component
 *
 * Displays JSON schema with syntax highlighting and collapsible tree view.
 * Can optionally show sample data in a second tab.
 *
 * @example
 * ```tsx
 * // With tabs (default)
 * <SchemaJsonViewer schema={mySchema} sampleData={mySampleData} />
 *
 * // Schema only, no tabs
 * <SchemaJsonViewer schema={mySchema} showTabs={false} />
 * ```
 */
export function SchemaJsonViewer({
  schema,
  sampleData,
  showTabs = true,
  collapsedLevel = 2,
}: SchemaJsonViewerProps) {
  // Track expansion state
  const [isExpanded, setIsExpanded] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Reset expansion state when toggled
  const handleExpandAll = () => {
    setIsExpanded(true);
    setIsCollapsed(false);
  };

  const handleCollapseAll = () => {
    setIsCollapsed(true);
    setIsExpanded(false);
  };

  // Common ReactJson props
  const jsonViewProps = {
    theme: 'rjv-default' as const,
    collapsed: isExpanded ? false : isCollapsed ? true : collapsedLevel,
    displayDataTypes: false,
    displayObjectSize: false,
    enableClipboard: true,
    name: null,
    style: {
      fontSize: '13px',
      fontFamily: 'monospace',
    },
  };

  // Control buttons component
  const ControlButtons = () => (
    <div className="flex gap-2">
      <Button
        variant="outline"
        size="sm"
        onClick={handleExpandAll}
        className="h-8"
      >
        <ChevronDown className="h-3 w-3 mr-1" />
        Expand All
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={handleCollapseAll}
        className="h-8"
      >
        <ChevronUp className="h-3 w-3 mr-1" />
        Collapse All
      </Button>
    </div>
  );

  // If no tabs, just show the schema
  if (!showTabs || !sampleData) {
    return (
      <Card className="p-4">
        <div className="flex justify-end mb-3">
          <ControlButtons />
        </div>
        <div>
          <ReactJson src={schema} {...jsonViewProps} />
        </div>
      </Card>
    );
  }

  // Show tabs with schema and sample data
  return (
    <Card>
      <Tabs defaultValue="schema">
        <div className="p-4 border-b">
          <div className="flex items-center justify-between mb-3">
            <TabsList className="grid w-full max-w-md grid-cols-2">
              <TabsTrigger value="schema">JSON Schema</TabsTrigger>
              <TabsTrigger value="sample">Sample Data</TabsTrigger>
            </TabsList>
            <ControlButtons />
          </div>
        </div>

        <TabsContent value="schema" className="p-4 mt-0">
          <ReactJson src={schema} {...jsonViewProps} />
        </TabsContent>

        <TabsContent value="sample" className="p-4 mt-0">
          {sampleData && Object.keys(sampleData).length > 0 ? (
            <ReactJson src={sampleData} {...jsonViewProps} />
          ) : (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <p>No properties defined yet. Add properties to see sample data.</p>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </Card>
  );
}
