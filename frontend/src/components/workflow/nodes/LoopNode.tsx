/**
 * LoopNode - Iterates over an array and executes child workflow for each item
 * Provides loop context variables: $loop.item, $loop.index, etc.
 */

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Repeat, CheckCircle2, AlertCircle } from 'lucide-react';
import type { LoopNodeData } from '@/types/workflow';

interface LoopNodeProps extends NodeProps {
  data: LoopNodeData;
}

export const LoopNode = memo(({ data, selected }: LoopNodeProps) => {
  const hasErrors = data.errors.length > 0;
  const arrayExpression = data.config?.arrayExpression || '';
  const maxIterations = data.config?.maxIterations;
  const continueOnError = data.config?.continueOnError;

  // Truncate expression for display
  const displayExpression = arrayExpression.length > 40
    ? `${arrayExpression.substring(0, 40)}...`
    : arrayExpression;

  return (
    <div
      className="min-w-[220px] rounded-lg border-2 shadow-md"
      style={{
        borderColor: selected
          ? 'hsl(var(--primary))'
          : hasErrors
          ? 'hsl(var(--destructive))'
          : data.isValid
          ? '#8b5cf6' // Purple/Violet for Loop
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
          backgroundColor: '#8b5cf6',
          border: '2px solid hsl(var(--background))',
        }}
      />

      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2 rounded-t-md"
        style={{
          backgroundColor: '#8b5cf6',
        }}
      >
        <Repeat className="w-4 h-4 text-white" />
        <span className="font-semibold text-sm text-white">
          {data.label}
        </span>
        {/* Max iterations badge */}
        {maxIterations && (
          <span
            className="ml-auto text-xs px-1.5 py-0.5 rounded"
            style={{
              backgroundColor: 'rgba(255, 255, 255, 0.2)',
              color: 'white',
            }}
          >
            max: {maxIterations}
          </span>
        )}
        {data.isValid ? (
          <CheckCircle2
            className={`w-4 h-4 ${maxIterations ? '' : 'ml-auto'}`}
            style={{ color: '#22c55e' }}
          />
        ) : hasErrors ? (
          <AlertCircle
            className={`w-4 h-4 ${maxIterations ? '' : 'ml-auto'}`}
            style={{ color: 'hsl(var(--destructive))' }}
          />
        ) : null}
      </div>

      {/* Body */}
      <div className="px-3 py-3">
        <div className="space-y-2">
          {/* Array Expression */}
          <div>
            <div className="text-xs font-medium mb-1" style={{ color: 'hsl(var(--muted-foreground))' }}>
              Iterate over:
            </div>
            <div
              className="text-xs font-mono rounded p-2 break-words"
              style={{
                backgroundColor: 'hsl(var(--muted))',
                color: arrayExpression ? 'hsl(var(--foreground))' : 'hsl(var(--muted-foreground))',
              }}
            >
              {displayExpression || 'Not configured'}
            </div>
          </div>

          {/* Continue on Error Badge */}
          {continueOnError && (
            <div className="flex items-center gap-1">
              <span
                className="text-xs px-1.5 py-0.5 rounded"
                style={{
                  backgroundColor: 'hsl(var(--muted))',
                  color: 'hsl(var(--muted-foreground))',
                }}
              >
                Continue on error
              </span>
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

      {/* Loop body handle (bottom) */}
      <div
        className="flex justify-center items-center px-3 py-2 border-t rounded-b-md"
        style={{
          borderColor: 'hsl(var(--border))',
          backgroundColor: 'hsl(var(--muted) / 0.3)',
        }}
      >
        <div className="flex items-center gap-1.5">
          <Repeat className="w-3 h-3" style={{ color: '#8b5cf6' }} />
          <span className="text-xs font-medium" style={{ color: '#8b5cf6' }}>
            Loop Body
          </span>
        </div>
      </div>

      {/* Output handle (right) - for after loop completion */}
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        style={{
          width: '12px',
          height: '12px',
          backgroundColor: '#8b5cf6',
          border: '2px solid hsl(var(--background))',
        }}
      />

      {/* Loop body handle (bottom) - connects to nodes inside the loop */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="loop-body"
        style={{
          width: '12px',
          height: '12px',
          backgroundColor: '#a78bfa',
          border: '2px solid hsl(var(--background))',
        }}
      />
    </div>
  );
});

LoopNode.displayName = 'LoopNode';
