import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, FileText, Plus, Clock, CheckCircle, XCircle, Loader2, RotateCw, Files, FileCode, Globe, Terminal } from 'lucide-react';
import { toast } from 'sonner';

import { Page, PageHeader, PageContent } from '@/components/layout';
import {
  DataTable,
  createSelectColumn,
  createSortableColumn,
  createBadgeColumn,
  createDateColumn,
  createActionsColumn,
} from '@/components/data-table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ProcessingModeBadge } from '@/components/markdown/ProcessingModeBadge';
import type { Job } from '@/types/job';
import { listJobs, retryJob } from '@/lib/api';
import { JobSource } from '@/types/enums';

export function JobList() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [retryingJobId, setRetryingJobId] = useState<string | null>(null);

  // Fetch jobs on mount with proper cleanup to prevent race conditions
  useEffect(() => {
    let isMounted = true;

    const loadJobs = async () => {
      try {
        setIsLoading(true);
        const response = await listJobs({ limit: 100, offset: 0 });

        // Only update state if component is still mounted
        if (isMounted) {
          setJobs(response.jobs);
        }
      } catch (error) {
        // Only show error if component is still mounted
        if (isMounted) {
          toast.error('Failed to load jobs', {
            description: error instanceof Error ? error.message : 'Unknown error',
          });
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadJobs();

    // Cleanup function to prevent state updates on unmounted component
    return () => {
      isMounted = false;
    };
  }, []);

  // Handle retry job
  const handleRetryJob = async (job: Job) => {
    try {
      setRetryingJobId(job.id);
      const response = await retryJob(job.id);

      toast.success('Job retried successfully', {
        description: `New job created: ${response.extraction_job_id.substring(0, 8)}...`,
      });

      // Refresh job list to show new job
      const updatedJobs = await listJobs({ limit: 100, offset: 0 });
      setJobs(updatedJobs.jobs);
    } catch (error) {
      toast.error('Failed to retry job', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setRetryingJobId(null);
    }
  };

  // Define columns
  const columns = [
    createSelectColumn<Job>(),
    createSortableColumn<Job>('id', 'Job ID', (id: string) => (
      <div className="font-mono text-xs">{id.substring(0, 8)}...</div>
    )),
    createSortableColumn<Job>('document_name', 'Document', (name: string) => (
      <div className="max-w-[200px] truncate">{name || 'N/A'}</div>
    )),
    createBadgeColumn<Job>('status', 'Status', {
      queued: 'secondary',
      processing: 'default',
      completed: 'outline',
      failed: 'destructive',
    }),
    createSortableColumn<Job>('model_used', 'Model', (model: string) => (
      <div className="text-sm text-muted-foreground">{model || 'N/A'}</div>
    )),
    {
      id: 'processing_mode',
      accessorKey: 'processing_mode',
      header: 'Mode',
      cell: ({ row }: { row: any }) => {
        const mode = row.original.processing_mode;
        return mode ? <ProcessingModeBadge mode={mode} /> : <span className="text-muted-foreground">N/A</span>;
      },
      filterFn: (row: any, id: string, value: string[]) => {
        return value.includes(row.getValue(id));
      },
    },
    {
      id: 'source',
      accessorKey: 'source',
      header: 'Source',
      cell: ({ row }: { row: any }) => {
        const source = row.original.source as JobSource;
        if (!source) return <span className="text-muted-foreground">N/A</span>;

        const isWebUI = source === JobSource.WEBUI;
        return (
          <Badge variant={isWebUI ? 'default' : 'secondary'} className="gap-1">
            {isWebUI ? <Globe className="h-3 w-3" /> : <Terminal className="h-3 w-3" />}
            {isWebUI ? 'Web UI' : 'API'}
          </Badge>
        );
      },
      filterFn: (row: any, id: string, value: string[]) => {
        return value.includes(row.getValue(id));
      },
    },
    createDateColumn<Job>('created_at', 'Created', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
    createActionsColumn<Job>([
      {
        label: 'View Details',
        icon: Eye,
        onClick: (job) => navigate(`/jobs/${job.id}`),
      },
      {
        label: 'View Results',
        icon: FileText,
        onClick: (job) => navigate(`/jobs/${job.id}/results`),
        show: (job) => job.status === 'completed',
      },
      {
        label: (job) => retryingJobId === job.id ? 'Retrying...' : 'Retry',
        icon: RotateCw,
        onClick: handleRetryJob,
        disabled: (job) => retryingJobId === job.id,
      },
    ]),
  ];

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Jobs' },
        ]}
        title="Extraction Jobs"
        subtitle="Monitor your document extraction jobs"
      />
      <PageContent>
        <div className="flex justify-end mb-4">
          <Button onClick={() => navigate('/jobs/new')}>
            <Plus className="mr-2 h-4 w-4" />
            Create Job
          </Button>
        </div>

        <DataTable
          columns={columns}
          data={jobs}
          searchPlaceholder="Search jobs..."
          searchableColumns={['id', 'document_name']}
          filterableColumns={[
            {
              id: 'status',
              title: 'Status',
              options: [
                {
                  label: 'Queued',
                  value: 'queued',
                  icon: Clock,
                },
                {
                  label: 'Processing',
                  value: 'processing',
                  icon: Loader2,
                },
                {
                  label: 'Completed',
                  value: 'completed',
                  icon: CheckCircle,
                },
                {
                  label: 'Failed',
                  value: 'failed',
                  icon: XCircle,
                },
              ],
            },
            {
              id: 'processing_mode',
              title: 'Processing Mode',
              options: [
                {
                  label: 'Direct',
                  value: 'direct',
                  icon: FileText,
                },
                {
                  label: 'Batch',
                  value: 'batch',
                  icon: Files,
                },
                {
                  label: 'Markdown',
                  value: 'markdown',
                  icon: FileCode,
                },
              ],
            },
            {
              id: 'source',
              title: 'Source',
              options: [
                {
                  label: 'Web UI',
                  value: 'webui',
                  icon: Globe,
                },
                {
                  label: 'API',
                  value: 'api',
                  icon: Terminal,
                },
              ],
            },
          ]}
          exportFilename="extraction-jobs"
          exportableColumns={['id', 'document_name', 'status', 'processing_mode', 'source', 'model_used', 'created_at']}
          isLoading={isLoading}
          emptyMessage="No jobs found. Create your first extraction job to get started."
        />
      </PageContent>
    </Page>
  );
}
