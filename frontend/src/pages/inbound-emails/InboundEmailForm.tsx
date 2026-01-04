/**
 * InboundEmailForm - Form for creating and editing inbound email addresses
 *
 * Features:
 * - Create new inbound email address
 * - Edit existing inbound email address
 * - JSON schema editor or dropdown for schema selection
 * - Model provider and name configuration
 * - Split mode and extraction mode selection
 * - Callback URL configuration
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { ArrowLeft, Loader2, Plus, X } from 'lucide-react';
import { toast } from 'sonner';

import { Page, PageHeader, PageContent } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';

import type {
  InboundEmailAddressCreate,
  InboundEmailAddressUpdate,
} from '@/types/inbound-email';
import type { ApiSchema } from '@/types/api-schema';
import {
  createInboundEmailAddress,
  updateInboundEmailAddress,
  getInboundEmailAddress,
} from '@/services/inbound-email.service';
import { listSchemas } from '@/lib/api';
// Note: SplitMode and ExtractionMode are used via their values in SPLIT_MODES and EXTRACTION_MODES constants

// ============================================================================
// CONSTANTS
// ============================================================================

const MODEL_PROVIDERS = [
  { value: 'google', label: 'Google (Gemini)' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'llamaextract', label: 'LlamaExtract' },
] as const;

const DEFAULT_MODELS: Record<string, string> = {
  google: 'gemini-2.5-flash',
  openai: 'gpt-4o',
  llamaextract: 'llama-extract',
};

const SPLIT_MODES = [
  { value: 'batch', label: 'Batch (All pages together)' },
  { value: 'per_page', label: 'Per Page (Each page separately)' },
  { value: 'auto', label: 'Auto Split (LLM detects document boundaries)' },
] as const;

const EXTRACTION_MODES = [
  { value: 'vllm', label: 'Vision LLM (Direct extraction)' },
  { value: 'markdown', label: 'Markdown Pipeline (Better for tables)' },
] as const;

// ============================================================================
// FORM TYPES
// ============================================================================

interface FormData {
  name: string;
  description: string;
  allowed_senders: string[];
  schema_definition_id: string;
  extraction_schema: string;
  custom_prompt: string;
  model_provider: string;
  model_name: string;
  split_mode: string;
  extraction_mode: string;
  callback_url: string;
  use_custom_schema: boolean;
}

// ============================================================================
// COMPONENT
// ============================================================================

export function InboundEmailForm() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEditMode = Boolean(id);

  // UI state
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [schemas, setSchemas] = useState<ApiSchema[]>([]);
  const [isLoadingSchemas, setIsLoadingSchemas] = useState(true);

  // Allowed senders input state
  const [senderInput, setSenderInput] = useState('');

  // Form setup
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
    reset,
  } = useForm<FormData>({
    defaultValues: {
      name: '',
      description: '',
      allowed_senders: [],
      schema_definition_id: '',
      extraction_schema: '',
      custom_prompt: '',
      model_provider: 'google',
      model_name: 'gemini-2.5-flash',
      split_mode: 'batch',
      extraction_mode: 'vllm',
      callback_url: '',
      use_custom_schema: false,
    },
  });

  // Watch form values
  const modelProvider = watch('model_provider');
  const useCustomSchema = watch('use_custom_schema');
  const allowedSenders = watch('allowed_senders');

  // Load schemas on mount
  useEffect(() => {
    let isMounted = true;

    const loadSchemas = async () => {
      try {
        setIsLoadingSchemas(true);
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

    return () => {
      isMounted = false;
    };
  }, []);

  // Load existing data in edit mode
  useEffect(() => {
    let isMounted = true;

    const loadAddress = async () => {
      if (!id) return;

      try {
        setIsLoading(true);
        const address = await getInboundEmailAddress(id);

        if (isMounted) {
          reset({
            name: address.name,
            description: address.description || '',
            allowed_senders: address.allowed_senders || [],
            schema_definition_id: address.schema_definition_id || '',
            extraction_schema: address.extraction_schema
              ? JSON.stringify(address.extraction_schema, null, 2)
              : '',
            custom_prompt: '',
            model_provider: address.model_provider,
            model_name: address.model_name,
            split_mode: address.split_mode,
            extraction_mode: address.extraction_mode,
            callback_url: address.callback_url || '',
            use_custom_schema: Boolean(address.extraction_schema),
          });
        }
      } catch (error) {
        if (isMounted) {
          toast.error('Failed to load inbound email address', {
            description: error instanceof Error ? error.message : 'Unknown error',
          });
          navigate('/inbound-emails');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadAddress();

    return () => {
      isMounted = false;
    };
  }, [id, reset, navigate]);

  // Update model name when provider changes
  useEffect(() => {
    if (DEFAULT_MODELS[modelProvider]) {
      setValue('model_name', DEFAULT_MODELS[modelProvider]);
    }
  }, [modelProvider, setValue]);

  // Add sender pattern
  const addSenderPattern = useCallback(() => {
    const pattern = senderInput.trim().toLowerCase();
    if (!pattern) return;

    // Validate pattern
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    const domainPattern = /^\*@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

    if (!emailPattern.test(pattern) && !domainPattern.test(pattern)) {
      toast.error('Invalid sender pattern', {
        description: 'Use email@domain.com or *@domain.com format',
      });
      return;
    }

    if (allowedSenders.includes(pattern)) {
      toast.warning('Pattern already added');
      return;
    }

    setValue('allowed_senders', [...allowedSenders, pattern]);
    setSenderInput('');
  }, [senderInput, allowedSenders, setValue]);

  // Remove sender pattern
  const removeSenderPattern = useCallback(
    (pattern: string) => {
      setValue(
        'allowed_senders',
        allowedSenders.filter((p) => p !== pattern)
      );
    },
    [allowedSenders, setValue]
  );

  // Form submission
  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);

    try {
      // Validate schema
      if (!data.use_custom_schema && !data.schema_definition_id) {
        toast.error('Schema required', {
          description: 'Please select a schema or provide a custom one',
        });
        setIsSubmitting(false);
        return;
      }

      if (data.use_custom_schema && !data.extraction_schema.trim()) {
        toast.error('Custom schema required', {
          description: 'Please provide a custom JSON schema',
        });
        setIsSubmitting(false);
        return;
      }

      // Parse custom schema if provided
      let extractionSchema: Record<string, unknown> | undefined;
      if (data.use_custom_schema && data.extraction_schema.trim()) {
        try {
          extractionSchema = JSON.parse(data.extraction_schema);
        } catch {
          toast.error('Invalid JSON schema', {
            description: 'Please provide valid JSON',
          });
          setIsSubmitting(false);
          return;
        }
      }

      if (isEditMode && id) {
        // Update existing address
        const updateData: InboundEmailAddressUpdate = {
          name: data.name,
          description: data.description || undefined,
          allowed_senders: data.allowed_senders.length > 0 ? data.allowed_senders : undefined,
          model_provider: data.model_provider,
          model_name: data.model_name,
          split_mode: data.split_mode,
          extraction_mode: data.extraction_mode,
          callback_url: data.callback_url || undefined,
        };

        if (data.use_custom_schema) {
          updateData.extraction_schema = extractionSchema;
          updateData.schema_definition_id = undefined;
        } else {
          updateData.schema_definition_id = data.schema_definition_id;
          updateData.extraction_schema = undefined;
        }

        await updateInboundEmailAddress(id, updateData);
        toast.success('Inbound email address updated');
        navigate(`/inbound-emails/${id}`);
      } else {
        // Create new address
        const createData: InboundEmailAddressCreate = {
          name: data.name,
          description: data.description || undefined,
          allowed_senders: data.allowed_senders.length > 0 ? data.allowed_senders : undefined,
          model_provider: data.model_provider,
          model_name: data.model_name,
          split_mode: data.split_mode,
          extraction_mode: data.extraction_mode,
          callback_url: data.callback_url || undefined,
          custom_prompt: data.custom_prompt || undefined,
        };

        if (data.use_custom_schema) {
          createData.extraction_schema = extractionSchema;
        } else {
          createData.schema_definition_id = data.schema_definition_id;
        }

        const result = await createInboundEmailAddress(createData);
        toast.success('Inbound email address created', {
          description: `Email: ${result.email_address}`,
        });
        navigate(`/inbound-emails/${result.id}`);
      }
    } catch (error) {
      toast.error(`Failed to ${isEditMode ? 'update' : 'create'} inbound email address`, {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <Page>
        <PageContent>
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </PageContent>
      </Page>
    );
  }

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Inbound Emails', href: '/inbound-emails' },
          { label: isEditMode ? 'Edit' : 'Create' },
        ]}
        title={isEditMode ? 'Edit Inbound Email Address' : 'Create Inbound Email Address'}
        subtitle={
          isEditMode
            ? 'Update the configuration for this inbound email address'
            : 'Create a new email address for automatic document processing'
        }
      />
      <PageContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate('/inbound-emails')}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
          </div>
          {/* Basic Information */}
          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
              <CardDescription>Name and description for this inbound email address</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  placeholder="e.g., Invoice Processing"
                  {...register('name', { required: 'Name is required' })}
                  disabled={isSubmitting}
                />
                {errors.name && (
                  <p className="text-sm text-destructive">{errors.name.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">
                  Description <Badge variant="secondary">Optional</Badge>
                </Label>
                <Textarea
                  id="description"
                  placeholder="Description of what this email address is used for..."
                  {...register('description')}
                  disabled={isSubmitting}
                />
              </div>
            </CardContent>
          </Card>

          {/* Allowed Senders */}
          <Card>
            <CardHeader>
              <CardTitle>Allowed Senders</CardTitle>
              <CardDescription>
                Restrict which email addresses can send to this address. Leave empty to accept from
                anyone.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="user@domain.com or *@domain.com"
                  value={senderInput}
                  onChange={(e) => setSenderInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      addSenderPattern();
                    }
                  }}
                  disabled={isSubmitting}
                />
                <Button type="button" variant="outline" onClick={addSenderPattern} disabled={isSubmitting}>
                  <Plus className="h-4 w-4" />
                </Button>
              </div>

              {allowedSenders.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {allowedSenders.map((pattern) => (
                    <Badge key={pattern} variant="secondary" className="gap-1">
                      {pattern}
                      <button
                        type="button"
                        onClick={() => removeSenderPattern(pattern)}
                        className="ml-1 hover:text-destructive"
                        disabled={isSubmitting}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Schema Configuration */}
          <Card>
            <CardHeader>
              <CardTitle>Extraction Schema</CardTitle>
              <CardDescription>Select a predefined schema or provide a custom JSON schema</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Switch
                    id="use_custom_schema"
                    checked={useCustomSchema}
                    onCheckedChange={(checked) => setValue('use_custom_schema', checked)}
                    disabled={isSubmitting}
                  />
                  <Label htmlFor="use_custom_schema">Use custom JSON schema</Label>
                </div>
              </div>

              {!useCustomSchema ? (
                <div className="space-y-2">
                  <Label htmlFor="schema_definition_id">Select Schema *</Label>
                  <Select
                    value={watch('schema_definition_id')}
                    onValueChange={(value) => setValue('schema_definition_id', value)}
                    disabled={isSubmitting || isLoadingSchemas}
                  >
                    <SelectTrigger id="schema_definition_id">
                      <SelectValue placeholder="Choose a schema..." />
                    </SelectTrigger>
                    <SelectContent>
                      {isLoadingSchemas ? (
                        <div className="p-2 text-sm text-muted-foreground">Loading schemas...</div>
                      ) : schemas.length === 0 ? (
                        <div className="p-2 text-sm text-muted-foreground">No schemas available</div>
                      ) : (
                        schemas.map((schema) => (
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
                        type="button"
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
                  <Label htmlFor="extraction_schema">Custom JSON Schema *</Label>
                  <Textarea
                    id="extraction_schema"
                    placeholder='{"type": "object", "properties": {...}}'
                    {...register('extraction_schema')}
                    disabled={isSubmitting}
                    className="font-mono text-sm min-h-[200px]"
                  />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Model Configuration */}
          <Card>
            <CardHeader>
              <CardTitle>Model Configuration</CardTitle>
              <CardDescription>Choose the AI model and processing settings</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="model_provider">Model Provider *</Label>
                  <Select
                    value={watch('model_provider')}
                    onValueChange={(value) => setValue('model_provider', value)}
                    disabled={isSubmitting}
                  >
                    <SelectTrigger id="model_provider">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {MODEL_PROVIDERS.map((provider) => (
                        <SelectItem key={provider.value} value={provider.value}>
                          {provider.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="model_name">Model Name *</Label>
                  <Input
                    id="model_name"
                    {...register('model_name', { required: 'Model name is required' })}
                    disabled={isSubmitting}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="split_mode">Split Mode</Label>
                  <Select
                    value={watch('split_mode')}
                    onValueChange={(value) => setValue('split_mode', value)}
                    disabled={isSubmitting}
                  >
                    <SelectTrigger id="split_mode">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SPLIT_MODES.map((mode) => (
                        <SelectItem key={mode.value} value={mode.value}>
                          {mode.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="extraction_mode">Extraction Mode</Label>
                  <Select
                    value={watch('extraction_mode')}
                    onValueChange={(value) => setValue('extraction_mode', value)}
                    disabled={isSubmitting}
                  >
                    <SelectTrigger id="extraction_mode">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {EXTRACTION_MODES.map((mode) => (
                        <SelectItem key={mode.value} value={mode.value}>
                          {mode.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Callback URL */}
          <Card>
            <CardHeader>
              <CardTitle>Webhook Configuration</CardTitle>
              <CardDescription>Optional webhook URL to receive extraction results</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Label htmlFor="callback_url">
                  Callback URL <Badge variant="secondary">Optional</Badge>
                </Label>
                <Input
                  id="callback_url"
                  type="url"
                  placeholder="https://your-domain.com/webhooks/extraction-complete"
                  {...register('callback_url')}
                  disabled={isSubmitting}
                />
                <p className="text-xs text-muted-foreground">
                  Results will be POSTed to this URL when extraction completes
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Submit */}
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate('/inbound-emails')}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {isEditMode ? 'Updating...' : 'Creating...'}
                </>
              ) : isEditMode ? (
                'Update'
              ) : (
                'Create'
              )}
            </Button>
          </div>
        </form>
      </PageContent>
    </Page>
  );
}
