/**
 * Backend API Schema Definition Types
 * Corresponds to app/schemas/schema_definition.py
 */

export interface ApiSchema {
  id: string;
  name: string;
  definitions: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CreateApiSchemaRequest {
  name: string;
  definitions: Record<string, any>;
}

export interface UpdateApiSchemaRequest {
  definitions: Record<string, any>;
}

export interface ApiSchemaListResponse {
  schemas: ApiSchema[];
  total: number;
  limit: number;
  offset: number;
}
