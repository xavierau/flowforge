/**
 * HumanReviewNode - Human-in-the-Loop (HITL) review step
 * Pauses workflow execution for human review and approval
 */

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { UserCheck, CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import type { HumanReviewNodeData, HumanReviewPriority } from '@/types/workflow';

interface HumanReviewNodeProps extends NodeProps {
  data: HumanReviewNodeData;
}

/**
 * Get priority badge styling
 */
function getPriorityStyle(priority: HumanReviewPriority | undefined): {
  backgroundColor: string;
  color: string;
  label: string;
} {
  switch (priority) {
    case 'critical':
      return {
        backgroundColor: '#dc2626',
        color: 'white',
        label: 'Critical',
      };
    case 'high':
      return {
        backgroundColor: '#ea580c',
        color: 'white',
        label: 'High',
      };
    case 'normal':
      return {
        backgroundColor: '#2563eb',
        color: 'white',
        label: 'Normal',
      };
    case 'low':
      return {
        backgroundColor: '#6b7280',
        color: 'white',
        label: 'Low',
      };
    default:
      return {
        backgroundColor: '#2563eb',
        color: 'white',
        label: 'Normal',
      };
  }
}

export const HumanReviewNode = memo(({ data, selected }: HumanReviewNodeProps) => {
  const hasErrors = data.errors.length > 0;
  const instructions = data.config?.instructions || '';
  const priority = data.config?.priority;
  const timeoutHours = data.config?.timeoutHours;
  const requiredFields = data.config?.requiredFields || [];

  // Truncate instructions for display
  const displayInstructions = instructions.length > 60
    ? `${instructions.substring(0, 60)}...`
    : instructions;

  const priorityStyle = getPriorityStyle(priority);

  return (
    <div
      className="min-w-[240px] rounded-lg border-2 shadow-md"
      style={{
        borderColor: selected
          ? 'hsl(var(--primary))'
          : hasErrors
          ? 'hsl(var(--destructive))'
          : data.isValid
          ? '#f59e0b' // Amber/Orange for Human Review
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
          backgroundColor: '#f59e0b',
          border: '2px solid hsl(var(--background))',
        }}
      />

      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2 rounded-t-md"
        style={{
          backgroundColor: '#f59e0b',
        }}
      >
        <UserCheck className="w-4 h-4 text-white" />
        <span className="font-semibold text-sm text-white">
          {data.label}
        </span>
        {/* HITL Badge */}
        <span
          className="text-xs font-bold px-1.5 py-0.5 rounded ml-auto"
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.25)',
            color: 'white',
          }}
        >
          HITL
        </span>
        {data.isValid ? (
          <CheckCircle2
            className="w-4 h-4"
            style={{ color: '#22c55e' }}
          />
        ) : hasErrors ? (
          <AlertCircle
            className="w-4 h-4"
            style={{ color: 'white' }}
          />
        ) : null}
      </div>

      {/* Body */}
      <div className="px-3 py-3">
        <div className="space-y-2">
          {/* Priority and Timeout badges */}
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className="text-xs font-medium px-2 py-0.5 rounded"
              style={{
                backgroundColor: priorityStyle.backgroundColor,
                color: priorityStyle.color,
              }}
            >
              {priorityStyle.label}
            </span>
            {timeoutHours && (
              <span
                className="text-xs px-2 py-0.5 rounded flex items-center gap-1"
                style={{
                  backgroundColor: 'hsl(var(--muted))',
                  color: 'hsl(var(--muted-foreground))',
                }}
              >
                <Clock className="w-3 h-3" />
                {timeoutHours}h
              </span>
            )}
          </div>

          {/* Instructions Preview */}
          {instructions && (
            <div>
              <div className="text-xs font-medium mb-1" style={{ color: 'hsl(var(--muted-foreground))' }}>
                Instructions:
              </div>
              <div
                className="text-xs rounded p-2 break-words"
                style={{
                  backgroundColor: 'hsl(var(--muted))',
                  color: 'hsl(var(--foreground))',
                }}
              >
                {displayInstructions}
              </div>
            </div>
          )}

          {/* Required Fields */}
          {requiredFields.length > 0 && (
            <div>
              <div className="text-xs font-medium mb-1" style={{ color: 'hsl(var(--muted-foreground))' }}>
                Required fields ({requiredFields.length}):
              </div>
              <div className="flex flex-wrap gap-1">
                {requiredFields.slice(0, 3).map((field, index) => (
                  <span
                    key={index}
                    className="text-xs px-1.5 py-0.5 rounded"
                    style={{
                      backgroundColor: 'hsl(var(--muted))',
                      color: 'hsl(var(--foreground))',
                    }}
                  >
                    {field}
                  </span>
                ))}
                {requiredFields.length > 3 && (
                  <span
                    className="text-xs px-1.5 py-0.5 rounded"
                    style={{
                      backgroundColor: 'hsl(var(--muted))',
                      color: 'hsl(var(--muted-foreground))',
                    }}
                  >
                    +{requiredFields.length - 3} more
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Not configured state */}
          {!instructions && requiredFields.length === 0 && (
            <div
              className="text-xs text-center py-2 rounded"
              style={{
                backgroundColor: 'hsl(var(--muted))',
                color: 'hsl(var(--muted-foreground))',
              }}
            >
              Configure review instructions
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

      {/* Output handles footer */}
      <div
        className="flex justify-between items-center px-3 py-2 border-t rounded-b-md"
        style={{
          borderColor: 'hsl(var(--border))',
          backgroundColor: 'hsl(var(--muted) / 0.3)',
        }}
      >
        {/* Approved handle */}
        <div className="flex items-center gap-1.5 relative">
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: '#22c55e' }}
          />
          <span className="text-xs font-semibold" style={{ color: '#22c55e' }}>
            Approved
          </span>
          <Handle
            type="source"
            position={Position.Bottom}
            id="approved"
            style={{
              left: '25%',
              width: '12px',
              height: '12px',
              backgroundColor: '#22c55e',
              border: '2px solid hsl(var(--background))',
            }}
          />
        </div>

        {/* Rejected handle */}
        <div className="flex items-center gap-1.5 relative">
          <span className="text-xs font-semibold" style={{ color: '#ef4444' }}>
            Rejected
          </span>
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: '#ef4444' }}
          />
          <Handle
            type="source"
            position={Position.Bottom}
            id="rejected"
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

HumanReviewNode.displayName = 'HumanReviewNode';
