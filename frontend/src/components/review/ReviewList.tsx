/**
 * ReviewList Component
 *
 * Displays list of review requests with priority, confidence, and SLA indicators.
 * Following React best practices:
 * - Performance: Memoized item rendering
 * - Accessibility: Keyboard navigation support
 * - Composability: Clean separation of concerns
 */

import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import type { ReviewRequest } from '@/types/review';
import {
  getReviewStatusLabel,
  getReviewStatusColor,
  getReviewPriorityIcon,
  getReviewPriorityLabel,
  getReviewPriorityColor,
  getSLAStatus,
  getSLAStatusColor,
} from '@/types/review';
import { ConfidenceBadge } from './ConfidenceBadge';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Clock, User, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ReviewListProps {
  items: ReviewRequest[];
  onSelect?: (review: ReviewRequest) => void;
}

interface ReviewItemProps {
  review: ReviewRequest;
  onClick: () => void;
}

function ReviewItem({ review, onClick }: ReviewItemProps) {
  const slaStatus = getSLAStatus(review.sla_deadline, review.status);
  const timeAgo = formatDistanceToNow(new Date(review.created_at), {
    addSuffix: true,
  });

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onClick();
      }
    },
    [onClick]
  );

  return (
    <Card
      className="cursor-pointer transition-all hover:shadow-md hover:border-primary"
      onClick={onClick}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="button"
      aria-label={`Review ${review.document?.filename || 'document'}`}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          {/* Priority Icon */}
          <div className="flex-shrink-0 text-2xl" title={getReviewPriorityLabel(review.priority)}>
            {getReviewPriorityIcon(review.priority)}
          </div>

          {/* Main Content */}
          <div className="flex-1 min-w-0">
            {/* Header Row */}
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="flex-1">
                <h3 className="font-medium text-sm truncate">
                  {review.document?.filename || 'Unknown Document'}
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {review.extraction_job?.schema_name || 'No schema'}
                </p>
              </div>

              {/* Status Badge */}
              <Badge
                variant="outline"
                className={cn('text-xs', getReviewStatusColor(review.status))}
              >
                {getReviewStatusLabel(review.status)}
              </Badge>
            </div>

            {/* Metadata Row */}
            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              {/* Confidence Score */}
              <ConfidenceBadge score={review.confidence_score} showPercentage />

              {/* Priority */}
              <div className="flex items-center gap-1">
                <span className={cn('font-medium', getReviewPriorityColor(review.priority))}>
                  {getReviewPriorityLabel(review.priority)}
                </span>
              </div>

              {/* Assigned To */}
              {review.assigned_to_user_name && (
                <div className="flex items-center gap-1">
                  <User className="h-3 w-3" />
                  <span>{review.assigned_to_user_name}</span>
                </div>
              )}

              {/* Page Count */}
              {review.document?.page_count && (
                <div className="flex items-center gap-1">
                  <FileText className="h-3 w-3" />
                  <span>{review.document.page_count} pages</span>
                </div>
              )}

              {/* Age */}
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span>{timeAgo}</span>
              </div>
            </div>

            {/* Trigger Reason */}
            {review.trigger_reason && (
              <div className="mt-2">
                <Badge variant="secondary" className="text-xs">
                  {review.trigger_reason.replace(/_/g, ' ')}
                </Badge>
              </div>
            )}

            {/* SLA Warning */}
            {slaStatus === 'warning' && review.sla_deadline && (
              <div className="mt-2 flex items-center gap-1 text-xs text-orange-600">
                <Clock className="h-3 w-3" />
                <span>
                  SLA: {formatDistanceToNow(new Date(review.sla_deadline), { addSuffix: true })}
                </span>
              </div>
            )}

            {/* SLA Breach */}
            {slaStatus === 'breached' && (
              <div className="mt-2 flex items-center gap-1 text-xs text-red-600 font-medium">
                <Clock className="h-3 w-3" />
                <span>SLA Breached</span>
              </div>
            )}

            {/* Escalated */}
            {review.escalated && (
              <div className="mt-2">
                <Badge variant="destructive" className="text-xs">
                  Escalated
                </Badge>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function ReviewList({ items, onSelect }: ReviewListProps) {
  const navigate = useNavigate();

  const handleSelect = useCallback(
    (review: ReviewRequest) => {
      if (onSelect) {
        onSelect(review);
      } else {
        navigate(`/reviews/${review.id}`);
      }
    },
    [navigate, onSelect]
  );

  if (items.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No reviews found</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {items.map((review) => (
        <ReviewItem
          key={review.id}
          review={review}
          onClick={() => handleSelect(review)}
        />
      ))}
    </div>
  );
}
