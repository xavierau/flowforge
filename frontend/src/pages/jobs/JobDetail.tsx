import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, FileText, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Page, PageHeader, PageContent } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { CodeExamplesModal } from '@/components/CodeExamplesModal';
import type { Job } from '@/types/job';
import { getJobStatus } from '@/lib/api';

export function JobDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (id) {
      loadJob(id);
      // Poll for updates if job is in progress
      const interval = setInterval(() => {
        if (job?.status === 'queued' || job?.status === 'processing') {
          loadJob(id);
        }
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [id, job?.status]);

  const loadJob = async (jobId: string) => {
    try {
      setIsLoading(true);
      const data = await getJobStatus(jobId);
      // Map JobStatusResponse to Job type (job_id -> id)
      setJob({
        id: data.job_id,
        document_id: data.document_id,
        status: data.status,
        progress: data.progress,
        started_at: data.started_at,
        updated_at: data.updated_at,
        created_at: data.updated_at, // JobStatusResponse doesn't have created_at, use updated_at
        error: data.error,
      });
    } catch (error) {
      toast.error('Failed to load job', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
      navigate('/jobs');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'queued':
        return <Clock className="h-5 w-5" />;
      case 'processing':
        return <Loader2 className="h-5 w-5 animate-spin" />;
      case 'completed':
        return <CheckCircle className="h-5 w-5" />;
      case 'failed':
        return <XCircle className="h-5 w-5" />;
      default:
        return null;
    }
  };

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'queued':
        return 'secondary';
      case 'processing':
        return 'default';
      case 'completed':
        return 'outline';
      case 'failed':
        return 'destructive';
      default:
        return 'default';
    }
  };

  if (isLoading && !job) {
    return (
      <Page>
        <PageContent>
          <div className="flex items-center justify-center h-64">
            <p className="text-muted-foreground">Loading job details...</p>
          </div>
        </PageContent>
      </Page>
    );
  }

  if (!job) {
    return null;
  }

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Jobs', href: '/jobs' },
          { label: `Job ${job.id.substring(0, 8)}` },
        ]}
        title={`Extraction Job: ${job.id.substring(0, 8)}...`}
        subtitle="Job details and processing status"
      />
      <PageContent>
        <div className="flex gap-2 mb-6">
          <Button variant="outline" onClick={() => navigate('/jobs')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Jobs
          </Button>
          {job.status === 'completed' && (
            <Button onClick={() => navigate(`/jobs/${job.id}/results`)}>
              <FileText className="mr-2 h-4 w-4" />
              View Results
            </Button>
          )}
          <CodeExamplesModal jobId={job.id} documentId={job.document_id} />
        </div>

        <div className="grid gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Job Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                {getStatusIcon(job.status)}
                <Badge variant={getStatusVariant(job.status)} className="capitalize">
                  {job.status}
                </Badge>
              </div>

              {job.progress && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Progress</span>
                    <span className="font-medium">
                      {job.progress.completed_pages || 0} / {job.progress.total_pages || 0} pages
                    </span>
                  </div>
                  <Progress
                    value={
                      job.progress.total_pages
                        ? (job.progress.completed_pages / job.progress.total_pages) * 100
                        : 0
                    }
                  />
                </div>
              )}

              {job.error && (
                <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20">
                  <p className="text-sm font-medium text-destructive">Error</p>
                  <p className="text-sm text-destructive/90 mt-1">{job.error}</p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Job Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="text-sm font-medium text-muted-foreground">Job ID</div>
                <div className="text-base font-mono">{job.id}</div>
              </div>
              <div>
                <div className="text-sm font-medium text-muted-foreground">Document ID</div>
                <div className="text-base font-mono">{job.document_id}</div>
              </div>
              {job.document_name && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Document Name</div>
                  <div className="text-base">{job.document_name}</div>
                </div>
              )}
              {job.model_used && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Model Used</div>
                  <div className="text-base">{job.model_used}</div>
                </div>
              )}
              <div>
                <div className="text-sm font-medium text-muted-foreground">Created</div>
                <div className="text-base">
                  {new Date(job.created_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              </div>
              {job.started_at && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Started</div>
                  <div className="text-base">
                    {new Date(job.started_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </div>
                </div>
              )}
              {job.completed_at && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Completed</div>
                  <div className="text-base">
                    {new Date(job.completed_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </PageContent>
    </Page>
  );
}
