import type { ColumnDef } from '@tanstack/react-table';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { DataTableColumnHeader } from './DataTableColumnHeader';
import { DataTableRowActions } from './DataTableRowActions';
import type { RowAction } from '@/types/data-table';

/**
 * Creates a selection checkbox column
 */
export function createSelectColumn<TData>(): ColumnDef<TData> {
  return {
    id: 'select',
    header: ({ table }) => (
      <Checkbox
        checked={table.getIsAllPageRowsSelected()}
        onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
        aria-label="Select all"
        className="translate-y-[2px]"
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(value) => row.toggleSelected(!!value)}
        aria-label="Select row"
        className="translate-y-[2px]"
      />
    ),
    enableSorting: false,
    enableHiding: false,
  };
}

/**
 * Creates a sortable text column
 */
export function createSortableColumn<TData>(
  accessorKey: string,
  title: string,
  cell?: (data: any) => React.ReactNode
): ColumnDef<TData> {
  return {
    accessorKey,
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title={title} />
    ),
    cell: cell
      ? ({ row }) => cell(row.getValue(accessorKey))
      : ({ row }) => <div>{row.getValue(accessorKey)}</div>,
    enableSorting: true,
    enableHiding: true,
  };
}

/**
 * Creates a badge column (useful for status)
 */
export function createBadgeColumn<TData>(
  accessorKey: string,
  title: string,
  variantMap?: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'>
): ColumnDef<TData> {
  return {
    accessorKey,
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title={title} />
    ),
    cell: ({ row }) => {
      const value = row.getValue(accessorKey) as string;
      const variant = variantMap?.[value] || 'default';

      return (
        <Badge variant={variant} className="capitalize">
          {value}
        </Badge>
      );
    },
    filterFn: (row, id, value) => {
      return value.includes(row.getValue(id));
    },
    enableSorting: true,
    enableHiding: true,
  };
}

/**
 * Creates a formatted date column
 */
export function createDateColumn<TData>(
  accessorKey: string,
  title: string,
  formatOptions?: Intl.DateTimeFormatOptions
): ColumnDef<TData> {
  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  };

  return {
    accessorKey,
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title={title} />
    ),
    cell: ({ row }) => {
      const date = row.getValue(accessorKey);
      if (!date) return <div className="text-muted-foreground">-</div>;

      const formattedDate = new Date(date as string).toLocaleDateString(
        'en-US',
        formatOptions || defaultOptions
      );

      return <div className="text-sm">{formattedDate}</div>;
    },
    enableSorting: true,
    enableHiding: true,
  };
}

/**
 * Creates an actions column with row-specific actions
 */
export function createActionsColumn<TData>(
  actions: RowAction<TData>[]
): ColumnDef<TData> {
  return {
    id: 'actions',
    cell: ({ row }) => <DataTableRowActions row={row} actions={actions} />,
    enableSorting: false,
    enableHiding: false,
  };
}

/**
 * Creates a custom column with full control
 */
export function createCustomColumn<TData>(
  config: Partial<ColumnDef<TData>>
): ColumnDef<TData> {
  return {
    enableSorting: true,
    enableHiding: true,
    ...config,
  } as ColumnDef<TData>;
}
