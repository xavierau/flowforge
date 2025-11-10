import type { ColumnDef } from '@tanstack/react-table';

/**
 * Configuration for filterable columns
 */
export interface FilterConfig {
  id: string;
  title: string;
  options: FilterOption[];
}

export interface FilterOption {
  label: string;
  value: string;
  icon?: React.ComponentType<{ className?: string }>;
}

/**
 * Row action configuration
 */
export interface RowAction<TData> {
  label: string;
  icon?: React.ComponentType<{ className?: string }>;
  onClick: (row: TData) => void;
  show?: (row: TData) => boolean;
  variant?: 'default' | 'destructive';
}

/**
 * Bulk action configuration
 */
export interface BulkAction<TData> {
  label: string;
  icon?: React.ComponentType<{ className?: string }>;
  onClick: (rows: TData[]) => void;
  variant?: 'default' | 'destructive';
}

/**
 * DataTable component props
 */
export interface DataTableProps<TData> {
  columns: ColumnDef<TData, any>[];
  data: TData[];

  // Pagination
  pageSize?: number;
  pageSizeOptions?: number[];

  // Search & Filtering
  searchPlaceholder?: string;
  searchableColumns?: string[];
  filterableColumns?: FilterConfig[];

  // Actions
  rowActions?: RowAction<TData>[];
  bulkActions?: BulkAction<TData>[];

  // Export
  exportFilename?: string;
  exportableColumns?: string[];

  // Loading & Empty States
  isLoading?: boolean;
  emptyMessage?: string;

  // Customization
  className?: string;
}

/**
 * Column header with sorting props
 */
export interface DataTableColumnHeaderProps<TData, TValue> {
  column: import('@tanstack/react-table').Column<TData, TValue>;
  title: string;
}

/**
 * Faceted filter props
 */
export interface DataTableFacetedFilterProps<TData, TValue> {
  column?: import('@tanstack/react-table').Column<TData, TValue>;
  title?: string;
  options: FilterOption[];
}

/**
 * Toolbar props
 */
export interface DataTableToolbarProps<TData> {
  table: import('@tanstack/react-table').Table<TData>;
  searchPlaceholder?: string;
  filterableColumns?: FilterConfig[];
  exportFilename?: string;
  exportableColumns?: string[];
}

/**
 * Pagination props
 */
export interface DataTablePaginationProps<TData> {
  table: import('@tanstack/react-table').Table<TData>;
  pageSizeOptions?: number[];
}

/**
 * Row actions props
 */
export interface DataTableRowActionsProps<TData> {
  row: import('@tanstack/react-table').Row<TData>;
  actions: RowAction<TData>[];
}

/**
 * View options (column visibility) props
 */
export interface DataTableViewOptionsProps<TData> {
  table: import('@tanstack/react-table').Table<TData>;
}
