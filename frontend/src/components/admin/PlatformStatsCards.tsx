/**
 * PlatformStatsCards Component
 *
 * Displays platform-wide statistics organized by category.
 * Following React best practices:
 * - Single Responsibility: Only displays platform stats
 * - Composition: Reuses StatsCard component
 * - DRY: Centralized stat configuration
 * - Type Safety: Full TypeScript support
 * - No side effects: Pure presentational component
 */

import { StatsCard } from '@/components/metrics/StatsCard';
import {
  Building2,
  Users,
  FileText,
  CheckCircle2,
  XCircle,
  Clock,
  Cpu,
  DollarSign,
  CreditCard,
  TrendingUp,
  Key,
} from 'lucide-react';
import type { PlatformStatistics } from '@/types/admin';

interface PlatformStatsCardsProps {
  stats: PlatformStatistics;
}

/**
 * PlatformStatsCards Component
 *
 * Renders a grid of statistics cards organized into categories:
 * - Tenant Metrics
 * - User & Activity
 * - Job Performance
 * - Resource Usage
 *
 * @example
 * ```tsx
 * <PlatformStatsCards stats={platformStats} />
 * ```
 */
export function PlatformStatsCards({ stats }: PlatformStatsCardsProps) {
  return (
    <div className="space-y-6">
      {/* Tenant Metrics */}
      <section>
        <h3 className="text-lg font-semibold mb-3">Tenant Metrics</h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatsCard
            title="Total Tenants"
            value={stats.total_tenants}
            icon={Building2}
            format="number"
          />
          <StatsCard
            title="Active Tenants"
            value={stats.active_tenants}
            icon={CheckCircle2}
            format="number"
            description="Currently active"
          />
          <StatsCard
            title="Suspended"
            value={stats.suspended_tenants}
            icon={XCircle}
            format="number"
          />
          <StatsCard
            title="New (30d)"
            value={stats.new_tenants_30d}
            icon={TrendingUp}
            format="number"
            description="Last 30 days"
          />
        </div>
      </section>

      {/* User & Activity Metrics */}
      <section>
        <h3 className="text-lg font-semibold mb-3">Users & Activity</h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatsCard
            title="Total Users"
            value={stats.total_users}
            icon={Users}
            format="number"
          />
          <StatsCard
            title="Active Users"
            value={stats.active_users}
            icon={Users}
            format="number"
            description="Active accounts"
          />
          <StatsCard
            title="Jobs (24h)"
            value={stats.jobs_24h}
            icon={Clock}
            format="number"
            description="Last 24 hours"
          />
          <StatsCard
            title="API Tokens"
            value={stats.total_api_tokens}
            icon={Key}
            format="number"
          />
        </div>
      </section>

      {/* Job Performance */}
      <section>
        <h3 className="text-lg font-semibold mb-3">Job Performance</h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatsCard
            title="Total Jobs"
            value={stats.total_jobs}
            icon={FileText}
            format="number"
          />
          <StatsCard
            title="Completed"
            value={stats.completed_jobs}
            icon={CheckCircle2}
            format="number"
          />
          <StatsCard
            title="Failed"
            value={stats.failed_jobs}
            icon={XCircle}
            format="number"
          />
          <StatsCard
            title="Success Rate"
            value={
              stats.total_jobs > 0
                ? (stats.completed_jobs / stats.total_jobs) * 100
                : 0
            }
            icon={TrendingUp}
            format="percentage"
          />
        </div>
      </section>

      {/* Resource Usage & Financial */}
      <section>
        <h3 className="text-lg font-semibold mb-3">Resources & Financial</h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatsCard
            title="Total Documents"
            value={stats.total_documents}
            icon={FileText}
            format="number"
          />
          <StatsCard
            title="Total Tokens"
            value={stats.total_tokens}
            icon={Cpu}
            format="number"
            description={`Input: ${new Intl.NumberFormat('en-US').format(stats.total_input_tokens)} | Output: ${new Intl.NumberFormat('en-US').format(stats.total_output_tokens)}`}
          />
          <StatsCard
            title="Estimated Cost"
            value={stats.estimated_total_cost}
            icon={DollarSign}
            format="currency"
          />
          <StatsCard
            title="Credits Balance"
            value={stats.total_credits_purchased - stats.total_credits_consumed}
            icon={CreditCard}
            format="number"
            description={`Used: ${new Intl.NumberFormat('en-US').format(stats.total_credits_consumed)} / ${new Intl.NumberFormat('en-US').format(stats.total_credits_purchased)}`}
          />
        </div>
      </section>
    </div>
  );
}
