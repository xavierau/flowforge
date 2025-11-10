/**
 * AdminActionDialog Component
 *
 * Confirmation dialog for destructive admin actions.
 * Follows React best practices:
 * - Controlled component pattern
 * - Single responsibility (confirmation UI)
 * - Proper event handling
 * - Accessible dialog with reason input
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
import { AlertCircle } from 'lucide-react';

interface AdminActionDialogProps {
  /**
   * Whether the dialog is open
   */
  open: boolean;

  /**
   * Callback when dialog should close
   */
  onOpenChange: (open: boolean) => void;

  /**
   * Action being confirmed (e.g., "Suspend Tenant", "Deactivate User")
   */
  title: string;

  /**
   * Description of the action and its consequences
   */
  description: string;

  /**
   * Name of the resource being acted upon (e.g., tenant name, user email)
   */
  resourceName: string;

  /**
   * Callback when action is confirmed
   * @param reason - Optional reason provided by admin
   */
  onConfirm: (reason?: string) => void | Promise<void>;

  /**
   * Whether the action is currently processing
   */
  isProcessing?: boolean;

  /**
   * Variant for the confirm button
   * @default 'destructive'
   */
  variant?: 'default' | 'destructive';
}

/**
 * AdminActionDialog Component
 *
 * Displays a confirmation dialog for admin actions with optional reason input.
 *
 * @example
 * ```tsx
 * <AdminActionDialog
 *   open={isDialogOpen}
 *   onOpenChange={setIsDialogOpen}
 *   title="Suspend Tenant"
 *   description="This will immediately suspend the tenant and prevent all users from accessing the system."
 *   resourceName="Acme Corp"
 *   onConfirm={handleSuspend}
 *   isProcessing={isSuspending}
 *   variant="destructive"
 * />
 * ```
 */
export function AdminActionDialog({
  open,
  onOpenChange,
  title,
  description,
  resourceName,
  onConfirm,
  isProcessing = false,
  variant = 'destructive',
}: AdminActionDialogProps) {
  const [reason, setReason] = useState('');

  /**
   * Handle confirm action
   * Clears reason and calls onConfirm
   */
  async function handleConfirm() {
    await onConfirm(reason || undefined);
    setReason(''); // Clear reason after action
  }

  /**
   * Handle cancel action
   * Clears reason and closes dialog
   */
  function handleCancel() {
    setReason('');
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-destructive" />
            {title}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        {/* Resource Name Display */}
        <div className="py-4">
          <div className="rounded-lg bg-muted p-4">
            <p className="text-sm font-medium text-foreground">
              Target: <span className="font-bold">{resourceName}</span>
            </p>
          </div>
        </div>

        {/* Reason Input */}
        <div className="space-y-2">
          <Label htmlFor="reason">Reason (Optional)</Label>
          <Input
            id="reason"
            placeholder="Enter reason for this action..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            disabled={isProcessing}
          />
          <p className="text-xs text-muted-foreground">
            This reason will be logged in the audit trail.
          </p>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={isProcessing}
          >
            Cancel
          </Button>
          <Button
            variant={variant}
            onClick={handleConfirm}
            disabled={isProcessing}
          >
            {isProcessing ? 'Processing...' : 'Confirm'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
