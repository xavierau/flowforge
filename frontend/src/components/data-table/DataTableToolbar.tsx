import { Cross2Icon } from '@radix-ui/react-icons';
import type { Table } from '@tanstack/react-table';
import { Download, Search } from 'lucide-react';
import Papa from 'papaparse';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DataTableViewOptions } from './DataTableViewOptions';
import { DataTableFacetedFilter } from './DataTableFacetedFilter';
import type { FilterConfig } from '@/types/data-table';

interface DataTableToolbarProps<TData> {
  table: Table<TData>;
  searchPlaceholder?: string;
  filterableColumns?: FilterConfig[];
  exportFilename?: string;
  exportableColumns?: string[];
}

export function DataTableToolbar<TData>({
  table,
  searchPlaceholder = 'Search...',
  filterableColumns = [],
  exportFilename = 'export',
  exportableColumns = [],
}: DataTableToolbarProps<TData>) {
  const isFiltered = table.getState().columnFilters.length > 0;

  const handleExport = () => {
    const rows = table.getFilteredRowModel().rows;
    const data = rows.map((row) => {
      const rowData: any = {};

      // If exportableColumns is specified, only include those columns
      if (exportableColumns.length > 0) {
        exportableColumns.forEach((columnId) => {
          rowData[columnId] = row.getValue(columnId);
        });
      } else {
        // Otherwise, include all visible columns
        table
          .getVisibleFlatColumns()
          .filter((column) => column.id !== 'select' && column.id !== 'actions')
          .forEach((column) => {
            rowData[column.id] = row.getValue(column.id);
          });
      }

      return rowData;
    });

    const csv = Papa.unparse(data);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `${exportFilename}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex flex-1 items-center space-x-2">
        <div className="relative w-full max-w-sm">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={searchPlaceholder}
            value={(table.getState().globalFilter as string) ?? ''}
            onChange={(event) => table.setGlobalFilter(event.target.value)}
            className="pl-8 h-9"
          />
        </div>
        {filterableColumns.map((filterColumn) => {
          const column = table.getColumn(filterColumn.id);
          return column ? (
            <DataTableFacetedFilter
              key={filterColumn.id}
              column={column}
              title={filterColumn.title}
              options={filterColumn.options}
            />
          ) : null;
        })}
        {isFiltered && (
          <Button
            variant="ghost"
            onClick={() => table.resetColumnFilters()}
            className="h-8 px-2 lg:px-3"
          >
            Reset
            <Cross2Icon className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>
      <div className="flex items-center space-x-2">
        <Button
          variant="outline"
          size="sm"
          className="h-8"
          onClick={handleExport}
        >
          <Download className="mr-2 h-4 w-4" />
          Export CSV
        </Button>
        <DataTableViewOptions table={table} />
      </div>
    </div>
  );
}
