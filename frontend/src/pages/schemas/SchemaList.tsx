import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, Pencil, Trash2, Plus } from 'lucide-react';
import { toast } from 'sonner';

import { Page, PageHeader, PageContent } from '@/components/layout';
import {
  DataTable,
  createSelectColumn,
  createSortableColumn,
  createDateColumn,
  createActionsColumn,
} from '@/components/data-table';
import { Button } from '@/components/ui/button';
import type { ApiSchema } from '@/types/api-schema';
import { listSchemas, deleteSchema } from '@/lib/api';

export function SchemaList() {
  const navigate = useNavigate();
  const [schemas, setSchemas] = useState<ApiSchema[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch schemas on mount
  useEffect(() => {
    loadSchemas();
  }, []);

  const loadSchemas = async () => {
    try {
      setIsLoading(true);
      const response = await listSchemas({ limit: 100, offset: 0 });
      setSchemas(response.schemas);
    } catch (error) {
      toast.error('Failed to load schemas', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (schemaId: string) => {
    if (!confirm('Are you sure you want to delete this schema?')) {
      return;
    }

    try {
      await deleteSchema(schemaId);
      toast.success('Schema deleted successfully');
      // Reload schemas
      await loadSchemas();
    } catch (error) {
      toast.error('Failed to delete schema', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  // Define columns
  const columns = [
    createSelectColumn<ApiSchema>(),
    createSortableColumn<ApiSchema>('name', 'Schema Name'),
    createDateColumn<ApiSchema>('created_at', 'Created', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }),
    createDateColumn<ApiSchema>('updated_at', 'Updated', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }),
    createActionsColumn<ApiSchema>([
      {
        label: 'View',
        icon: Eye,
        onClick: (schema) => navigate(`/schemas/${schema.id}`),
      },
      {
        label: 'Edit',
        icon: Pencil,
        onClick: (schema) => navigate(`/schema-builder?schemaId=${schema.id}`),
      },
      {
        label: 'Delete',
        icon: Trash2,
        onClick: (schema) => handleDelete(schema.id),
        variant: 'destructive',
      },
    ]),
  ];

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Schemas' },
        ]}
        title="Schemas"
        subtitle="Manage your extraction schemas"
      />
      <PageContent>
        <div className="flex justify-end mb-4">
          <Button onClick={() => navigate('/schema-builder')}>
            <Plus className="mr-2 h-4 w-4" />
            Create Schema
          </Button>
        </div>

        <DataTable
          columns={columns}
          data={schemas}
          searchPlaceholder="Search schemas..."
          searchableColumns={['name']}
          exportFilename="schemas"
          exportableColumns={['name', 'created_at', 'updated_at']}
          isLoading={isLoading}
          emptyMessage="No schemas found. Create your first schema to get started."
        />
      </PageContent>
    </Page>
  );
}
