/**
 * JoinNode - Synchronization barrier for parallel branches
 * Waits for ALL incoming branches to complete before proceeding
 * Maps to Conductor's JOIN task type
 */

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Merge, CheckCircle2, AlertCircle, Users } from 'lucide-react';
import type { JoinNodeData } from '@/types/workflow';

interface JoinNodeProps extends NodeProps {
  data: JoinNodeData;
}

export const JoinNode = memo(({ data, selected }: JoinNodeProps) => {
  const hasErrors = data.errors.length > 0;

  return (
    <div
      className="min-w-[220px] rounded-lg border-2 shadow-md"
      style={{
        borderColor: selected
          ? 'hsl(var(--primary))'
          : hasErrors
          ? 'hsl(var(--destructive))'
          : data.isValid
          ? '#3b82f6' // Blue for join operations
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
        <Merge className="w-4 h-4" style={{ color: '#3b82f6' }} />
        <span className="font-semibold text-sm" style={{ color: 'hsl(var(--foreground))' }}>
          {data.label}
        </span>
        {data.isValid ? (
          <CheckCircle2
            className="w-4 h-4 ml-auto"
            style={{ color: '#3b82f6' }}
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
          {/* Info Section */}
          <div
            className="flex items-start gap-2 p-2 rounded"
            style={{
              backgroundColor: 'hsl(var(--muted) / 0.5)',
            }}
          >
            <Users className="w-4 h-4 mt-0.5 flex-shrink-0" style={{ color: '#3b82f6' }} />
            <div className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
              <p className="font-medium mb-1">Synchronization Barrier</p>
              <p>
                Waits for ALL incoming branches to complete before executing downstream tasks.
              </p>
            </div>
          </div>

          {/* Behavior Description */}
          <div
            className="p-2 rounded border text-xs"
            style={{
              backgroundColor: 'hsl(var(--muted) / 0.3)',
              borderColor: 'hsl(var(--border))',
              color: 'hsl(var(--muted-foreground))',
            }}
          >
            <p className="font-medium mb-1">Behavior:</p>
            <ul className="list-disc list-inside space-y-0.5">
              <li>Blocks until all inputs arrive</li>
              <li>Aggregates upstream outputs</li>
              <li>Enables parallel branch convergence</li>
            </ul>
          </div>
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
        position={Position.Bottom}
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

JoinNode.displayName = 'JoinNode';
