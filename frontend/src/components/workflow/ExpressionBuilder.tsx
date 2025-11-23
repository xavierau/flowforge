/**
 * ExpressionBuilder - UI for building n8n-style expressions
 * Shows available nodes and their data structure for easy reference
 */

import { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { WorkflowNode } from '@/types/workflow';
import { formatExpression } from '@/lib/expression-parser';

interface ExpressionBuilderProps {
  /**
   * Available nodes that can be referenced (typically previous nodes)
   */
  nodes: WorkflowNode[];
  /**
   * Callback when expression is inserted
   */
  onInsert: (expression: string) => void;
  /**
   * Button variant
   */
  variant?: 'default' | 'outline' | 'ghost';
  /**
   * Button size
   */
  size?: 'default' | 'sm' | 'lg' | 'icon';
}

interface FieldNode {
  path: string;
  value: unknown;
  isObject: boolean;
}

/**
 * Parse object into tree structure for display
 */
function parseObjectStructure(
  obj: unknown,
  basePath: string = ''
): FieldNode[] {
  if (!obj || typeof obj !== 'object') return [];

  const fields: FieldNode[] = [];

  Object.entries(obj).forEach(([key, value]) => {
    const path = basePath ? `${basePath}.${key}` : key;
    const isObject = value !== null && typeof value === 'object';

    fields.push({
      path,
      value,
      isObject,
    });
  });

  return fields;
}

/**
 * Tree node component for displaying data structure
 */
function TreeNode({
  field,
  nodeName,
  onSelect,
}: {
  field: FieldNode;
  nodeName: string;
  onSelect: (expression: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const childFields = useMemo(() => {
    if (!field.isObject) return [];
    return parseObjectStructure(field.value, field.path);
  }, [field.isObject, field.value, field.path]);

  const expression = formatExpression(nodeName, field.path);

  const handleCopy = () => {
    navigator.clipboard.writeText(expression);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleInsert = () => {
    onSelect(expression);
  };

  return (
    <div>
      <div
        className="flex items-center gap-1 px-2 py-1 rounded hover:bg-muted/50 cursor-pointer group"
        onClick={() => {
          if (field.isObject) {
            setExpanded(!expanded);
          } else {
            handleInsert();
          }
        }}
      >
        {field.isObject ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
            className="p-0.5"
          >
            {expanded ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
          </button>
        ) : (
          <span className="w-4" />
        )}

        <span className="flex-1 text-sm font-mono truncate">
          {field.path.split('.').pop()}
        </span>

        {!field.isObject && (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleCopy();
              }}
              className="p-1 hover:bg-muted rounded"
              title="Copy expression"
            >
              {copied ? (
                <Check className="h-3 w-3 text-green-500" />
              ) : (
                <Copy className="h-3 w-3" />
              )}
            </button>
          </div>
        )}

        {!field.isObject && (
          <span className="text-xs text-muted-foreground truncate max-w-[100px]">
            {String(field.value)}
          </span>
        )}
      </div>

      {field.isObject && expanded && (
        <div className="ml-4 border-l pl-2" style={{ borderColor: 'hsl(var(--border))' }}>
          {childFields.map((childField) => (
            <TreeNode
              key={childField.path}
              field={childField}
              nodeName={nodeName}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Node card showing data structure
 */
function NodeCard({
  node,
  onSelect,
}: {
  node: WorkflowNode;
  onSelect: (expression: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  const outputData = node.data.outputData || {
    data: {
      // Example structure for display
      prompt: 'Example prompt',
      callback_url: 'https://example.com/callback',
      file_url: 'https://example.com/file.pdf',
    },
  };

  const rootFields = useMemo(
    () => parseObjectStructure(outputData),
    [outputData]
  );

  return (
    <div
      className="border rounded-lg overflow-hidden"
      style={{
        borderColor: 'hsl(var(--border))',
        backgroundColor: 'hsl(var(--card))',
      }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-muted/50 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4" />
        ) : (
          <ChevronRight className="h-4 w-4" />
        )}
        <span className="font-medium text-sm">{node.data.label}</span>
        <span className="text-xs text-muted-foreground ml-auto">
          {node.data.type}
        </span>
      </button>

      {expanded && (
        <div className="px-3 pb-2 space-y-1">
          {rootFields.map((field) => (
            <TreeNode
              key={field.path}
              field={field}
              nodeName={node.data.label}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Expression builder component
 */
export function ExpressionBuilder({
  nodes,
  onInsert,
  variant = 'outline',
  size = 'sm',
}: ExpressionBuilderProps) {
  const [open, setOpen] = useState(false);

  const handleInsert = (expression: string) => {
    onInsert(expression);
    setOpen(false);
  };

  if (nodes.length === 0) {
    return null;
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant={variant} size={size}>
          Insert Expression
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-96 p-0"
        align="start"
        style={{
          backgroundColor: 'hsl(var(--popover))',
          borderColor: 'hsl(var(--border))',
        }}
      >
        <div className="p-3 border-b" style={{ borderColor: 'hsl(var(--border))' }}>
          <h4 className="font-semibold text-sm mb-1">Available Nodes</h4>
          <p className="text-xs text-muted-foreground">
            Click on a field to insert its expression
          </p>
          <div className="mt-2 p-2 rounded bg-muted">
            <code className="text-xs">
              {'{{$("NodeName").data.field}}'}
            </code>
          </div>
        </div>

        <ScrollArea className="h-[400px]">
          <div className="p-3 space-y-2">
            {nodes.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                No previous nodes available.
                <br />
                Connect nodes to reference their data.
              </p>
            ) : (
              nodes.map((node) => (
                <NodeCard key={node.id} node={node} onSelect={handleInsert} />
              ))
            )}
          </div>
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}
