/**
 * JobCreate Component
 *
 * Single-step document extraction job creation workflow:
 * - Uses the combined /api/v1/jobs/extract endpoint
 * - Uploads document and creates extraction job in one API call
 * - No polling required - backend handles document processing asynchronously
 *
 * Design Principles:
 * - Single Responsibility: Handles only job creation workflow
 * - Proper State Management: Form state isolated in component
 * - useEffect Best Practices: Cleanup on unmount, proper dependencies
 * - Error Handling: User-friendly error messages with toast notifications
 * - Simplified Flow: Single API call instead of upload → poll → submit
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Upload, FileText, X, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Page, PageHeader, PageContent } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { extractFromFile, listSchemas } from '@/lib/api';
import type { ApiSchema } from '@/types/api-schema';
import { Badge } from '@/components/ui/badge';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_FILE_TYPES = ['application/pdf', 'image/png', 'image/jpeg'];

interface FormData {
  file: File | null;
  schemaId: string;
  customSchema: string;
  customPrompt: string;
  processingMode: 'batch' | 'per_page';
  callbackUrl: string;
}

export function JobCreate() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Form state
  const [formData, setFormData] = useState<FormData>({
    file: null,
    schemaId: '',
    customSchema: '',
    customPrompt: '',
    processingMode: 'batch',
    callbackUrl: '',
  });

  // UI state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [schemas, setSchemas] = useState<ApiSchema[]>([]);
  const [isLoadingSchemas, setIsLoadingSchemas] = useState(true);
  const [useCustomSchema, setUseCustomSchema] = useState(false);

  // Load available schemas on mount
  useEffect(() => {
    let isMounted = true;

    const loadSchemas = async () => {
      try {
        const response = await listSchemas({ limit: 100 });
        if (isMounted) {
          setSchemas(response.schemas);
        }
      } catch (error) {
        if (isMounted) {
          toast.error('Failed to load schemas', {
            description: error instanceof Error ? error.message : 'Unknown error',
          });
        }
      } finally {
        if (isMounted) {
          setIsLoadingSchemas(false);
        }
      }
    };

    loadSchemas();

    // Cleanup function to prevent state updates after unmount
    return () => {
      isMounted = false;
    };
  }, []);

  // File selection handler
  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!ALLOWED_FILE_TYPES.includes(file.type)) {
      toast.error('Invalid file type', {
        description: 'Please upload a PDF, PNG, or JPEG file',
      });
      return;
    }

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      toast.error('File too large', {
        description: `Maximum file size is ${MAX_FILE_SIZE / 1024 / 1024}MB`,
      });
      return;
    }

    setFormData(prev => ({ ...prev, file }));
  }, []);

  // Remove selected file
  const handleRemoveFile = useCallback(() => {
    setFormData(prev => ({ ...prev, file: null }));
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  // Form validation
  const validateForm = useCallback((): string | null => {
    if (!formData.file) {
      return 'Please select a file to upload';
    }

    if (!useCustomSchema && !formData.schemaId) {
      return 'Please select a schema or use custom schema';
    }

    if (useCustomSchema && !formData.customSchema.trim()) {
      return 'Please provide a custom schema';
    }

    if (useCustomSchema) {
      try {
        JSON.parse(formData.customSchema);
      } catch {
        return 'Invalid JSON in custom schema';
      }
    }

    return null;
  }, [formData, useCustomSchema]);

  // Submit handler - Single API call to upload and create extraction job
  const handleSubmit = useCallback(async () => {
    const validationError = validateForm();
    if (validationError) {
      toast.error('Validation Error', { description: validationError });
      return;
    }

    if (!formData.file) {
      return;
    }

    setIsSubmitting(true);

    try {
      // Build extract request
      const extractRequest: any = {
        file: formData.file,
        model_provider: 'google',
        model_name: 'gemini-2.5-flash',
        processing_mode: formData.processingMode,
      };

      // Add schema configuration
      if (useCustomSchema) {
        extractRequest.extraction_schema = JSON.parse(formData.customSchema);
      } else {
        extractRequest.schema_definition_id = formData.schemaId;
      }

      // Add optional fields
      if (formData.customPrompt?.trim()) {
        extractRequest.custom_prompt = formData.customPrompt;
      }

      if (formData.callbackUrl?.trim()) {
        extractRequest.callback_url = formData.callbackUrl;
      }

      // Single API call - upload and create job
      const response = await extractFromFile(extractRequest);

      toast.success('Job created successfully', {
        description: `Job ID: ${response.extraction_job_id}`,
      });

      // Navigate to job detail page
      navigate(`/jobs/${response.extraction_job_id}`);
    } catch (error) {
      toast.error('Failed to create job', {
        description: error instanceof Error ? error.message : 'Unknown error occurred',
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [formData, useCustomSchema, validateForm, navigate]);

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Jobs', href: '/jobs' },
          { label: 'Create Job' },
        ]}
        title="Create Extraction Job"
        subtitle="Upload a document and configure extraction settings"
      />
      <PageContent>
        <div className="flex gap-2 mb-6">
          <Button variant="outline" onClick={() => navigate('/jobs')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Jobs
          </Button>
        </div>

        <div className="max-w-2xl mx-auto space-y-6">
          {/* File Upload Section */}
          <Card>
            <CardHeader>
              <CardTitle>Upload Document</CardTitle>
              <CardDescription>
                Upload a PDF, PNG, or JPEG file (max {MAX_FILE_SIZE / 1024 / 1024}MB)
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!formData.file ? (
                <div className="border-2 border-dashed border-muted rounded-lg p-12 text-center">
                  <Upload className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-sm text-muted-foreground mb-4">
                    Click to browse and select a file
                  </p>
                  <Button
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isSubmitting}
                  >
                    Browse Files
                  </Button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                </div>
              ) : (
                <div className="flex items-center gap-4 p-4 border rounded-lg">
                  <FileText className="h-10 w-10 text-muted-foreground flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{formData.file.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {(formData.file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={handleRemoveFile}
                    disabled={isSubmitting}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Schema Selection Section */}
          <Card>
            <CardHeader>
              <CardTitle>Extraction Schema</CardTitle>
              <CardDescription>
                Select a predefined schema or provide your own JSON schema
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Button
                  variant={!useCustomSchema ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setUseCustomSchema(false)}
                  disabled={isSubmitting}
                >
                  Predefined Schema
                </Button>
                <Button
                  variant={useCustomSchema ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setUseCustomSchema(true)}
                  disabled={isSubmitting}
                >
                  Custom Schema
                </Button>
              </div>

              {!useCustomSchema ? (
                <div className="space-y-2">
                  <Label htmlFor="schema-select">Select Schema</Label>
                  <Select
                    value={formData.schemaId}
                    onValueChange={(value) =>
                      setFormData(prev => ({ ...prev, schemaId: value }))
                    }
                    disabled={isSubmitting || isLoadingSchemas}
                  >
                    <SelectTrigger id="schema-select">
                      <SelectValue placeholder="Choose a schema..." />
                    </SelectTrigger>
                    <SelectContent>
                      {isLoadingSchemas ? (
                        <div className="p-2 text-sm text-muted-foreground">
                          Loading schemas...
                        </div>
                      ) : schemas.length === 0 ? (
                        <div className="p-2 text-sm text-muted-foreground">
                          No schemas available
                        </div>
                      ) : (
                        schemas.map(schema => (
                          <SelectItem key={schema.id} value={schema.id}>
                            {schema.name}
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                  {schemas.length === 0 && !isLoadingSchemas && (
                    <p className="text-sm text-muted-foreground">
                      No schemas found.{' '}
                      <button
                        onClick={() => navigate('/schema-builder')}
                        className="text-primary hover:underline"
                      >
                        Create one
                      </button>
                    </p>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  <Label htmlFor="custom-schema">Custom JSON Schema</Label>
                  <Textarea
                    id="custom-schema"
                    placeholder='{"properties": {...}}'
                    value={formData.customSchema}
                    onChange={(e) =>
                      setFormData(prev => ({ ...prev, customSchema: e.target.value }))
                    }
                    disabled={isSubmitting}
                    className="font-mono text-sm min-h-[200px]"
                  />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Extraction Settings Section */}
          <Card>
            <CardHeader>
              <CardTitle>Extraction Settings</CardTitle>
              <CardDescription>
                Configure processing mode and custom instructions
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="processing-mode">Processing Mode</Label>
                <Select
                  value={formData.processingMode}
                  onValueChange={(value: 'batch' | 'per_page') =>
                    setFormData(prev => ({ ...prev, processingMode: value }))
                  }
                  disabled={isSubmitting}
                >
                  <SelectTrigger id="processing-mode">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="batch">
                      Batch (All pages at once - faster)
                    </SelectItem>
                    <SelectItem value="per_page">
                      Per Page (Individual page processing)
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="custom-prompt">
                  Custom Prompt <Badge variant="secondary">Optional</Badge>
                </Label>
                <Textarea
                  id="custom-prompt"
                  placeholder="Add additional instructions for the AI model..."
                  value={formData.customPrompt}
                  onChange={(e) =>
                    setFormData(prev => ({ ...prev, customPrompt: e.target.value }))
                  }
                  disabled={isSubmitting}
                  className="min-h-[100px]"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="callback-url">
                  Callback URL <Badge variant="secondary">Optional</Badge>
                </Label>
                <Input
                  id="callback-url"
                  type="url"
                  placeholder="https://your-domain.com/webhooks/extraction-complete"
                  value={formData.callbackUrl}
                  onChange={(e) =>
                    setFormData(prev => ({ ...prev, callbackUrl: e.target.value }))
                  }
                  disabled={isSubmitting}
                />
                <p className="text-xs text-muted-foreground">
                  Optional webhook URL to receive extraction results when the job completes
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Submit Section */}
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => navigate('/jobs')}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating Job...
                </>
              ) : (
                'Create Extraction Job'
              )}
            </Button>
          </div>
        </div>
      </PageContent>
    </Page>
  );
}
