/**
 * JobsChart Component
 *
 * Line chart displaying jobs processed over time using Recharts.
 * Follows React best practices:
 * - Single Responsibility: Only displays jobs time series
 * - No side effects: Pure presentational component
 * - Proper composition: Uses Recharts components
 * - Responsive design: Auto-adjusts to container size
 * - Accessibility: Includes proper labels and ARIA attributes
 */

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { TimeSeriesDataPoint } from '@/types/metrics';
import { format, parseISO } from 'date-fns';

interface JobsChartProps {
  /**
   * Time series data for jobs
   */
  data: TimeSeriesDataPoint[];

  /**
   * Optional chart title
   * @default "Jobs Processed"
   */
  title?: string;

  /**
   * Optional className for card styling
   */
  className?: string;
}

/**
 * Custom tooltip for displaying formatted data
 */
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const data = payload[0];
  const date = data.payload.date;
  const value = data.value;

  return (
    <div className="rounded-lg border bg-background p-2 shadow-md">
      <p className="text-sm font-medium">
        {format(parseISO(date), 'MMM dd, yyyy')}
      </p>
      <p className="text-sm text-muted-foreground">
        Jobs: <span className="font-semibold text-foreground">{value}</span>
      </p>
    </div>
  );
}

/**
 * JobsChart Component
 *
 * Renders a line chart showing jobs processed over time.
 * Uses Recharts for visualization with responsive container.
 *
 * @example
 * ```tsx
 * <JobsChart
 *   data={[
 *     { date: '2025-01-01', value: 10 },
 *     { date: '2025-01-02', value: 15 },
 *   ]}
 *   title="Jobs Processed"
 * />
 * ```
 */
export function JobsChart({
  data,
  title = 'Jobs Processed',
  className,
}: JobsChartProps) {
  // Format date for x-axis display
  const formattedData = data.map((item) => ({
    ...item,
    displayDate: format(parseISO(item.date), 'MMM dd'),
  }));

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={formattedData}
              margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="displayDate"
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="value"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={{ fill: 'hsl(var(--primary))' }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
