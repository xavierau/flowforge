/**
 * TokenCreatedDialog Component
 *
 * Shows the newly created token exactly once with copy functionality and usage example.
 * Critical security UX: This is the ONLY time the full token is shown.
 *
 * Design Principles:
 * - Single purpose: Display token and guide user to save it
 * - Security-first: Clear warnings that token won't be shown again
 * - User-friendly: Copy button with visual feedback
 * - No state persistence: Token is not stored anywhere
 */

import { useState } from 'react';
import { Check, Copy, AlertTriangle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface TokenCreatedDialogProps {
  token: string;
  tokenName: string;
  open: boolean;
  onClose: () => void;
}

export function TokenCreatedDialog({
  token,
  tokenName,
  open,
  onClose,
}: TokenCreatedDialogProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(token);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy token:', err);
    }
  };

  const usageExample = `curl -X POST https://api.example.com/v1/documents/upload \\
  -H "Authorization: Bearer ${token}" \\
  -F "file=@document.pdf"`;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>API Token Created Successfully</DialogTitle>
          <DialogDescription>
            Your token "{tokenName}" has been created.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Security Warning */}
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              <strong>Important:</strong> Save this token now! For security reasons, it won't
              be shown again. If you lose it, you'll need to create a new token.
            </AlertDescription>
          </Alert>

          {/* Token Display */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">Your API Token</label>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopy}
                className="gap-2"
              >
                {copied ? (
                  <>
                    <Check className="h-4 w-4" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4" />
                    Copy Token
                  </>
                )}
              </Button>
            </div>
            <div className="relative">
              <code className="block w-full bg-muted p-4 rounded-md text-sm font-mono break-all">
                {token}
              </code>
            </div>
          </div>

          {/* Usage Example */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Usage Example</label>
            <pre className="bg-muted p-4 rounded-md text-xs overflow-x-auto">
              <code>{usageExample}</code>
            </pre>
            <p className="text-xs text-muted-foreground">
              Include the token in the Authorization header of your API requests using the
              Bearer scheme.
            </p>
          </div>

          {/* Best Practices */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Best Practices</label>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>Store the token securely (e.g., in environment variables)</li>
              <li>Never commit the token to version control</li>
              <li>Use different tokens for different environments</li>
              <li>Revoke tokens immediately if compromised</li>
              <li>Rotate tokens regularly for enhanced security</li>
            </ul>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={onClose} className="w-full sm:w-auto">
            I've Saved My Token
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
