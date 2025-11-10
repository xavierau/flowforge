/**
 * Page Component
 *
 * Top-level page wrapper that composes PageHeader and PageContent.
 * Provides consistent layout, padding, and spacing for all pages.
 *
 * Design Principles:
 * - Composition: Composes PageHeader and PageContent components
 * - Single Responsibility: Manages page-level layout structure
 * - Flexibility: Children can include header and content
 * - Consistent spacing: Standard padding and gaps
 * - Clean API: Simple, predictable interface
 *
 * Usage Pattern:
 * This component expects children to be PageHeader and PageContent components.
 * It provides the outer container and consistent spacing between sections.
 */

import { cn } from '@/lib/utils';

interface PageProps {
  /**
   * Page content (typically PageHeader + PageContent components)
   */
  children: React.ReactNode;

  /**
   * Optional className for custom styling
   */
  className?: string;
}

/**
 * Page Component
 *
 * Top-level wrapper for page content. Composes PageHeader and PageContent
 * with consistent layout and spacing.
 *
 * @example
 * ```tsx
 * <Page>
 *   <PageHeader
 *     breadcrumbs={[
 *       { label: 'Home', href: '/dashboard' },
 *       { label: 'Current Page' }
 *     ]}
 *     title="Page Title"
 *     subtitle="Page description"
 *   />
 *   <PageContent>
 *     <div>Your content here</div>
 *   </PageContent>
 * </Page>
 * ```
 */
export function Page({ children, className }: PageProps) {
  return (
    <div className={cn('p-6 space-y-6', className)}>
      {children}
    </div>
  );
}
