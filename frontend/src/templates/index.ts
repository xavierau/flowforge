import { invoiceTemplate } from './invoice';
import { resumeTemplate } from './resume';
import { receiptTemplate } from './receipt';
import { bankStatementTemplate } from './bank-statement';
import { passportTemplate } from './passport';
import { idCardTemplate } from './id-card';
import type { Template } from '@/types/template';

export const templates: Template[] = [
  invoiceTemplate,
  receiptTemplate,
  bankStatementTemplate,
  resumeTemplate,
  passportTemplate,
  idCardTemplate,
];

export function getTemplate(id: string): Template | undefined {
  return templates.find(t => t.id === id);
}

export function getTemplatesByCategory(category: string): Template[] {
  return templates.filter(t => t.category === category);
}
