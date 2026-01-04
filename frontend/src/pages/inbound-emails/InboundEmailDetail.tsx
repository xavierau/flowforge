/**
 * InboundEmailDetail - Detail page for an inbound email address
 *
 * Features:
 * - Display address details (name, email, status, config)
 * - Statistics (emails received, documents processed)
 * - Processing logs table with pagination
 * - Actions: Edit, Activate/Deactivate
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Loader2,
  Pencil,
  Power,
  PowerOff,
  Mail,
  Copy,
  Check,
  RefreshCw,
  FileText,
  AlertCircle,
  Clock,
  CheckCircle,
  XCircle,
  Ban,
} from 'lucide-react';
import { toast } from 'sonner';

import { Page, PageHeader, PageContent } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import type {
  InboundEmailAddressResponse,
  InboundEmailLogResponse,
  InboundEmailLogStatus,
} from '@/types/inbound-email';
import {
  getInboundEmailLogStatusLabel,
  getInboundEmailLogStatusVariant,
} from '@/types/inbound-email';
import {
  getInboundEmailAddress,
  getInboundEmailLogs,
  updateInboundEmailAddress,
} from '@/services/inbound-email.service';
import { getSplitModeLabel, getExtractionModeLabel, SplitMode, ExtractionMode, isSplitMode, isExtractionMode } from '@/types/enums';

// ============================================================================
// HELPER COMPONENTS
// ============================================================================

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  description?: string;
}

function StatCard({ title, value, icon, description }: StatCardProps) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-primary/10 rounded-lg">{icon}</div>
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
            {description && <p className="text-xs text-muted-foreground">{description}</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function getStatusIcon(status: InboundEmailLogStatus) {
  switch (status) {
    case 'received':
      return <Clock className="h-4 w-4" />;
    case 'processing':
      return <Loader2 className="h-4 w-4 animate-spin" />;
    case 'processed':
      return <CheckCircle className="h-4 w-4" />;
    case 'failed':
      return <XCircle className="h-4 w-4" />;
    case 'rejected':
      return <Ban className="h-4 w-4" />;
    default:
      return <AlertCircle className="h-4 w-4" />;
  }
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function InboundEmailDetail() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  // State
  const [address, setAddress] = useState<InboundEmailAddressResponse | null>(null);
  const [logs, setLogs] = useState<InboundEmailLogResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingLogs, setIsLoadingLogs] = useState(true);
  const [isCopied, setIsCopied] = useState(false);
  const [isToggling, setIsToggling] = useState(false);

  // Pagination
  const [logsPage, setLogsPage] = useState(0);
  const [logsTotal, setLogsTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const LOGS_PER_PAGE = 10;

  // Load address details
  const loadAddress = useCallback(async () => {
    if (!id) return;

    try {
      setIsLoading(true);
      const data = await getInboundEmailAddress(id);
      setAddress(data);
    } catch (error) {
      toast.error('Failed to load inbound email address', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
      navigate('/inbound-emails');
    } finally {
      setIsLoading(false);
    }
  }, [id, navigate]);

  // Load logs
  const loadLogs = useCallback(async () => {
    if (!id) return;

    try {
      setIsLoadingLogs(true);
      const response = await getInboundEmailLogs(id, {
        status_filter: statusFilter || undefined,
        limit: LOGS_PER_PAGE,
        offset: logsPage * LOGS_PER_PAGE,
      });
      setLogs(response.logs);
      setLogsTotal(response.total);
    } catch (error) {
      toast.error('Failed to load email logs', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsLoadingLogs(false);
    }
  }, [id, logsPage, statusFilter]);

  // Initial load
  useEffect(() => {
    loadAddress();
  }, [loadAddress]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  // Copy email to clipboard
  const handleCopyEmail = async () => {
    if (!address) return;

    try {
      await navigator.clipboard.writeText(address.email_address);
      setIsCopied(true);
      toast.success('Email address copied to clipboard');
      setTimeout(() => setIsCopied(false), 2000);
    } catch {
      toast.error('Failed to copy email address');
    }
  };

  // Toggle active status
  const handleToggleActive = async () => {
    if (!address || !id) return;

    try {
      setIsToggling(true);
      await updateInboundEmailAddress(id, { is_active: !address.is_active });
      toast.success(address.is_active ? 'Address deactivated' : 'Address activated');
      await loadAddress();
    } catch (error) {
      toast.error('Failed to update status', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsToggling(false);
    }
  };

  // Format date
  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  // Calculate total pages
  const totalPages = Math.ceil(logsTotal / LOGS_PER_PAGE);

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

  if (!address) {
    return null;
  }

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Inbound Emails', href: '/inbound-emails' },
          { label: address.name },
        ]}
        title={
          <div className="flex items-center gap-3">
            <span>{address.name}</span>
            <Badge
              variant={address.is_active ? 'default' : 'secondary'}
              className={address.is_active ? 'bg-green-100 text-green-700' : ''}
            >
              {address.is_active ? 'Active' : 'Inactive'}
            </Badge>
          </div>
        }
        subtitle={address.description || 'Inbound email address for document processing'}
      />
      <PageContent>
        {/* Action Buttons */}
        <div className="flex gap-2 mb-6">
          <Button variant="outline" onClick={() => navigate('/inbound-emails')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <Button variant="outline" onClick={() => navigate(`/inbound-emails/${id}/edit`)}>
            <Pencil className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <Button
            variant="outline"
            onClick={handleToggleActive}
            disabled={isToggling}
          >
            {isToggling ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : address.is_active ? (
              <PowerOff className="mr-2 h-4 w-4" />
            ) : (
              <Power className="mr-2 h-4 w-4" />
            )}
            {address.is_active ? 'Deactivate' : 'Activate'}
          </Button>
        </div>

        {/* Email Address Card */}
        <Card className="mb-6">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-primary/10 rounded-lg">
                  <Mail className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Email Address</p>
                  <p className="text-xl font-mono">{address.email_address}</p>
                </div>
              </div>
              <Button variant="outline" onClick={handleCopyEmail}>
                {isCopied ? (
                  <Check className="mr-2 h-4 w-4" />
                ) : (
                  <Copy className="mr-2 h-4 w-4" />
                )}
                {isCopied ? 'Copied!' : 'Copy'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <StatCard
            title="Emails Received"
            value={address.emails_received_count.toLocaleString()}
            icon={<Mail className="h-5 w-5 text-primary" />}
          />
          <StatCard
            title="Documents Processed"
            value={address.documents_processed_count.toLocaleString()}
            icon={<FileText className="h-5 w-5 text-primary" />}
          />
          <StatCard
            title="Last Email"
            value={address.last_email_at ? 'Recent' : 'Never'}
            icon={<Clock className="h-5 w-5 text-primary" />}
            description={formatDate(address.last_email_at)}
          />
        </div>

        {/* Configuration */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
            <CardDescription>Processing settings for incoming emails</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Model Provider</p>
                <p className="font-medium capitalize">{address.model_provider}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Model Name</p>
                <p className="font-medium">{address.model_name}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Split Mode</p>
                <p className="font-medium">
                  {isSplitMode(address.split_mode)
                    ? getSplitModeLabel(address.split_mode as SplitMode)
                    : address.split_mode}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Extraction Mode</p>
                <p className="font-medium">
                  {isExtractionMode(address.extraction_mode)
                    ? getExtractionModeLabel(address.extraction_mode as ExtractionMode)
                    : address.extraction_mode}
                </p>
              </div>
            </div>

            {address.allowed_senders && address.allowed_senders.length > 0 && (
              <div className="mt-4">
                <p className="text-sm text-muted-foreground mb-2">Allowed Senders</p>
                <div className="flex flex-wrap gap-2">
                  {address.allowed_senders.map((sender) => (
                    <Badge key={sender} variant="outline">
                      {sender}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {address.callback_url && (
              <div className="mt-4">
                <p className="text-sm text-muted-foreground">Callback URL</p>
                <p className="font-mono text-sm break-all">{address.callback_url}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Email Logs */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Email Logs</CardTitle>
                <CardDescription>Recent emails processed by this address</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="All statuses" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All statuses</SelectItem>
                    <SelectItem value="received">Received</SelectItem>
                    <SelectItem value="processing">Processing</SelectItem>
                    <SelectItem value="processed">Processed</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                    <SelectItem value="rejected">Rejected</SelectItem>
                  </SelectContent>
                </Select>
                <Button variant="outline" size="icon" onClick={loadLogs} disabled={isLoadingLogs}>
                  <RefreshCw className={`h-4 w-4 ${isLoadingLogs ? 'animate-spin' : ''}`} />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isLoadingLogs && logs.length === 0 ? (
              <div className="flex items-center justify-center h-32">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : logs.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No email logs found. Emails sent to this address will appear here.
              </div>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Sender</TableHead>
                      <TableHead>Subject</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Attachments</TableHead>
                      <TableHead>Received</TableHead>
                      <TableHead>Links</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{log.sender_email}</p>
                            {log.sender_name && (
                              <p className="text-xs text-muted-foreground">{log.sender_name}</p>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="max-w-[200px] truncate">
                            {log.subject || '(No subject)'}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={getInboundEmailLogStatusVariant(log.status)}
                            className="gap-1"
                          >
                            {getStatusIcon(log.status)}
                            {getInboundEmailLogStatusLabel(log.status)}
                          </Badge>
                          {log.error_message && (
                            <p className="text-xs text-destructive mt-1 max-w-[150px] truncate">
                              {log.error_message}
                            </p>
                          )}
                        </TableCell>
                        <TableCell>
                          {log.attachment_count > 0 ? (
                            <div>
                              <Badge variant="outline">{log.attachment_count} files</Badge>
                              {log.attachment_names && log.attachment_names.length > 0 && (
                                <p className="text-xs text-muted-foreground mt-1 max-w-[150px] truncate">
                                  {log.attachment_names.join(', ')}
                                </p>
                              )}
                            </div>
                          ) : (
                            <span className="text-muted-foreground">None</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <span className="text-sm text-muted-foreground">
                            {formatDate(log.received_at)}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col gap-1">
                            {log.document_ids && log.document_ids.length > 0 && (
                              <span className="text-xs text-muted-foreground">
                                {log.document_ids.length} document(s)
                              </span>
                            )}
                            {log.extraction_job_ids && log.extraction_job_ids.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {log.extraction_job_ids.slice(0, 2).map((jobId) => (
                                  <Link
                                    key={jobId}
                                    to={`/jobs/${jobId}`}
                                    className="text-xs text-primary hover:underline"
                                  >
                                    Job {jobId.substring(0, 8)}...
                                  </Link>
                                ))}
                                {log.extraction_job_ids.length > 2 && (
                                  <span className="text-xs text-muted-foreground">
                                    +{log.extraction_job_ids.length - 2} more
                                  </span>
                                )}
                              </div>
                            )}
                            {(!log.document_ids || log.document_ids.length === 0) &&
                              (!log.extraction_job_ids || log.extraction_job_ids.length === 0) && (
                                <span className="text-xs text-muted-foreground">-</span>
                              )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-4">
                    <p className="text-sm text-muted-foreground">
                      Showing {logsPage * LOGS_PER_PAGE + 1} to{' '}
                      {Math.min((logsPage + 1) * LOGS_PER_PAGE, logsTotal)} of {logsTotal} entries
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setLogsPage((p) => Math.max(0, p - 1))}
                        disabled={logsPage === 0 || isLoadingLogs}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setLogsPage((p) => Math.min(totalPages - 1, p + 1))}
                        disabled={logsPage >= totalPages - 1 || isLoadingLogs}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </PageContent>
    </Page>
  );
}
