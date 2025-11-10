/**
 * ModelDistributionChart Component
 *
 * Pie chart displaying model usage distribution.
 * Follows React best practices:
 * - Single Responsibility: Only displays model distribution
 * - No side effects: Pure presentational component
 * - Proper composition: Uses Recharts components
 * - Responsive design: Auto-adjusts to container size
 * - Accessibility: Includes legend and proper labels
 */

import { useState } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { ModelDistribution } from '@/types/metrics';

interface ModelDistributionChartProps {
  /**
   * Model distribution data
   */
  data: ModelDistribution[];

  /**
   * Optional chart title
   * @default "Model Distribution"
   */
  title?: string;

  /**
   * Optional className for card styling
   */
  className?: string;
}

/**
 * Color palette for different models
 * Uses HSL colors from Tailwind CSS design system
 */
const COLORS = [
  'hsl(var(--chart-1))',
  'hsl(var(--chart-2))',
  'hsl(var(--chart-3))',
  'hsl(var(--chart-4))',
  'hsl(var(--chart-5))',
];

/**
 * Custom label renderer for pie slices showing percentage
 */
function renderCustomLabel({
  cx,
  cy,
  midAngle,
  innerRadius,
  outerRadius,
  percent,
}: any) {
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  // Only show label if percentage is >= 5% to avoid clutter
  if (percent < 0.05) {
    return null;
  }

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor={x > cx ? 'start' : 'end'}
      dominantBaseline="central"
      className="text-xs font-semibold"
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
}

/**
 * Custom tooltip for displaying model details
 */
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const data = payload[0].payload;

  return (
    <div className="rounded-lg border bg-background p-3 shadow-md">
      <p className="text-sm font-medium mb-1">{data.model}</p>
      <div className="space-y-1">
        <p className="text-xs text-muted-foreground">
          Jobs: <span className="font-semibold text-foreground">{data.count}</span>
        </p>
        <p className="text-xs text-muted-foreground">
          Share:{' '}
          <span className="font-semibold text-foreground">
            {data.percentage.toFixed(1)}%
          </span>
        </p>
      </div>
    </div>
  );
}

/**
 * ModelDistributionChart Component
 *
 * Renders a pie chart showing distribution of jobs across different models.
 * Interactive with hover effects and detailed tooltips.
 *
 * @example
 * ```tsx
 * <ModelDistributionChart
 *   data={[
 *     { model: 'gemini-2.5-flash', count: 100, percentage: 50 },
 *     { model: 'gpt-4-vision', count: 75, percentage: 37.5 },
 *     { model: 'deepseek-vl', count: 25, percentage: 12.5 },
 *   ]}
 *   title="Model Distribution"
 * />
 * ```
 */
export function ModelDistributionChart({
  data,
  title = 'Model Distribution',
  className,
}: ModelDistributionChartProps) {
  const [activeIndex, setActiveIndex] = useState<number | undefined>(undefined);

  /**
   * Handler for mouse enter on pie slice
   * Highlights the active slice without side effects beyond UI state
   */
  const onPieEnter = (_: any, index: number) => {
    setActiveIndex(index);
  };

  /**
   * Handler for mouse leave
   * Resets active state
   */
  const onPieLeave = () => {
    setActiveIndex(undefined);
  };

  // Handle empty data case
  if (!data || data.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base font-semibold">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-[300px] items-center justify-center">
            <p className="text-sm text-muted-foreground">No data available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              {(() => {
                // Use IIFE to avoid TypeScript errors with Recharts types
                const PieComponent = Pie as any;
                return (
                  <PieComponent
                    data={data}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={renderCustomLabel}
                    outerRadius={100}
                    innerRadius={50}
                    fill="#8884d8"
                    dataKey="count"
                    activeIndex={activeIndex}
                    activeShape={{
                      outerRadius: 110,
                      stroke: 'hsl(var(--border))',
                      strokeWidth: 2,
                    }}
                    onMouseEnter={onPieEnter}
                    onMouseLeave={onPieLeave}
                  >
                    {data.map((_item, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={COLORS[index % COLORS.length]}
                      />
                    ))}
                  </PieComponent>
                );
              })()}
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: '12px' }}
                formatter={(_value, entry: any) => {
                  // Show model name in legend
                  return entry.payload.model;
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
