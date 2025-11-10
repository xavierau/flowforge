/**
 * PageHeader Component
 *
 * Renders page header with breadcrumb navigation, title, and optional subtitle.
 * Provides consistent header structure across all pages.
 *
 * Design Principles:
 * - Single Responsibility: Only renders page header content
 * - Composition: Composes Breadcrumb component
 * - Flexibility: Optional subtitle and breadcrumbs
 * - Accessibility: Semantic HTML structure
 * - Clean separation: Header content only, no layout concerns
 */

import { Breadcrumb, type BreadcrumbItem } from './Breadcrumb';

interface PageHeaderProps {
  /**
   * Page title (renders as h1)
   */
  title: string;

  /**
   * Optional subtitle or description
   */
  subtitle?: string;

  /**
   * Optional breadcrumb navigation items
   * If omitted, no breadcrumb is rendered
   */
  breadcrumbs?: BreadcrumbItem[];

  /**
   * Optional className for custom styling
   */
  className?: string;
}

/**
 * PageHeader Component
 *
 * Renders a page header with breadcrumb navigation, title, and optional subtitle.
 * Provides consistent structure and spacing across all pages.
 *
 * @example
 * ```tsx
 * <PageHeader
 *   breadcrumbs={[
 *     { label: 'Home', href: '/dashboard' },
 *     { label: 'Schema Builder' }
 *   ]}
 *   title="Schema Builder"
 *   subtitle="Create and manage your JSON schemas"
 * />
 * ```
 */
export function PageHeader({
  title,
  subtitle,
  breadcrumbs,
  className,
}: PageHeaderProps) {
  return (
    <header className={className}>
      {/* Breadcrumb Navigation */}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <Breadcrumb items={breadcrumbs} className="mb-3" />
      )}

      {/* Title */}
      <h1 className="text-3xl font-bold tracking-tight text-foreground">
        {title}
      </h1>

      {/* Subtitle */}
      {subtitle && (
        <p className="mt-2 text-base text-muted-foreground">
          {subtitle}
        </p>
      )}
    </header>
  );
}
