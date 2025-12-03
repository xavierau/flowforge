/**
 * ConfidenceBadge Component
 *
 * Displays AI confidence score with visual indicators.
 * Design: Clean, composable, type-safe.
 */

import { getConfidenceBadgeProps, getConfidenceLevel } from '@/types/review';
import { cn } from '@/lib/utils';

interface ConfidenceBadgeProps {
  score: number | null;
  showPercentage?: boolean;
  className?: string;
}

export function ConfidenceBadge({
  score,
  showPercentage = true,
  className,
}: ConfidenceBadgeProps) {
  const { label, color, icon } = getConfidenceBadgeProps(score);
  const level = getConfidenceLevel(score);

  // Background colors based on level
  const bgColor = {
    high: 'bg-green-50',
    medium: 'bg-orange-50',
    low: 'bg-red-50',
    unknown: 'bg-gray-50',
  }[level];

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
        bgColor,
        color,
        className
      )}
      title={label}
    >
      <span className="text-sm">{icon}</span>
      {showPercentage && score !== null && (
        <span>{Math.round(score * 100)}%</span>
      )}
      {!showPercentage && <span>{label}</span>}
    </div>
  );
}
