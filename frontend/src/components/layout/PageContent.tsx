/**
 * PageContent Component
 *
 * Container for main page content with consistent padding, layout, and visual elevation.
 * Provides semantic structure, consistent spacing, and card-style background.
 *
 * Design Principles:
 * - Single Responsibility: Only manages content container
 * - Semantic HTML: Uses <section> for content sections
 * - Consistent spacing: Standard padding across all pages
 * - Visual hierarchy: Elevated with shadow, border, and background
 * - Flexibility: Accepts any children
 */

import { cn } from '@/lib/utils';

interface PageContentProps {
  /**
   * Page content to render
   */
  children: React.ReactNode;

  /**
   * Optional className for custom styling
   */
  className?: string;

  /**
   * Optional ARIA label for accessibility
   */
  'aria-label'?: string;
}

/**
 * PageContent Component
 *
 * Wraps page content with consistent padding and semantic structure.
 * Use this for the main content area below the PageHeader.
 *
 * @example
 * ```tsx
 * <PageContent>
 *   <div>Your page content here</div>
 * </PageContent>
 * ```
 */
export function PageContent({
  children,
  className,
  'aria-label': ariaLabel,
}: PageContentProps) {
  return (
    <section
      className={cn(
        'space-y-6 rounded-lg border bg-white p-6 shadow-sm overflow-hidden min-w-0',
        className
      )}
      aria-label={ariaLabel || 'Page content'}
    >
      {children}
    </section>
  );
}
