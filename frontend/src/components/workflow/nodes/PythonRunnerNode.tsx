/**
 * PythonRunnerNode - Execute Python code on extraction results
 * Embeds CodeMirror for Python editing
 */

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Code, CheckCircle2, AlertCircle } from 'lucide-react';
import type { PythonRunnerNodeData } from '@/types/workflow';

interface PythonRunnerNodeProps extends NodeProps {
  data: PythonRunnerNodeData;
}

export const PythonRunnerNode = memo(({ data, selected }: PythonRunnerNodeProps) => {
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
        <Code className="w-4 h-4" style={{ color: 'hsl(var(--primary))' }} />
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
        <div className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
          Python code execution
        </div>
        <div className="text-xs mt-1" style={{ color: 'hsl(var(--muted-foreground))' }}>
          Input: {'{data: extraction_result}'}
        </div>
        {data.config.code && (
          <div className="mt-2 text-xs font-mono p-2 rounded" style={{
            backgroundColor: 'hsl(var(--muted))',
            color: 'hsl(var(--muted-foreground))'
          }}>
            {data.config.code.split('\n')[0].substring(0, 40)}
            {data.config.code.length > 40 ? '...' : ''}
          </div>
        )}

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

PythonRunnerNode.displayName = 'PythonRunnerNode';
