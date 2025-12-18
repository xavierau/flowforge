/**
 * Frontend Configuration
 * Centralized configuration from environment variables
 */

/**
 * Schema Builder Configuration
 */
export const SCHEMA_CONFIG = {
  /**
   * Maximum nesting depth for schema properties
   * Controls how deep nested objects/arrays can go
   * Default: 3 (levels 0, 1, 2, 3)
   */
  MAX_NESTING_LEVEL: parseInt(import.meta.env.VITE_MAX_NESTING_LEVEL || '3', 10),
} as const;

/**
 * API Configuration
 */
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL || '',
} as const;
