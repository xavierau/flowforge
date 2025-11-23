/**
 * IfNode - Conditional branching node
 * Evaluates a condition and routes to True or False paths
 */

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { GitBranch, CheckCircle2, AlertCircle } from 'lucide-react';
import type { IfNodeData } from '@/types/workflow';

interface IfNodeProps extends NodeProps {
  data: IfNodeData;
}

export const IfNode = memo(({ data, selected }: IfNodeProps) => {
  const hasErrors = data.errors.length > 0;
  const condition = data.config?.condition || '';

  return (
    <div
      className="min-w-[250px] rounded-lg border-2 shadow-md"
      style={{
        borderColor: selected
          ? 'hsl(var(--primary))'
          : hasErrors
          ? 'hsl(var(--destructive))'
          : data.isValid
          ? '#22c55e'
          : 'hsl(var(--border))',
        backgroundColor: 'hsl(var(--card))',
      }}
    >
      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Top}
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
        <GitBranch className="w-4 h-4" style={{ color: 'hsl(var(--primary))' }} />
        <span className="font-semibold text-sm" style={{ color: 'hsl(var(--foreground))' }}>
          {data.label}
        </span>
        {data.isValid ? (
          <CheckCircle2
            className="w-4 h-4 ml-auto"
            style={{ color: '#22c55e' }}
          />
        ) : hasErrors ? (
          <AlertCircle
            className="w-4 h-4 ml-auto"
            style={{ color: 'hsl(var(--destructive))' }}
          />
        ) : null}
      </div>

      {/* Body */}
      <div className="px-3 py-3">
        <div className="space-y-2">
          <div className="text-xs font-medium" style={{ color: 'hsl(var(--muted-foreground))' }}>
            Condition:
          </div>
          <div
            className="text-xs font-mono rounded p-2 break-words"
            style={{
              backgroundColor: 'hsl(var(--muted))',
              color: condition ? 'hsl(var(--foreground))' : 'hsl(var(--muted-foreground))',
            }}
          >
            {condition || 'Not configured'}
          </div>
        </div>

        {/* Show first error if any */}
        {hasErrors && (
          <div className="mt-2 text-xs" style={{ color: 'hsl(var(--destructive))' }}>
            {data.errors[0].message}
          </div>
        )}
      </div>

      {/* Output handles footer */}
      <div
        className="flex justify-between items-center px-3 py-2 border-t rounded-b-md"
        style={{
          borderColor: 'hsl(var(--border))',
          backgroundColor: 'hsl(var(--muted) / 0.3)',
        }}
      >
        {/* True handle */}
        <div className="flex items-center gap-1.5 relative">
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: '#22c55e' }}
          />
          <span className="text-xs font-semibold" style={{ color: '#22c55e' }}>
            True
          </span>
          <Handle
            type="source"
            position={Position.Bottom}
            id="true"
            style={{
              left: '25%',
              width: '12px',
              height: '12px',
              backgroundColor: '#22c55e',
              border: '2px solid hsl(var(--background))',
            }}
          />
        </div>

        {/* False handle */}
        <div className="flex items-center gap-1.5 relative">
          <span className="text-xs font-semibold" style={{ color: '#ef4444' }}>
            False
          </span>
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: '#ef4444' }}
          />
          <Handle
            type="source"
            position={Position.Bottom}
            id="false"
            style={{
              left: '75%',
              width: '12px',
              height: '12px',
              backgroundColor: '#ef4444',
              border: '2px solid hsl(var(--background))',
            }}
          />
        </div>
      </div>
    </div>
  );
});

IfNode.displayName = 'IfNode';
