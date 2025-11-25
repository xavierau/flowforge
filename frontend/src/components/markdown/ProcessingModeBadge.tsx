/**
 * ProcessingModeBadge Component
 *
 * Displays a colored badge for processing mode with appropriate icon and color.
 *
 * Design Principles:
 * - Single Responsibility: Display processing mode badge only
 * - Reusable: Can be used in list view, detail view, etc.
 * - Type-safe: Uses ProcessingMode enum
 * - Accessible: Proper ARIA labels and semantic HTML
 */

import { FileText, Files, FileCode } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { ProcessingMode, getProcessingModeLabel } from '@/types/enums';

interface ProcessingModeBadgeProps {
  mode: ProcessingMode;
  variant?: 'default' | 'secondary' | 'outline';
}

/**
 * Get icon component for processing mode
 */
function getProcessingModeIcon(mode: ProcessingMode): React.ComponentType<{ className?: string }> {
  switch (mode) {
    case ProcessingMode.PER_PAGE:
      return FileText;
    case ProcessingMode.BATCH:
      return Files;
    case ProcessingMode.MARKDOWN:
      return FileCode;
    default:
      return FileText;
  }
}

/**
 * Get color variant for processing mode
 */
function getProcessingModeVariant(mode: ProcessingMode): 'default' | 'secondary' | 'outline' {
  switch (mode) {
    case ProcessingMode.PER_PAGE:
      return 'secondary';
    case ProcessingMode.BATCH:
      return 'default';
    case ProcessingMode.MARKDOWN:
      return 'outline';
    default:
      return 'secondary';
  }
}

export function ProcessingModeBadge({ mode, variant }: ProcessingModeBadgeProps) {
  const Icon = getProcessingModeIcon(mode);
  const badgeVariant = variant || getProcessingModeVariant(mode);
  const label = getProcessingModeLabel(mode);

  return (
    <Badge variant={badgeVariant} className="gap-1">
      <Icon className="h-3 w-3" aria-hidden="true" />
      <span>{label}</span>
    </Badge>
  );
}
