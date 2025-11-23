/**
 * ExtractionNode - Document extraction with schema
 * Configures file source, prompt, and extraction schema
 */

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { FileText, CheckCircle2, AlertCircle } from 'lucide-react';
import type { ExtractionNodeData } from '@/types/workflow';

interface ExtractionNodeProps extends NodeProps {
  data: ExtractionNodeData;
}

export const ExtractionNode = memo(({ data, selected }: ExtractionNodeProps) => {
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
        <FileText className="w-4 h-4" style={{ color: 'hsl(var(--primary))' }} />
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
            <span className="font-medium">Source:</span> {data.config.fileSource}
          </div>
          {data.config.schemaId && (
            <div className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
              <span className="font-medium">Schema:</span> {data.config.schemaId}
            </div>
          )}
          {data.config.prompt && (
            <div className="text-xs truncate" style={{ color: 'hsl(var(--muted-foreground))' }}>
              <span className="font-medium">Prompt:</span> {data.config.prompt.substring(0, 30)}
              {data.config.prompt.length > 30 ? '...' : ''}
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

ExtractionNode.displayName = 'ExtractionNode';
