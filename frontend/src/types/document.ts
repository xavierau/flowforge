/**
 * Document Types
 * Corresponds to app/models/document.py
 */

import type { MarkdownConverter } from './enums';

/**
 * Document page with optional markdown content
 */
export interface DocumentPage {
  id: string;
  document_id: string;
  page_number: number;
  image_path: string;
  preprocessed_image_path?: string;
  markdown_content?: string;
  markdown_provider?: MarkdownConverter;
  markdown_generated_at?: string;
  status: string;
  created_at: string;
}

/**
 * Document with pages
 */
export interface Document {
  id: string;
  tenant_id: string;
  filename: string;
  file_path: string;
  file_type: string;
  file_size: number;
  page_count: number;
  status: string;
  created_at: string;
  updated_at: string;
  pages?: DocumentPage[];
}
