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
import { Switch } from '@/components/ui/switch';
import { extractFromFile, listSchemas } from '@/lib/api';
import type { ApiSchema } from '@/types/api-schema';
import { Badge } from '@/components/ui/badge';
import { MarkdownPipelineConfig } from '@/components/markdown/MarkdownPipelineConfig';
import {
  SplitMode,
  ExtractionMode,
  MarkdownConverter,
  MarkdownFormat,
  getSplitModeDescription,
  getExtractionModeDescription,
} from '@/types/enums';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertTriangle } from 'lucide-react';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_FILE_TYPES = ['application/pdf', 'image/png', 'image/jpeg'];
const PDF_MIME_TYPE = 'application/pdf';

/**
 * Check if a file is a PDF based on MIME type
 */
function isPdfFile(file: File | null): boolean {
  return file?.type === PDF_MIME_TYPE;
}

interface FormData {
  file: File | null;
  schemaId: string;
  customSchema: string;
  customPrompt: string;
  // New granular mode fields
  splitMode: SplitMode;
  extractionMode: ExtractionMode;
  markdownConverter: MarkdownConverter;
  markdownFormat: MarkdownFormat;
  callbackUrl: string;
  enableThinking: boolean;
  thinkingBudget: number;
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
    // New granular mode fields (defaults)
    splitMode: SplitMode.BATCH,
    extractionMode: ExtractionMode.VLLM,
    markdownConverter: MarkdownConverter.GEMINI_VISION,
    markdownFormat: MarkdownFormat.TABLE_HEAVY,
    callbackUrl: '',
    enableThinking: false,
    thinkingBudget: 3000,
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

    // Auto-reset split mode to BATCH if non-PDF file is selected while Auto is active
    const isNewFilePdf = file.type === PDF_MIME_TYPE;
    if (!isNewFilePdf && formData.splitMode === SplitMode.AUTO) {
      toast.info('Split mode changed', {
        description: 'Auto split mode only works with PDF files. Changed to Batch mode.',
      });
      setFormData(prev => ({ ...prev, file, splitMode: SplitMode.BATCH }));
    } else {
      setFormData(prev => ({ ...prev, file }));
    }
  }, [formData.splitMode]);

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

    // Validate auto split mode only works with PDF files
    if (formData.splitMode === SplitMode.AUTO && !isPdfFile(formData.file)) {
      return 'Auto split mode is only supported for PDF files. Please select a PDF or choose a different split mode.';
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
      // Build extract request with new granular mode fields
      const extractRequest: any = {
        file: formData.file,
        model_provider: 'google',
        model_name: 'gemini-2.5-flash',
        // New granular mode fields
        split_mode: formData.splitMode,
        extraction_mode: formData.extractionMode,
      };

      // Add schema configuration
      if (useCustomSchema) {
        extractRequest.extraction_schema = JSON.parse(formData.customSchema);
      } else {
        extractRequest.schema_definition_id = formData.schemaId;
      }

      // Add markdown pipeline configuration if markdown extraction mode
      if (formData.extractionMode === ExtractionMode.MARKDOWN) {
        extractRequest.markdown_converter = formData.markdownConverter;
        extractRequest.markdown_format = formData.markdownFormat;
      }

      // Add optional fields
      if (formData.customPrompt?.trim()) {
        extractRequest.custom_prompt = formData.customPrompt;
      }

      if (formData.callbackUrl?.trim()) {
        extractRequest.callback_url = formData.callbackUrl;
      }

      // Add thinking mode configuration
      extractRequest.enable_thinking = formData.enableThinking;
      extractRequest.thinking_budget = formData.thinkingBudget;

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
                Configure how the document is split and how extraction is performed
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Split Mode Selection */}
              <div className="space-y-2">
                <Label htmlFor="split-mode">Document Split Mode</Label>
                <Select
                  value={formData.splitMode}
                  onValueChange={(value) =>
                    setFormData(prev => ({ ...prev, splitMode: value as SplitMode }))
                  }
                  disabled={isSubmitting}
                >
                  <SelectTrigger id="split-mode">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={SplitMode.BATCH}>
                      Batch (1 call - recommended)
                    </SelectItem>
                    <SelectItem value={SplitMode.PER_PAGE}>
                      Per Page (N calls)
                    </SelectItem>
                    <SelectItem
                      value={SplitMode.AUTO}
                      disabled={formData.file !== null && !isPdfFile(formData.file)}
                    >
                      Auto (LLM Split - costs extra credits){formData.file && !isPdfFile(formData.file) ? ' - PDF only' : ''}
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  {getSplitModeDescription(formData.splitMode)}
                </p>
                {/* Inline error when Auto is selected with non-PDF file */}
                {formData.splitMode === SplitMode.AUTO && formData.file && !isPdfFile(formData.file) && (
                  <p className="text-sm text-destructive font-medium">
                    Auto split mode requires a PDF file. Please upload a PDF or select a different split mode.
                  </p>
                )}
              </div>

              {/* Warning for Auto split mode */}
              {formData.splitMode === SplitMode.AUTO && (
                <Alert variant="default" className="border-orange-200 bg-orange-50">
                  <AlertTriangle className="h-4 w-4 text-orange-600" />
                  <AlertDescription className="text-orange-800">
                    Auto split uses LLM to detect document boundaries. This costs additional credits
                    and creates separate extraction jobs for each detected document.
                    {isPdfFile(formData.file) ? '' : ' Only works with PDF files.'}
                  </AlertDescription>
                </Alert>
              )}

              {/* Extraction Mode Selection */}
              <div className="space-y-2">
                <Label htmlFor="extraction-mode">Extraction Method</Label>
                <Select
                  value={formData.extractionMode}
                  onValueChange={(value) =>
                    setFormData(prev => ({ ...prev, extractionMode: value as ExtractionMode }))
                  }
                  disabled={isSubmitting}
                >
                  <SelectTrigger id="extraction-mode">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ExtractionMode.VLLM}>
                      Vision LLM (direct image extraction)
                    </SelectItem>
                    <SelectItem value={ExtractionMode.MARKDOWN}>
                      Markdown Pipeline (better for tables)
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  {getExtractionModeDescription(formData.extractionMode)}
                </p>
              </div>

              {/* Show markdown configuration only when markdown extraction mode is selected */}
              {formData.extractionMode === ExtractionMode.MARKDOWN && (
                <MarkdownPipelineConfig
                  converter={formData.markdownConverter}
                  format={formData.markdownFormat}
                  onConverterChange={(converter) =>
                    setFormData(prev => ({ ...prev, markdownConverter: converter }))
                  }
                  onFormatChange={(format) =>
                    setFormData(prev => ({ ...prev, markdownFormat: format }))
                  }
                  disabled={isSubmitting}
                />
              )}

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

          {/* Advanced Options Section */}
          <Card>
            <CardHeader>
              <CardTitle>Advanced Options</CardTitle>
              <CardDescription>
                Configure advanced AI processing features
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="enable-thinking">Enable AI Thinking Mode</Label>
                    <p className="text-sm text-muted-foreground">
                      Allows the AI to spend more tokens on reasoning before generating the response. This can improve accuracy for complex documents.
                    </p>
                  </div>
                  <Switch
                    id="enable-thinking"
                    checked={formData.enableThinking}
                    onCheckedChange={(checked) =>
                      setFormData(prev => ({ ...prev, enableThinking: checked }))
                    }
                    disabled={isSubmitting}
                  />
                </div>

                {formData.enableThinking && (
                  <div className="space-y-2 ml-6 border-l-2 border-muted pl-4">
                    <Label htmlFor="thinking-budget">
                      Thinking Budget (Tokens)
                    </Label>
                    <Input
                      id="thinking-budget"
                      type="number"
                      min={0}
                      max={10000}
                      step={100}
                      value={formData.thinkingBudget}
                      onChange={(e) => {
                        const value = parseInt(e.target.value) || 0;
                        setFormData(prev => ({
                          ...prev,
                          thinkingBudget: Math.min(Math.max(value, 0), 10000)
                        }));
                      }}
                      disabled={isSubmitting}
                      className="max-w-xs"
                    />
                    <p className="text-xs text-muted-foreground">
                      Number of tokens allocated for AI reasoning (0-10,000). Higher values allow more thorough analysis but consume more tokens.
                    </p>
                  </div>
                )}
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
