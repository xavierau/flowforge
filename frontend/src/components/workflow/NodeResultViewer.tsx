/**
 * NodeResultViewer - JSON result display with syntax highlighting and collapsible tree
 * Displays node execution output data with copy to clipboard functionality
 */

import { useState } from 'react';
import { Copy, ChevronRight, ChevronDown, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface NodeResultViewerProps {
  data: Record<string, unknown>;
  nodeId: string;
  maxDepth?: number;
}

interface TreeNodeProps {
  name: string;
  value: unknown;
  depth: number;
  maxDepth: number;
}

function TreeNode({ name, value, depth, maxDepth }: TreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(depth < 2); // Auto-expand first 2 levels

  const isObject = value !== null && typeof value === 'object' && !Array.isArray(value);
  const isArray = Array.isArray(value);
  const isExpandable = isObject || isArray;

  const indent = depth * 16;

  const renderValue = () => {
    if (value === null) return <span style={{ color: 'hsl(var(--muted-foreground))' }}>null</span>;
    if (value === undefined) return <span style={{ color: 'hsl(var(--muted-foreground))' }}>undefined</span>;

    switch (typeof value) {
      case 'string':
        return <span style={{ color: 'hsl(var(--success))' }}>"{value}"</span>;
      case 'number':
        return <span style={{ color: 'hsl(var(--primary))' }}>{value}</span>;
      case 'boolean':
        return <span style={{ color: 'hsl(var(--warning))' }}>{String(value)}</span>;
      case 'object':
        if (isArray) {
          return <span style={{ color: 'hsl(var(--muted-foreground))' }}>Array({(value as unknown[]).length})</span>;
        }
        return <span style={{ color: 'hsl(var(--muted-foreground))' }}>Object</span>;
      default:
        return <span>{String(value)}</span>;
    }
  };

  if (depth > maxDepth) {
    return null;
  }

  return (
    <div>
      <div
        className="flex items-center gap-1 py-0.5 hover:bg-muted/30 rounded cursor-pointer"
        style={{ paddingLeft: `${indent}px` }}
        onClick={() => isExpandable && setIsExpanded(!isExpanded)}
      >
        {isExpandable && (
          <span className="w-4 h-4 flex items-center justify-center">
            {isExpanded ? (
              <ChevronDown className="h-3 w-3" style={{ color: 'hsl(var(--muted-foreground))' }} />
            ) : (
              <ChevronRight className="h-3 w-3" style={{ color: 'hsl(var(--muted-foreground))' }} />
            )}
          </span>
        )}
        {!isExpandable && <span className="w-4" />}

        <span className="font-medium text-sm" style={{ color: 'hsl(var(--foreground))' }}>
          {name}:
        </span>
        <span className="text-sm ml-1">{renderValue()}</span>
      </div>

      {isExpandable && isExpanded && (
        <div>
          {isArray &&
            (value as unknown[]).map((item, index) => (
              <TreeNode
                key={index}
                name={`[${index}]`}
                value={item}
                depth={depth + 1}
                maxDepth={maxDepth}
              />
            ))}
          {isObject &&
            Object.entries(value as Record<string, unknown>).map(([key, val]) => (
              <TreeNode key={key} name={key} value={val} depth={depth + 1} maxDepth={maxDepth} />
            ))}
        </div>
      )}
    </div>
  );
}

export function NodeResultViewer({ data, maxDepth = 5 }: NodeResultViewerProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
    }
  };

  return (
    <div
      className="border rounded p-2 text-xs font-mono"
      style={{
        backgroundColor: 'hsl(var(--muted) / 0.3)',
        borderColor: 'hsl(var(--border))',
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold" style={{ color: 'hsl(var(--muted-foreground))' }}>
          Output Data
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 px-2 gap-1"
          onClick={handleCopy}
        >
          {copied ? (
            <>
              <Check className="h-3 w-3" />
              Copied
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              Copy
            </>
          )}
        </Button>
      </div>

      <div className="max-h-64 overflow-y-auto">
        {Object.entries(data).map(([key, value]) => (
          <TreeNode key={key} name={key} value={value} depth={0} maxDepth={maxDepth} />
        ))}
      </div>
    </div>
  );
}
