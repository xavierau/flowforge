/**
 * CreateTokenDialog Component
 *
 * Dialog for creating new API tokens with name, scopes, and expiration selection.
 *
 * Design Principles:
 * - Controlled component: Open state managed by parent
 * - Form validation: Ensures name and at least one scope selected
 * - No external side effects: Calls onSuccess callback with created token
 * - Proper cleanup: Resets form when dialog closes
 */

import { useState, useEffect } from 'react';
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
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { AVAILABLE_SCOPES, EXPIRATION_OPTIONS } from '@/types/api-token';
import type { ApiTokenCreateRequest } from '@/types/api-token';

interface CreateTokenDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: ApiTokenCreateRequest) => Promise<void>;
  userPermissions: string[]; // User's actual permissions to filter available scopes
}

export function CreateTokenDialog({
  open,
  onOpenChange,
  onSubmit,
  userPermissions,
}: CreateTokenDialogProps) {
  const [name, setName] = useState('');
  const [selectedScopes, setSelectedScopes] = useState<string[]>([]);
  const [expiresInDays, setExpiresInDays] = useState<number | null>(30);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      setName('');
      setSelectedScopes([]);
      setExpiresInDays(30);
      setError(null);
    }
  }, [open]);

  const handleScopeToggle = (scope: string) => {
    setSelectedScopes((prev) =>
      prev.includes(scope)
        ? prev.filter((s) => s !== scope)
        : [...prev, scope]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!name.trim()) {
      setError('Token name is required');
      return;
    }

    if (selectedScopes.length === 0) {
      setError('At least one scope must be selected');
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit({
        name: name.trim(),
        scopes: selectedScopes,
        expires_in_days: expiresInDays,
      });
      // Parent will handle closing and showing success
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create token');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Filter scopes to only those the user has permission for
  // CRITICAL SECURITY: Users can only create tokens with scopes they have permission for
  const allowedScopes = AVAILABLE_SCOPES.filter((scope) =>
    userPermissions.includes(scope.value)
  );

  // Group allowed scopes by category
  const scopesByGroup = allowedScopes.reduce((acc, scope) => {
    if (!acc[scope.group]) {
      acc[scope.group] = [];
    }
    acc[scope.group].push(scope);
    return acc;
  }, {} as Record<string, typeof AVAILABLE_SCOPES>);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Create API Token</DialogTitle>
          <DialogDescription>
            Create a new API token to authenticate your applications and scripts.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="space-y-6 py-4">
            {/* Token Name */}
            <div className="space-y-2">
              <Label htmlFor="token-name">Token Name</Label>
              <Input
                id="token-name"
                placeholder="e.g., Production API Key"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={isSubmitting}
                required
              />
              <p className="text-xs text-muted-foreground">
                A descriptive name to help you identify this token later.
              </p>
            </div>

            {/* Scopes */}
            <div className="space-y-2">
              <Label>Scopes</Label>
              <p className="text-xs text-muted-foreground mb-3">
                Select the permissions this token will have. Only scopes you have permission for are shown. Choose only what's needed.
              </p>
              {allowedScopes.length === 0 ? (
                <div className="border rounded-lg p-4 bg-muted/50 text-center">
                  <p className="text-sm text-muted-foreground">
                    You don't have any permissions to grant to API tokens. Please contact your administrator.
                  </p>
                </div>
              ) : (
                <div className="space-y-4 border rounded-lg p-4 max-h-[300px] overflow-y-auto">
                {Object.entries(scopesByGroup).map(([group, scopes]) => (
                  <div key={group} className="space-y-2">
                    <h4 className="font-medium text-sm">{group}</h4>
                    <div className="space-y-2 ml-4">
                      {scopes.map((scope) => (
                        <div key={scope.value} className="flex items-center space-x-2">
                          <Checkbox
                            id={scope.value}
                            checked={selectedScopes.includes(scope.value)}
                            onCheckedChange={() => handleScopeToggle(scope.value)}
                            disabled={isSubmitting}
                          />
                          <label
                            htmlFor={scope.value}
                            className="text-sm font-normal leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                          >
                            {scope.label}
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
                </div>
              )}
            </div>

            {/* Expiration */}
            <div className="space-y-2">
              <Label htmlFor="expiration">Expiration</Label>
              <Select
                value={expiresInDays?.toString() ?? 'null'}
                onValueChange={(value) =>
                  setExpiresInDays(value === 'null' ? null : parseInt(value))
                }
                disabled={isSubmitting}
              >
                <SelectTrigger id="expiration">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EXPIRATION_OPTIONS.map((option) => (
                    <SelectItem
                      key={option.value?.toString() ?? 'null'}
                      value={option.value?.toString() ?? 'null'}
                    >
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                The token will expire after this period. Tokens that never expire should be
                used with caution.
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md text-sm">
                {error}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || allowedScopes.length === 0}>
              {isSubmitting ? 'Creating...' : 'Create Token'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
