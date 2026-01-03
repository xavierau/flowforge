import { useEffect, useState, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Download, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Page, PageHeader, PageContent } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { CodeExamplesModal } from '@/components/CodeExamplesModal';
import { PDFPreview } from '@/components/preview/PDFPreview';
import { ImagePreview } from '@/components/preview/ImagePreview';
import { SchemaJsonViewer } from '@/components/preview/SchemaJsonViewer';
import { MarkdownViewer } from '@/components/markdown/MarkdownViewer';
import type { Job, JobResultResponse } from '@/types/job';
import type { DocumentStatusResponse } from '@/lib/api';
import { getJobStatus, getJobResult, getDocument } from '@/lib/api';
import {
  ExtractionMode,
  getSplitModeLabel,
  getExtractionModeLabel,
  isSplitMode,
  isExtractionMode,
} from '@/types/enums';

export function JobDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [result, setResult] = useState<JobResultResponse | null>(null);
  const [document, setDocument] = useState<DocumentStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Use ref to track status for polling without triggering re-renders
  const jobStatusRef = useRef<string | null>(null);

  // Update ref whenever job status changes
  useEffect(() => {
    jobStatusRef.current = job?.status ?? null;
  }, [job?.status]);

  // Initial load - only runs when id changes
  useEffect(() => {
    if (id) {
      loadJob(id);
    }
  }, [id]);

  // Separate polling effect - only depends on id
  useEffect(() => {
    if (!id) return;

    const interval = setInterval(() => {
      // Check ref instead of state to avoid stale closure
      if (jobStatusRef.current === 'queued' || jobStatusRef.current === 'processing') {
        loadJob(id);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [id]);

  const loadJob = async (jobId: string) => {
    try {
      setIsLoading(true);
      const data = await getJobStatus(jobId);
      // Map JobStatusResponse to Job type (job_id -> id)
      const mappedJob: Job = {
        id: data.job_id,
        document_id: data.document_id,
        status: data.status,
        progress: data.progress,
        started_at: data.started_at,
        updated_at: data.updated_at,
        created_at: data.updated_at,
        error: data.error,
      };
      setJob(mappedJob);

      // If job is completed, load results and document info
      if (data.status === 'completed') {
        try {
          const resultData = await getJobResult(jobId);
          setResult(resultData);

          const docData = await getDocument(data.document_id);
          setDocument(docData);
        } catch (error) {
          console.error('Failed to load results:', error);
        }
      }
    } catch (error) {
      toast.error('Failed to load job', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
      navigate('/jobs');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = () => {
    if (!result) return;

    const json = JSON.stringify(result.extracted_data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const linkElement = window.document.createElement('a');
    linkElement.href = url;
    linkElement.download = `extraction-${id?.substring(0, 8)}.json`;
    linkElement.click();
    URL.revokeObjectURL(url);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'queued':
        return <Clock className="h-4 w-4" />;
      case 'processing':
        return <Loader2 className="h-4 w-4 animate-spin" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4" />;
      case 'failed':
        return <XCircle className="h-4 w-4" />;
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
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </PageContent>
      </Page>
    );
  }

  if (!job) {
    return null;
  }

  // Use extraction_mode with fallback to deprecated processing_mode
  const isMarkdownMode = result?.extraction_mode === ExtractionMode.MARKDOWN ||
    (!result?.extraction_mode && result?.processing_mode === 'markdown');

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Jobs', href: '/jobs' },
          { label: `Job ${job.id.substring(0, 8)}` },
        ]}
        title={
          <div className="flex items-center gap-3">
            <span>Extraction Job</span>
            <Badge variant={getStatusVariant(job.status)} className="capitalize flex items-center gap-1.5">
              {getStatusIcon(job.status)}
              {job.status}
            </Badge>
          </div>
        }
      />
      <PageContent>
        {/* Action buttons */}
        <div className="flex gap-2 mb-6">
          <Button variant="outline" size="sm" onClick={() => navigate('/jobs')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          {job.status === 'completed' && result && (
            <Button size="sm" onClick={handleDownload}>
              <Download className="mr-2 h-4 w-4" />
              Download JSON
            </Button>
          )}
          <CodeExamplesModal jobId={job.id} documentId={job.document_id} />
        </div>

        {/* Processing state: Show progress */}
        {(job.status === 'queued' || job.status === 'processing') && (
          <Card>
            <CardContent className="py-12">
              <div className="flex flex-col items-center justify-center text-center space-y-4">
                <Loader2 className="h-12 w-12 animate-spin text-primary" />
                <div>
                  <h3 className="text-lg font-medium">
                    {job.status === 'queued' ? 'Waiting in queue...' : 'Processing document...'}
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    This may take a moment depending on document size
                  </p>
                </div>
                {job.progress && job.progress.total_pages > 0 && (
                  <div className="w-full max-w-md space-y-2">
                    <Progress
                      value={(job.progress.completed_pages / job.progress.total_pages) * 100}
                    />
                    <p className="text-sm text-muted-foreground">
                      {job.progress.completed_pages} of {job.progress.total_pages} pages processed
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Failed state: Show error */}
        {job.status === 'failed' && (
          <Card className="border-destructive">
            <CardContent className="py-8">
              <div className="flex flex-col items-center justify-center text-center space-y-4">
                <XCircle className="h-12 w-12 text-destructive" />
                <div>
                  <h3 className="text-lg font-medium text-destructive">Extraction Failed</h3>
                  {job.error && (
                    <p className="text-sm text-muted-foreground mt-2 max-w-md">
                      {job.error}
                    </p>
                  )}
                </div>
                <Button variant="outline" onClick={() => navigate('/jobs/new')}>
                  Try Again
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Completed state: Show results */}
        {job.status === 'completed' && result && (
          <>
            {isMarkdownMode ? (
              // Markdown mode: Show markdown viewer
              <MarkdownViewer documentId={job.document_id} />
            ) : (
              // Standard mode: Show side-by-side document preview and extracted data
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left: Document Preview */}
                <Card className="h-[700px]">
                  <CardHeader className="py-3 px-4">
                    <CardTitle className="text-sm font-medium">Document</CardTitle>
                  </CardHeader>
                  <CardContent className="h-[calc(100%-52px)] p-0">
                    {document ? (
                      document.mime_type === 'application/pdf' ? (
                        <PDFPreview
                          documentId={result.document_id}
                          filename={document.filename}
                        />
                      ) : (
                        <ImagePreview
                          documentId={result.document_id}
                          filename={document.filename}
                        />
                      )
                    ) : (
                      <div className="w-full h-full bg-muted rounded-lg flex items-center justify-center">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Right: Extracted Data */}
                <Card className="h-[700px]">
                  <CardHeader className="py-3 px-4">
                    <CardTitle className="text-sm font-medium">Extracted Data</CardTitle>
                  </CardHeader>
                  <CardContent className="h-[calc(100%-52px)] p-0">
                    <div className="h-full overflow-auto">
                      <SchemaJsonViewer
                        schema={result.extracted_data}
                        showTabs={false}
                        collapsedLevel={3}
                      />
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Metadata summary (compact) */}
            {result.metadata && (
              <div className="flex flex-wrap gap-4 text-sm text-muted-foreground mt-4 pt-4 border-t">
                <span>Model: <span className="text-foreground">{result.metadata.model_used}</span></span>
                <span>Time: <span className="text-foreground">{(result.metadata.processing_time_ms / 1000).toFixed(1)}s</span></span>
                {result.metadata.confidence_score > 0 && (
                  <span>Confidence: <span className="text-foreground">{(result.metadata.confidence_score * 100).toFixed(0)}%</span></span>
                )}
                {/* Display new granular mode fields */}
                {result.split_mode && isSplitMode(result.split_mode) && (
                  <span>Split: <span className="text-foreground">{getSplitModeLabel(result.split_mode)}</span></span>
                )}
                {result.extraction_mode && isExtractionMode(result.extraction_mode) && (
                  <span>Extraction: <span className="text-foreground">{getExtractionModeLabel(result.extraction_mode)}</span></span>
                )}
              </div>
            )}
          </>
        )}
      </PageContent>
    </Page>
  );
}
