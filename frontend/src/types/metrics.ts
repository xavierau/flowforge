/**
 * Metrics and billing type definitions
 *
 * Aligns with backend API responses from /api/v1/metrics/*
 */

/**
 * Time series data point for line charts
 */
export interface TimeSeriesDataPoint {
  date: string;
  value: number;
}

/**
 * Token usage data with breakdown
 */
export interface TokenUsageData {
  date: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

/**
 * Model usage distribution
 */
export interface ModelDistribution {
  model: string;
  count: number;
  percentage: number;
}

/**
 * Summary statistics for dashboard
 */
export interface MetricStats {
  total_jobs: number;
  total_pages: number;
  total_tokens: number;
  estimated_cost: number;
}

/**
 * Complete dashboard metrics response
 */
export interface DashboardMetrics {
  stats: MetricStats;
  jobs_over_time: TimeSeriesDataPoint[];
  pages_over_time: TimeSeriesDataPoint[];
  tokens_over_time: TokenUsageData[];
  model_distribution: ModelDistribution[];
}

/**
 * Individual completed job for billing
 */
export interface CompletedJob {
  job_id: string;
  document_id: string;
  document_name: string;
  model: string;
  pages_processed: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_cost: number;
  processing_time: number;
  completed_at: string;
  tenant_id: string;
}

/**
 * Completed jobs response with pagination
 */
export interface CompletedJobsResponse {
  jobs: CompletedJob[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  total_cost: number;
}

/**
 * Filters for completed jobs query
 */
export interface CompletedJobsFilters {
  start_date?: string;
  end_date?: string;
  model?: string;
}

/**
 * Date range options for metrics
 */
export type DateRangeOption = 7 | 30 | 90;
