/**
 * MarkdownViewer Component
 *
 * Displays markdown content for document pages with debugging capabilities.
 *
 * Design Principles:
 * - Single Responsibility: Display markdown content only
 * - useEffect Best Practices: Proper dependencies and cleanup
 * - Composition: Uses shadcn/ui Tabs component
 * - Error Handling: Loading and error states
 * - Accessibility: ARIA labels and keyboard navigation
 */

import { useState, useMemo, useCallback } from 'react';
import { Copy, Check, Loader2, AlertCircle } from 'lucide-react';
import DOMPurify from 'dompurify';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { useDocumentMarkdown } from '@/hooks/useDocumentMarkdown';
import { getMarkdownConverterLabel } from '@/types/enums';

interface MarkdownViewerProps {
  documentId: string;
}

/**
 * Individual page markdown view with copy functionality
 */
function PageMarkdownView({
  pageNumber,
  content,
  provider,
  generatedAt,
}: {
  pageNumber: number;
  content: string;
  provider?: string;
  generatedAt?: string;
}) {
  const [copied, setCopied] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  // Copy to clipboard handler with timeout reset
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [content]);

  // Format timestamp for display
  const formattedTime = useMemo(() => {
    if (!generatedAt) return null;
    try {
      return new Date(generatedAt).toLocaleString();
    } catch {
      return generatedAt;
    }
  }, [generatedAt]);

  return (
    <div className="space-y-4">
      {/* Header with metadata and actions */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium">Page {pageNumber}</h3>
            {provider && (
              <Badge variant="secondary" className="text-xs">
                {getMarkdownConverterLabel(provider as any)}
              </Badge>
            )}
          </div>
          {formattedTime && (
            <p className="text-xs text-muted-foreground">
              Generated: {formattedTime}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={showPreview ? 'default' : 'outline'}
            size="sm"
            onClick={() => setShowPreview(!showPreview)}
          >
            {showPreview ? 'Raw' : 'Preview'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            disabled={copied}
          >
            {copied ? (
              <>
                <Check className="h-4 w-4 mr-1" />
                Copied
              </>
            ) : (
              <>
                <Copy className="h-4 w-4 mr-1" />
                Copy
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Content display */}
      <div className="border rounded-lg p-4 max-h-[600px] overflow-auto" style={{ backgroundColor: 'hsl(var(--muted) / 0.3)' }}>
        {showPreview ? (
          <div
            className="prose prose-sm max-w-none dark:prose-invert"
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(
                content.replace(/\n/g, '<br />'),
                {
                  ALLOWED_TAGS: ['br', 'p', 'strong', 'em', 'code', 'pre', 'table', 'tr', 'td', 'th', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'a', 'blockquote', 'hr'],
                  ALLOWED_ATTR: ['class', 'href', 'target', 'rel']
                }
              ),
            }}
          />
        ) : (
          <pre className="text-xs font-mono whitespace-pre-wrap break-words">
            {content}
          </pre>
        )}
      </div>
    </div>
  );
}

/**
 * Main MarkdownViewer component
 */
export function MarkdownViewer({ documentId }: MarkdownViewerProps) {
  const { pages, isLoading, error, refetch } = useDocumentMarkdown(documentId);

  // Filter pages with markdown content
  const pagesWithMarkdown = useMemo(
    () => pages.filter((page) => page.markdown_content),
    [pages]
  );

  // Loading state
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Markdown Content</CardTitle>
          <CardDescription>Loading document pages...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Markdown Content</CardTitle>
          <CardDescription>Error loading markdown content</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <AlertCircle className="h-12 w-12 text-red-500" />
            <p className="text-sm text-muted-foreground">{error.message}</p>
            <Button onClick={refetch} variant="outline">
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // No markdown content
  if (pagesWithMarkdown.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Markdown Content</CardTitle>
          <CardDescription>No markdown content available</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 space-y-2">
            <p className="text-sm text-muted-foreground">
              This document does not have markdown content generated yet.
            </p>
            <p className="text-xs text-muted-foreground">
              Markdown content is only available for jobs using markdown pipeline mode.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Display markdown content in tabs
  return (
    <Card>
      <CardHeader>
        <CardTitle>Markdown Content</CardTitle>
        <CardDescription>
          Layout-preserving markdown extracted from document pages
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue={`page-${pagesWithMarkdown[0].page_number}`}>
          <TabsList className="w-full justify-start overflow-x-auto">
            {pagesWithMarkdown.map((page) => (
              <TabsTrigger key={page.id} value={`page-${page.page_number}`}>
                Page {page.page_number}
              </TabsTrigger>
            ))}
          </TabsList>
          {pagesWithMarkdown.map((page) => (
            <TabsContent key={page.id} value={`page-${page.page_number}`} className="mt-4">
              <PageMarkdownView
                pageNumber={page.page_number}
                content={page.markdown_content || ''}
                provider={page.markdown_provider}
                generatedAt={page.markdown_generated_at}
              />
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  );
}
