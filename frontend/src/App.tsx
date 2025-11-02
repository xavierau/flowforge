import { useState, useCallback } from 'react';
import { FileJson, Download, Save, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { JsonPreview } from '@/components/preview/JsonPreview';
import { SchemaTree } from '@/components/schema-builder/SchemaTree';
import { TemplateSelector } from '@/components/templates/TemplateSelector';
import { Toaster } from '@/components/ui/sonner';
import { toast } from 'sonner';
import { useSchemaStore } from '@/store/schemaStore';
import { propertiesToJsonSchema } from '@/lib/schema-converter';
import { submitSchema, validateSchemaName, SchemaApiError } from '@/lib/api';

function App() {
  const { schemaName, properties, setSchemaName, markClean } = useSchemaStore();
  const [nameError, setNameError] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);

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
    // Validate name first
    const validation = validateSchemaName(schemaName);
    if (!validation.isValid) {
      setNameError(validation.error || 'Invalid schema name');
      toast.error('Cannot save schema', {
        description: validation.error || 'Please fix the schema name',
      });
      return;
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

      await submitSchema({
        name: schemaName.trim(),
        definitions: schema,
      });

      // Success - mark as clean and show toast
      markClean();
      toast.success('Schema saved successfully!', {
        description: `"${schemaName}" has been saved to the database`,
      });
    } catch (error) {
      if (error instanceof SchemaApiError) {
        // Handle specific API errors
        if (error.statusCode === 409) {
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
          toast.error('Failed to save schema', {
            description: error.message || 'An unexpected error occurred',
          });
        }
      } else {
        // Unknown error
        toast.error('Failed to save schema', {
          description: error instanceof Error ? error.message : 'An unexpected error occurred',
        });
      }
    } finally {
      setIsSaving(false);
    }
  }, [schemaName, properties, setSchemaName, markClean]);

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

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="flex items-center justify-between px-6 py-4">
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
                  className={nameError ? 'border-destructive focus-visible:ring-destructive' : ''}
                  aria-label="Schema name"
                  aria-invalid={!!nameError}
                  aria-describedby={nameError ? 'name-error' : undefined}
                />
                {nameError && (
                  <p id="name-error" className="text-xs text-destructive">
                    {nameError}
                  </p>
                )}
              </div>
              <p className="text-sm text-muted-foreground mt-1">JSON Schema Builder</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <TemplateSelector />
            <Button
              onClick={handleSaveSchema}
              disabled={isSaveDisabled}
              variant="default"
              aria-label="Save schema"
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Schema
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
              Export Schema
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left Panel - Schema Tree */}
        <div className="w-1/2 border-r overflow-auto p-6">
          <div className="mb-4">
            <h2 className="text-lg font-semibold mb-2">Schema Structure</h2>
            <p className="text-sm text-muted-foreground">
              Build your JSON schema by adding properties. Maximum 3 levels of nesting supported.
            </p>
          </div>

          <SchemaTree />
        </div>

        {/* Right Panel - JSON Preview */}
        <div className="w-1/2 overflow-auto p-6">
          <div className="mb-4">
            <h2 className="text-lg font-semibold mb-2">Preview</h2>
            <p className="text-sm text-muted-foreground">
              View the generated JSON Schema and sample data
            </p>
          </div>

          <JsonPreview />
        </div>
      </main>

      {/* Toast notifications */}
      <Toaster />
    </div>
  );
}

export default App;
