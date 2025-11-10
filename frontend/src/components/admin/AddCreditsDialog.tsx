/**
 * Add Credits Dialog Component
 *
 * Dialog for super admins to manually add credits to a tenant account.
 */

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, AlertCircle } from 'lucide-react';
import { addTenantCredits } from '@/services/admin.service';

interface AddCreditsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenantId: string;
  tenantName: string;
  currentBalance: number;
  onSuccess: () => void;
}

export function AddCreditsDialog({
  open,
  onOpenChange,
  tenantId,
  tenantName,
  currentBalance,
  onSuccess,
}: AddCreditsDialogProps) {
  const [amount, setAmount] = useState<string>('');
  const [reason, setReason] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    const amountNum = parseInt(amount, 10);
    if (!amount || isNaN(amountNum) || amountNum <= 0) {
      setError('Amount must be a positive number');
      return;
    }

    if (!reason.trim()) {
      setError('Reason is required');
      return;
    }

    try {
      setLoading(true);
      await addTenantCredits(tenantId, amountNum, reason.trim());

      // Reset form
      setAmount('');
      setReason('');
      setError(null);

      // Close dialog and notify parent
      onOpenChange(false);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add credits');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setAmount('');
    setReason('');
    setError(null);
    onOpenChange(false);
  };

  const predictedBalance = amount && !isNaN(parseInt(amount, 10))
    ? currentBalance + parseInt(amount, 10)
    : currentBalance;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add Credits</DialogTitle>
            <DialogDescription>
              Manually add credits to <strong>{tenantName}</strong>'s account
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Current Balance */}
            <div className="space-y-2">
              <Label>Current Balance</Label>
              <div className="text-2xl font-bold">{currentBalance.toLocaleString()} credits</div>
            </div>

            {/* Amount Input */}
            <div className="space-y-2">
              <Label htmlFor="amount">
                Amount to Add <span className="text-destructive">*</span>
              </Label>
              <Input
                id="amount"
                type="number"
                min="1"
                step="1"
                placeholder="e.g., 1000"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                disabled={loading}
                required
              />
              <p className="text-sm text-muted-foreground">
                Must be a positive integer
              </p>
            </div>

            {/* Predicted New Balance */}
            {amount && !isNaN(parseInt(amount, 10)) && parseInt(amount, 10) > 0 && (
              <div className="rounded-lg bg-muted p-3">
                <p className="text-sm text-muted-foreground">New Balance</p>
                <p className="text-xl font-semibold">{predictedBalance.toLocaleString()} credits</p>
              </div>
            )}

            {/* Reason Input */}
            <div className="space-y-2">
              <Label htmlFor="reason">
                Reason <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="reason"
                placeholder="e.g., Compensation for service downtime"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                disabled={loading}
                rows={3}
                maxLength={500}
                required
              />
              <p className="text-sm text-muted-foreground">
                {reason.length}/500 characters
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleCancel} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Adding...
                </>
              ) : (
                'Add Credits'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
