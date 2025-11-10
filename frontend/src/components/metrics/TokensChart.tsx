/**
 * TokensChart Component
 *
 * Stacked area chart displaying token usage over time (input/output/total).
 * Follows React best practices:
 * - Single Responsibility: Only displays token usage time series
 * - No side effects: Pure presentational component
 * - Proper composition: Uses Recharts components
 * - Responsive design: Auto-adjusts to container size
 * - Accessibility: Includes proper labels and legend
 */

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { TokenUsageData } from '@/types/metrics';
import { format, parseISO } from 'date-fns';

interface TokensChartProps {
  /**
   * Token usage time series data
   */
  data: TokenUsageData[];

  /**
   * Optional chart title
   * @default "Token Usage"
   */
  title?: string;

  /**
   * Optional className for card styling
   */
  className?: string;
}

/**
 * Custom tooltip for displaying formatted token data
 */
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const data = payload[0].payload;

  return (
    <div className="rounded-lg border bg-background p-3 shadow-md">
      <p className="text-sm font-medium mb-2">
        {format(parseISO(data.date), 'MMM dd, yyyy')}
      </p>
      <div className="space-y-1">
        <p className="text-xs text-muted-foreground flex items-center justify-between gap-3">
          <span className="flex items-center gap-1">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: 'hsl(var(--chart-1))' }}
            />
            Input Tokens:
          </span>
          <span className="font-semibold text-foreground">
            {data.input_tokens.toLocaleString()}
          </span>
        </p>
        <p className="text-xs text-muted-foreground flex items-center justify-between gap-3">
          <span className="flex items-center gap-1">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: 'hsl(var(--chart-2))' }}
            />
            Output Tokens:
          </span>
          <span className="font-semibold text-foreground">
            {data.output_tokens.toLocaleString()}
          </span>
        </p>
        <div className="border-t pt-1 mt-1">
          <p className="text-xs font-medium flex items-center justify-between gap-3">
            <span>Total:</span>
            <span>{data.total_tokens.toLocaleString()}</span>
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * TokensChart Component
 *
 * Renders a stacked area chart showing input, output, and total token usage over time.
 * Provides visual breakdown of token consumption patterns.
 *
 * @example
 * ```tsx
 * <TokensChart
 *   data={[
 *     {
 *       date: '2025-01-01',
 *       input_tokens: 1000,
 *       output_tokens: 500,
 *       total_tokens: 1500
 *     },
 *   ]}
 *   title="Token Usage"
 * />
 * ```
 */
export function TokensChart({
  data,
  title = 'Token Usage',
  className,
}: TokensChartProps) {
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
            <AreaChart
              data={formattedData}
              margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
            >
              <defs>
                <linearGradient id="colorInput" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor="hsl(var(--chart-1))"
                    stopOpacity={0.8}
                  />
                  <stop
                    offset="95%"
                    stopColor="hsl(var(--chart-1))"
                    stopOpacity={0.1}
                  />
                </linearGradient>
                <linearGradient id="colorOutput" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor="hsl(var(--chart-2))"
                    stopOpacity={0.8}
                  />
                  <stop
                    offset="95%"
                    stopColor="hsl(var(--chart-2))"
                    stopOpacity={0.1}
                  />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="displayDate"
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
                tickFormatter={(value) => {
                  // Format large numbers with K suffix
                  return value >= 1000 ? `${(value / 1000).toFixed(0)}K` : value;
                }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: '12px' }}
                formatter={(value) => {
                  const labels: Record<string, string> = {
                    input_tokens: 'Input',
                    output_tokens: 'Output',
                  };
                  return labels[value] || value;
                }}
              />
              <Area
                type="monotone"
                dataKey="input_tokens"
                stackId="1"
                stroke="hsl(var(--chart-1))"
                fill="url(#colorInput)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="output_tokens"
                stackId="1"
                stroke="hsl(var(--chart-2))"
                fill="url(#colorOutput)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
