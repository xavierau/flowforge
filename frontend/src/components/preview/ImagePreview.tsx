import { useEffect, useState, useCallback } from 'react';
import { Loader2, ZoomIn, ZoomOut, RotateCw } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { getDocumentFile } from '@/lib/api';

interface ImagePreviewProps {
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
 * Image Preview Component
 *
 * Displays an image document with zoom and rotation controls.
 * Fetches the image file from the backend using the document ID.
 *
 * Features:
 * - Zoom in/out controls
 * - Rotation (90° increments)
 * - Fit to container
 * - Loading state
 * - Error handling
 *
 * @example
 * ```tsx
 * <ImagePreview documentId="123" filename="receipt.jpg" />
 * ```
 */
export function ImagePreview({ documentId, filename }: ImagePreviewProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [scale, setScale] = useState<number>(1.0);
  const [rotation, setRotation] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load image file from backend
  useEffect(() => {
    let isCancelled = false;
    let objectUrl: string | null = null;

    const loadImage = async () => {
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
        setImageUrl(objectUrl);
      } catch (err) {
        if (!isCancelled) {
          const message = err instanceof Error ? err.message : 'Failed to load image';
          setError(message);
          toast.error('Failed to load image', {
            description: message,
          });
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };

    loadImage();

    // Cleanup function - revoke object URL to prevent memory leaks
    return () => {
      isCancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [documentId]);

  // Zoom handlers
  const zoomIn = useCallback(() => {
    setScale((prev) => Math.min(3.0, prev + 0.2));
  }, []);

  const zoomOut = useCallback(() => {
    setScale((prev) => Math.max(0.3, prev - 0.2));
  }, []);

  const resetZoom = useCallback(() => {
    setScale(1.0);
  }, []);

  // Rotation handler
  const rotate = useCallback(() => {
    setRotation((prev) => (prev + 90) % 360);
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground">Loading image...</p>
      </div>
    );
  }

  // Error state
  if (error || !imageUrl) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-6">
        <p className="text-destructive mb-2">Failed to load image</p>
        <p className="text-sm text-muted-foreground">{error || 'Unknown error'}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Controls */}
      <div className="flex items-center justify-between p-3 border-b bg-muted/50">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {filename || 'Image'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={zoomOut}>
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={resetZoom}
            disabled={scale === 1.0}
          >
            <span className="text-sm">{Math.round(scale * 100)}%</span>
          </Button>
          <Button variant="outline" size="sm" onClick={zoomIn}>
            <ZoomIn className="h-4 w-4" />
          </Button>
          <div className="w-px h-6 bg-border mx-1" />
          <Button variant="outline" size="sm" onClick={rotate}>
            <RotateCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Image Viewer */}
      <div className="flex-1 overflow-auto bg-muted/20">
        <div className="flex items-center justify-center min-h-full p-4">
          <img
            src={imageUrl}
            alt={filename || 'Document preview'}
            style={{
              transform: `scale(${scale}) rotate(${rotation}deg)`,
              transition: 'transform 0.2s ease-in-out',
              maxWidth: '100%',
              maxHeight: '100%',
              objectFit: 'contain',
            }}
            className="shadow-lg"
          />
        </div>
      </div>
    </div>
  );
}
