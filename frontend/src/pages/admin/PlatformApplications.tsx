/**
 * Platform Applications Management Page
 *
 * Allows super admins to view, create, and manage platform applications
 * that integrate with the Platform API.
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Key, Activity, AlertCircle, CheckCircle, XCircle } from 'lucide-react';
import { Page, PageHeader, PageContent } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { toast } from 'sonner';
import {
  listApplications,
  createApplication,
  copyToClipboard,
} from '@/services/platform.service';
import type {
  PlatformApplication,
  PlatformApplicationCreated,
  CreateApplicationRequest,
} from '@/services/platform.service';

export function PlatformApplications() {
  const navigate = useNavigate();
  const [applications, setApplications] = useState<PlatformApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [createdApp, setCreatedApp] = useState<PlatformApplicationCreated | null>(null);
  const [formData, setFormData] = useState<CreateApplicationRequest>({
    name: '',
    slug: '',
    description: '',
    webhook_url: '',
    allowed_ips: [],
    rate_limit_per_minute: 60,
    rate_limit_per_hour: 1000,
  });
  const [allowedIpsInput, setAllowedIpsInput] = useState('');

  useEffect(() => {
    loadApplications();
  }, []);

  const loadApplications = async () => {
    try {
      setLoading(true);
      const response = await listApplications({ limit: 100 });
      setApplications(response.applications);
    } catch (error) {
      toast.error('Failed to load applications', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateApplication = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const payload: CreateApplicationRequest = {
        ...formData,
        allowed_ips: allowedIpsInput
          ? allowedIpsInput.split(',').map(ip => ip.trim()).filter(Boolean)
          : [],
      };

      const result = await createApplication(payload);
      setCreatedApp(result);
      toast.success('Application created successfully');
      await loadApplications();
    } catch (error) {
      toast.error('Failed to create application', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  const handleCopyApiKey = async (apiKey: string) => {
    try {
      await copyToClipboard(apiKey);
      toast.success('API key copied to clipboard');
    } catch (error) {
      toast.error('Failed to copy API key');
    }
  };

  const handleCloseCreateDialog = () => {
    setIsCreateDialogOpen(false);
    setCreatedApp(null);
    setFormData({
      name: '',
      slug: '',
      description: '',
      webhook_url: '',
      allowed_ips: [],
      rate_limit_per_minute: 60,
      rate_limit_per_hour: 1000,
    });
    setAllowedIpsInput('');
  };

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Admin', href: '/admin' },
          { label: 'Platform Applications' },
        ]}
        title="Platform Applications"
        subtitle="Manage external applications that integrate with the Platform API"
      />

      <PageContent>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-2xl font-semibold">Applications</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {applications.length} {applications.length === 1 ? 'application' : 'applications'} registered
            </p>
          </div>

          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                New Application
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              {!createdApp ? (
                <>
                  <DialogHeader>
                    <DialogTitle>Create Platform Application</DialogTitle>
                    <DialogDescription>
                      Register a new application to integrate with the Platform API.
                      An initial API key will be generated automatically.
                    </DialogDescription>
                  </DialogHeader>

                  <form onSubmit={handleCreateApplication} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="name">Application Name*</Label>
                        <Input
                          id="name"
                          value={formData.name}
                          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                          placeholder="My Mobile App"
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="slug">Slug*</Label>
                        <Input
                          id="slug"
                          value={formData.slug}
                          onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                          placeholder="my-mobile-app"
                          pattern="^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$"
                          required
                        />
                        <p className="text-xs text-muted-foreground">
                          Lowercase letters, numbers, and hyphens only
                        </p>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="description">Description</Label>
                      <Textarea
                        id="description"
                        value={formData.description}
                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        placeholder="Describe the purpose of this application"
                        rows={3}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="webhook_url">Webhook URL (Optional)</Label>
                      <Input
                        id="webhook_url"
                        type="url"
                        value={formData.webhook_url}
                        onChange={(e) => setFormData({ ...formData, webhook_url: e.target.value })}
                        placeholder="https://example.com/webhooks/platform"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="allowed_ips">Allowed IP Addresses (Optional)</Label>
                      <Input
                        id="allowed_ips"
                        value={allowedIpsInput}
                        onChange={(e) => setAllowedIpsInput(e.target.value)}
                        placeholder="203.0.113.0/24, 198.51.100.42"
                      />
                      <p className="text-xs text-muted-foreground">
                        Comma-separated list of IPs or CIDR ranges. Leave empty to allow all IPs.
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="rate_limit_per_minute">Rate Limit (per minute)</Label>
                        <Input
                          id="rate_limit_per_minute"
                          type="number"
                          min="1"
                          max="10000"
                          value={formData.rate_limit_per_minute}
                          onChange={(e) =>
                            setFormData({ ...formData, rate_limit_per_minute: parseInt(e.target.value) })
                          }
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="rate_limit_per_hour">Rate Limit (per hour)</Label>
                        <Input
                          id="rate_limit_per_hour"
                          type="number"
                          min="1"
                          max="100000"
                          value={formData.rate_limit_per_hour}
                          onChange={(e) =>
                            setFormData({ ...formData, rate_limit_per_hour: parseInt(e.target.value) })
                          }
                          required
                        />
                      </div>
                    </div>

                    <DialogFooter>
                      <Button type="button" variant="outline" onClick={handleCloseCreateDialog}>
                        Cancel
                      </Button>
                      <Button type="submit">Create Application</Button>
                    </DialogFooter>
                  </form>
                </>
              ) : (
                <>
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <CheckCircle className="h-5 w-5 text-green-500" />
                      Application Created Successfully
                    </DialogTitle>
                    <DialogDescription>
                      Your application has been created. Save the API key below - it will only be shown once.
                    </DialogDescription>
                  </DialogHeader>

                  <div className="space-y-4">
                    <Alert>
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        <strong>Important:</strong> Store this API key securely. You won't be able to see it again.
                      </AlertDescription>
                    </Alert>

                    <div className="space-y-2">
                      <Label>Application Name</Label>
                      <Input value={createdApp.name} readOnly />
                    </div>

                    <div className="space-y-2">
                      <Label>Application Slug</Label>
                      <Input value={createdApp.slug} readOnly />
                    </div>

                    <div className="space-y-2">
                      <Label>Initial API Key</Label>
                      <div className="flex gap-2">
                        <Input
                          value={createdApp.initial_api_key}
                          readOnly
                          className="font-mono text-sm"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => handleCopyApiKey(createdApp.initial_api_key)}
                        >
                          Copy
                        </Button>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        This key has full access (*:*). You can create additional keys with limited scopes.
                      </p>
                    </div>
                  </div>

                  <DialogFooter>
                    <Button onClick={handleCloseCreateDialog}>Done</Button>
                  </DialogFooter>
                </>
              )}
            </DialogContent>
          </Dialog>
        </div>

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : applications.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center h-64">
              <Key className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No Applications Yet</h3>
              <p className="text-sm text-muted-foreground text-center mb-4">
                Create your first platform application to start integrating external apps.
              </p>
              <Button onClick={() => setIsCreateDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Application
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {applications.map((app) => (
              <Card
                key={app.id}
                className="hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => navigate(`/admin/platform/${app.id}`)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        {app.name}
                        {app.is_active ? (
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
                      <CardDescription className="mt-1">
                        {app.description || 'No description'}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>

                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Slug</p>
                      <p className="font-mono">{app.slug}</p>
                    </div>

                    <div>
                      <p className="text-muted-foreground">API Keys</p>
                      <p className="flex items-center gap-1">
                        <Key className="h-4 w-4" />
                        {app.api_key_count}
                      </p>
                    </div>

                    <div>
                      <p className="text-muted-foreground">Rate Limits</p>
                      <p className="flex items-center gap-1">
                        <Activity className="h-4 w-4" />
                        {app.rate_limit_per_minute}/min, {app.rate_limit_per_hour}/hr
                      </p>
                    </div>

                    <div>
                      <p className="text-muted-foreground">Created</p>
                      <p>{new Date(app.created_at).toLocaleDateString()}</p>
                    </div>
                  </div>

                  {app.allowed_ips && app.allowed_ips.length > 0 && (
                    <div className="mt-4 p-3 bg-muted rounded-md">
                      <p className="text-xs text-muted-foreground mb-1">IP Whitelist:</p>
                      <p className="text-sm font-mono">{app.allowed_ips.join(', ')}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </PageContent>
    </Page>
  );
}
