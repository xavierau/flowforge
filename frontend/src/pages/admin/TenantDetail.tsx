/**
 * TenantDetail Page
 *
 * Detailed view of a single tenant with metrics and management.
 * Follows React best practices:
 * - Proper useEffect for data fetching with cleanup
 * - Separate states for different data sets
 * - Tab-based navigation for related data
 * - Loading and error states
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Page, PageHeader, PageContent } from '@/components/layout';
import { StatsCard } from '@/components/metrics/StatsCard';
import { AdminActionDialog } from '@/components/admin/AdminActionDialog';
import { AddCreditsDialog } from '@/components/admin/AddCreditsDialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  getTenantDetails,
  getTenantUsers,
  getTenantTokens,
  updateTenantStatus,
  AdminApiError,
} from '@/services/admin.service';
import type {
  TenantDetailResponse,
  UserListItem,
  ApiTokenListItem,
} from '@/types/admin';
import {
  AlertCircle,
  RefreshCw,
  FileText,
  CheckCircle2,
  Cpu,
  DollarSign,
  Users,
  Key,
  Ban,
  CheckCircle,
  Plus,
  Coins,
} from 'lucide-react';

type TabType = 'users' | 'tokens';

/**
 * TenantDetail Component
 *
 * Displays comprehensive tenant information with tabs for users and API tokens.
 */
export function TenantDetail() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const navigate = useNavigate();

  // Data state
  const [tenantDetails, setTenantDetails] = useState<TenantDetailResponse | null>(null);
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [tokens, setTokens] = useState<ApiTokenListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // UI state
  const [activeTab, setActiveTab] = useState<TabType>('users');
  const [actionDialog, setActionDialog] = useState({
    open: false,
    currentStatus: '',
  });
  const [addCreditsDialogOpen, setAddCreditsDialogOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  /**
   * Fetch tenant details, users, and tokens
   *
   * Dependencies: [tenantId] - refetch when tenant ID changes
   */
  useEffect(() => {
    if (!tenantId) return;

    let isCancelled = false;

    async function fetchData(id: string) {
      setIsLoading(true);
      setError(null);

      try {
        const [details, userList, tokenList] = await Promise.all([
          getTenantDetails(id),
          getTenantUsers(id),
          getTenantTokens(id),
        ]);

        if (!isCancelled) {
          setTenantDetails(details);
          setUsers(userList);
          setTokens(tokenList);
          setIsLoading(false);
        }
      } catch (err) {
        if (!isCancelled) {
          if (err instanceof AdminApiError) {
            setError(err.message);
          } else {
            setError('Failed to load tenant details');
          }
          setIsLoading(false);
        }
      }
    }

    fetchData(tenantId);

    return () => {
      isCancelled = true;
    };
  }, [tenantId]);

  /**
   * Refetch tenant data after credit addition
   */
  const refetchTenantData = async () => {
    if (!tenantId) return;

    try {
      const details = await getTenantDetails(tenantId);
      setTenantDetails(details);
    } catch (err) {
      if (err instanceof AdminApiError) {
        setError(err.message);
      } else {
        setError('Failed to refresh tenant details');
      }
    }
  };

  /**
   * Handle status update
   */
  async function handleConfirmStatusUpdate(reason?: string) {
    if (!tenantId || !tenantDetails) return;

    setIsProcessing(true);

    try {
      const newStatus =
        tenantDetails.tenant.status === 'active' ? 'suspended' : 'active';

      await updateTenantStatus(tenantId, newStatus, reason);

      // Refresh details
      const details = await getTenantDetails(tenantId);
      setTenantDetails(details);

      setActionDialog({ open: false, currentStatus: '' });
      setIsProcessing(false);
    } catch (err) {
      if (err instanceof AdminApiError) {
        setError(err.message);
      } else {
        setError('Failed to update tenant status');
      }
      setIsProcessing(false);
    }
  }

  /**
   * Format date for display
   */
  function formatDate(dateString: string | null): string {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  if (!tenantId) {
    navigate('/admin/tenants');
    return null;
  }

  if (isLoading) {
    return (
      <Page>
        <PageContent>
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Loading tenant details...</p>
            </div>
          </div>
        </PageContent>
      </Page>
    );
  }

  if (error || !tenantDetails) {
    return (
      <Page>
        <PageContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error || 'Tenant not found'}</AlertDescription>
          </Alert>
        </PageContent>
      </Page>
    );
  }

  const { tenant, metrics } = tenantDetails;

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Admin', href: '/admin' },
          { label: 'Tenants', href: '/admin/tenants' },
          { label: tenant.name },
        ]}
        title={tenant.name}
        subtitle={`Slug: ${tenant.slug}`}
      >
        <div className="flex items-center gap-2">
          {tenant.status === 'active' ? (
            <Badge variant="default">Active</Badge>
          ) : (
            <Badge variant="destructive">{tenant.status}</Badge>
          )}
          <Button
            variant={tenant.status === 'active' ? 'destructive' : 'default'}
            size="sm"
            onClick={() =>
              setActionDialog({ open: true, currentStatus: tenant.status })
            }
          >
            {tenant.status === 'active' ? (
              <>
                <Ban className="h-4 w-4 mr-2" />
                Suspend
              </>
            ) : (
              <>
                <CheckCircle className="h-4 w-4 mr-2" />
                Activate
              </>
            )}
          </Button>
        </div>
      </PageHeader>

      <PageContent>
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Tenant Info Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Tenant Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Plan</p>
                <p className="text-lg font-semibold">{tenant.subscription_plan}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Created</p>
                <p className="text-lg font-semibold">{formatDate(tenant.created_at)}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Last Activity</p>
                <p className="text-lg font-semibold">{formatDate(tenant.last_activity)}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Status</p>
                <p className="text-lg font-semibold capitalize">{tenant.status}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Credit Management Card */}
        <Card className="mb-6 border-blue-200 bg-blue-50">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Coins className="h-5 w-5 text-blue-600" />
                <CardTitle className="text-blue-900">Credit Balance</CardTitle>
              </div>
              <Button
                size="sm"
                onClick={() => setAddCreditsDialogOpen(true)}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Credits
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <p className="text-4xl font-bold text-blue-900">
                {tenant.credit_balance.toLocaleString()}
              </p>
              <p className="text-lg text-blue-700">credits</p>
            </div>
            <p className="text-sm text-blue-700 mt-2">
              {metrics.credits_consumed.toLocaleString()} credits consumed to date
            </p>
          </CardContent>
        </Card>

        {/* Add Credits Dialog */}
        <AddCreditsDialog
          open={addCreditsDialogOpen}
          onOpenChange={setAddCreditsDialogOpen}
          tenantId={tenantId}
          tenantName={tenant.name}
          currentBalance={tenant.credit_balance}
          onSuccess={refetchTenantData}
        />

        {/* Metrics */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
          <StatsCard
            title="Total Jobs"
            value={metrics.total_jobs}
            icon={FileText}
            format="number"
          />
          <StatsCard
            title="Completed Jobs"
            value={metrics.completed_jobs}
            icon={CheckCircle2}
            format="number"
          />
          <StatsCard
            title="Total Tokens"
            value={metrics.total_tokens}
            icon={Cpu}
            format="number"
          />
          <StatsCard
            title="Estimated Cost"
            value={metrics.estimated_cost}
            icon={DollarSign}
            format="currency"
          />
        </div>

        {/* Tabs */}
        <Card>
          <CardHeader>
            <div className="flex border-b">
              <button
                className={`px-4 py-2 font-medium ${
                  activeTab === 'users'
                    ? 'border-b-2 border-primary text-primary'
                    : 'text-muted-foreground'
                }`}
                onClick={() => setActiveTab('users')}
              >
                <Users className="h-4 w-4 inline mr-2" />
                Users ({users.length})
              </button>
              <button
                className={`px-4 py-2 font-medium ${
                  activeTab === 'tokens'
                    ? 'border-b-2 border-primary text-primary'
                    : 'text-muted-foreground'
                }`}
                onClick={() => setActiveTab('tokens')}
              >
                <Key className="h-4 w-4 inline mr-2" />
                API Tokens ({tokens.length})
              </button>
            </div>
          </CardHeader>
          <CardContent>
            {activeTab === 'users' && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Full Name</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Login</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell className="font-medium">{user.email}</TableCell>
                      <TableCell>{user.full_name || '-'}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{user.role_display_name}</Badge>
                      </TableCell>
                      <TableCell>
                        {user.is_active ? (
                          <Badge variant="default">Active</Badge>
                        ) : (
                          <Badge variant="destructive">Inactive</Badge>
                        )}
                      </TableCell>
                      <TableCell>{formatDate(user.last_login)}</TableCell>
                    </TableRow>
                  ))}
                  {users.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground">
                        No users found
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}

            {activeTab === 'tokens' && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Owner</TableHead>
                    <TableHead>Scopes</TableHead>
                    <TableHead>Last Used</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tokens.map((token) => (
                    <TableRow key={token.id}>
                      <TableCell className="font-medium">{token.name}</TableCell>
                      <TableCell>{token.user_email}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {token.scopes.slice(0, 3).map((scope) => (
                            <Badge key={scope} variant="outline" className="text-xs">
                              {scope}
                            </Badge>
                          ))}
                          {token.scopes.length > 3 && (
                            <Badge variant="outline" className="text-xs">
                              +{token.scopes.length - 3}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>{formatDate(token.last_used_at)}</TableCell>
                      <TableCell>
                        {token.is_active ? (
                          <Badge variant="default">Active</Badge>
                        ) : (
                          <Badge variant="destructive">Revoked</Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                  {tokens.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground">
                        No API tokens found
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </PageContent>

      {/* Status Update Dialog */}
      <AdminActionDialog
        open={actionDialog.open}
        onOpenChange={(open) => setActionDialog({ ...actionDialog, open })}
        title={tenant.status === 'active' ? 'Suspend Tenant' : 'Activate Tenant'}
        description={
          tenant.status === 'active'
            ? 'This will immediately suspend the tenant and prevent all users from accessing the system.'
            : 'This will activate the tenant and allow users to access the system.'
        }
        resourceName={tenant.name}
        onConfirm={handleConfirmStatusUpdate}
        isProcessing={isProcessing}
        variant={tenant.status === 'active' ? 'destructive' : 'default'}
      />
    </Page>
  );
}
