/**
 * MarkdownPipelineConfig Component
 *
 * Configuration form section for markdown pipeline options.
 * Extracted from JobCreate to follow Single Responsibility Principle.
 *
 * Design Principles:
 * - Single Responsibility: Handles markdown pipeline configuration UI only
 * - Controlled Component: Parent manages state
 * - Composition: Uses shadcn/ui components
 * - Accessible: Proper labels, descriptions, and ARIA attributes
 */

import { InfoIcon } from 'lucide-react';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  MarkdownConverter,
  MarkdownFormat,
  getMarkdownConverterLabel,
  getMarkdownConverterDescription,
  getMarkdownFormatLabel,
} from '@/types/enums';

interface MarkdownPipelineConfigProps {
  converter: MarkdownConverter;
  format: MarkdownFormat;
  onConverterChange: (converter: MarkdownConverter) => void;
  onFormatChange: (format: MarkdownFormat) => void;
  disabled?: boolean;
}

export function MarkdownPipelineConfig({
  converter,
  format,
  onConverterChange,
  onFormatChange,
  disabled = false,
}: MarkdownPipelineConfigProps) {
  return (
    <div className="space-y-4 p-4 border rounded-lg" style={{ backgroundColor: 'hsl(var(--muted) / 0.3)' }}>
      <div className="flex items-start gap-2">
        <InfoIcon className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" aria-hidden="true" />
        <div className="space-y-1">
          <p className="text-sm font-medium">Markdown Pipeline</p>
          <p className="text-xs text-muted-foreground">
            Two-stage extraction: Image → Layout-preserving markdown (cached for reuse) → JSON (cheap).
            Best for documents with 3+ pages or complex tables.
          </p>
        </div>
      </div>

      <div className="space-y-4 pt-2">
        <div className="space-y-2">
          <Label htmlFor="markdown-converter">
            Markdown Converter
          </Label>
          <Select
            value={converter}
            onValueChange={(value) => onConverterChange(value as MarkdownConverter)}
            disabled={disabled}
          >
            <SelectTrigger id="markdown-converter">
              <SelectValue placeholder="Select converter..." />
            </SelectTrigger>
            <SelectContent>
              {Object.values(MarkdownConverter).map((conv) => (
                <SelectItem key={conv} value={conv}>
                  <div className="flex flex-col items-start">
                    <span>{getMarkdownConverterLabel(conv)}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            {getMarkdownConverterDescription(converter)}
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="markdown-format">
            Markdown Format Style
          </Label>
          <Select
            value={format}
            onValueChange={(value) => onFormatChange(value as MarkdownFormat)}
            disabled={disabled}
          >
            <SelectTrigger id="markdown-format">
              <SelectValue placeholder="Select format..." />
            </SelectTrigger>
            <SelectContent>
              {Object.values(MarkdownFormat).map((fmt) => (
                <SelectItem key={fmt} value={fmt}>
                  {getMarkdownFormatLabel(fmt)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            {format === MarkdownFormat.TABLE_HEAVY && 'Optimized for documents with many tables'}
            {format === MarkdownFormat.LAYOUT_PRESERVED && 'Maintains original document layout structure'}
            {format === MarkdownFormat.STANDARD && 'General-purpose markdown format'}
          </p>
        </div>
      </div>
    </div>
  );
}
