/**
 * Platform Application Detail Page
 *
 * View and manage a specific platform application including:
 * - Application settings
 * - API key management
 * - Activity logs
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Key,
  Plus,
  Copy,
  Trash2,
  CheckCircle,
  XCircle,
  AlertCircle,
  Activity,
  Settings,
  ArrowLeft,
  Eye,
  EyeOff,
} from 'lucide-react';
import { Page, PageHeader, PageContent } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import {
  getApplication,
  listApiKeys,
  createApiKey,
  revokeApiKey,
  updateApplication,
  deactivateApplication,
  activateApplication,
  PLATFORM_SCOPES,
  copyToClipboard,
  formatDate,
} from '@/services/platform.service';
import type {
  PlatformApplication,
  PlatformApiKey,
  PlatformApiKeyCreated,
  CreateApiKeyRequest,
  UpdateApplicationRequest,
} from '@/services/platform.service';

export function PlatformApplicationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [application, setApplication] = useState<PlatformApplication | null>(null);
  const [apiKeys, setApiKeys] = useState<PlatformApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreateKeyDialogOpen, setIsCreateKeyDialogOpen] = useState(false);
  const [createdKey, setCreatedKey] = useState<PlatformApiKeyCreated | null>(null);
  const [keyToRevoke, setKeyToRevoke] = useState<PlatformApiKey | null>(null);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [showFullKey, setShowFullKey] = useState(false);

  const [keyFormData, setKeyFormData] = useState<CreateApiKeyRequest>({
    name: '',
    scopes: [],
    expires_in_days: undefined,
  });

  const [editFormData, setEditFormData] = useState<UpdateApplicationRequest>({});
  const [allowedIpsInput, setAllowedIpsInput] = useState('');

  useEffect(() => {
    if (id) {
      loadApplication();
      loadApiKeys();
    }
  }, [id]);

  const loadApplication = async () => {
    if (!id) return;

    try {
      setLoading(true);
      const app = await getApplication(id);
      setApplication(app);
      setEditFormData({
        name: app.name,
        description: app.description || '',
        webhook_url: app.webhook_url || '',
        allowed_ips: app.allowed_ips,
        rate_limit_per_minute: app.rate_limit_per_minute,
        rate_limit_per_hour: app.rate_limit_per_hour,
      });
      setAllowedIpsInput(app.allowed_ips.join(', '));
    } catch (error) {
      toast.error('Failed to load application', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
      navigate('/admin/platform');
    } finally {
      setLoading(false);
    }
  };

  const loadApiKeys = async () => {
    if (!id) return;

    try {
      const keys = await listApiKeys(id);
      setApiKeys(keys);
    } catch (error) {
      toast.error('Failed to load API keys', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;

    try {
      const result = await createApiKey(id, keyFormData);
      setCreatedKey(result);
      toast.success('API key created successfully');
      await loadApiKeys();
    } catch (error) {
      toast.error('Failed to create API key', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  const handleRevokeKey = async () => {
    if (!keyToRevoke) return;

    try {
      await revokeApiKey(keyToRevoke.id);
      toast.success('API key revoked successfully');
      setKeyToRevoke(null);
      await loadApiKeys();
    } catch (error) {
      toast.error('Failed to revoke API key', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  const handleUpdateApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;

    try {
      const payload: UpdateApplicationRequest = {
        ...editFormData,
        allowed_ips: allowedIpsInput
          ? allowedIpsInput.split(',').map(ip => ip.trim()).filter(Boolean)
          : [],
      };

      await updateApplication(id, payload);
      toast.success('Application updated successfully');
      setIsEditDialogOpen(false);
      await loadApplication();
    } catch (error) {
      toast.error('Failed to update application', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  const handleToggleActive = async () => {
    if (!application) return;

    try {
      if (application.is_active) {
        await deactivateApplication(application.id);
        toast.success('Application deactivated');
      } else {
        await activateApplication(application.id);
        toast.success('Application activated');
      }
      await loadApplication();
    } catch (error) {
      toast.error(`Failed to ${application.is_active ? 'deactivate' : 'activate'} application`, {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  const handleCopyKey = async (key: string) => {
    try {
      await copyToClipboard(key);
      toast.success('API key copied to clipboard');
    } catch (error) {
      toast.error('Failed to copy API key');
    }
  };

  const handleToggleScope = (scope: string) => {
    setKeyFormData((prev) => {
      const scopes = prev.scopes.includes(scope)
        ? prev.scopes.filter((s) => s !== scope)
        : [...prev.scopes, scope];
      return { ...prev, scopes };
    });
  };

  const handleCloseCreateKeyDialog = () => {
    setIsCreateKeyDialogOpen(false);
    setCreatedKey(null);
    setKeyFormData({
      name: '',
      scopes: [],
      expires_in_days: undefined,
    });
  };

  if (loading || !application) {
    return (
      <Page>
        <PageContent>
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </PageContent>
      </Page>
    );
  }

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Admin', href: '/admin' },
          { label: 'Platform Applications', href: '/admin/platform' },
          { label: application.name },
        ]}
        title={application.name}
        subtitle={application.description || 'Platform application details and API key management'}
      />

      <PageContent>
        <div className="flex justify-between items-center mb-6">
          <Button variant="outline" onClick={() => navigate('/admin/platform')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Applications
          </Button>

          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setIsEditDialogOpen(true)}>
              <Settings className="h-4 w-4 mr-2" />
              Edit Settings
            </Button>
            <Button
              variant={application.is_active ? 'destructive' : 'default'}
              onClick={handleToggleActive}
            >
              {application.is_active ? (
                <>
                  <XCircle className="h-4 w-4 mr-2" />
                  Deactivate
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Activate
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Application Status Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Application Status
              {application.is_active ? (
                <Badge variant="default" className="bg-green-500">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Active
                </Badge>
              ) : (
                <Badge variant="secondary">
                  <XCircle className="h-3 w-3 mr-1" />
                  Inactive
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Slug</p>
                <p className="font-mono">{application.slug}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">API Keys</p>
                <p>{application.api_key_count} active</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Rate Limit (per minute)</p>
                <p>{application.rate_limit_per_minute} requests</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Rate Limit (per hour)</p>
                <p>{application.rate_limit_per_hour} requests</p>
              </div>
            </div>

            {application.webhook_url && (
              <div className="mt-4">
                <p className="text-sm text-muted-foreground">Webhook URL</p>
                <p className="font-mono text-sm">{application.webhook_url}</p>
              </div>
            )}

            {application.allowed_ips.length > 0 && (
              <div className="mt-4">
                <p className="text-sm text-muted-foreground">IP Whitelist</p>
                <p className="font-mono text-sm">{application.allowed_ips.join(', ')}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* API Keys Section */}
        <Tabs defaultValue="keys" className="space-y-6">
          <TabsList>
            <TabsTrigger value="keys">
              <Key className="h-4 w-4 mr-2" />
              API Keys
            </TabsTrigger>
            <TabsTrigger value="activity">
              <Activity className="h-4 w-4 mr-2" />
              Activity
            </TabsTrigger>
          </TabsList>

          <TabsContent value="keys" className="space-y-6">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-lg font-semibold">API Keys</h3>
                <p className="text-sm text-muted-foreground">
                  Manage API keys for this application
                </p>
              </div>

              <Dialog open={isCreateKeyDialogOpen} onOpenChange={setIsCreateKeyDialogOpen}>
                <Button onClick={() => setIsCreateKeyDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create API Key
                </Button>

                <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                  {!createdKey ? (
                    <>
                      <DialogHeader>
                        <DialogTitle>Create API Key</DialogTitle>
                        <DialogDescription>
                          Generate a new API key with custom scopes and expiration.
                        </DialogDescription>
                      </DialogHeader>

                      <form onSubmit={handleCreateKey} className="space-y-4">
                        <div className="space-y-2">
                          <Label htmlFor="key-name">Key Name*</Label>
                          <Input
                            id="key-name"
                            value={keyFormData.name}
                            onChange={(e) => setKeyFormData({ ...keyFormData, name: e.target.value })}
                            placeholder="Production Key"
                            required
                          />
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="expires">Expires In (days)</Label>
                          <Input
                            id="expires"
                            type="number"
                            min="1"
                            max="365"
                            value={keyFormData.expires_in_days || ''}
                            onChange={(e) =>
                              setKeyFormData({
                                ...keyFormData,
                                expires_in_days: e.target.value ? parseInt(e.target.value) : undefined,
                              })
                            }
                            placeholder="Leave empty for no expiration"
                          />
                        </div>

                        <div className="space-y-2">
                          <Label>Scopes*</Label>
                          <div className="border rounded-md p-4 space-y-2 max-h-[300px] overflow-y-auto">
                            {PLATFORM_SCOPES.map((scope) => (
                              <div key={scope.value} className="flex items-start space-x-2">
                                <Checkbox
                                  id={scope.value}
                                  checked={keyFormData.scopes.includes(scope.value)}
                                  onCheckedChange={() => handleToggleScope(scope.value)}
                                />
                                <div className="grid gap-1.5 leading-none">
                                  <label
                                    htmlFor={scope.value}
                                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                                  >
                                    {scope.label}
                                  </label>
                                  <p className="text-sm text-muted-foreground">
                                    {scope.description}
                                  </p>
                                </div>
                              </div>
                            ))}
                          </div>
                          {keyFormData.scopes.length === 0 && (
                            <p className="text-sm text-destructive">Please select at least one scope</p>
                          )}
                        </div>

                        <DialogFooter>
                          <Button type="button" variant="outline" onClick={handleCloseCreateKeyDialog}>
                            Cancel
                          </Button>
                          <Button type="submit" disabled={keyFormData.scopes.length === 0}>
                            Create Key
                          </Button>
                        </DialogFooter>
                      </form>
                    </>
                  ) : (
                    <>
                      <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                          <CheckCircle className="h-5 w-5 text-green-500" />
                          API Key Created
                        </DialogTitle>
                        <DialogDescription>
                          Save this key securely - you won't be able to see it again.
                        </DialogDescription>
                      </DialogHeader>

                      <div className="space-y-4">
                        <Alert>
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>
                            <strong>Important:</strong> Store this API key securely. It will only be shown once.
                          </AlertDescription>
                        </Alert>

                        <div className="space-y-2">
                          <Label>API Key</Label>
                          <div className="flex gap-2">
                            <Input
                              value={showFullKey ? createdKey.token : `${createdKey.token_prefix}${'*'.repeat(40)}`}
                              readOnly
                              className="font-mono text-sm"
                            />
                            <Button
                              type="button"
                              variant="outline"
                              onClick={() => setShowFullKey(!showFullKey)}
                            >
                              {showFullKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                            </Button>
                            <Button
                              type="button"
                              variant="outline"
                              onClick={() => handleCopyKey(createdKey.token)}
                            >
                              <Copy className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>

                        <div className="space-y-2">
                          <Label>Scopes</Label>
                          <div className="flex flex-wrap gap-2">
                            {createdKey.scopes.map((scope) => (
                              <Badge key={scope} variant="secondary">
                                {scope}
                              </Badge>
                            ))}
                          </div>
                        </div>

                        {createdKey.expires_at && (
                          <div className="space-y-2">
                            <Label>Expires</Label>
                            <Input value={formatDate(createdKey.expires_at)} readOnly />
                          </div>
                        )}
                      </div>

                      <DialogFooter>
                        <Button onClick={handleCloseCreateKeyDialog}>Done</Button>
                      </DialogFooter>
                    </>
                  )}
                </DialogContent>
              </Dialog>
            </div>

            {apiKeys.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center h-48">
                  <Key className="h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No API keys yet</p>
                  <Button onClick={() => setIsCreateKeyDialogOpen(true)} className="mt-4">
                    <Plus className="h-4 w-4 mr-2" />
                    Create First Key
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {apiKeys.map((key) => (
                  <Card key={key.id}>
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div>
                          <CardTitle className="flex items-center gap-2">
                            {key.name}
                            {key.is_active ? (
                              <Badge variant="default" className="bg-green-500">Active</Badge>
                            ) : (
                              <Badge variant="secondary">Revoked</Badge>
                            )}
                          </CardTitle>
                          <CardDescription className="mt-1 font-mono">
                            {key.token_prefix}{'*'.repeat(40)}
                          </CardDescription>
                        </div>
                        {key.is_active && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setKeyToRevoke(key)}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Revoke
                          </Button>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                        <div>
                          <p className="text-muted-foreground">Created</p>
                          <p>{formatDate(key.created_at)}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Last Used</p>
                          <p>{formatDate(key.last_used_at)}</p>
                        </div>
                        {key.expires_at && (
                          <div>
                            <p className="text-muted-foreground">Expires</p>
                            <p>{formatDate(key.expires_at)}</p>
                          </div>
                        )}
                      </div>

                      <div>
                        <p className="text-sm text-muted-foreground mb-2">Scopes:</p>
                        <div className="flex flex-wrap gap-2">
                          {key.scopes.map((scope) => (
                            <Badge key={scope} variant="secondary">
                              {scope}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="activity">
            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
                <CardDescription>View API usage and audit logs</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Activity logs coming soon...</p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Revoke Key Confirmation Dialog */}
        <Dialog open={!!keyToRevoke} onOpenChange={() => setKeyToRevoke(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Revoke API Key</DialogTitle>
              <DialogDescription>
                Are you sure you want to revoke this API key? This action cannot be undone.
              </DialogDescription>
            </DialogHeader>

            {keyToRevoke && (
              <div className="space-y-2">
                <p className="font-medium">{keyToRevoke.name}</p>
                <p className="text-sm text-muted-foreground font-mono">
                  {keyToRevoke.token_prefix}{'*'.repeat(40)}
                </p>
              </div>
            )}

            <DialogFooter>
              <Button variant="outline" onClick={() => setKeyToRevoke(null)}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleRevokeKey}>
                Revoke Key
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Edit Application Dialog */}
        <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Edit Application Settings</DialogTitle>
              <DialogDescription>
                Update application configuration and rate limits.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleUpdateApplication} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="edit-name">Application Name</Label>
                <Input
                  id="edit-name"
                  value={editFormData.name}
                  onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-description">Description</Label>
                <Textarea
                  id="edit-description"
                  value={editFormData.description}
                  onChange={(e) => setEditFormData({ ...editFormData, description: e.target.value })}
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-webhook">Webhook URL</Label>
                <Input
                  id="edit-webhook"
                  type="url"
                  value={editFormData.webhook_url}
                  onChange={(e) => setEditFormData({ ...editFormData, webhook_url: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-ips">Allowed IP Addresses</Label>
                <Input
                  id="edit-ips"
                  value={allowedIpsInput}
                  onChange={(e) => setAllowedIpsInput(e.target.value)}
                  placeholder="203.0.113.0/24, 198.51.100.42"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-rate-min">Rate Limit (per minute)</Label>
                  <Input
                    id="edit-rate-min"
                    type="number"
                    value={editFormData.rate_limit_per_minute}
                    onChange={(e) =>
                      setEditFormData({ ...editFormData, rate_limit_per_minute: parseInt(e.target.value) })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="edit-rate-hour">Rate Limit (per hour)</Label>
                  <Input
                    id="edit-rate-hour"
                    type="number"
                    value={editFormData.rate_limit_per_hour}
                    onChange={(e) =>
                      setEditFormData({ ...editFormData, rate_limit_per_hour: parseInt(e.target.value) })
                    }
                  />
                </div>
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsEditDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit">Save Changes</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </PageContent>
    </Page>
  );
}
