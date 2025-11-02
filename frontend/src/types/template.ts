/**
 * Template type definitions
 */

export interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  schema: any; // The actual JSON Schema object
  icon?: string; // Optional Lucide icon name
}

export type TemplateCategory = 'Financial' | 'HR' | 'Legal' | 'Custom';
