/**
 * HttpRequestNode - Make HTTP requests with previous node data
 * Configures URL, method, and headers
 */

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Send, CheckCircle2, AlertCircle } from 'lucide-react';
import type { HttpRequestNodeData, HttpHeader } from '@/types/workflow';

interface HttpRequestNodeProps extends NodeProps {
  data: HttpRequestNodeData;
}

export const HttpRequestNode = memo(({ data, selected }: HttpRequestNodeProps) => {
  const hasErrors = data.errors.length > 0;

  return (
    <div
      className="min-w-[200px] rounded-lg border-2 shadow-md"
      style={{
        borderColor: selected
          ? 'hsl(var(--primary))'
          : hasErrors
          ? 'hsl(var(--destructive))'
          : data.isValid
          ? 'hsl(var(--success))'
          : 'hsl(var(--border))',
        backgroundColor: 'hsl(var(--card))',
      }}
    >
      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        style={{
          width: '12px',
          height: '12px',
          backgroundColor: 'hsl(var(--primary))',
          border: '2px solid hsl(var(--background))',
        }}
      />

      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2 rounded-t-md"
        style={{
          backgroundColor: 'hsl(var(--muted))',
        }}
      >
        <Send className="w-4 h-4" style={{ color: 'hsl(var(--primary))' }} />
        <span className="font-semibold text-sm" style={{ color: 'hsl(var(--foreground))' }}>
          {data.label}
        </span>
        {data.isValid ? (
          <CheckCircle2
            className="w-4 h-4 ml-auto"
            style={{ color: 'hsl(var(--success))' }}
          />
        ) : hasErrors ? (
          <AlertCircle
            className="w-4 h-4 ml-auto"
            style={{ color: 'hsl(var(--destructive))' }}
          />
        ) : null}
      </div>

      {/* Body */}
      <div className="px-3 py-2">
        <div className="space-y-1">
          <div className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
            <span
              className="font-medium px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: 'hsl(var(--primary) / 0.1)',
                color: 'hsl(var(--primary))',
              }}
            >
              {data.config.method}
            </span>
          </div>
          {data.config.url && (
            <div className="text-xs truncate" style={{ color: 'hsl(var(--muted-foreground))' }}>
              {data.config.url.substring(0, 35)}
              {data.config.url.length > 35 ? '...' : ''}
            </div>
          )}
          {data.config.headers.length > 0 && (
            <div className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
              {data.config.headers.filter((h: HttpHeader) => h.enabled).length} header(s)
            </div>
          )}
        </div>

        {/* Show first error if any */}
        {hasErrors && (
          <div className="mt-2 text-xs" style={{ color: 'hsl(var(--destructive))' }}>
            {data.errors[0].message}
          </div>
        )}
      </div>

      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        style={{
          width: '12px',
          height: '12px',
          backgroundColor: 'hsl(var(--primary))',
          border: '2px solid hsl(var(--background))',
        }}
      />
    </div>
  );
});

HttpRequestNode.displayName = 'HttpRequestNode';
