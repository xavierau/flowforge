import { useState, useCallback, useEffect } from 'react';
import { FileJson, Download, Save, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { JsonPreview } from '@/components/preview/JsonPreview';
import { SchemaTree } from '@/components/schema-builder/SchemaTree';
import { TemplateSelector } from '@/components/templates/TemplateSelector';
import { Page, PageHeader } from '@/components/layout';
import { toast } from 'sonner';
import { useSchemaStore } from '@/store/schemaStore';
import { propertiesToJsonSchema, jsonSchemaToProperties } from '@/lib/schema-converter';
import { submitSchema, validateSchemaName, SchemaApiError, getSchema, updateSchema, ApiServiceError } from '@/lib/api';
import { useNavigate, useSearchParams } from 'react-router-dom';

export function SchemaBuilder() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const schemaId = searchParams.get('schemaId');
  const { schemaName, properties, setSchemaName, markClean, loadTemplate } = useSchemaStore();
  const [nameError, setNameError] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Load existing schema if schemaId is provided
  useEffect(() => {
    if (schemaId) {
      setIsLoading(true);
      getSchema(schemaId)
        .then((schema) => {
          // Convert API schema format to Properties
          const props = jsonSchemaToProperties(schema.definitions);
          loadTemplate(props, schema.name);
          toast.success('Schema loaded', {
            description: `Loaded schema "${schema.name}" for editing`,
          });
        })
        .catch((error) => {
          if (error instanceof ApiServiceError) {
            if (error.statusCode === 404) {
              toast.error('Schema not found', {
                description: 'The requested schema could not be found',
              });
            } else if (error.statusCode === 401) {
              toast.error('Authentication required', {
                description: 'Please log in to view schemas',
              });
              setTimeout(() => navigate('/login'), 1500);
            } else {
              toast.error('Failed to load schema', {
                description: error.detail || 'An error occurred while loading the schema',
              });
            }
          } else {
            toast.error('Failed to load schema', {
              description: error instanceof Error ? error.message : 'Unknown error',
            });
          }
          // Navigate back to schemas list on error
          setTimeout(() => navigate('/schemas'), 2000);
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  }, [schemaId, loadTemplate, navigate]);

  // Handle schema name change with validation
  const handleNameChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newName = e.target.value;
    setSchemaName(newName);

    // Clear error when user starts typing
    if (nameError) {
      setNameError('');
    }
  }, [setSchemaName, nameError]);

  // Validate name on blur
  const handleNameBlur = useCallback(() => {
    const validation = validateSchemaName(schemaName);
    if (!validation.isValid && validation.error) {
      setNameError(validation.error);
    }
  }, [schemaName]);

  // Handle schema save/submit
  const handleSaveSchema = useCallback(async () => {
    // Validate name first (skip for updates since name is immutable)
    if (!schemaId) {
      const validation = validateSchemaName(schemaName);
      if (!validation.isValid) {
        setNameError(validation.error || 'Invalid schema name');
        toast.error('Cannot save schema', {
          description: validation.error || 'Please fix the schema name',
        });
        return;
      }
    }

    // Validate properties exist
    if (properties.length === 0) {
      toast.error('Cannot save schema', {
        description: 'Please add at least one property to the schema',
      });
      return;
    }

    setIsSaving(true);
    setNameError('');

    try {
      const schema = propertiesToJsonSchema(properties, schemaName);

      if (schemaId) {
        // Update existing schema
        await updateSchema(schemaId, {
          definitions: schema,
        });

        // Success - mark as clean and show toast
        markClean();
        toast.success('Schema updated successfully!', {
          description: `"${schemaName}" has been updated`,
        });
      } else {
        // Create new schema
        const result = await submitSchema({
          name: schemaName.trim(),
          definitions: schema,
        });

        // Success - mark as clean and show toast
        markClean();
        toast.success('Schema created successfully!', {
          description: `"${schemaName}" has been saved to the database`,
        });

        // Navigate to the edit URL with the new schema ID
        navigate(`/schema-builder?schemaId=${result.id}`, { replace: true });
      }
    } catch (error) {
      if (error instanceof SchemaApiError || error instanceof ApiServiceError) {
        // Handle specific API errors
        if (error.statusCode === 401) {
          // Unauthorized - redirect to login
          toast.error('Authentication required', {
            description: 'Please log in to save schemas',
          });
          setTimeout(() => {
            navigate('/login');
          }, 1500);
        } else if (error.statusCode === 409) {
          setNameError('Schema name already exists');
          toast.error('Schema name already exists', {
            description: 'Please choose a different name for your schema',
          });
        } else if (error.statusCode === 400) {
          toast.error('Invalid schema', {
            description: error.detail || 'The schema format is invalid',
          });
        } else if (error.statusCode === 422) {
          toast.error('Validation error', {
            description: error.detail || 'Please check your schema data',
          });
        } else if (error.statusCode === 0) {
          // Network error
          toast.error('Connection failed', {
            description: 'Could not connect to the server. Please ensure the API is running.',
          });
        } else {
          toast.error(`Failed to ${schemaId ? 'update' : 'save'} schema`, {
            description: error.message || 'An unexpected error occurred',
          });
        }
      } else {
        // Unknown error
        toast.error(`Failed to ${schemaId ? 'update' : 'save'} schema`, {
          description: error instanceof Error ? error.message : 'An unexpected error occurred',
        });
      }
    } finally {
      setIsSaving(false);
    }
  }, [schemaName, properties, schemaId, markClean, navigate]);

  const handleExport = () => {
    const schema = propertiesToJsonSchema(properties, schemaName);
    const blob = new Blob([JSON.stringify(schema, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${schemaName.replace(/\s+/g, '_').toLowerCase()}_schema.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Determine if save button should be disabled
  const isSaveDisabled =
    properties.length === 0 ||
    !schemaName.trim() ||
    schemaName.trim().length > 255 ||
    isSaving;

  // Show loading state while fetching schema
  if (isLoading) {
    return (
      <Page className="h-full flex flex-col p-0">
        <div className="px-6 pt-6 pb-4">
          <PageHeader
            breadcrumbs={[
              { label: 'Dashboard', href: '/dashboard' },
              { label: 'Schema Builder' },
            ]}
            title="Schema Builder"
            subtitle="Loading schema..."
          />
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
            <p className="text-muted-foreground">Loading schema data...</p>
          </div>
        </div>
      </Page>
    );
  }

  return (
    <Page className="p-0">
      {/* Page Header with Breadcrumb */}
      <div className="px-6 pt-6 pb-4">
        <PageHeader
          breadcrumbs={[
            { label: 'Dashboard', href: '/dashboard' },
            { label: 'Schemas', href: '/schemas' },
            { label: schemaId ? 'Edit Schema' : 'New Schema' },
          ]}
          title={schemaId ? 'Edit Schema' : 'Schema Builder'}
          subtitle={schemaId ? 'Update your JSON schema definition' : 'Create and manage your JSON schemas'}
        />
      </div>

      {/* Schema Toolbar */}
      <div className="border-y bg-white px-6 py-4 sticky top-0 z-10 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-1 max-w-md">
            <FileJson className="h-6 w-6 text-primary flex-shrink-0" />
            <div className="flex-1">
              <div className="flex flex-col gap-1">
                <Input
                  type="text"
                  value={schemaName}
                  onChange={handleNameChange}
                  onBlur={handleNameBlur}
                  placeholder="Enter schema name"
                  maxLength={255}
                  disabled={!!schemaId}
                  className={nameError ? 'border-destructive focus-visible:ring-destructive' : ''}
                  aria-label="Schema name"
                  aria-invalid={!!nameError}
                  aria-describedby={nameError ? 'name-error' : undefined}
                  title={schemaId ? 'Schema name cannot be changed after creation' : 'Enter a unique schema name'}
                />
                {nameError && (
                  <p id="name-error" className="text-xs text-destructive">
                    {nameError}
                  </p>
                )}
                {schemaId && (
                  <p className="text-xs text-muted-foreground">
                    Name cannot be changed after creation
                  </p>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {!schemaId && <TemplateSelector />}
            <Button
              onClick={handleSaveSchema}
              disabled={isSaveDisabled}
              variant="default"
              aria-label={schemaId ? 'Update schema' : 'Save schema'}
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {schemaId ? 'Updating...' : 'Saving...'}
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  {schemaId ? 'Update' : 'Save'}
                </>
              )}
            </Button>
            <Button
              onClick={handleExport}
              disabled={properties.length === 0}
              variant="outline"
              aria-label="Export schema as JSON"
            >
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex">
        {/* Left Panel - Schema Tree */}
        <div className="w-1/2 border-r">
          <div className="px-6 py-3 border-b bg-white sticky top-[73px] z-10">
            <h2 className="font-semibold">Schema Structure</h2>
            <p className="text-xs text-muted-foreground mt-1">
              Build your JSON schema by adding properties
            </p>
          </div>
          <div className="px-6 py-4">
            <SchemaTree />
          </div>
        </div>

        {/* Right Panel - JSON Preview */}
        <div className="w-1/2">
          <div className="px-6 py-3 border-b bg-white sticky top-[73px] z-10">
            <h2 className="font-semibold">Preview</h2>
            <p className="text-xs text-muted-foreground mt-1">
              Generated JSON Schema and sample data
            </p>
          </div>
          <div className="px-6 py-4">
            <JsonPreview />
          </div>
        </div>
      </main>
    </Page>
  );
}
