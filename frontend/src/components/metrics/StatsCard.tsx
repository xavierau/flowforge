/**
 * StatsCard Component
 *
 * Displays a single metric statistic with icon, title, and formatted value.
 * Follows React best practices:
 * - Single Responsibility: Only displays one stat
 * - Composition: Uses shadcn/ui Card components
 * - Flexibility: Supports multiple format types
 * - Type Safety: Full TypeScript support
 * - No side effects: Pure presentational component
 */

import { Card, CardContent } from '@/components/ui/card';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Value format types for different display styles
 */
type ValueFormat = 'number' | 'currency' | 'percentage';

interface StatsCardProps {
  /**
   * Card title
   */
  title: string;

  /**
   * Stat value (will be formatted according to format prop)
   */
  value: number;

  /**
   * Icon component from lucide-react
   */
  icon: LucideIcon;

  /**
   * Optional description or subtitle
   */
  description?: string;

  /**
   * Format type for value display
   * @default 'number'
   */
  format?: ValueFormat;

  /**
   * Optional className for custom styling
   */
  className?: string;
}

/**
 * Formats a number based on the specified format type
 */
function formatValue(value: number, format: ValueFormat): string {
  switch (format) {
    case 'currency':
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(value);

    case 'percentage':
      return `${value.toFixed(1)}%`;

    case 'number':
    default:
      return new Intl.NumberFormat('en-US', {
        maximumFractionDigits: 0,
      }).format(value);
  }
}

/**
 * StatsCard Component
 *
 * Displays a metric with icon, title, formatted value, and optional description.
 *
 * @example
 * ```tsx
 * <StatsCard
 *   title="Total Jobs"
 *   value={1234}
 *   icon={FileText}
 *   description="Last 30 days"
 *   format="number"
 * />
 * ```
 *
 * @example
 * ```tsx
 * <StatsCard
 *   title="Total Cost"
 *   value={45.67}
 *   icon={DollarSign}
 *   format="currency"
 * />
 * ```
 */
export function StatsCard({
  title,
  value,
  icon: Icon,
  description,
  format = 'number',
  className,
}: StatsCardProps) {
  const formattedValue = formatValue(value, format);

  return (
    <Card className={cn('', className)}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between space-x-4">
          {/* Icon */}
          <div className="flex-shrink-0">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
              <Icon className="h-6 w-6 text-primary" aria-hidden="true" />
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-muted-foreground truncate">
              {title}
            </p>
            <p className="mt-1 text-2xl font-bold text-foreground">
              {formattedValue}
            </p>
            {description && (
              <p className="mt-1 text-xs text-muted-foreground truncate">
                {description}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
