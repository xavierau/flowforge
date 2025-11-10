/**
 * Profile Page Component
 *
 * Displays user profile information with:
 * - User details from authentication
 * - Avatar display
 * - Account metadata (creation date, last login)
 * - Role and tenant information
 *
 * Following React best practices:
 * - Single responsibility: displays user profile only
 * - useEffect for data fetching with proper cleanup
 * - Composition with Page/PageHeader/PageContent layout
 * - Error and loading states
 */

import { useState, useEffect } from 'react';
import { User, Mail, Calendar, Shield, Building2 } from 'lucide-react';
import { toast } from 'sonner';

import { Page } from '@/components/layout/Page';
import { PageHeader } from '@/components/layout/PageHeader';
import { PageContent } from '@/components/layout/PageContent';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

import { getCurrentUser, UserApiError } from '@/services/user.service';
import type { UserProfile } from '@/types/profile';

/**
 * Get initials from full name for avatar fallback
 */
function getInitials(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

/**
 * Format date string to readable format
 */
function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

/**
 * Get role badge variant
 */
function getRoleBadgeVariant(
  role: string
): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (role) {
    case 'admin':
      return 'default';
    case 'user':
      return 'secondary';
    case 'viewer':
      return 'outline';
    default:
      return 'secondary';
  }
}

/**
 * Profile Page Component
 */
export function Profile() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  /**
   * Fetch user profile on component mount
   * useEffect with empty dependency array - runs once on mount
   * Cleanup: AbortController to cancel in-flight requests
   */
  useEffect(() => {
    const abortController = new AbortController();

    async function fetchProfile() {
      try {
        const data = await getCurrentUser();
        if (!abortController.signal.aborted) {
          setProfile(data);
        }
      } catch (error) {
        if (!abortController.signal.aborted) {
          if (error instanceof UserApiError) {
            toast.error('Failed to load profile', {
              description: error.message,
            });
          } else {
            toast.error('Network error', {
              description: 'Please check your connection and try again.',
            });
          }
        }
      } finally {
        if (!abortController.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    fetchProfile();

    // Cleanup function: abort fetch if component unmounts
    return () => {
      abortController.abort();
    };
  }, []); // Empty deps - fetch once on mount

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Profile' },
        ]}
        title="Profile"
        subtitle="View your account information and details"
      />

      <PageContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        ) : profile ? (
          <div className="grid gap-6 md:grid-cols-2">
            {/* Profile Overview Card */}
            <Card>
              <CardHeader>
                <CardTitle>Account Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Avatar and Name */}
                <div className="flex items-center gap-4">
                  <Avatar className="h-20 w-20">
                    <AvatarImage src={profile.avatar_url} alt={profile.full_name} />
                    <AvatarFallback className="text-lg">
                      {getInitials(profile.full_name)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold">{profile.full_name}</h3>
                    <p className="text-sm text-muted-foreground">
                      {profile.email}
                    </p>
                    <div className="mt-2">
                      <Badge variant={getRoleBadgeVariant(profile.role.name)}>
                        {profile.role.display_name || profile.role.name}
                      </Badge>
                    </div>
                  </div>
                </div>

                <Separator />

                {/* Contact Information */}
                <div className="space-y-4">
                  <h4 className="text-sm font-semibold">Contact Details</h4>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <Mail className="h-4 w-4 text-muted-foreground" />
                      <div className="flex-1">
                        <p className="text-sm font-medium">Email</p>
                        <p className="text-sm text-muted-foreground">
                          {profile.email}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Account Details Card */}
            <Card>
              <CardHeader>
                <CardTitle>Account Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Organization Info */}
                <div className="space-y-4">
                  <h4 className="text-sm font-semibold">Organization</h4>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <Building2 className="h-4 w-4 text-muted-foreground" />
                      <div className="flex-1">
                        <p className="text-sm font-medium">Tenant</p>
                        <p className="text-sm text-muted-foreground">
                          {profile.tenant.name || profile.tenant.id}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <Shield className="h-4 w-4 text-muted-foreground" />
                      <div className="flex-1">
                        <p className="text-sm font-medium">Role</p>
                        <p className="text-sm text-muted-foreground">
                          {profile.role.display_name || profile.role.name}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <Separator />

                {/* Account Dates */}
                <div className="space-y-4">
                  <h4 className="text-sm font-semibold">Account Activity</h4>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <Calendar className="h-4 w-4 text-muted-foreground" />
                      <div className="flex-1">
                        <p className="text-sm font-medium">Member Since</p>
                        <p className="text-sm text-muted-foreground">
                          {formatDate(profile.created_at)}
                        </p>
                      </div>
                    </div>

                    {profile.last_login && (
                      <div className="flex items-center gap-3">
                        <User className="h-4 w-4 text-muted-foreground" />
                        <div className="flex-1">
                          <p className="text-sm font-medium">Last Login</p>
                          <p className="text-sm text-muted-foreground">
                            {formatDate(profile.last_login)}
                          </p>
                        </div>
                      </div>
                    )}

                    <div className="flex items-center gap-3">
                      <div
                        className={`h-2 w-2 rounded-full ${
                          profile.is_active ? 'bg-green-500' : 'bg-red-500'
                        }`}
                      />
                      <div className="flex-1">
                        <p className="text-sm font-medium">Account Status</p>
                        <p className="text-sm text-muted-foreground">
                          {profile.is_active ? 'Active' : 'Inactive'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">
                Unable to load profile information
              </p>
            </CardContent>
          </Card>
        )}
      </PageContent>
    </Page>
  );
}
