/**
 * PricingManagement Page
 *
 * Admin page for managing model pricing.
 * Follows React best practices:
 * - Proper useEffect for data fetching with cleanup
 * - Separate states for different data sets
 * - Loading and error states
 * - Form validation
 */

import { useState, useEffect, useCallback } from 'react';
import { Page, PageHeader, PageContent } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  listPricing,
  createPricing,
  getPricingHistory,
  deactivatePricing,
  getSupportedModels,
  PricingApiError,
} from '@/services/pricing.service';
import type {
  ModelPricing,
  ModelPricingHistoryResponse,
  CreateModelPricingRequest,
} from '@/types/pricing';
import { getPricingStatus, type PricingStatus } from '@/types/pricing';
import {
  AlertCircle,
  RefreshCw,
  Plus,
  DollarSign,
  History,
  Ban,
  Loader2,
} from 'lucide-react';

/**
 * Format currency value for display
 */
function formatPrice(value: number): string {
  return `$${value.toFixed(4)}`;
}

/**
 * Format date for display
 */
function formatDate(dateString: string | null): string {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format date for datetime-local input
 */
function formatDateForInput(date: Date): string {
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/**
 * Get badge variant based on pricing status
 */
function getStatusBadge(status: PricingStatus): {
  variant: 'default' | 'secondary' | 'destructive' | 'outline';
  label: string;
} {
  switch (status) {
    case 'current':
      return { variant: 'default', label: 'Current' };
    case 'future':
      return { variant: 'secondary', label: 'Future' };
    case 'superseded':
      return { variant: 'outline', label: 'Superseded' };
    case 'deactivated':
      return { variant: 'destructive', label: 'Deactivated' };
  }
}

/**
 * PricingManagement Component
 *
 * Displays model pricing table with CRUD operations.
 */
export function PricingManagement() {
  // Data state
  const [pricingList, setPricingList] = useState<ModelPricing[]>([]);
  const [supportedModels, setSupportedModels] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [historyDialogOpen, setHistoryDialogOpen] = useState(false);
  const [deactivateDialogOpen, setDeactivateDialogOpen] = useState(false);

  // Form states
  const [formData, setFormData] = useState<CreateModelPricingRequest>({
    model_name: '',
    input_price_per_million: 0,
    output_price_per_million: 0,
    effective_from: '',
    notes: '',
  });
  const [customModelName, setCustomModelName] = useState('');
  const [useCustomModel, setUseCustomModel] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // History dialog state
  const [historyData, setHistoryData] = useState<ModelPricingHistoryResponse | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Deactivate dialog state
  const [selectedPricing, setSelectedPricing] = useState<ModelPricing | null>(null);
  const [deactivateReason, setDeactivateReason] = useState('');
  const [isDeactivating, setIsDeactivating] = useState(false);

  /**
   * Fetch pricing list and supported models
   */
  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [pricingResponse, modelsResponse] = await Promise.all([
        listPricing(),
        getSupportedModels(),
      ]);

      setPricingList(pricingResponse.pricing);
      setSupportedModels(modelsResponse);
    } catch (err) {
      if (err instanceof PricingApiError) {
        setError(err.message);
      } else {
        setError('Failed to load pricing data');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Initial data fetch
   */
  useEffect(() => {
    let isCancelled = false;

    async function loadData() {
      setIsLoading(true);
      setError(null);

      try {
        const [pricingResponse, modelsResponse] = await Promise.all([
          listPricing(),
          getSupportedModels(),
        ]);

        if (!isCancelled) {
          setPricingList(pricingResponse.pricing);
          setSupportedModels(modelsResponse);
          setIsLoading(false);
        }
      } catch (err) {
        if (!isCancelled) {
          if (err instanceof PricingApiError) {
            setError(err.message);
          } else {
            setError('Failed to load pricing data');
          }
          setIsLoading(false);
        }
      }
    }

    loadData();

    return () => {
      isCancelled = true;
    };
  }, []);

  /**
   * Reset form data
   */
  function resetForm() {
    setFormData({
      model_name: '',
      input_price_per_million: 0,
      output_price_per_million: 0,
      effective_from: '',
      notes: '',
    });
    setCustomModelName('');
    setUseCustomModel(false);
    setFormError(null);
  }

  /**
   * Handle create pricing submission
   */
  async function handleCreatePricing() {
    setFormError(null);

    // Validation
    const modelName = useCustomModel ? customModelName.trim() : formData.model_name;
    if (!modelName) {
      setFormError('Please select or enter a model name');
      return;
    }

    if (formData.input_price_per_million < 0) {
      setFormError('Input price must be non-negative');
      return;
    }

    if (formData.output_price_per_million < 0) {
      setFormError('Output price must be non-negative');
      return;
    }

    setIsSubmitting(true);

    try {
      const requestData: CreateModelPricingRequest = {
        model_name: modelName,
        input_price_per_million: formData.input_price_per_million,
        output_price_per_million: formData.output_price_per_million,
      };

      if (formData.effective_from) {
        requestData.effective_from = new Date(formData.effective_from).toISOString();
      }

      if (formData.notes?.trim()) {
        requestData.notes = formData.notes.trim();
      }

      await createPricing(requestData);

      // Refresh data and close dialog
      await fetchData();
      setCreateDialogOpen(false);
      resetForm();
    } catch (err) {
      if (err instanceof PricingApiError) {
        setFormError(err.message);
      } else {
        setFormError('Failed to create pricing');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  /**
   * Handle view history
   */
  async function handleViewHistory(modelName: string) {
    setHistoryDialogOpen(true);
    setIsLoadingHistory(true);
    setHistoryData(null);

    try {
      const response = await getPricingHistory(modelName);
      setHistoryData(response);
    } catch (err) {
      if (err instanceof PricingApiError) {
        setError(err.message);
      } else {
        setError('Failed to load pricing history');
      }
      setHistoryDialogOpen(false);
    } finally {
      setIsLoadingHistory(false);
    }
  }

  /**
   * Handle deactivate pricing
   */
  async function handleDeactivatePricing() {
    if (!selectedPricing || !deactivateReason.trim()) {
      return;
    }

    setIsDeactivating(true);

    try {
      await deactivatePricing(selectedPricing.id, deactivateReason.trim());

      // Refresh data and close dialog
      await fetchData();
      setDeactivateDialogOpen(false);
      setSelectedPricing(null);
      setDeactivateReason('');
    } catch (err) {
      if (err instanceof PricingApiError) {
        setError(err.message);
      } else {
        setError('Failed to deactivate pricing');
      }
    } finally {
      setIsDeactivating(false);
    }
  }

  /**
   * Open deactivate dialog
   */
  function openDeactivateDialog(pricing: ModelPricing) {
    setSelectedPricing(pricing);
    setDeactivateReason('');
    setDeactivateDialogOpen(true);
  }

  /**
   * Group pricing by model for display
   */
  const pricingByModel = pricingList.reduce(
    (acc, pricing) => {
      if (!acc[pricing.model_name]) {
        acc[pricing.model_name] = [];
      }
      acc[pricing.model_name].push(pricing);
      return acc;
    },
    {} as Record<string, ModelPricing[]>
  );

  // Get unique models that have current pricing
  const modelsWithCurrentPricing = Object.keys(pricingByModel).filter((model) =>
    pricingByModel[model].some((p) => getPricingStatus(p) === 'current')
  );

  if (isLoading) {
    return (
      <Page>
        <PageContent>
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Loading pricing data...</p>
            </div>
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
          { label: 'Pricing Management' },
        ]}
        title="Model Pricing Management"
        subtitle={`${modelsWithCurrentPricing.length} models with active pricing`}
      >
        <div className="flex items-center gap-2">
          <Button onClick={() => fetchData()} variant="outline" size="sm">
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            onClick={() => {
              resetForm();
              setCreateDialogOpen(true);
            }}
            size="sm"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Pricing
          </Button>
        </div>
      </PageHeader>

      <PageContent>
        {/* Error Alert */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Summary Card */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-primary" />
              <CardTitle>Pricing Overview</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Models with Pricing
                </p>
                <p className="text-2xl font-bold">{modelsWithCurrentPricing.length}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Total Pricing Records
                </p>
                <p className="text-2xl font-bold">{pricingList.length}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Supported Models
                </p>
                <p className="text-2xl font-bold">{supportedModels.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Pricing Table */}
        <Card>
          <CardHeader>
            <CardTitle>Model Pricing</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model</TableHead>
                  <TableHead className="text-right">Input Price</TableHead>
                  <TableHead className="text-right">Output Price</TableHead>
                  <TableHead>Effective From</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created By</TableHead>
                  <TableHead>Notes</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pricingList.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={8}
                      className="text-center text-muted-foreground py-8"
                    >
                      No pricing records found. Click "Add Pricing" to create one.
                    </TableCell>
                  </TableRow>
                ) : (
                  pricingList.map((pricing) => {
                    const status = getPricingStatus(pricing);
                    const statusBadge = getStatusBadge(status);

                    return (
                      <TableRow
                        key={pricing.id}
                        className={status === 'deactivated' ? 'opacity-60' : ''}
                      >
                        <TableCell className="font-medium">
                          {pricing.model_name}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {formatPrice(pricing.input_price_per_million)}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {formatPrice(pricing.output_price_per_million)}
                        </TableCell>
                        <TableCell>{formatDate(pricing.effective_from)}</TableCell>
                        <TableCell>
                          <Badge variant={statusBadge.variant}>{statusBadge.label}</Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {pricing.created_by_email}
                        </TableCell>
                        <TableCell className="max-w-[200px] truncate text-sm text-muted-foreground">
                          {pricing.notes || '-'}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleViewHistory(pricing.model_name)}
                              title="View history"
                            >
                              <History className="h-4 w-4" />
                            </Button>
                            {status === 'current' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openDeactivateDialog(pricing)}
                                title="Deactivate"
                                className="text-destructive hover:text-destructive"
                              >
                                <Ban className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </PageContent>

      {/* Create Pricing Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Add Model Pricing</DialogTitle>
            <DialogDescription>
              Create a new pricing configuration for a model. If pricing already exists
              for this model, the new pricing will supersede the old one.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {formError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}

            {/* Model Selection */}
            <div className="grid gap-2">
              <Label htmlFor="model_name">Model Name</Label>
              {!useCustomModel ? (
                <div className="flex gap-2">
                  <Select
                    value={formData.model_name}
                    onValueChange={(value) =>
                      setFormData({ ...formData, model_name: value })
                    }
                  >
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder="Select a model" />
                    </SelectTrigger>
                    <SelectContent>
                      {supportedModels.map((model) => (
                        <SelectItem key={model} value={model}>
                          {model}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setUseCustomModel(true)}
                  >
                    Custom
                  </Button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <Input
                    id="custom_model"
                    value={customModelName}
                    onChange={(e) => setCustomModelName(e.target.value)}
                    placeholder="Enter custom model name"
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setUseCustomModel(false);
                      setCustomModelName('');
                    }}
                  >
                    Select
                  </Button>
                </div>
              )}
            </div>

            {/* Input Price */}
            <div className="grid gap-2">
              <Label htmlFor="input_price">Input Price (per million tokens)</Label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                  $
                </span>
                <Input
                  id="input_price"
                  type="number"
                  step="0.0001"
                  min="0"
                  value={formData.input_price_per_million}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      input_price_per_million: parseFloat(e.target.value) || 0,
                    })
                  }
                  className="pl-7"
                />
              </div>
            </div>

            {/* Output Price */}
            <div className="grid gap-2">
              <Label htmlFor="output_price">Output Price (per million tokens)</Label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                  $
                </span>
                <Input
                  id="output_price"
                  type="number"
                  step="0.0001"
                  min="0"
                  value={formData.output_price_per_million}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      output_price_per_million: parseFloat(e.target.value) || 0,
                    })
                  }
                  className="pl-7"
                />
              </div>
            </div>

            {/* Effective From */}
            <div className="grid gap-2">
              <Label htmlFor="effective_from">
                Effective From (optional, defaults to now)
              </Label>
              <Input
                id="effective_from"
                type="datetime-local"
                value={formData.effective_from}
                onChange={(e) =>
                  setFormData({ ...formData, effective_from: e.target.value })
                }
                min={formatDateForInput(new Date())}
              />
            </div>

            {/* Notes */}
            <div className="grid gap-2">
              <Label htmlFor="notes">Notes (optional)</Label>
              <Textarea
                id="notes"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Add any notes about this pricing..."
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setCreateDialogOpen(false);
                resetForm();
              }}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button onClick={handleCreatePricing} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Pricing
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* History Dialog */}
      <Dialog open={historyDialogOpen} onOpenChange={setHistoryDialogOpen}>
        <DialogContent className="sm:max-w-[700px]">
          <DialogHeader>
            <DialogTitle>
              Pricing History: {historyData?.model_name || 'Loading...'}
            </DialogTitle>
            <DialogDescription>
              View all pricing records for this model, including superseded and deactivated
              entries.
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            {isLoadingHistory ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : historyData ? (
              <div className="space-y-4">
                {/* Current Pricing */}
                {historyData.current_pricing && (
                  <div className="p-4 border rounded-lg bg-primary/5">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="default">Current</Badge>
                      <span className="text-sm text-muted-foreground">
                        Active since {formatDate(historyData.current_pricing.effective_from)}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-muted-foreground">Input Price</p>
                        <p className="font-mono text-lg">
                          {formatPrice(historyData.current_pricing.input_price_per_million)}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Output Price</p>
                        <p className="font-mono text-lg">
                          {formatPrice(historyData.current_pricing.output_price_per_million)}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* History Table */}
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Effective From</TableHead>
                      <TableHead>Effective Until</TableHead>
                      <TableHead className="text-right">Input</TableHead>
                      <TableHead className="text-right">Output</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {historyData.history.map((pricing) => {
                      const status = getPricingStatus(pricing);
                      const statusBadge = getStatusBadge(status);

                      return (
                        <TableRow key={pricing.id}>
                          <TableCell>{formatDate(pricing.effective_from)}</TableCell>
                          <TableCell>{formatDate(pricing.effective_until)}</TableCell>
                          <TableCell className="text-right font-mono">
                            {formatPrice(pricing.input_price_per_million)}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {formatPrice(pricing.output_price_per_million)}
                          </TableCell>
                          <TableCell>
                            <Badge variant={statusBadge.variant}>{statusBadge.label}</Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <p className="text-center text-muted-foreground">No history available</p>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setHistoryDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Deactivate Dialog */}
      <Dialog open={deactivateDialogOpen} onOpenChange={setDeactivateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Deactivate Pricing</DialogTitle>
            <DialogDescription>
              Are you sure you want to deactivate pricing for{' '}
              <strong>{selectedPricing?.model_name}</strong>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <div className="grid gap-2">
              <Label htmlFor="deactivate_reason">Reason for deactivation</Label>
              <Textarea
                id="deactivate_reason"
                value={deactivateReason}
                onChange={(e) => setDeactivateReason(e.target.value)}
                placeholder="Please provide a reason for deactivating this pricing..."
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setDeactivateDialogOpen(false);
                setSelectedPricing(null);
                setDeactivateReason('');
              }}
              disabled={isDeactivating}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeactivatePricing}
              disabled={isDeactivating || !deactivateReason.trim()}
            >
              {isDeactivating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Deactivate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Page>
  );
}
