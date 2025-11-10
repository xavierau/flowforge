/**
 * TypeScript types for Admin API
 * Matches backend schemas in app/schemas/admin.py
 */

// ============================================================================
// Platform Statistics Types
// ============================================================================

export interface PlatformStatistics {
  // Tenant metrics
  total_tenants: number;
  active_tenants: number;
  suspended_tenants: number;
  new_tenants_30d: number;

  // User metrics
  total_users: number;
  active_users: number;

  // Job metrics
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  jobs_24h: number;

  // Document metrics
  total_documents: number;
  total_pages: number;

  // Token metrics
  total_tokens: number;
  total_input_tokens: number;
  total_output_tokens: number;

  // Financial metrics
  estimated_total_cost: number;
  total_credits_purchased: number;
  total_credits_consumed: number;

  // API Token metrics
  total_api_tokens: number;
}

// ============================================================================
// Tenant Types
// ============================================================================

export interface TenantListItem {
  id: string;
  name: string;
  slug: string;
  status: string;
  subscription_plan: string;
  user_count: number;
  document_count: number;
  job_count: number;
  completed_jobs: number;
  failed_jobs: number;
  credit_balance: number;
  total_credits_consumed: number;
  created_at: string;
  last_activity: string | null;
}

export interface TenantListResponse {
  tenants: TenantListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface TenantSubscriptionInfo {
  plan: string;
  status: string;
  stripe_subscription_id: string | null;
  stripe_customer_id: string | null;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  features: Record<string, unknown>;
}

export interface TenantMetrics {
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  pending_jobs: number;
  total_documents: number;
  total_pages: number;
  total_tokens: number;
  total_input_tokens: number;
  total_output_tokens: number;
  estimated_cost: number;
  credit_balance: number;
  credits_consumed: number;
}

export interface TenantDetailResponse {
  tenant: TenantListItem;
  subscription: TenantSubscriptionInfo | null;
  metrics: TenantMetrics;
  user_count: number;
  api_token_count: number;
}

// ============================================================================
// User Types
// ============================================================================

export interface UserListItem {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  tenant_id: string;
  tenant_name: string;
  tenant_status: string;
  role_id: string;
  role_name: string;
  role_display_name: string;
  last_login: string | null;
  created_at: string;
  api_token_count: number;
}

export interface UserListResponse {
  users: UserListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UserDetailResponse {
  user: UserListItem;
  permissions: string[];
  recent_activity: Record<string, unknown>;
}

// ============================================================================
// API Token Types
// ============================================================================

export interface ApiTokenListItem {
  id: string;
  name: string;
  token_prefix: string;
  scopes: string[];
  is_active: boolean;
  expires_at: string | null;
  last_used_at: string | null;
  last_used_ip: string | null;
  created_at: string;
  user_id: string;
  user_email: string;
  tenant_id: string;
  tenant_name: string;
}

export interface ApiTokenListResponse {
  tokens: ApiTokenListItem[];
  total: number;
}

// ============================================================================
// Audit Log Types
// ============================================================================

export interface AuditLogEntry {
  id: string;
  user_id: string;
  user_email: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  endpoint: string;
  method: string;
  ip_address: string | null;
  user_agent: string | null;
  status_code: number | null;
  error_message: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface AuditLogListResponse {
  logs: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ============================================================================
// Admin Action Types (Request Bodies)
// ============================================================================

export interface UpdateTenantStatusRequest {
  status: string;
  reason?: string;
}

export interface UpdateUserStatusRequest {
  is_active: boolean;
  reason?: string;
}

export interface RevokeApiTokenRequest {
  reason?: string;
}

export interface AddTenantCreditsRequest {
  amount: number;
  reason: string;
}

// ============================================================================
// Platform Settings Types
// ============================================================================

export interface PlatformSetting {
  key: string;
  value: unknown;
  description: string | null;
  category: string;
  created_at: string;
  updated_at: string;
}

export interface PlatformSettingsListResponse {
  settings: PlatformSetting[];
  total: number;
}

export interface UpdatePlatformSettingRequest {
  value: unknown;
  description?: string;
}

// ============================================================================
// Analytics Types
// ============================================================================

export interface TopTenantItem {
  id: string;
  name: string;
  slug: string;
  subscription_plan: string;
  job_count: number;
  total_tokens: number;
  estimated_cost: number;
  user_count: number;
  created_at: string;
  last_activity: string | null;
}

export interface TopTenantsResponse {
  tenants: TopTenantItem[];
  period_days: number;
}

// ============================================================================
// Generic Response Types
// ============================================================================

export interface SuccessResponse {
  success: boolean;
  message: string;
  data?: Record<string, unknown>;
}

export interface ErrorResponse {
  success: boolean;
  error: string;
  detail?: string;
}

// ============================================================================
// Filter/Pagination Types
// ============================================================================

export interface TenantFilters {
  page?: number;
  page_size?: number;
  status?: string;
  plan?: string;
  search?: string;
}

export interface UserFilters {
  page?: number;
  page_size?: number;
  tenant_id?: string;
  role_id?: string;
  is_active?: boolean;
  search?: string;
}
