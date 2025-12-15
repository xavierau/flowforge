/**
 * RecentJobsWidget Component
 *
 * Displays a compact table of recent extraction jobs showing source (Web UI vs API),
 * status, document name, and creation time. Provides quick visibility into recent activity.
 *
 * Follows React best practices:
 * - Single Responsibility: Only displays recent jobs
 * - Composition: Uses shadcn/ui components
 * - Pure presentation: No side effects, receives data via props
 * - Type safety: Full TypeScript support
 */

import { Link, useNavigate } from 'react-router-dom';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import type { Job } from '@/types/job';
import { JobSource } from '@/types/enums';
import { format, parseISO } from 'date-fns';
import {
  Globe,
  Terminal,
  Clock,
  Loader2,
  CheckCircle,
  XCircle,
  ArrowRight,
} from 'lucide-react';

interface RecentJobsWidgetProps {
  /**
   * Array of recent jobs to display
   */
  jobs: Job[];

  /**
   * Loading state
   */
  isLoading?: boolean;

  /**
   * Optional className
   */
  className?: string;

  /**
   * Maximum number of jobs to show (default: 5)
   */
  maxJobs?: number;
}

/**
 * Status badge component for job status
 */
function StatusBadge({ status }: { status: Job['status'] }) {
  const config = {
    queued: { variant: 'secondary' as const, icon: Clock, label: 'Queued' },
    processing: { variant: 'default' as const, icon: Loader2, label: 'Processing' },
    completed: { variant: 'outline' as const, icon: CheckCircle, label: 'Completed' },
    failed: { variant: 'destructive' as const, icon: XCircle, label: 'Failed' },
  };

  const { variant, icon: Icon, label } = config[status];
  const isProcessing = status === 'processing';

  return (
    <Badge variant={variant} className="gap-1">
      <Icon className={`h-3 w-3 ${isProcessing ? 'animate-spin' : ''}`} />
      {label}
    </Badge>
  );
}

/**
 * Source badge component showing Web UI vs API origin
 */
function SourceBadge({ source }: { source?: JobSource | string }) {
  if (!source) return <span className="text-muted-foreground text-xs">—</span>;

  const isWebUI = source === JobSource.WEBUI || source === 'webui';

  return (
    <Badge variant={isWebUI ? 'default' : 'secondary'} className="gap-1">
      {isWebUI ? <Globe className="h-3 w-3" /> : <Terminal className="h-3 w-3" />}
      {isWebUI ? 'Web UI' : 'API'}
    </Badge>
  );
}

/**
 * RecentJobsWidget Component
 *
 * Displays a compact widget showing recent extraction jobs with their source,
 * status, and creation time. Includes a link to view all jobs.
 *
 * @example
 * ```tsx
 * <RecentJobsWidget
 *   jobs={recentJobs}
 *   isLoading={false}
 *   maxJobs={5}
 * />
 * ```
 */
export function RecentJobsWidget({
  jobs,
  isLoading = false,
  className,
  maxJobs = 5,
}: RecentJobsWidgetProps) {
  const navigate = useNavigate();

  // Limit displayed jobs
  const displayedJobs = jobs.slice(0, maxJobs);

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold">Recent Jobs</CardTitle>
            <CardDescription className="text-xs">
              Latest extraction jobs from Web UI and API
            </CardDescription>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/jobs')}
            className="text-xs"
          >
            View All
            <ArrowRight className="ml-1 h-3 w-3" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[80px]">Source</TableHead>
                <TableHead>Document</TableHead>
                <TableHead className="w-[100px]">Status</TableHead>
                <TableHead className="w-[120px]">Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Loading...
                    </div>
                  </TableCell>
                </TableRow>
              ) : displayedJobs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                    No jobs yet. Create your first extraction job to get started.
                  </TableCell>
                </TableRow>
              ) : (
                displayedJobs.map((job) => (
                  <TableRow key={job.id}>
                    <TableCell>
                      <SourceBadge source={job.source} />
                    </TableCell>
                    <TableCell className="max-w-[200px]">
                      <Link
                        to={`/jobs/${job.id}`}
                        className="text-primary hover:underline truncate block text-sm"
                        title={job.document_name || 'Unknown document'}
                      >
                        {job.document_name || 'Unknown document'}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={job.status} />
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {format(parseISO(job.created_at), 'MMM dd, HH:mm')}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Summary footer */}
        {!isLoading && jobs.length > 0 && (
          <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex gap-3">
              <span>
                Web UI: {jobs.filter(j => j.source === JobSource.WEBUI).length}
              </span>
              <span>
                API: {jobs.filter(j => j.source === JobSource.API || !j.source).length}
              </span>
            </div>
            <span>Total: {jobs.length}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
