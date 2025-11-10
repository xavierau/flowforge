/**
 * ApiTokenList Component
 *
 * Displays a table of API tokens with actions to revoke them.
 * Uses shadcn/ui Table component for consistent styling.
 *
 * Design Principles:
 * - Single Responsibility: Only displays token list
 * - Composability: Receives tokens and callbacks as props
 * - No side effects: All data fetching done by parent
 */

import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { ApiToken } from '@/types/api-token';

interface ApiTokenListProps {
  tokens: ApiToken[];
  onRevoke: (tokenId: string) => Promise<void>;
}

export function ApiTokenList({ tokens, onRevoke }: ApiTokenListProps) {
  const [confirmingTokenId, setConfirmingTokenId] = useState<string | null>(null);
  const [isRevoking, setIsRevoking] = useState(false);

  const handleRevoke = async () => {
    if (!confirmingTokenId) return;

    setIsRevoking(true);
    try {
      await onRevoke(confirmingTokenId);
      setConfirmingTokenId(null);
    } catch (error) {
      // Error handled by parent
      console.error('Failed to revoke token:', error);
    } finally {
      setIsRevoking(false);
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const isExpired = (expiresAt: string | null) => {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
  };

  if (tokens.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-muted-foreground">No API tokens yet</p>
        <p className="text-sm text-muted-foreground mt-2">
          Create your first token to get started with the API
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Token</TableHead>
              <TableHead>Scopes</TableHead>
              <TableHead>Expires</TableHead>
              <TableHead>Last Used</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tokens.map((token) => {
              const expired = isExpired(token.expires_at);

              return (
                <TableRow key={token.token_id}>
                  <TableCell className="font-medium">{token.name}</TableCell>
                  <TableCell>
                    <code className="text-xs bg-muted px-2 py-1 rounded">
                      {token.token_prefix}...
                    </code>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {token.scopes.slice(0, 3).map((scope) => (
                        <Badge key={scope} variant="secondary" className="text-xs">
                          {scope}
                        </Badge>
                      ))}
                      {token.scopes.length > 3 && (
                        <Badge variant="secondary" className="text-xs">
                          +{token.scopes.length - 3} more
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {expired ? (
                      <span className="text-destructive">
                        Expired {formatDate(token.expires_at)}
                      </span>
                    ) : (
                      formatDate(token.expires_at)
                    )}
                  </TableCell>
                  <TableCell>{formatDate(token.last_used_at)}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setConfirmingTokenId(token.token_id)}
                      aria-label="Revoke token"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* Revoke Confirmation Dialog */}
      <Dialog
        open={confirmingTokenId !== null}
        onOpenChange={(open) => !open && setConfirmingTokenId(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Revoke API Token</DialogTitle>
            <DialogDescription>
              Are you sure you want to revoke this token? This action cannot be undone and
              any applications using this token will lose access immediately.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmingTokenId(null)}
              disabled={isRevoking}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleRevoke}
              disabled={isRevoking}
            >
              {isRevoking ? 'Revoking...' : 'Revoke Token'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
