/**
 * Model Service
 *
 * Provides methods for fetching available models for extraction, LLM, and markdown.
 * Following SOLID principles:
 * - Single Responsibility: Handles only model-related API calls
 * - Open/Closed: Easy to extend with new model operations
 * - Interface Segregation: Focused interface for model operations
 *
 * Uses centralized API client from lib/api-client.ts for:
 * - Automatic token refresh on 401 responses
 * - Auth header injection
 * - Consistent error handling
 */

import { apiFetch, API_BASE_URL, handleApiResponse } from '@/lib/api-client';

/**
 * Model available for use in extraction, LLM, or markdown conversion.
 */
export interface AvailableModel {
  id: string;
  provider: string;
  modelName: string;
  displayName: string;
  supportsVision: boolean;
  supportsMarkdownConversion: boolean;
  supportsJsonMode: boolean;
  inputPricePerMillion: number;
  outputPricePerMillion: number;
  isDefaultExtraction: boolean;
  isDefaultMarkdown: boolean;
  isDefaultLlm: boolean;
}

/**
 * Default models for each use case.
 */
export interface DefaultModels {
  extraction: AvailableModel | null;
  markdown: AvailableModel | null;
  llm: AvailableModel | null;
}

/**
 * Response from the available models endpoint.
 */
export interface AvailableModelsResponse {
  models: AvailableModel[];
  defaults: DefaultModels;
  providers: string[];
}

/**
 * Use case types for filtering models.
 */
export type ModelUseCase = 'extraction' | 'llm' | 'markdown';

/**
 * Convert snake_case API response to camelCase.
 */
function transformModel(apiModel: Record<string, unknown>): AvailableModel {
  return {
    id: apiModel.id as string,
    provider: apiModel.provider as string,
    modelName: apiModel.model_name as string,
    displayName: apiModel.display_name as string,
    supportsVision: apiModel.supports_vision as boolean,
    supportsMarkdownConversion: apiModel.supports_markdown_conversion as boolean,
    supportsJsonMode: apiModel.supports_json_mode as boolean,
    inputPricePerMillion: apiModel.input_price_per_million as number,
    outputPricePerMillion: apiModel.output_price_per_million as number,
    isDefaultExtraction: apiModel.is_default_extraction as boolean,
    isDefaultMarkdown: apiModel.is_default_markdown as boolean,
    isDefaultLlm: apiModel.is_default_llm as boolean,
  };
}

/**
 * API response structure (snake_case from backend).
 */
interface ApiAvailableModelsResponse {
  models: Record<string, unknown>[];
  defaults: {
    extraction: Record<string, unknown> | null;
    markdown: Record<string, unknown> | null;
    llm: Record<string, unknown> | null;
  };
  providers: string[];
}

/**
 * Get available models for a specific use case.
 *
 * @param useCase - Optional filter: 'extraction', 'llm', or 'markdown'
 * @param provider - Optional filter by provider name
 * @returns Promise resolving to AvailableModelsResponse
 */
export async function getAvailableModels(
  useCase?: ModelUseCase,
  provider?: string
): Promise<AvailableModelsResponse> {
  const params = new URLSearchParams();

  if (useCase) {
    params.set('use_case', useCase);
  }
  if (provider) {
    params.set('provider', provider);
  }

  const queryString = params.toString();
  const url = queryString
    ? `${API_BASE_URL}/models/available?${queryString}`
    : `${API_BASE_URL}/models/available`;

  const response = await apiFetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  const data = await handleApiResponse<ApiAvailableModelsResponse>(response);

  return {
    models: data.models.map(transformModel),
    defaults: {
      extraction: data.defaults.extraction
        ? transformModel(data.defaults.extraction)
        : null,
      markdown: data.defaults.markdown
        ? transformModel(data.defaults.markdown)
        : null,
      llm: data.defaults.llm ? transformModel(data.defaults.llm) : null,
    },
    providers: data.providers,
  };
}

/**
 * Get list of available providers with active models.
 *
 * @returns Promise resolving to array of provider names
 */
export async function getAvailableProviders(): Promise<string[]> {
  const response = await apiFetch(`${API_BASE_URL}/models/providers`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  const data = await handleApiResponse<{ providers: string[] }>(response);
  return data.providers;
}
