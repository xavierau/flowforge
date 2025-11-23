import type { Row } from '@tanstack/react-table';
import { MoreHorizontal } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { RowAction } from '@/types/data-table';

interface DataTableRowActionsProps<TData> {
  row: Row<TData>;
  actions: RowAction<TData>[];
}

export function DataTableRowActions<TData>({
  row,
  actions,
}: DataTableRowActionsProps<TData>) {
  const rowData = row.original;

  // Filter actions based on show condition
  const visibleActions = actions.filter((action) =>
    action.show ? action.show(rowData) : true
  );

  if (visibleActions.length === 0) {
    return null;
  }

  // Group actions by variant
  const defaultActions = visibleActions.filter(
    (action) => action.variant !== 'destructive'
  );
  const destructiveActions = visibleActions.filter(
    (action) => action.variant === 'destructive'
  );

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="flex h-8 w-8 p-0 data-[state=open]:bg-muted"
        >
          <MoreHorizontal className="h-4 w-4" />
          <span className="sr-only">Open menu</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[160px]">
        {defaultActions.map((action, index) => {
          const isDisabled = action.disabled ? action.disabled(rowData) : false;
          const label = typeof action.label === 'function' ? action.label(rowData) : action.label;

          return (
            <DropdownMenuItem
              key={index}
              onClick={() => !isDisabled && action.onClick(rowData)}
              disabled={isDisabled}
            >
              {action.icon && <action.icon className="mr-2 h-4 w-4" />}
              {label}
            </DropdownMenuItem>
          );
        })}
        {defaultActions.length > 0 && destructiveActions.length > 0 && (
          <DropdownMenuSeparator />
        )}
        {destructiveActions.map((action, index) => {
          const isDisabled = action.disabled ? action.disabled(rowData) : false;
          const label = typeof action.label === 'function' ? action.label(rowData) : action.label;

          return (
            <DropdownMenuItem
              key={index}
              onClick={() => !isDisabled && action.onClick(rowData)}
              disabled={isDisabled}
              className="text-destructive focus:text-destructive"
            >
              {action.icon && <action.icon className="mr-2 h-4 w-4" />}
              {label}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
