import { useEffect, useState, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { ChevronLeft, ChevronRight, Loader2, ZoomIn, ZoomOut } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { getDocumentFile } from '@/lib/api';

import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PDFPreviewProps {
  /**
   * Document ID to fetch and display
   */
  documentId: string;

  /**
   * Optional filename for display
   */
  filename?: string;

  /**
   * Optional container height
   * @default "100%"
   */
  height?: string;
}

/**
 * PDF Preview Component
 *
 * Displays a PDF document with page navigation and zoom controls.
 * Fetches the PDF file from the backend using the document ID.
 *
 * Features:
 * - Page navigation (prev/next)
 * - Page number display
 * - Zoom in/out controls
 * - Loading state
 * - Error handling
 *
 * @example
 * ```tsx
 * <PDFPreview documentId="123" filename="invoice.pdf" />
 * ```
 */
export function PDFPreview({ documentId }: PDFPreviewProps) {
  const [file, setFile] = useState<string | null>(null);
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load PDF file from backend
  useEffect(() => {
    let isCancelled = false;
    let objectUrl: string | null = null;

    const loadPDF = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const blob = await getDocumentFile(documentId);

        // Check if component was unmounted
        if (isCancelled) {
          return;
        }

        // Create object URL for the blob
        objectUrl = URL.createObjectURL(blob);
        setFile(objectUrl);
      } catch (err) {
        if (!isCancelled) {
          const message = err instanceof Error ? err.message : 'Failed to load PDF';
          setError(message);
          toast.error('Failed to load PDF', {
            description: message,
          });
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };

    loadPDF();

    // Cleanup function
    return () => {
      isCancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [documentId]);

  // Handle document load success
  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPageNumber(1);
  }, []);

  // Handle document load error
  const onDocumentLoadError = useCallback((error: Error) => {
    setError(error.message);
    toast.error('Failed to load PDF', {
      description: error.message,
    });
  }, []);

  // Navigation handlers
  const goToPrevPage = useCallback(() => {
    setPageNumber((prev) => Math.max(1, prev - 1));
  }, []);

  const goToNextPage = useCallback(() => {
    setPageNumber((prev) => Math.min(numPages, prev + 1));
  }, [numPages]);

  // Zoom handlers
  const zoomIn = useCallback(() => {
    setScale((prev) => Math.min(2.0, prev + 0.1));
  }, []);

  const zoomOut = useCallback(() => {
    setScale((prev) => Math.max(0.5, prev - 0.1));
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground">Loading PDF...</p>
      </div>
    );
  }

  // Error state
  if (error || !file) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-6">
        <p className="text-destructive mb-2">Failed to load PDF</p>
        <p className="text-sm text-muted-foreground">{error || 'Unknown error'}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Controls */}
      <div className="flex items-center justify-between p-3 border-b bg-muted/50">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={goToPrevPage}
            disabled={pageNumber <= 1}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm">
            Page {pageNumber} of {numPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={goToNextPage}
            disabled={pageNumber >= numPages}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={zoomOut}>
            <ZoomOut className="h-4 w-4" />
          </Button>
          <span className="text-sm">{Math.round(scale * 100)}%</span>
          <Button variant="outline" size="sm" onClick={zoomIn}>
            <ZoomIn className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* PDF Viewer */}
      <div className="flex-1 overflow-auto bg-muted/20">
        <div className="flex justify-center p-4">
          <Document
            file={file}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            }
          >
            <Page
              pageNumber={pageNumber}
              scale={scale}
              loading={
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              }
              renderTextLayer={true}
              renderAnnotationLayer={true}
            />
          </Document>
        </div>
      </div>
    </div>
  );
}
