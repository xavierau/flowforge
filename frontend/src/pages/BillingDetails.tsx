/**
 * BillingDetails Page
 *
 * Displays completed jobs for billing purposes with pagination and filtering.
 * Follows React best practices:
 * - Proper useEffect with cleanup and dependencies
 * - Single data fetching effect with error handling
 * - Loading and error states
 * - Composition of billing components
 * - Controlled pagination without unnecessary re-renders
 */

import { useState, useEffect } from 'react';
import { Page, PageHeader, PageContent } from '@/components/layout';
import { CompletedJobsTable } from '@/components/metrics';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import {
  getCompletedJobs,
  MetricsApiError,
} from '@/services/metrics.service';
import {
  getCurrentSubscription,
  SubscriptionApiError,
} from '@/services/subscription.service';
import type { CompletedJobsResponse } from '@/types/metrics';
import type { Subscription } from '@/types/profile';
import { Zap, Download, AlertCircle } from 'lucide-react';

/**
 * Format number with thousands separator
 */
function formatNumber(num: number): string {
  return num.toLocaleString();
}

/**
 * Format timestamp to relative time
 */
function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const date = new Date(timestamp);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
}

/**
 * BillingDetails Component
 *
 * Displays billing information with:
 * - Credit balance card with progress bar
 * - Completed jobs table with pagination
 * - Export button (placeholder)
 * - Loading and error states
 *
 * @example
 * ```tsx
 * <BillingDetails />
 * ```
 */
export function BillingDetails() {
  // State management
  const [billingData, setBillingData] = useState<CompletedJobsResponse | null>(
    null
  );
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 50;

  /**
   * Fetch billing data and subscription
   *
   * Single effect that fetches both datasets in parallel when page changes.
   * Includes proper error handling and cleanup.
   * Dependencies: [currentPage] - refetch when page changes
   */
  useEffect(() => {
    let isCancelled = false;

    async function fetchData() {
      setIsLoading(true);
      setError(null);

      try {
        // Fetch both billing data and subscription in parallel
        const [billingResult, subscriptionResult] = await Promise.all([
          getCompletedJobs(currentPage, pageSize),
          getCurrentSubscription(),
        ]);

        // Only update state if component is still mounted
        if (!isCancelled) {
          setBillingData(billingResult);
          setSubscription(subscriptionResult);
          setIsLoading(false);
        }
      } catch (err) {
        // Only update state if component is still mounted
        if (!isCancelled) {
          if (err instanceof MetricsApiError || err instanceof SubscriptionApiError) {
            setError(err.message);
          } else {
            setError('Failed to load billing data');
          }
          setIsLoading(false);
        }
      }
    }

    fetchData();

    // Cleanup function to prevent state updates after unmount
    return () => {
      isCancelled = true;
    };
  }, [currentPage]);

  /**
   * Handle page change
   * Pure function with no side effects beyond state update
   */
  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
  };

  /**
   * Handle export (placeholder)
   * Will be implemented when backend endpoint is ready
   */
  const handleExport = () => {
    // TODO: Implement export functionality
    alert('Export functionality will be available soon');
  };

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Billing' },
        ]}
        title="Billing Details"
        subtitle="View your completed jobs and associated costs"
      />

      <PageContent>
        {/* Error State */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Loading State */}
        {isLoading && !billingData && (
          <div className="flex h-[400px] items-center justify-center">
            <div className="text-center">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent align-[-0.125em]"></div>
              <p className="mt-4 text-sm text-muted-foreground">
                Loading billing data...
              </p>
            </div>
          </div>
        )}

        {/* Credit Balance and Export */}
        {billingData && subscription && (
          <>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              {/* Credit Balance Card */}
              <Card className="flex-1">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Zap className="h-4 w-4 text-primary" />
                    Credit Balance
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {/* Large balance number */}
                    <p className="text-3xl font-bold">
                      {formatNumber(subscription.credits_balance)}
                    </p>

                    {/* Progress bar visualization */}
                    <Progress
                      value={
                        subscription.credits_balance + subscription.credits_used > 0
                          ? (subscription.credits_balance /
                              (subscription.credits_balance +
                                subscription.credits_used)) *
                            100
                          : 0
                      }
                      className="h-2"
                    />

                    {/* Usage and last updated */}
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">
                        {formatNumber(subscription.credits_used)} used this month
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Updated {formatRelativeTime(subscription.balance_last_updated)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Export Button */}
              <Button
                onClick={handleExport}
                variant="outline"
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                Export
              </Button>
            </div>

            {/* Completed Jobs Table */}
            <CompletedJobsTable
              jobs={billingData.jobs}
              total={billingData.total}
              page={currentPage}
              pageSize={pageSize}
              totalCost={billingData.total_cost}
              isLoading={isLoading}
              onPageChange={handlePageChange}
            />
          </>
        )}
      </PageContent>
    </Page>
  );
}
