/**
 * Profile and Settings Type Definitions
 *
 * Defines data structures for user profiles, invitations, subscriptions,
 * and account settings following SOLID principles.
 */

/**
 * Role Information
 * Matches backend RoleInfo schema
 */
export interface RoleInfo {
  id: string;
  name: string;
  display_name: string;
}

/**
 * Tenant Information
 * Matches backend TenantInfo schema
 */
export interface TenantInfo {
  id: string;
  name: string;
  subscription_plan: string;
}

/**
 * Extended User Profile
 * Matches backend UserDetailResponse schema
 */
export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string;
  is_active: boolean;
  is_verified: boolean;
  locale?: string;
  last_login?: string;
  created_at: string;
  role: RoleInfo;
  tenant: TenantInfo;
  permissions: string[];
}

/**
 * User Role Enum (for backwards compatibility and filters)
 */
export type UserRole = 'admin' | 'user' | 'viewer';

/**
 * User Invitation
 */
export interface UserInvitation {
  id: string;
  email: string;
  role: UserRole;
  invited_by: string;
  invited_by_name?: string;
  created_at: string;
  expires_at: string;
  status: InvitationStatus;
}

/**
 * Invitation Status
 */
export type InvitationStatus = 'pending' | 'accepted' | 'expired' | 'cancelled';

/**
 * Create Invitation Request
 */
export interface CreateInvitationRequest {
  email: string;
  role: UserRole;
}

/**
 * Subscription Plan
 */
export type SubscriptionPlan = 'free' | 'pro' | 'enterprise';

/**
 * Subscription Details
 */
export interface Subscription {
  id?: string;
  tenant_id?: string;
  plan: SubscriptionPlan;
  status: SubscriptionStatus;
  credits_balance: number;
  credits_used: number;
  balance_last_updated: string;
  documents_processed?: number;
  api_calls_count?: number;
  billing_cycle_start?: string;
  billing_cycle_end?: string;
  billing_period_start?: string;
  billing_period_end?: string;
  created_at?: string;
  updated_at?: string;
  cancel_at_period_end?: boolean;
  features?: Record<string, unknown>;
}

/**
 * Subscription Status
 */
export type SubscriptionStatus = 'active' | 'cancelled' | 'expired' | 'suspended';

/**
 * Plan Features
 */
export interface PlanFeatures {
  plan: SubscriptionPlan;
  name: string;
  price: number;
  billing_period: 'monthly' | 'yearly';
  features: string[];
  credits_per_month: number;
  max_documents_per_month: number;
  max_api_calls_per_month: number;
  support_level: string;
}

/**
 * Usage Statistics
 */
export interface UsageStatistics {
  documents_processed: number;
  api_calls_count: number;
  credits_used: number;
  credits_remaining: number;
  period_start: string;
  period_end: string;
}

/**
 * Account Settings Update Request
 */
export interface UpdateAccountRequest {
  full_name?: string;
  email?: string;
}

/**
 * Password Change Request
 */
export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

/**
 * Notification Preferences
 */
export interface NotificationPreferences {
  email_on_job_complete: boolean;
  email_on_job_failed: boolean;
  email_on_low_credits: boolean;
  email_on_subscription_changes: boolean;
  email_marketing: boolean;
}
