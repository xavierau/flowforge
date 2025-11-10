import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Pencil, Trash2, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';

import { Page, PageHeader, PageContent } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { SchemaJsonViewer } from '@/components/preview/SchemaJsonViewer';
import type { ApiSchema } from '@/types/api-schema';
import { getSchema, deleteSchema } from '@/lib/api';

export function SchemaDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [schema, setSchema] = useState<ApiSchema | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (id) {
      loadSchema(id);
    }
  }, [id]);

  const loadSchema = async (schemaId: string) => {
    try {
      setIsLoading(true);
      const data = await getSchema(schemaId);
      setSchema(data);
    } catch (error) {
      toast.error('Failed to load schema', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
      navigate('/schemas');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!schema || !confirm('Are you sure you want to delete this schema?')) {
      return;
    }

    try {
      await deleteSchema(schema.id);
      toast.success('Schema deleted successfully');
      navigate('/schemas');
    } catch (error) {
      toast.error('Failed to delete schema', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  if (isLoading) {
    return (
      <Page>
        <PageContent>
          <div className="flex items-center justify-center h-64">
            <p className="text-muted-foreground">Loading schema...</p>
          </div>
        </PageContent>
      </Page>
    );
  }

  if (!schema) {
    return null;
  }

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Schemas', href: '/schemas' },
          { label: schema.name },
        ]}
        title={schema.name}
        subtitle="Schema details and definition"
      />
      <PageContent>
        <div className="flex gap-2 mb-6">
          <Button variant="outline" onClick={() => navigate('/schemas')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Schemas
          </Button>
          <Button onClick={() => navigate(`/schema-builder?schemaId=${schema.id}`)}>
            <Pencil className="mr-2 h-4 w-4" />
            Edit Schema
          </Button>
          <Button variant="destructive" onClick={handleDelete}>
            <Trash2 className="mr-2 h-4 w-4" />
            Delete Schema
          </Button>
        </div>

        <div className="grid gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Schema Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="text-sm font-medium text-muted-foreground">Name</div>
                <div className="text-base font-semibold">{schema.name}</div>
              </div>
              <div>
                <div className="text-sm font-medium text-muted-foreground">Created</div>
                <div className="text-base">
                  {new Date(schema.created_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              </div>
              <div>
                <div className="text-sm font-medium text-muted-foreground">Last Updated</div>
                <div className="text-base">
                  {new Date(schema.updated_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              </div>
            </CardContent>
          </Card>

          <div>
            <h3 className="text-lg font-semibold mb-4">Schema Definition</h3>
            <SchemaJsonViewer
              schema={schema.definitions}
              showTabs={false}
              collapsedLevel={2}
            />
          </div>
        </div>
      </PageContent>
    </Page>
  );
}
