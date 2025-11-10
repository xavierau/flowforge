/**
 * Admin Dashboard Page
 *
 * Platform-wide statistics dashboard for super admins.
 * Follows React best practices:
 * - Proper useEffect with cleanup and dependencies
 * - Single data fetching effect with error handling
 * - Loading and error states
 * - Composition of metric components
 * - No unnecessary re-renders
 */

import { useState, useEffect } from 'react';
import { Page, PageHeader, PageContent } from '@/components/layout';
import { PlatformStatsCards } from '@/components/admin/PlatformStatsCards';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  getDashboardMetrics,
  AdminApiError,
} from '@/services/admin.service';
import type { PlatformStatistics } from '@/types/admin';
import { AlertCircle, RefreshCw } from 'lucide-react';

/**
 * AdminDashboard Component
 *
 * Displays comprehensive platform statistics:
 * - Tenant metrics (total, active, suspended, new)
 * - User metrics (total, active)
 * - Job performance (total, completed, failed, success rate)
 * - Resource usage (documents, tokens, cost, credits)
 *
 * @example
 * ```tsx
 * <AdminDashboard />
 * ```
 */
export function AdminDashboard() {
  // State management
  const [stats, setStats] = useState<PlatformStatistics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch platform statistics
   *
   * Single effect that fetches data on mount.
   * Includes proper error handling and cleanup.
   * Dependencies: [] - fetch once on mount
   */
  useEffect(() => {
    let isCancelled = false;

    async function fetchStats() {
      setIsLoading(true);
      setError(null);

      try {
        const data = await getDashboardMetrics();

        // Only update state if component is still mounted
        if (!isCancelled) {
          setStats(data);
          setIsLoading(false);
        }
      } catch (err) {
        // Only update state if component is still mounted
        if (!isCancelled) {
          if (err instanceof AdminApiError) {
            setError(err.message);
          } else {
            setError('Failed to load platform statistics');
          }
          setIsLoading(false);
        }
      }
    }

    fetchStats();

    // Cleanup function to prevent state updates after unmount
    return () => {
      isCancelled = true;
    };
  }, []);

  /**
   * Refresh statistics manually
   * Uses same pattern as initial fetch
   */
  async function handleRefresh() {
    setIsLoading(true);
    setError(null);

    try {
      const data = await getDashboardMetrics();
      setStats(data);
      setIsLoading(false);
    } catch (err) {
      if (err instanceof AdminApiError) {
        setError(err.message);
      } else {
        setError('Failed to load platform statistics');
      }
      setIsLoading(false);
    }
  }

  return (
    <Page>
      <PageHeader
        title="Platform Dashboard"
        subtitle="Overview of all tenants, users, and system activity"
      >
        <Button
          onClick={handleRefresh}
          disabled={isLoading}
          variant="outline"
          size="sm"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </PageHeader>

      <PageContent>
        {/* Error State */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Loading State */}
        {isLoading && !stats && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Loading platform statistics...
              </p>
            </div>
          </div>
        )}

        {/* Statistics Display */}
        {!isLoading && stats && <PlatformStatsCards stats={stats} />}
      </PageContent>
    </Page>
  );
}
