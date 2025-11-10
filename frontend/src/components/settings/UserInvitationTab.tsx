/**
 * User Invitation Tab Component
 *
 * Manages user invitations with:
 * - Form to invite users by email
 * - Role selection dropdown
 * - List of pending invitations
 * - Resend/cancel actions
 *
 * Following React best practices:
 * - Single responsibility: handles only invitation management
 * - useEffect with cleanup for data fetching
 * - Controlled form with react-hook-form
 * - Optimistic UI updates
 */

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { Mail, Send, RotateCw, X } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

import {
  getInvitations,
  createInvitation,
  resendInvitation,
  cancelInvitation,
  UserApiError,
} from '@/services/user.service';
import type {
  UserInvitation,
  CreateInvitationRequest,
  UserRole,
} from '@/types/profile';

/**
 * Format date to relative time
 */
function formatRelativeDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffInMs = now.getTime() - date.getTime();
  const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24));

  if (diffInDays === 0) return 'Today';
  if (diffInDays === 1) return 'Yesterday';
  if (diffInDays < 7) return `${diffInDays} days ago`;
  if (diffInDays < 30) return `${Math.floor(diffInDays / 7)} weeks ago`;
  return date.toLocaleDateString();
}

/**
 * Get status badge variant
 */
function getStatusBadgeVariant(
  status: string
): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'pending':
      return 'default';
    case 'accepted':
      return 'secondary';
    case 'expired':
      return 'destructive';
    case 'cancelled':
      return 'outline';
    default:
      return 'secondary';
  }
}

/**
 * User Invitation Tab Component
 */
export function UserInvitationTab() {
  const [invitations, setInvitations] = useState<UserInvitation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
    watch,
  } = useForm<CreateInvitationRequest>({
    defaultValues: {
      email: '',
      role: 'user',
    },
  });

  const selectedRole = watch('role');

  /**
   * Fetch invitations on mount
   * useEffect with cleanup for aborting in-flight requests
   */
  useEffect(() => {
    const abortController = new AbortController();

    async function fetchInvitations() {
      try {
        const data = await getInvitations();
        if (!abortController.signal.aborted) {
          setInvitations(data);
        }
      } catch (error) {
        if (!abortController.signal.aborted) {
          if (error instanceof UserApiError) {
            toast.error('Failed to load invitations', {
              description: error.message,
            });
          }
        }
      } finally {
        if (!abortController.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    fetchInvitations();

    return () => {
      abortController.abort();
    };
  }, []);

  /**
   * Handle invitation form submission
   */
  const onSubmit = async (data: CreateInvitationRequest) => {
    setIsSubmitting(true);

    try {
      const newInvitation = await createInvitation(data);

      // Optimistically update UI
      setInvitations((prev) => [newInvitation, ...prev]);

      toast.success('Invitation sent', {
        description: `Invitation sent to ${data.email}`,
      });

      // Reset form
      reset();
    } catch (error) {
      if (error instanceof UserApiError) {
        toast.error('Failed to send invitation', {
          description: error.message,
        });
      } else {
        toast.error('Network error', {
          description: 'Please try again later.',
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  /**
   * Handle resending invitation
   */
  const handleResend = async (invitationId: string) => {
    setProcessingId(invitationId);

    try {
      await resendInvitation(invitationId);

      toast.success('Invitation resent', {
        description: 'The invitation email has been sent again.',
      });
    } catch (error) {
      if (error instanceof UserApiError) {
        toast.error('Failed to resend invitation', {
          description: error.message,
        });
      }
    } finally {
      setProcessingId(null);
    }
  };

  /**
   * Handle cancelling invitation
   */
  const handleCancel = async (invitationId: string) => {
    setProcessingId(invitationId);

    try {
      await cancelInvitation(invitationId);

      // Optimistically update UI
      setInvitations((prev) => prev.filter((inv) => inv.id !== invitationId));

      toast.success('Invitation cancelled', {
        description: 'The invitation has been cancelled.',
      });
    } catch (error) {
      if (error instanceof UserApiError) {
        toast.error('Failed to cancel invitation', {
          description: error.message,
        });
      }
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* Invite User Form */}
      <Card>
        <CardHeader>
          <CardTitle>Invite User</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Email Field */}
            <div className="space-y-2">
              <Label htmlFor="email">Email Address</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="user@example.com"
                  className="pl-10"
                  disabled={isSubmitting}
                  {...register('email', {
                    required: 'Email is required',
                    pattern: {
                      value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                      message: 'Invalid email address',
                    },
                  })}
                />
              </div>
              {errors.email && (
                <p className="text-sm text-destructive">{errors.email.message}</p>
              )}
            </div>

            {/* Role Selection */}
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Select
                value={selectedRole}
                onValueChange={(value: UserRole) => setValue('role', value)}
                disabled={isSubmitting}
              >
                <SelectTrigger id="role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="user">User</SelectItem>
                  <SelectItem value="viewer">Viewer</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {selectedRole === 'admin' && 'Full access to all features'}
                {selectedRole === 'user' && 'Can create and manage resources'}
                {selectedRole === 'viewer' && 'Read-only access'}
              </p>
            </div>

            {/* Submit Button */}
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <span className="mr-2">Sending...</span>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                  Send Invitation
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Pending Invitations List */}
      <Card>
        <CardHeader>
          <CardTitle>Pending Invitations</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          ) : invitations.length === 0 ? (
            <p className="text-center text-sm text-muted-foreground py-8">
              No pending invitations
            </p>
          ) : (
            <div className="space-y-4">
              {invitations.map((invitation, index) => (
                <div key={invitation.id}>
                  {index > 0 && <Separator className="my-4" />}
                  <div className="space-y-2">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {invitation.email}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="outline" className="text-xs">
                            {invitation.role}
                          </Badge>
                          <Badge
                            variant={getStatusBadgeVariant(invitation.status)}
                            className="text-xs"
                          >
                            {invitation.status}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          Sent {formatRelativeDate(invitation.created_at)}
                        </p>
                      </div>

                      {invitation.status === 'pending' && (
                        <div className="flex gap-1 ml-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleResend(invitation.id)}
                            disabled={processingId === invitation.id}
                            title="Resend invitation"
                          >
                            <RotateCw className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleCancel(invitation.id)}
                            disabled={processingId === invitation.id}
                            title="Cancel invitation"
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
