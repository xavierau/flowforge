/**
 * LLMNode - Execute LLM prompts with workflow data
 * Supports multiple providers (Google, OpenAI) and configurable parameters
 */

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Brain, CheckCircle2, AlertCircle } from 'lucide-react';
import type { LLMNodeData } from '@/types/workflow';

interface LLMNodeProps extends NodeProps {
  data: LLMNodeData;
}

/**
 * Get provider badge color based on provider name
 */
function getProviderColor(provider: string): string {
  switch (provider) {
    case 'google':
      return '#4285f4'; // Google Blue
    case 'openai':
      return '#10a37f'; // OpenAI Green
    default:
      return '#3b82f6'; // Default Blue
  }
}

/**
 * Get provider display name
 */
function getProviderDisplayName(provider: string): string {
  switch (provider) {
    case 'google':
      return 'Google';
    case 'openai':
      return 'OpenAI';
    default:
      return provider;
  }
}

export const LLMNode = memo(({ data, selected }: LLMNodeProps) => {
  const hasErrors = data.errors.length > 0;
  const provider = data.config?.provider || '';
  const model = data.config?.model || '';
  const prompt = data.config?.prompt || '';
  const temperature = data.config?.temperature;
  const isDefaultTemperature = temperature === undefined || temperature === 0.7;

  // Truncate prompt for display
  const displayPrompt = prompt.length > 50
    ? `${prompt.substring(0, 50)}...`
    : prompt;

  const providerColor = getProviderColor(provider);

  return (
    <div
      className="min-w-[220px] rounded-lg border-2 shadow-md"
      style={{
        borderColor: selected
          ? 'hsl(var(--primary))'
          : hasErrors
          ? 'hsl(var(--destructive))'
          : data.isValid
          ? '#3b82f6' // Blue for LLM
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
          backgroundColor: '#3b82f6',
          border: '2px solid hsl(var(--background))',
        }}
      />

      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2 rounded-t-md"
        style={{
          backgroundColor: '#3b82f6',
        }}
      >
        <Brain className="w-4 h-4 text-white" />
        <span className="font-semibold text-sm text-white">
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
            style={{ color: 'white' }}
          />
        ) : null}
      </div>

      {/* Body */}
      <div className="px-3 py-3">
        <div className="space-y-2">
          {/* Provider and Model badges */}
          <div className="flex items-center gap-2 flex-wrap">
            {provider && (
              <span
                className="text-xs font-medium px-2 py-0.5 rounded"
                style={{
                  backgroundColor: providerColor,
                  color: 'white',
                }}
              >
                {getProviderDisplayName(provider)}
              </span>
            )}
            {model && (
              <span
                className="text-xs px-2 py-0.5 rounded"
                style={{
                  backgroundColor: 'hsl(var(--muted))',
                  color: 'hsl(var(--foreground))',
                }}
              >
                {model}
              </span>
            )}
          </div>

          {/* Temperature badge (if not default) */}
          {!isDefaultTemperature && temperature !== undefined && (
            <div className="flex items-center gap-1">
              <span
                className="text-xs px-1.5 py-0.5 rounded"
                style={{
                  backgroundColor: 'hsl(var(--muted))',
                  color: 'hsl(var(--muted-foreground))',
                }}
              >
                temp: {temperature}
              </span>
            </div>
          )}

          {/* Prompt Preview */}
          {prompt && (
            <div>
              <div className="text-xs font-medium mb-1" style={{ color: 'hsl(var(--muted-foreground))' }}>
                Prompt:
              </div>
              <div
                className="text-xs rounded p-2 break-words"
                style={{
                  backgroundColor: 'hsl(var(--muted))',
                  color: 'hsl(var(--foreground))',
                }}
              >
                {displayPrompt || 'Not configured'}
              </div>
            </div>
          )}

          {/* Not configured state */}
          {!provider && !model && !prompt && (
            <div
              className="text-xs text-center py-2 rounded"
              style={{
                backgroundColor: 'hsl(var(--muted))',
                color: 'hsl(var(--muted-foreground))',
              }}
            >
              Configure LLM settings
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
          backgroundColor: '#3b82f6',
          border: '2px solid hsl(var(--background))',
        }}
      />
    </div>
  );
});

LLMNode.displayName = 'LLMNode';
