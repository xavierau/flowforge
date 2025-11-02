import { invoiceTemplate } from './invoice';
import { resumeTemplate } from './resume';
import type { Template } from '@/types/template';

export const templates: Template[] = [
  invoiceTemplate,
  resumeTemplate,
];

export function getTemplate(id: string): Template | undefined {
  return templates.find(t => t.id === id);
}

export function getTemplatesByCategory(category: string): Template[] {
  return templates.filter(t => t.category === category);
}
