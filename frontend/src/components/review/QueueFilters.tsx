/**
 * QueueFilters Component
 *
 * Filter and sort controls for review queue.
 * Following React best practices:
 * - Controlled component pattern
 * - Proper onChange handling
 * - No internal state (lifted to parent)
 */

import { ReviewRequestStatus, ReviewPriority } from '@/types/review';
import type { QueueFilters as QueueFiltersType } from '@/types/review';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { X, Filter } from 'lucide-react';

interface QueueFiltersProps {
  filters: QueueFiltersType;
  onChange: (filters: QueueFiltersType) => void;
}

export function QueueFilters({ filters, onChange }: QueueFiltersProps) {
  const hasActiveFilters =
    filters.status ||
    filters.priority ||
    filters.assigned_to_me ||
    filters.unassigned ||
    filters.escalated;

  const handleClearFilters = () => {
    onChange({});
  };

  const handleStatusChange = (value: string) => {
    if (value === 'all') {
      const { status, ...rest } = filters;
      onChange(rest);
    } else {
      onChange({ ...filters, status: value as ReviewRequestStatus });
    }
  };

  const handlePriorityChange = (value: string) => {
    if (value === 'all') {
      const { priority, ...rest } = filters;
      onChange(rest);
    } else {
      onChange({ ...filters, priority: value as ReviewPriority });
    }
  };

  const handleSortChange = (value: string) => {
    if (value === 'default') {
      const { sort_by, sort_order, ...rest } = filters;
      onChange(rest);
    } else {
      onChange({
        ...filters,
        sort_by: value as QueueFiltersType['sort_by'],
        sort_order: 'desc',
      });
    }
  };

  const toggleMyQueue = () => {
    onChange({
      ...filters,
      assigned_to_me: !filters.assigned_to_me,
    });
  };

  const toggleUnassigned = () => {
    onChange({
      ...filters,
      unassigned: !filters.unassigned,
    });
  };

  const toggleEscalated = () => {
    onChange({
      ...filters,
      escalated: !filters.escalated,
    });
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Quick Filters */}
      <div className="flex flex-wrap gap-2">
        <Button
          variant={filters.assigned_to_me ? 'default' : 'outline'}
          size="sm"
          onClick={toggleMyQueue}
        >
          My Queue
        </Button>
        <Button
          variant={filters.unassigned ? 'default' : 'outline'}
          size="sm"
          onClick={toggleUnassigned}
        >
          Unassigned
        </Button>
        <Button
          variant={filters.escalated ? 'default' : 'outline'}
          size="sm"
          onClick={toggleEscalated}
        >
          Escalated
        </Button>
      </div>

      {/* Advanced Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Filters:</span>
        </div>

        {/* Status Filter */}
        <Select
          value={filters.status as string || 'all'}
          onValueChange={handleStatusChange}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value={ReviewRequestStatus.PENDING}>Pending</SelectItem>
            <SelectItem value={ReviewRequestStatus.ASSIGNED}>Assigned</SelectItem>
            <SelectItem value={ReviewRequestStatus.IN_REVIEW}>In Review</SelectItem>
            <SelectItem value={ReviewRequestStatus.COMPLETED}>Completed</SelectItem>
            <SelectItem value={ReviewRequestStatus.ESCALATED}>Escalated</SelectItem>
          </SelectContent>
        </Select>

        {/* Priority Filter */}
        <Select
          value={filters.priority as string || 'all'}
          onValueChange={handlePriorityChange}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All Priorities" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Priorities</SelectItem>
            <SelectItem value={ReviewPriority.CRITICAL}>⚡ Critical</SelectItem>
            <SelectItem value={ReviewPriority.HIGH}>🔶 High</SelectItem>
            <SelectItem value={ReviewPriority.NORMAL}>🟢 Normal</SelectItem>
            <SelectItem value={ReviewPriority.LOW}>⚪ Low</SelectItem>
          </SelectContent>
        </Select>

        {/* Sort By */}
        <Select
          value={filters.sort_by || 'default'}
          onValueChange={handleSortChange}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Sort By" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="default">Default Order</SelectItem>
            <SelectItem value="priority">Priority</SelectItem>
            <SelectItem value="age">Age (Oldest First)</SelectItem>
            <SelectItem value="confidence">Confidence (Low First)</SelectItem>
            <SelectItem value="sla_deadline">SLA Deadline</SelectItem>
          </SelectContent>
        </Select>

        {/* Clear Filters */}
        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={handleClearFilters}>
            <X className="h-4 w-4 mr-1" />
            Clear Filters
          </Button>
        )}
      </div>

      {/* Active Filter Tags */}
      {hasActiveFilters && (
        <div className="flex flex-wrap gap-2">
          {filters.status && (
            <Badge variant="secondary">
              Status: {filters.status}
              <button
                className="ml-1 hover:text-destructive"
                onClick={() => {
                  const { status, ...rest } = filters;
                  onChange(rest);
                }}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          )}
          {filters.priority && (
            <Badge variant="secondary">
              Priority: {filters.priority}
              <button
                className="ml-1 hover:text-destructive"
                onClick={() => {
                  const { priority, ...rest } = filters;
                  onChange(rest);
                }}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}
