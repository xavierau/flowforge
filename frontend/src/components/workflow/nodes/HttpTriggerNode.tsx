/**
 * HttpTriggerNode - Entry point for workflow
 * Accepts webhook data at runtime, no configuration needed
 */

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Webhook, CheckCircle2 } from 'lucide-react';
import type { HttpTriggerNodeData } from '@/types/workflow';

interface HttpTriggerNodeProps extends NodeProps {
  data: HttpTriggerNodeData;
}

export const HttpTriggerNode = memo(({ data, selected }: HttpTriggerNodeProps) => {
  return (
    <div
      className="min-w-[200px] rounded-lg border-2 shadow-md"
      style={{
        borderColor: selected
          ? 'hsl(var(--primary))'
          : data.isValid
          ? 'hsl(var(--success))'
          : 'hsl(var(--border))',
        backgroundColor: 'hsl(var(--card))',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2 rounded-t-md"
        style={{
          backgroundColor: 'hsl(var(--muted))',
        }}
      >
        <Webhook className="w-4 h-4" style={{ color: 'hsl(var(--primary))' }} />
        <span className="font-semibold text-sm" style={{ color: 'hsl(var(--foreground))' }}>
          {data.label}
        </span>
        {data.isValid && (
          <CheckCircle2
            className="w-4 h-4 ml-auto"
            style={{ color: 'hsl(var(--success))' }}
          />
        )}
      </div>

      {/* Body */}
      <div className="px-3 py-2">
        <div className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
          Workflow trigger - accepts HTTP requests
        </div>
        <div className="text-xs mt-1" style={{ color: 'hsl(var(--muted-foreground))' }}>
          Runtime data: prompt, file_url, callback_url
        </div>
      </div>

      {/* Output handle only - no input */}
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

HttpTriggerNode.displayName = 'HttpTriggerNode';
