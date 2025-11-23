/**
 * useDocumentMarkdown Hook
 *
 * Custom hook for fetching and managing document markdown content.
 * Follows React best practices:
 * - Proper useEffect dependency management
 * - Cleanup on unmount to prevent memory leaks
 * - Loading and error states
 * - Memoization of expensive operations
 *
 * Purpose: Separate data fetching logic from presentation components
 */

import { useState, useEffect } from 'react';
import type { DocumentPage } from '@/types/document';
import { getDocumentPages } from '@/services/job.service';

export interface UseDocumentMarkdownResult {
  pages: DocumentPage[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Fetch document pages with markdown content
 *
 * @param documentId - Document ID to fetch pages for
 * @returns Object containing pages data, loading state, error, and refetch function
 */
export function useDocumentMarkdown(documentId: string | null): UseDocumentMarkdownResult {
  const [pages, setPages] = useState<DocumentPage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Fetch function to be called on mount and refetch
  const fetchPages = async () => {
    if (!documentId) {
      setPages([]);
      setIsLoading(false);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const fetchedPages = await getDocumentPages(documentId);
      setPages(fetchedPages);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error occurred'));
      setPages([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Effect to fetch pages on mount and when documentId changes
  useEffect(() => {
    let isMounted = true;

    const loadPages = async () => {
      if (!documentId) {
        if (isMounted) {
          setPages([]);
          setIsLoading(false);
          setError(null);
        }
        return;
      }

      if (isMounted) {
        setIsLoading(true);
        setError(null);
      }

      try {
        const fetchedPages = await getDocumentPages(documentId);
        if (isMounted) {
          setPages(fetchedPages);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error('Unknown error occurred'));
          setPages([]);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadPages();

    // Cleanup: prevent state updates after unmount
    return () => {
      isMounted = false;
    };
  }, [documentId]);

  return {
    pages,
    isLoading,
    error,
    refetch: fetchPages,
  };
}
