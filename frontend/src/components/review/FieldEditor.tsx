/**
 * FieldEditor Component
 *
 * Editable field view for review corrections with confidence indicators.
 * Following React best practices:
 * - Controlled inputs with onChange callback
 * - Proper form validation
 * - Accessibility with labels and ARIA
 * - Performance with useCallback
 */

import { useCallback, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ConfidenceBadge } from './ConfidenceBadge';
import { Edit2, Check, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ExtractedField {
  path: string;
  label: string;
  value: unknown;
  confidence?: number;
  type?: 'string' | 'number' | 'boolean' | 'array' | 'object';
}

interface FieldEditorProps {
  data: Record<string, unknown>;
  onChange: (fieldPath: string, newValue: unknown, originalValue: unknown) => void;
  className?: string;
}

export function FieldEditor({ data, onChange, className }: FieldEditorProps) {
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>('');

  // Flatten nested object into field list
  const fields = flattenObject(data);

  const handleStartEdit = useCallback((field: ExtractedField) => {
    setEditingField(field.path);
    setEditValue(String(field.value ?? ''));
  }, []);

  const handleCancelEdit = useCallback(() => {
    setEditingField(null);
    setEditValue('');
  }, []);

  const handleSaveEdit = useCallback(
    (field: ExtractedField) => {
      if (editingField === field.path) {
        // Parse value based on type
        let parsedValue: unknown = editValue;
        if (field.type === 'number') {
          parsedValue = parseFloat(editValue);
        } else if (field.type === 'boolean') {
          parsedValue = editValue === 'true';
        }

        onChange(field.path, parsedValue, field.value);
        setEditingField(null);
        setEditValue('');
      }
    },
    [editingField, editValue, onChange]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, field: ExtractedField) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSaveEdit(field);
      } else if (e.key === 'Escape') {
        handleCancelEdit();
      }
    },
    [handleSaveEdit, handleCancelEdit]
  );

  // Group fields by section (top-level keys)
  const groupedFields = groupFieldsBySection(fields);

  return (
    <Card className={cn('flex flex-col h-full overflow-auto', className)}>
      <CardHeader className="border-b">
        <CardTitle className="text-base">Extracted Fields</CardTitle>
      </CardHeader>

      <CardContent className="flex-1 p-4 space-y-6">
        {Object.entries(groupedFields).map(([section, sectionFields]) => (
          <div key={section}>
            {/* Section Header */}
            <h3 className="text-sm font-semibold mb-3 text-gray-700 uppercase tracking-wide">
              {section}
            </h3>

            {/* Fields */}
            <div className="space-y-3">
              {sectionFields.map((field) => {
                const isEditing = editingField === field.path;
                const hasLowConfidence =
                  field.confidence !== undefined && field.confidence < 0.8;

                return (
                  <div
                    key={field.path}
                    className={cn(
                      'rounded-lg border p-3 transition-colors',
                      hasLowConfidence && 'border-orange-200 bg-orange-50',
                      isEditing && 'border-primary bg-blue-50'
                    )}
                  >
                    {/* Field Label and Confidence */}
                    <div className="flex items-center justify-between mb-2">
                      <Label className="text-sm font-medium">{field.label}</Label>
                      {field.confidence !== undefined && (
                        <ConfidenceBadge score={field.confidence} showPercentage />
                      )}
                    </div>

                    {/* Field Value / Editor */}
                    {isEditing ? (
                      <div className="space-y-2">
                        {field.type === 'string' && String(field.value).length > 50 ? (
                          <Textarea
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onKeyDown={(e) => handleKeyDown(e, field)}
                            className="w-full"
                            rows={3}
                            autoFocus
                          />
                        ) : (
                          <Input
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onKeyDown={(e) => handleKeyDown(e, field)}
                            type={field.type === 'number' ? 'number' : 'text'}
                            className="w-full"
                            autoFocus
                          />
                        )}

                        {/* Edit Actions */}
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            onClick={() => handleSaveEdit(field)}
                          >
                            <Check className="h-4 w-4 mr-1" />
                            Save
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={handleCancelEdit}
                          >
                            <X className="h-4 w-4 mr-1" />
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between">
                        <div className="flex-1 text-sm">
                          {field.type === 'array' ? (
                            <Badge variant="secondary">
                              {Array.isArray(field.value) ? `${field.value.length} items` : 'Array'}
                            </Badge>
                          ) : field.type === 'object' ? (
                            <Badge variant="secondary">Object</Badge>
                          ) : (
                            <span className="font-mono">
                              {String(field.value ?? 'N/A')}
                            </span>
                          )}
                        </div>

                        {/* Edit Button */}
                        {field.type !== 'array' && field.type !== 'object' && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleStartEdit(field)}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    )}

                    {/* Field Path (for debugging) */}
                    <div className="mt-2 text-xs text-muted-foreground">
                      {field.path}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

/**
 * Flatten nested object into field list
 */
function flattenObject(
  obj: Record<string, unknown>,
  prefix = '',
  result: ExtractedField[] = []
): ExtractedField[] {
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    const label = key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

    if (value && typeof value === 'object' && !Array.isArray(value)) {
      // Nested object - recurse
      flattenObject(value as Record<string, unknown>, path, result);
    } else {
      // Leaf node - add to result
      result.push({
        path,
        label,
        value,
        type: inferType(value),
        confidence: undefined, // Could be enriched from metadata
      });
    }
  }

  return result;
}

/**
 * Infer field type from value
 */
function inferType(value: unknown): ExtractedField['type'] {
  if (Array.isArray(value)) return 'array';
  if (value === null || value === undefined) return 'string';
  if (typeof value === 'number') return 'number';
  if (typeof value === 'boolean') return 'boolean';
  if (typeof value === 'object') return 'object';
  return 'string';
}

/**
 * Group fields by top-level section
 */
function groupFieldsBySection(fields: ExtractedField[]): Record<string, ExtractedField[]> {
  const grouped: Record<string, ExtractedField[]> = {};

  for (const field of fields) {
    const section = field.path.split('.')[0] || 'General';
    if (!grouped[section]) {
      grouped[section] = [];
    }
    grouped[section].push(field);
  }

  return grouped;
}
