/**
 * Review Store - Zustand State Management
 *
 * Manages review queue state, current review, and corrections.
 * Following React best practices:
 * - Immutable state updates
 * - Proper error handling
 * - No side effects in store (only in actions)
 * - Clear action naming
 * - Debounced filter changes to prevent excessive API calls
 */

import { create } from 'zustand';
import type {
  ReviewRequest,
  ReviewCorrection,
  QueueFilters,
  ReviewMetrics,
  SubmitReviewRequest,
} from '@/types/review';
import * as reviewService from '@/services/review.service';

// Debounce delay in milliseconds
const FILTER_DEBOUNCE_MS = 300;

// Debounce timer reference (module-level to persist across renders)
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

interface ReviewState {
  // Queue state
  queue: ReviewRequest[];
  queueTotal: number;
  queuePage: number;
  queuePageSize: number;
  queueFilters: QueueFilters;

  // Current review state
  currentReview: ReviewRequest | null;
  corrections: ReviewCorrection[];

  // Metrics
  metrics: ReviewMetrics | null;

  // UI state
  loading: boolean;
  error: string | null;

  // Actions - Queue Management
  fetchQueue: (filters?: QueueFilters) => Promise<void>;
  setQueueFilters: (filters: QueueFilters) => void;
  clearQueue: () => void;

  // Actions - Review Management
  loadReview: (reviewId: string) => Promise<void>;
  assignReview: (reviewId: string, userId?: string) => Promise<void>;
  startReview: (reviewId: string) => Promise<void>;
  submitReview: (reviewId: string, data: SubmitReviewRequest) => Promise<void>;
  cancelReview: (reviewId: string) => Promise<void>;
  escalateReview: (reviewId: string, reason: string) => Promise<void>;

  // Actions - Corrections Management
  addCorrection: (correction: ReviewCorrection) => void;
  updateCorrection: (index: number, correction: ReviewCorrection) => void;
  removeCorrection: (index: number) => void;
  clearCorrections: () => void;

  // Actions - Metrics
  fetchMetrics: () => Promise<void>;

  // Actions - Error Handling
  clearError: () => void;
  setError: (error: string) => void;
}

export const useReviewStore = create<ReviewState>((set, get) => ({
  // Initial state
  queue: [],
  queueTotal: 0,
  queuePage: 1,
  queuePageSize: 20,
  queueFilters: {},

  currentReview: null,
  corrections: [],

  metrics: null,

  loading: false,
  error: null,

  // Queue Actions
  fetchQueue: async (filters?: QueueFilters) => {
    set({ loading: true, error: null });

    try {
      const currentFilters = filters || get().queueFilters;
      const response = await reviewService.getReviewQueue(currentFilters);

      set({
        queue: response.items,
        queueTotal: response.total,
        queuePage: response.page,
        queuePageSize: response.page_size,
        queueFilters: currentFilters,
        loading: false,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch review queue';
      set({ error: message, loading: false });
      throw error;
    }
  },

  setQueueFilters: (filters: QueueFilters) => {
    // Update filters immediately for UI responsiveness
    set({ queueFilters: filters });

    // Debounce the API call to prevent excessive requests
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }

    debounceTimer = setTimeout(() => {
      get().fetchQueue(filters);
      debounceTimer = null;
    }, FILTER_DEBOUNCE_MS);
  },

  clearQueue: () => {
    set({
      queue: [],
      queueTotal: 0,
      queuePage: 1,
      queueFilters: {},
    });
  },

  // Review Management Actions
  loadReview: async (reviewId: string) => {
    set({ loading: true, error: null });

    try {
      const review = await reviewService.getReview(reviewId);

      // Load existing corrections if any
      const corrections = await reviewService.getReviewCorrections(reviewId);

      set({
        currentReview: review,
        corrections: corrections || [],
        loading: false,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load review';
      set({ error: message, loading: false, currentReview: null });
      throw error;
    }
  },

  assignReview: async (reviewId: string, userId?: string) => {
    set({ loading: true, error: null });

    try {
      const updatedReview = await reviewService.assignReview(reviewId, userId);

      // Update current review if it matches
      const state = get();
      if (state.currentReview?.id === reviewId) {
        set({ currentReview: updatedReview });
      }

      // Update queue item if it exists
      const queueIndex = state.queue.findIndex(r => r.id === reviewId);
      if (queueIndex !== -1) {
        const updatedQueue = [...state.queue];
        updatedQueue[queueIndex] = updatedReview;
        set({ queue: updatedQueue });
      }

      set({ loading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to assign review';
      set({ error: message, loading: false });
      throw error;
    }
  },

  startReview: async (reviewId: string) => {
    set({ loading: true, error: null });

    try {
      const updatedReview = await reviewService.startReview(reviewId);

      set({
        currentReview: updatedReview,
        loading: false,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to start review';
      set({ error: message, loading: false });
      throw error;
    }
  },

  submitReview: async (reviewId: string, data: SubmitReviewRequest) => {
    set({ loading: true, error: null });

    try {
      const updatedReview = await reviewService.submitReview(reviewId, data);

      set({
        currentReview: updatedReview,
        corrections: [], // Clear corrections after submit
        loading: false,
      });

      // Refresh queue to reflect completed review
      await get().fetchQueue();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to submit review';
      set({ error: message, loading: false });
      throw error;
    }
  },

  cancelReview: async (reviewId: string) => {
    set({ loading: true, error: null });

    try {
      const updatedReview = await reviewService.cancelReview(reviewId);

      set({
        currentReview: updatedReview,
        loading: false,
      });

      // Refresh queue
      await get().fetchQueue();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to cancel review';
      set({ error: message, loading: false });
      throw error;
    }
  },

  escalateReview: async (reviewId: string, reason: string) => {
    set({ loading: true, error: null });

    try {
      const updatedReview = await reviewService.escalateReview(reviewId, reason);

      set({
        currentReview: updatedReview,
        loading: false,
      });

      // Refresh queue
      await get().fetchQueue();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to escalate review';
      set({ error: message, loading: false });
      throw error;
    }
  },

  // Corrections Management Actions
  addCorrection: (correction: ReviewCorrection) => {
    const state = get();
    set({
      corrections: [...state.corrections, correction],
    });
  },

  updateCorrection: (index: number, correction: ReviewCorrection) => {
    const state = get();
    const updated = [...state.corrections];
    updated[index] = correction;
    set({ corrections: updated });
  },

  removeCorrection: (index: number) => {
    const state = get();
    const updated = state.corrections.filter((_, i) => i !== index);
    set({ corrections: updated });
  },

  clearCorrections: () => {
    set({ corrections: [] });
  },

  // Metrics Actions
  fetchMetrics: async () => {
    set({ loading: true, error: null });

    try {
      const metrics = await reviewService.getReviewMetrics();
      set({ metrics, loading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch metrics';
      set({ error: message, loading: false });
      throw error;
    }
  },

  // Error Handling Actions
  clearError: () => {
    set({ error: null });
  },

  setError: (error: string) => {
    set({ error });
  },
}));
