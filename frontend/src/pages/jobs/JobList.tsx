import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, FileText, Plus, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react';
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
import type { Job } from '@/types/job';
import { listJobs } from '@/lib/api';

export function JobList() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);

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
          ]}
          exportFilename="extraction-jobs"
          exportableColumns={['id', 'document_name', 'status', 'model_used', 'created_at']}
          isLoading={isLoading}
          emptyMessage="No jobs found. Create your first extraction job to get started."
        />
      </PageContent>
    </Page>
  );
}
