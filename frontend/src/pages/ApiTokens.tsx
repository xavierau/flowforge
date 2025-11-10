/**
 * ApiTokens Page
 *
 * Main page for API token management. Users can create, view, and revoke API tokens.
 *
 * Design Principles:
 * - Component Composition: Uses Page/PageHeader/PageContent layout
 * - State Management: Local state for tokens and dialog visibility
 * - Effect Management: Proper useEffect for data fetching with cleanup
 * - Error Handling: User-friendly error messages with toast notifications
 */

import { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';
import { toast } from 'sonner';
import { Page, PageHeader, PageContent } from '@/components/layout';
import { Button } from '@/components/ui/button';
import {
  ApiTokenList,
  CreateTokenDialog,
  TokenCreatedDialog,
} from '@/components/api-tokens';
import { apiTokenService } from '@/services/api-token.service';
import { getCurrentUser } from '@/services/user.service';
import type { ApiToken, ApiTokenCreateRequest, ApiTokenCreateResponse } from '@/types/api-token';

export function ApiTokens() {
  const [tokens, setTokens] = useState<ApiToken[]>([]);
  const [userPermissions, setUserPermissions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createdToken, setCreatedToken] = useState<ApiTokenCreateResponse | null>(null);

  // Fetch tokens and user permissions on mount
  useEffect(() => {
    let isMounted = true;

    const fetchData = async () => {
      try {
        // Fetch both tokens and user profile in parallel
        const [tokensData, userProfile] = await Promise.all([
          apiTokenService.listTokens(),
          getCurrentUser(),
        ]);

        if (isMounted) {
          setTokens(tokensData);
          setUserPermissions(userProfile.permissions);
        }
      } catch (error) {
        if (isMounted) {
          console.error('Failed to load data:', error);
          toast.error('Failed to load API tokens');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchData();

    // Cleanup function
    return () => {
      isMounted = false;
    };
  }, []);

  const handleCreateToken = async (data: ApiTokenCreateRequest) => {
    try {
      const newToken = await apiTokenService.createToken(data);

      // Close create dialog
      setCreateDialogOpen(false);

      // Show the created token dialog
      setCreatedToken(newToken);

      // Add to tokens list (without the full token)
      setTokens((prev) => [
        {
          token_id: newToken.token_id,
          name: newToken.name,
          token_prefix: newToken.token_prefix,
          scopes: newToken.scopes,
          expires_at: newToken.expires_at,
          last_used_at: null,
          created_at: newToken.created_at,
        },
        ...prev,
      ]);

      toast.success('API token created successfully');
    } catch (error) {
      // Error is handled in CreateTokenDialog
      throw error;
    }
  };

  const handleRevokeToken = async (tokenId: string) => {
    try {
      await apiTokenService.revokeToken(tokenId);

      // Remove from list
      setTokens((prev) => prev.filter((t) => t.token_id !== tokenId));

      toast.success('API token revoked successfully');
    } catch (error) {
      console.error('Failed to revoke token:', error);
      toast.error('Failed to revoke token');
      throw error;
    }
  };

  const handleCloseCreatedDialog = () => {
    setCreatedToken(null);
  };

  return (
    <Page>
      <div className="flex items-start justify-between">
        <PageHeader
          breadcrumbs={[
            { label: 'Dashboard', href: '/dashboard' },
            { label: 'API Tokens' },
          ]}
          title="API Tokens"
          subtitle="Manage API tokens for programmatic access to your account"
        />
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create Token
        </Button>
      </div>

      <PageContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-muted-foreground">Loading tokens...</div>
          </div>
        ) : (
          <ApiTokenList tokens={tokens} onRevoke={handleRevokeToken} />
        )}

        {/* Create Token Dialog */}
        <CreateTokenDialog
          open={createDialogOpen}
          onOpenChange={setCreateDialogOpen}
          onSubmit={handleCreateToken}
          userPermissions={userPermissions}
        />

        {/* Token Created Dialog */}
        {createdToken && (
          <TokenCreatedDialog
            token={createdToken.token}
            tokenName={createdToken.name}
            open={true}
            onClose={handleCloseCreatedDialog}
          />
        )}
      </PageContent>
    </Page>
  );
}
