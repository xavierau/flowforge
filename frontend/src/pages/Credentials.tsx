/**
 * Credentials Page
 *
 * Manage workflow credentials/secrets for use in workflow expressions.
 * Supports:
 * - Tenant-level credentials (available to all workflows)
 * - Workflow-specific credentials
 * - Create, view, and delete operations
 *
 * Credentials are referenced in workflows using: {{$secrets.CREDENTIAL_NAME}}
 */

import { useState, useEffect, useCallback } from 'react';
import { Page, PageHeader, PageContent } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Key,
  Plus,
  Trash2,
  AlertCircle,
  Building,
  Workflow,
  Copy,
  Check,
} from 'lucide-react';
import { credentialService } from '@/services/credential.service';
import type {
  Credential,
  CredentialCreateRequest,
  CredentialScope,
} from '@/types/credential';
import { formatSecretExpression } from '@/lib/expression-parser';

/**
 * Credentials Page Component
 */
export function Credentials() {
  // State management
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scopeFilter, setScopeFilter] = useState<CredentialScope | 'all'>(
    'all'
  );

  // Dialog state
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [deleteCredentialId, setDeleteCredentialId] = useState<string | null>(
    null
  );

  // Form state
  const [formData, setFormData] = useState<CredentialCreateRequest>({
    name: '',
    value: '',
    description: '',
    scope: 'tenant',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Copy feedback state
  const [copiedId, setCopiedId] = useState<string | null>(null);

  /**
   * Fetch credentials from API
   */
  const fetchCredentials = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await credentialService.listCredentials(
        scopeFilter !== 'all' ? { scope: scopeFilter } : undefined
      );
      setCredentials(response.credentials);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to load credentials'
      );
    } finally {
      setIsLoading(false);
    }
  }, [scopeFilter]);

  /**
   * Load credentials on mount and when filter changes
   */
  useEffect(() => {
    fetchCredentials();
  }, [fetchCredentials]);

  /**
   * Handle form input changes
   */
  const handleInputChange = (
    field: keyof CredentialCreateRequest,
    value: string
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setFormError(null);
  };

  /**
   * Validate credential name (alphanumeric and underscores only)
   */
  const isValidCredentialName = (name: string): boolean => {
    return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name);
  };

  /**
   * Create new credential
   */
  const handleCreateCredential = async () => {
    // Validation
    if (!formData.name.trim()) {
      setFormError('Name is required');
      return;
    }
    if (!isValidCredentialName(formData.name)) {
      setFormError(
        'Name must start with a letter or underscore and contain only letters, numbers, and underscores'
      );
      return;
    }
    if (!formData.value.trim()) {
      setFormError('Value is required');
      return;
    }

    setIsSubmitting(true);
    setFormError(null);

    try {
      await credentialService.createCredential(formData);
      setIsCreateDialogOpen(false);
      setFormData({
        name: '',
        value: '',
        description: '',
        scope: 'tenant',
      });
      fetchCredentials();
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : 'Failed to create credential'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  /**
   * Delete credential
   */
  const handleDeleteCredential = async () => {
    if (!deleteCredentialId) return;

    try {
      await credentialService.deleteCredential(deleteCredentialId);
      setDeleteCredentialId(null);
      fetchCredentials();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to delete credential'
      );
    }
  };

  /**
   * Copy expression to clipboard
   */
  const handleCopyExpression = async (credentialName: string) => {
    const expression = formatSecretExpression(credentialName);
    try {
      await navigator.clipboard.writeText(expression);
      setCopiedId(credentialName);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = expression;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopiedId(credentialName);
      setTimeout(() => setCopiedId(null), 2000);
    }
  };

  /**
   * Get scope badge styling
   */
  const getScopeBadge = (scope: CredentialScope) => {
    if (scope === 'tenant') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          <Building className="h-3 w-3" />
          Tenant
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
        <Workflow className="h-3 w-3" />
        Workflow
      </span>
    );
  };

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Credentials' },
        ]}
        title="Credentials"
        subtitle="Manage secrets for use in workflow expressions"
      />

      <PageContent>
        {/* Actions Bar */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Label htmlFor="scope-filter" className="text-sm whitespace-nowrap">
              Filter by scope:
            </Label>
            <Select
              value={scopeFilter}
              onValueChange={(value) =>
                setScopeFilter(value as CredentialScope | 'all')
              }
            >
              <SelectTrigger id="scope-filter" className="w-[140px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="tenant">Tenant-level</SelectItem>
                <SelectItem value="workflow">Workflow-specific</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Dialog
            open={isCreateDialogOpen}
            onOpenChange={setIsCreateDialogOpen}
          >
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Credential
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Credential</DialogTitle>
                <DialogDescription>
                  Add a new secret that can be referenced in workflows using the
                  expression syntax.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4 py-4">
                {/* Name */}
                <div className="space-y-2">
                  <Label htmlFor="credential-name">Name</Label>
                  <Input
                    id="credential-name"
                    value={formData.name}
                    onChange={(e) =>
                      handleInputChange(
                        'name',
                        e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, '_')
                      )
                    }
                    placeholder="API_KEY"
                  />
                  <p className="text-xs text-muted-foreground">
                    Use in workflows as:{' '}
                    <code className="bg-muted px-1 py-0.5 rounded">
                      {formatSecretExpression(formData.name || 'NAME')}
                    </code>
                  </p>
                </div>

                {/* Value */}
                <div className="space-y-2">
                  <Label htmlFor="credential-value">Value</Label>
                  <Input
                    id="credential-value"
                    type="password"
                    value={formData.value}
                    onChange={(e) => handleInputChange('value', e.target.value)}
                    placeholder="Enter secret value..."
                  />
                  <p className="text-xs text-muted-foreground">
                    The value will be encrypted and never shown again.
                  </p>
                </div>

                {/* Description */}
                <div className="space-y-2">
                  <Label htmlFor="credential-description">
                    Description (optional)
                  </Label>
                  <Textarea
                    id="credential-description"
                    value={formData.description}
                    onChange={(e) =>
                      handleInputChange('description', e.target.value)
                    }
                    placeholder="What is this credential used for?"
                    rows={2}
                  />
                </div>

                {/* Scope */}
                <div className="space-y-2">
                  <Label htmlFor="credential-scope">Scope</Label>
                  <Select
                    value={formData.scope}
                    onValueChange={(value) =>
                      handleInputChange('scope', value as CredentialScope)
                    }
                  >
                    <SelectTrigger id="credential-scope">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="tenant">
                        <span className="flex items-center gap-2">
                          <Building className="h-4 w-4" />
                          Tenant-level (all workflows)
                        </span>
                      </SelectItem>
                      <SelectItem value="workflow">
                        <span className="flex items-center gap-2">
                          <Workflow className="h-4 w-4" />
                          Workflow-specific
                        </span>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Error */}
                {formError && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{formError}</AlertDescription>
                  </Alert>
                )}
              </div>

              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setIsCreateDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleCreateCredential}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Creating...' : 'Create Credential'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        {/* Error State */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="flex h-[200px] items-center justify-center">
            <div className="text-center">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent align-[-0.125em]"></div>
              <p className="mt-4 text-sm text-muted-foreground">
                Loading credentials...
              </p>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && credentials.length === 0 && (
          <div className="flex flex-col items-center justify-center h-[200px] border-2 border-dashed rounded-lg">
            <Key className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-1">No credentials yet</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Create credentials to use in your workflow expressions
            </p>
            <Button onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add First Credential
            </Button>
          </div>
        )}

        {/* Credentials List */}
        {!isLoading && credentials.length > 0 && (
          <div className="border rounded-lg divide-y">
            {credentials.map((credential) => (
              <div
                key={credential.id}
                className="p-4 flex items-center justify-between gap-4"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Key className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <span className="font-medium font-mono truncate">
                      {credential.name}
                    </span>
                    {getScopeBadge(credential.scope)}
                  </div>
                  {credential.description && (
                    <p className="text-sm text-muted-foreground truncate ml-6">
                      {credential.description}
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground mt-1 ml-6">
                    Created:{' '}
                    {new Date(credential.createdAt).toLocaleDateString()}
                  </p>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {/* Copy Expression Button */}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleCopyExpression(credential.name)}
                    className="gap-1"
                  >
                    {copiedId === credential.name ? (
                      <>
                        <Check className="h-3 w-3" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="h-3 w-3" />
                        Copy Expression
                      </>
                    )}
                  </Button>

                  {/* Delete Button */}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setDeleteCredentialId(credential.id)}
                    className="text-destructive hover:text-destructive hover:bg-destructive/10"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Usage Info */}
        <div className="bg-muted/50 rounded-lg p-4 border">
          <h3 className="font-medium mb-2">How to use credentials</h3>
          <p className="text-sm text-muted-foreground mb-3">
            Reference credentials in your workflow nodes using the expression
            syntax:
          </p>
          <code className="block bg-background px-3 py-2 rounded border text-sm font-mono">
            {formatSecretExpression('YOUR_CREDENTIAL_NAME')}
          </code>
          <p className="text-xs text-muted-foreground mt-3">
            Credentials are securely stored and their values are never exposed
            in the UI. They are only decrypted at runtime during workflow
            execution.
          </p>
        </div>
      </PageContent>

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={!!deleteCredentialId}
        onOpenChange={(open: boolean) => !open && setDeleteCredentialId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Credential</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this credential? This action
              cannot be undone. Any workflows using this credential will fail
              until the reference is updated.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteCredential}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Page>
  );
}
