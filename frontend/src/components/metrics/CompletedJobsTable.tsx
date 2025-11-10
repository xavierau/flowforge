/**
 * CompletedJobsTable Component
 *
 * Simplified data table displaying completed jobs for billing with pagination.
 * Shows Job ID (linked), Credit Usage, Processing Time, and Completion Date.
 *
 * Follows React best practices:
 * - Single Responsibility: Only displays completed jobs table
 * - Composition: Uses shadcn/ui table components
 * - Proper state management: Controlled pagination
 * - No unnecessary effects: Pure presentation logic
 * - Type safety: Full TypeScript support
 */

import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableFooter,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { CompletedJob } from '@/types/metrics';
import { format, parseISO } from 'date-fns';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface CompletedJobsTableProps {
  /**
   * Array of completed jobs
   */
  jobs: CompletedJob[];

  /**
   * Total number of jobs (for pagination)
   */
  total: number;

  /**
   * Current page number (1-indexed)
   */
  page: number;

  /**
   * Number of items per page
   */
  pageSize: number;

  /**
   * Total cost across all jobs (not just current page)
   */
  totalCost: number;

  /**
   * Loading state
   */
  isLoading?: boolean;

  /**
   * Callback when page changes
   */
  onPageChange: (newPage: number) => void;

  /**
   * Optional className
   */
  className?: string;
}

/**
 * Format number with thousands separator
 */
function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US').format(value);
}

/**
 * Format processing time in seconds to readable format
 */
function formatProcessingTime(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
}

/**
 * CompletedJobsTable Component
 *
 * Displays a table of completed jobs with pagination.
 * Includes columns for Job ID (linked to job details), Credit Usage, Processing Time, and Completion Date.
 *
 * @example
 * ```tsx
 * <CompletedJobsTable
 *   jobs={completedJobs}
 *   total={150}
 *   page={1}
 *   pageSize={50}
 *   totalCost={45.67}
 *   onPageChange={(page) => setCurrentPage(page)}
 * />
 * ```
 */
export function CompletedJobsTable({
  jobs,
  total,
  page,
  pageSize,
  isLoading = false,
  onPageChange,
  className,
}: CompletedJobsTableProps) {
  // Calculate pagination info
  const totalPages = Math.ceil(total / pageSize);
  const hasNextPage = page < totalPages;
  const hasPrevPage = page > 1;
  const startItem = (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, total);

  // Calculate page credit usage (sum of pages on current page)
  const pageCredits = useMemo(() => {
    return jobs.reduce((sum, job) => sum + job.pages_processed, 0);
  }, [jobs]);

  /**
   * Navigate to previous page
   * No side effects beyond state update via callback
   */
  const handlePrevPage = () => {
    if (hasPrevPage) {
      onPageChange(page - 1);
    }
  };

  /**
   * Navigate to next page
   * No side effects beyond state update via callback
   */
  const handleNextPage = () => {
    if (hasNextPage) {
      onPageChange(page + 1);
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base font-semibold">
          Completed Jobs
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Job ID</TableHead>
                <TableHead className="text-right">Credit Usage</TableHead>
                <TableHead className="text-right">Time</TableHead>
                <TableHead>Completed</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center">
                    Loading...
                  </TableCell>
                </TableRow>
              ) : jobs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center">
                    No completed jobs found
                  </TableCell>
                </TableRow>
              ) : (
                jobs.map((job) => (
                  <TableRow key={job.job_id}>
                    <TableCell className="font-medium">
                      <Link
                        to={`/jobs/${job.job_id}`}
                        className="text-primary hover:underline"
                      >
                        {job.job_id}
                      </Link>
                    </TableCell>
                    <TableCell className="text-right">
                      {job.pages_processed}
                    </TableCell>
                    <TableCell className="text-right text-sm text-muted-foreground">
                      {formatProcessingTime(job.processing_time)}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {format(parseISO(job.completed_at), 'MMM dd, yyyy HH:mm')}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
            <TableFooter>
              <TableRow>
                <TableCell className="font-medium">
                  Page Total
                </TableCell>
                <TableCell className="text-right font-bold">
                  {formatNumber(pageCredits)}
                </TableCell>
                <TableCell colSpan={2} />
              </TableRow>
              <TableRow>
                <TableCell className="font-medium">
                  Overall Total ({total} jobs)
                </TableCell>
                <TableCell className="text-right font-bold">
                  {formatNumber(total)}
                </TableCell>
                <TableCell colSpan={2} />
              </TableRow>
            </TableFooter>
          </Table>
        </div>

        {/* Pagination Controls */}
        <div className="flex items-center justify-between mt-4">
          <div className="text-sm text-muted-foreground">
            Showing {startItem} to {endItem} of {total} jobs
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePrevPage}
              disabled={!hasPrevPage || isLoading}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Previous
            </Button>
            <div className="text-sm font-medium">
              Page {page} of {totalPages}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleNextPage}
              disabled={!hasNextPage || isLoading}
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
