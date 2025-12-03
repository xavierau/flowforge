/**
 * ReviewQueue Page
 *
 * Human-in-the-Loop review queue with filtering and metrics.
 * Following React best practices:
 * - Proper useEffect with dependencies
 * - Error handling with try/catch
 * - Loading states
 * - Keyboard navigation support
 */

import { useEffect, useState, useCallback } from 'react';
import { useReviewStore } from '@/store/reviewStore';
import { QueueFilters } from '@/components/review/QueueFilters';
import { ReviewList } from '@/components/review/ReviewList';
import { Page, PageHeader, PageContent } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export function ReviewQueue() {
  const {
    queue,
    queueTotal,
    queueFilters,
    metrics,
    loading,
    error,
    fetchQueue,
    setQueueFilters,
    fetchMetrics,
    clearError,
  } = useReviewStore();

  const [isRefreshing, setIsRefreshing] = useState(false);

  // Fetch queue and metrics on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        await Promise.all([fetchQueue(), fetchMetrics()]);
      } catch (err) {
        // Error is handled by store
        console.error('Failed to load review queue:', err);
      }
    };

    loadData();
  }, []); // Run only on mount

  // Handle manual refresh
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([fetchQueue(), fetchMetrics()]);
    } catch (err) {
      console.error('Failed to refresh:', err);
    } finally {
      setIsRefreshing(false);
    }
  }, [fetchQueue, fetchMetrics]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // R for refresh
      if (e.key === 'r' && !e.ctrlKey && !e.metaKey) {
        const target = e.target as HTMLElement;
        // Only if not in an input field
        if (!['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) {
          e.preventDefault();
          handleRefresh();
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [handleRefresh]);

  return (
    <Page>
      <PageHeader
        breadcrumbs={[{ label: 'Reviews' }]}
        title="Review Queue"
        subtitle="Human-in-the-Loop document review and validation"
      />

      <PageContent>
        {/* Error Alert */}
        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between">
              <span>{error}</span>
              <Button variant="outline" size="sm" onClick={clearError}>
                Dismiss
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {/* Metrics Cards */}
        {metrics && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <MetricCard
              title="My Queue"
              value={metrics.my_queue_count}
              className="border-blue-200"
            />
            <MetricCard
              title="Pending"
              value={metrics.pending_count}
              className="border-gray-200"
            />
            <MetricCard
              title="Escalated"
              value={metrics.escalated_count}
              className="border-red-200"
            />
            <MetricCard
              title="SLA Breaches"
              value={metrics.sla_breach_count}
              className={cn(
                metrics.sla_breach_count > 0 ? 'border-red-500 bg-red-50' : 'border-gray-200'
              )}
            />
          </div>
        )}

        {/* Filters */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Filters</CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={isRefreshing || loading}
              >
                <RefreshCw
                  className={cn('h-4 w-4 mr-2', (isRefreshing || loading) && 'animate-spin')}
                />
                Refresh
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <QueueFilters filters={queueFilters} onChange={setQueueFilters} />
          </CardContent>
        </Card>

        {/* Queue List */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">
              Reviews ({queueTotal} total)
            </h2>
          </div>

          {loading && queue.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <RefreshCw className="h-8 w-8 animate-spin text-primary mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">Loading reviews...</p>
              </div>
            </div>
          ) : (
            <ReviewList items={queue} />
          )}
        </div>

        {/* Keyboard Shortcuts Help */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Keyboard Shortcuts</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground space-y-1">
            <div>
              <kbd className="px-2 py-1 bg-muted rounded">R</kbd> - Refresh queue
            </div>
            <div>
              <kbd className="px-2 py-1 bg-muted rounded">Enter</kbd> - Open selected review
            </div>
          </CardContent>
        </Card>
      </PageContent>
    </Page>
  );
}

interface MetricCardProps {
  title: string;
  value: number;
  className?: string;
}

function MetricCard({ title, value, className }: MetricCardProps) {
  return (
    <Card className={cn('border-2', className)}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  );
}
