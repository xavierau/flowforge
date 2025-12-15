/**
 * Dashboard Page
 *
 * Main metrics dashboard showing job statistics, token usage, and model distribution.
 * Follows React best practices:
 * - Proper useEffect with cleanup and dependencies
 * - Single data fetching effect with error handling
 * - Loading and error states
 * - Composition of metric components
 * - Date range selection without unnecessary re-renders
 */

import { useState, useEffect } from 'react';
import { Page, PageHeader, PageContent } from '@/components/layout';
import {
  StatsCard,
  JobsChart,
  PagesChart,
  TokensChart,
  ModelDistributionChart,
  RecentJobsWidget,
} from '@/components/metrics';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  getDashboardMetrics,
  MetricsApiError,
} from '@/services/metrics.service';
import { listJobs } from '@/lib/api';
import type { DashboardMetrics, DateRangeOption } from '@/types/metrics';
import type { Job } from '@/types/job';
import {
  FileText,
  FileStack,
  Coins,
  DollarSign,
  AlertCircle,
} from 'lucide-react';

/**
 * Dashboard Component
 *
 * Displays comprehensive metrics dashboard with:
 * - 4 stat cards (jobs, pages, tokens, cost)
 * - 4 charts (jobs over time, pages over time, tokens breakdown, model distribution)
 * - Date range selector
 * - Loading and error states
 *
 * @example
 * ```tsx
 * <Dashboard />
 * ```
 */
export function Dashboard() {
  // State management
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<DateRangeOption>(30);

  // Recent jobs state
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);

  /**
   * Fetch dashboard metrics
   *
   * Single effect that fetches data when dateRange changes.
   * Includes proper error handling and cleanup.
   * Dependencies: [dateRange] - refetch when date range changes
   */
  useEffect(() => {
    let isCancelled = false;

    async function fetchMetrics() {
      setIsLoading(true);
      setError(null);

      try {
        const data = await getDashboardMetrics(dateRange);

        // Only update state if component is still mounted
        if (!isCancelled) {
          setMetrics(data);
          setIsLoading(false);
        }
      } catch (err) {
        // Only update state if component is still mounted
        if (!isCancelled) {
          if (err instanceof MetricsApiError) {
            setError(err.message);
          } else {
            setError('Failed to load dashboard metrics');
          }
          setIsLoading(false);
        }
      }
    }

    fetchMetrics();

    // Cleanup function to prevent state updates after unmount
    return () => {
      isCancelled = true;
    };
  }, [dateRange]);

  /**
   * Fetch recent jobs
   *
   * Single effect that fetches jobs on mount.
   * Includes proper error handling and cleanup.
   * Dependencies: [] - only fetch on mount
   */
  useEffect(() => {
    let isCancelled = false;

    async function fetchRecentJobs() {
      setIsLoadingJobs(true);

      try {
        const data = await listJobs({ limit: 10, offset: 0 });

        // Only update state if component is still mounted
        if (!isCancelled) {
          setRecentJobs(data.jobs);
          setIsLoadingJobs(false);
        }
      } catch (err) {
        // Only update state if component is still mounted
        if (!isCancelled) {
          // Silently fail for jobs - not critical for dashboard
          console.error('Failed to load recent jobs:', err);
          setIsLoadingJobs(false);
        }
      }
    }

    fetchRecentJobs();

    // Cleanup function to prevent state updates after unmount
    return () => {
      isCancelled = true;
    };
  }, []);

  /**
   * Handle date range change
   * Pure function with no side effects beyond state update
   */
  const handleDateRangeChange = (newRange: DateRangeOption) => {
    setDateRange(newRange);
  };

  return (
    <Page>
      <PageHeader
        breadcrumbs={[{ label: 'Dashboard' }]}
        title="Dashboard"
        subtitle="Overview of your document processing activity"
      />

      <PageContent>
        {/* Date Range Selector */}
        <div className="flex justify-end gap-2">
          <Button
            variant={dateRange === 7 ? 'default' : 'outline'}
            size="sm"
            onClick={() => handleDateRangeChange(7)}
            disabled={isLoading}
          >
            7 days
          </Button>
          <Button
            variant={dateRange === 30 ? 'default' : 'outline'}
            size="sm"
            onClick={() => handleDateRangeChange(30)}
            disabled={isLoading}
          >
            30 days
          </Button>
          <Button
            variant={dateRange === 90 ? 'default' : 'outline'}
            size="sm"
            onClick={() => handleDateRangeChange(90)}
            disabled={isLoading}
          >
            90 days
          </Button>
        </div>

        {/* Error State */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Loading State */}
        {isLoading && !metrics && (
          <div className="flex h-[400px] items-center justify-center">
            <div className="text-center">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent align-[-0.125em]"></div>
              <p className="mt-4 text-sm text-muted-foreground">
                Loading dashboard metrics...
              </p>
            </div>
          </div>
        )}

        {/* Stats Cards Grid */}
        {metrics && (
          <>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <StatsCard
                title="Total Jobs"
                value={metrics.stats.total_jobs}
                icon={FileText}
                description={`Last ${dateRange} days`}
                format="number"
              />
              <StatsCard
                title="Pages Processed"
                value={metrics.stats.total_pages}
                icon={FileStack}
                description={`Last ${dateRange} days`}
                format="number"
              />
              <StatsCard
                title="Total Tokens"
                value={metrics.stats.total_tokens}
                icon={Coins}
                description={`Last ${dateRange} days`}
                format="number"
              />
              <StatsCard
                title="Estimated Cost"
                value={metrics.stats.estimated_cost}
                icon={DollarSign}
                description={`Last ${dateRange} days`}
                format="currency"
              />
            </div>

            {/* Charts Grid */}
            <div className="grid gap-4 md:grid-cols-2">
              <JobsChart
                data={metrics.jobs_over_time}
                title="Jobs Processed Over Time"
              />
              <PagesChart
                data={metrics.pages_over_time}
                title="Pages Processed Over Time"
              />
              <TokensChart
                data={metrics.tokens_over_time}
                title="Token Usage Over Time"
              />
              <ModelDistributionChart
                data={metrics.model_distribution}
                title="Model Usage Distribution"
              />
            </div>

            {/* Recent Jobs Widget */}
            <RecentJobsWidget
              jobs={recentJobs}
              isLoading={isLoadingJobs}
              maxJobs={5}
            />
          </>
        )}
      </PageContent>
    </Page>
  );
}
