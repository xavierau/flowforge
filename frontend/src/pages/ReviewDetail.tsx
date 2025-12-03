/**
 * ReviewDetail Page
 *
 * Split-view review interface with document viewer and field editor.
 * Following React best practices:
 * - Proper useEffect with cleanup
 * - Keyboard shortcuts with event listeners
 * - Error boundaries with error states
 * - Performance optimization with useCallback
 */

import { useEffect, useCallback, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useReviewStore } from '@/store/reviewStore';
import { DocumentViewer } from '@/components/review/DocumentViewer';
import { FieldEditor } from '@/components/review/FieldEditor';
import { ConfidenceBadge } from '@/components/review/ConfidenceBadge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  AlertCircle,
  Check,
  X,
  AlertTriangle,
  ArrowLeft,
  Save,
} from 'lucide-react';
import {
  getReviewStatusLabel,
  getReviewPriorityIcon,
  getReviewPriorityLabel,
  CorrectionType,
  ReviewRequestStatus,
} from '@/types/review';
import type { ReviewCorrection } from '@/types/review';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

export function ReviewDetail() {
  const { reviewId } = useParams<{ reviewId: string }>();
  const navigate = useNavigate();

  const {
    currentReview,
    corrections,
    loading,
    error,
    loadReview,
    startReview,
    submitReview,
    addCorrection,
    clearError,
  } = useReviewStore();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [reviewNotes, setReviewNotes] = useState('');

  // Load review on mount
  useEffect(() => {
    if (!reviewId) {
      navigate('/reviews');
      return;
    }

    const load = async () => {
      try {
        await loadReview(reviewId);
      } catch (err) {
        console.error('Failed to load review:', err);
      }
    };

    load();
  }, [reviewId, loadReview, navigate]);

  // Start review if assigned and not yet started
  useEffect(() => {
    if (
      currentReview &&
      currentReview.status === ReviewRequestStatus.ASSIGNED &&
      reviewId
    ) {
      const start = async () => {
        try {
          await startReview(reviewId);
          toast.success('Review started');
        } catch (err) {
          console.error('Failed to start review:', err);
        }
      };

      start();
    }
  }, [currentReview, reviewId, startReview]);

  // Handle field changes
  const handleFieldChange = useCallback(
    (fieldPath: string, newValue: unknown, originalValue: unknown) => {
      if (!currentReview?.extraction_job?.id) return;

      const correction: ReviewCorrection = {
        extraction_result_id: currentReview.extraction_job.id,
        field_path: fieldPath,
        original_value: originalValue,
        corrected_value: newValue,
        correction_type: CorrectionType.VALUE_CHANGE,
        correction_notes: null,
        reviewer_confidence: null,
      };

      addCorrection(correction);
      toast.success(`Field "${fieldPath}" updated`);
    },
    [currentReview, addCorrection]
  );

  // Submit review with approval
  const handleApprove = useCallback(async () => {
    if (!reviewId) return;

    setIsSubmitting(true);
    try {
      await submitReview(reviewId, {
        corrections,
        review_notes: reviewNotes || undefined,
        action: 'approve',
      });

      toast.success('Review approved and submitted');
      navigate('/reviews');
    } catch (err) {
      console.error('Failed to submit review:', err);
      toast.error('Failed to submit review');
    } finally {
      setIsSubmitting(false);
    }
  }, [reviewId, corrections, reviewNotes, submitReview, navigate]);

  // Submit review with rejection
  const handleReject = useCallback(async () => {
    if (!reviewId) return;

    setIsSubmitting(true);
    try {
      await submitReview(reviewId, {
        corrections,
        review_notes: reviewNotes || 'Document rejected',
        action: 'reject',
      });

      toast.success('Review rejected');
      navigate('/reviews');
    } catch (err) {
      console.error('Failed to reject review:', err);
      toast.error('Failed to reject review');
    } finally {
      setIsSubmitting(false);
    }
  }, [reviewId, corrections, reviewNotes, submitReview, navigate]);

  // Escalate review
  const handleEscalate = useCallback(async () => {
    if (!reviewId) return;

    const reason = prompt('Reason for escalation:');
    if (!reason) return;

    try {
      const { escalateReview } = useReviewStore.getState();
      await escalateReview(reviewId, reason);
      toast.success('Review escalated');
      navigate('/reviews');
    } catch (err) {
      console.error('Failed to escalate review:', err);
      toast.error('Failed to escalate review');
    }
  }, [reviewId, navigate]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Ctrl/Cmd + S to save
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        // Auto-save is handled on field blur
        toast.info('Changes are auto-saved');
      }

      // A for approve
      if (e.key === 'a' && !e.ctrlKey && !e.metaKey) {
        const target = e.target as HTMLElement;
        if (!['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) {
          e.preventDefault();
          handleApprove();
        }
      }

      // Escape to go back
      if (e.key === 'Escape') {
        navigate('/reviews');
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [handleApprove, navigate]);

  // Loading state
  if (loading && !currentReview) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading review...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !currentReview) {
    return (
      <div className="flex items-center justify-center min-h-screen p-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="space-y-4">
            <p>{error || 'Review not found'}</p>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => navigate('/reviews')}>
                Back to Queue
              </Button>
              {error && (
                <Button variant="outline" onClick={clearError}>
                  Dismiss
                </Button>
              )}
            </div>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="border-b bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Left: Back button and title */}
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/reviews')}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Queue
            </Button>

            <div>
              <h1 className="text-lg font-semibold flex items-center gap-2">
                <span className="text-2xl">
                  {getReviewPriorityIcon(currentReview.priority)}
                </span>
                {currentReview.document?.filename || 'Document Review'}
              </h1>
              <p className="text-sm text-muted-foreground">
                {getReviewPriorityLabel(currentReview.priority)} Priority •{' '}
                {getReviewStatusLabel(currentReview.status)}
              </p>
            </div>
          </div>

          {/* Right: Actions and confidence */}
          <div className="flex items-center gap-4">
            <ConfidenceBadge score={currentReview.confidence_score} />

            {corrections.length > 0 && (
              <Badge variant="secondary">
                <Save className="h-3 w-3 mr-1" />
                {corrections.length} {corrections.length === 1 ? 'change' : 'changes'}
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* Split View */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Document Viewer (50%) */}
        <div className="w-1/2 border-r p-4 overflow-auto">
          <DocumentViewer
            documentId={currentReview.document_id || currentReview.extraction_job?.document_id || ''}
            pageCount={currentReview.document?.page_count}
          />
        </div>

        {/* Right: Field Editor (50%) */}
        <div className="w-1/2 p-4 overflow-auto">
          <FieldEditor
            data={currentReview.extracted_data || {}}
            onChange={handleFieldChange}
          />
        </div>
      </div>

      {/* Action Bar */}
      <div className="border-t bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Left: Review notes */}
          <div className="flex-1 max-w-md">
            <input
              type="text"
              placeholder="Add review notes (optional)"
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              className="w-full px-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              onClick={handleEscalate}
              disabled={isSubmitting}
            >
              <AlertTriangle className="h-4 w-4 mr-2" />
              Escalate
            </Button>

            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={isSubmitting}
            >
              <X className="h-4 w-4 mr-2" />
              Reject
            </Button>

            <Button onClick={handleApprove} disabled={isSubmitting}>
              <Check className="h-4 w-4 mr-2" />
              Approve & Next
            </Button>
          </div>
        </div>
      </div>

      {/* Keyboard Shortcuts Hint */}
      <div className="absolute bottom-20 right-6 bg-black/80 text-white text-xs px-3 py-2 rounded-md">
        <div className="space-y-1">
          <div>
            <kbd className="px-1.5 py-0.5 bg-white/20 rounded">A</kbd> Approve
          </div>
          <div>
            <kbd className="px-1.5 py-0.5 bg-white/20 rounded">Esc</kbd> Back to queue
          </div>
        </div>
      </div>
    </div>
  );
}
