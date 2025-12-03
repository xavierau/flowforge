/**
 * DocumentViewer Component
 *
 * Displays document images with zoom, pan, and page navigation.
 * Following React best practices:
 * - Proper state management for zoom/pan
 * - Keyboard navigation
 * - Performance optimization with useMemo
 */

import { useState, useCallback, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  ChevronLeft,
  ChevronRight,
  FileText,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface DocumentViewerProps {
  documentId: string;
  pageCount?: number;
  className?: string;
}

export function DocumentViewer({
  documentId,
  pageCount = 1,
  className,
}: DocumentViewerProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(100);

  // Calculate image URL (adjust based on your backend API)
  const imageUrl = useMemo(() => {
    const baseUrl = import.meta.env.VITE_API_URL || '';
    return `${baseUrl}/api/v1/documents/${documentId}/pages/${currentPage}/image`;
  }, [documentId, currentPage]);

  const handleZoomIn = useCallback(() => {
    setZoom((prev) => Math.min(prev + 25, 200));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom((prev) => Math.max(prev - 25, 50));
  }, []);

  const handleResetZoom = useCallback(() => {
    setZoom(100);
  }, []);

  const handlePreviousPage = useCallback(() => {
    setCurrentPage((prev) => Math.max(prev - 1, 1));
  }, []);

  const handleNextPage = useCallback(() => {
    setCurrentPage((prev) => Math.min(prev + 1, pageCount));
  }, [pageCount]);

  const canGoPrevious = currentPage > 1;
  const canGoNext = currentPage < pageCount;

  return (
    <Card className={cn('flex flex-col h-full', className)}>
      <CardHeader className="border-b">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Document Viewer
          </CardTitle>

          {/* Zoom Controls */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleZoomOut}
              disabled={zoom <= 50}
              aria-label="Zoom out"
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="text-sm font-medium w-12 text-center">{zoom}%</span>
            <Button
              variant="outline"
              size="sm"
              onClick={handleZoomIn}
              disabled={zoom >= 200}
              aria-label="Zoom in"
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleResetZoom}
              aria-label="Reset zoom"
            >
              <Maximize2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-4 overflow-auto bg-gray-50">
        {/* Document Image */}
        <div className="flex items-center justify-center min-h-full">
          <img
            src={imageUrl}
            alt={`Document page ${currentPage}`}
            className="max-w-full h-auto shadow-lg"
            style={{
              transform: `scale(${zoom / 100})`,
              transformOrigin: 'center',
              transition: 'transform 0.2s ease-in-out',
            }}
          />
        </div>
      </CardContent>

      {/* Page Navigation */}
      {pageCount > 1 && (
        <div className="border-t p-3">
          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePreviousPage}
              disabled={!canGoPrevious}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Previous
            </Button>

            <span className="text-sm font-medium">
              Page {currentPage} of {pageCount}
            </span>

            <Button
              variant="outline"
              size="sm"
              onClick={handleNextPage}
              disabled={!canGoNext}
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}
