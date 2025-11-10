/**
 * Breadcrumb Navigation Component
 *
 * Renders breadcrumb navigation trail with proper accessibility.
 * Uses shadcn/ui Breadcrumb components for consistent styling.
 *
 * Design Principles:
 * - Single Responsibility: Only renders breadcrumb navigation
 * - Accessibility: Proper ARIA labels and semantic HTML
 * - Composability: Uses shadcn/ui primitives
 * - Type Safety: Full TypeScript support
 *
 * Features:
 * - Automatic handling of links vs current page
 * - Integration with React Router
 * - Accessible navigation landmarks
 */

import { Link } from 'react-router-dom';
import {
  Breadcrumb as BreadcrumbRoot,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';

export interface BreadcrumbItem {
  /**
   * Display label for the breadcrumb item
   */
  label: string;

  /**
   * Optional href for navigation
   * If omitted, renders as current page (not clickable)
   */
  href?: string;
}

interface BreadcrumbProps {
  /**
   * Array of breadcrumb items to display
   * Last item is automatically treated as current page if no href provided
   */
  items: BreadcrumbItem[];

  /**
   * Optional className for custom styling
   */
  className?: string;
}

/**
 * Breadcrumb Navigation Component
 *
 * Renders a breadcrumb trail with proper semantics and accessibility.
 * Integrates with React Router for client-side navigation.
 *
 * @example
 * ```tsx
 * <Breadcrumb
 *   items={[
 *     { label: 'Home', href: '/dashboard' },
 *     { label: 'Settings', href: '/settings' },
 *     { label: 'Profile' }
 *   ]}
 * />
 * ```
 */
export function Breadcrumb({ items, className }: BreadcrumbProps) {
  // Don't render anything if no items provided
  if (!items || items.length === 0) {
    return null;
  }

  return (
    <BreadcrumbRoot className={className}>
      <BreadcrumbList>
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          const isClickable = Boolean(item.href);

          return (
            <div key={`${item.label}-${index}`} className="flex items-center gap-1.5">
              <BreadcrumbItem>
                {isClickable ? (
                  <BreadcrumbLink asChild>
                    <Link to={item.href!}>{item.label}</Link>
                  </BreadcrumbLink>
                ) : (
                  <BreadcrumbPage>{item.label}</BreadcrumbPage>
                )}
              </BreadcrumbItem>

              {/* Don't render separator after last item */}
              {!isLast && <BreadcrumbSeparator />}
            </div>
          );
        })}
      </BreadcrumbList>
    </BreadcrumbRoot>
  );
}
