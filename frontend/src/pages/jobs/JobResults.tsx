import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Download } from 'lucide-react';
import { toast } from 'sonner';

import { Page, PageHeader, PageContent } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PDFPreview } from '@/components/preview/PDFPreview';
import { ImagePreview } from '@/components/preview/ImagePreview';
import { SchemaJsonViewer } from '@/components/preview/SchemaJsonViewer';
import type { JobResultResponse } from '@/types/job';
import type { DocumentStatusResponse } from '@/lib/api';
import { getJobResult, getDocument } from '@/lib/api';

export function JobResults() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [result, setResult] = useState<JobResultResponse | null>(null);
  const [document, setDocument] = useState<DocumentStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (id) {
      loadResult(id);
    }
  }, [id]);

  const loadResult = async (jobId: string) => {
    try {
      setIsLoading(true);
      const data = await getJobResult(jobId);
      setResult(data);

      // Fetch document metadata to determine file type
      const docData = await getDocument(data.document_id);
      setDocument(docData);
    } catch (error) {
      toast.error('Failed to load results', {
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

  if (isLoading) {
    return (
      <Page>
        <PageContent>
          <div className="flex items-center justify-center h-64">
            <p className="text-muted-foreground">Loading results...</p>
          </div>
        </PageContent>
      </Page>
    );
  }

  if (!result) {
    return null;
  }

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Jobs', href: '/jobs' },
          { label: `Job ${id?.substring(0, 8)}`, href: `/jobs/${id}` },
          { label: 'Results' },
        ]}
        title="Extraction Results"
        subtitle="View and download the extracted data"
      />
      <PageContent>
        <div className="flex gap-2 mb-6">
          <Button variant="outline" onClick={() => navigate(`/jobs/${id}`)}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Job Details
          </Button>
          <Button onClick={handleDownload}>
            <Download className="mr-2 h-4 w-4" />
            Download JSON
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-6">
          {/* Left Column: Document Preview */}
          <Card className="h-[800px]">
            <CardHeader>
              <CardTitle>Document Preview</CardTitle>
            </CardHeader>
            <CardContent className="h-[calc(100%-80px)] p-0">
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
                  <p className="text-muted-foreground">Loading preview...</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Right Column: Extracted Data */}
          <Card className="h-[800px]">
            <CardHeader>
              <CardTitle>Extracted Data</CardTitle>
            </CardHeader>
            <CardContent className="h-[calc(100%-80px)] p-0">
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
      </PageContent>
    </Page>
  );
}
