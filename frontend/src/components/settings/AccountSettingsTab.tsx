/**
 * Account Settings Tab Component
 *
 * Manages account settings with:
 * - Profile information editing
 * - Password change form
 * - Notification preferences
 * - Danger zone (account deletion)
 *
 * Following React best practices:
 * - Single responsibility: handles only account settings
 * - useEffect with cleanup for data fetching
 * - Controlled forms with react-hook-form
 * - Proper validation and error handling
 */

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Save, AlertTriangle, Trash2 } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

import {
  getCurrentUser,
  updateAccount,
  changePassword,
  getNotificationPreferences,
  updateNotificationPreferences,
  deleteAccount,
  UserApiError,
} from '@/services/user.service';
import { clearTokens } from '@/services/auth.service';
import type {
  UserProfile,
  UpdateAccountRequest,
  ChangePasswordRequest,
  NotificationPreferences,
} from '@/types/profile';

/**
 * Account Settings Tab Component
 */
export function AccountSettingsTab() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [preferences, setPreferences] = useState<NotificationPreferences | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isSavingPassword, setIsSavingPassword] = useState(false);
  const [isSavingPreferences, setIsSavingPreferences] = useState(false);
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  // Profile form
  const {
    register: registerProfile,
    handleSubmit: handleSubmitProfile,
    formState: { errors: profileErrors },
    reset: resetProfile,
  } = useForm<UpdateAccountRequest>();

  // Password form
  const {
    register: registerPassword,
    handleSubmit: handleSubmitPassword,
    formState: { errors: passwordErrors },
    reset: resetPassword,
    watch: watchPassword,
  } = useForm<ChangePasswordRequest>();

  const newPassword = watchPassword('new_password');

  /**
   * Fetch user data and preferences on mount
   * useEffect with cleanup for aborting in-flight requests
   */
  useEffect(() => {
    const abortController = new AbortController();

    async function fetchData() {
      try {
        const [profileData, preferencesData] = await Promise.all([
          getCurrentUser(),
          getNotificationPreferences(),
        ]);

        if (!abortController.signal.aborted) {
          setProfile(profileData);
          setPreferences(preferencesData);

          // Initialize profile form
          resetProfile({
            full_name: profileData.full_name,
            email: profileData.email,
          });
        }
      } catch (error) {
        if (!abortController.signal.aborted) {
          if (error instanceof UserApiError) {
            toast.error('Failed to load account data', {
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

    fetchData();

    return () => {
      abortController.abort();
    };
  }, [resetProfile]);

  /**
   * Handle profile update
   */
  const onSubmitProfile = async (data: UpdateAccountRequest) => {
    setIsSavingProfile(true);

    try {
      const updatedProfile = await updateAccount(data);
      setProfile(updatedProfile);

      toast.success('Profile updated', {
        description: 'Your profile information has been updated.',
      });
    } catch (error) {
      if (error instanceof UserApiError) {
        toast.error('Failed to update profile', {
          description: error.message,
        });
      }
    } finally {
      setIsSavingProfile(false);
    }
  };

  /**
   * Handle password change
   */
  const onSubmitPassword = async (data: ChangePasswordRequest) => {
    setIsSavingPassword(true);

    try {
      await changePassword(data);

      toast.success('Password changed', {
        description: 'Your password has been updated successfully.',
      });

      // Reset password form
      resetPassword();
    } catch (error) {
      if (error instanceof UserApiError) {
        toast.error('Failed to change password', {
          description: error.message,
        });
      }
    } finally {
      setIsSavingPassword(false);
    }
  };

  /**
   * Handle notification preference toggle
   */
  const handlePreferenceToggle = async (
    key: keyof NotificationPreferences,
    value: boolean
  ) => {
    if (!preferences) return;

    const updatedPreferences = { ...preferences, [key]: value };
    setPreferences(updatedPreferences);

    setIsSavingPreferences(true);

    try {
      await updateNotificationPreferences(updatedPreferences);
    } catch (error) {
      // Revert on error
      setPreferences(preferences);

      if (error instanceof UserApiError) {
        toast.error('Failed to update preferences', {
          description: error.message,
        });
      }
    } finally {
      setIsSavingPreferences(false);
    }
  };

  /**
   * Handle account deletion
   */
  const handleDeleteAccount = async () => {
    setIsDeletingAccount(true);

    try {
      await deleteAccount();

      toast.success('Account deleted', {
        description: 'Your account has been permanently deleted.',
      });

      // Clear tokens and redirect to home
      clearTokens();
      navigate('/');
    } catch (error) {
      if (error instanceof UserApiError) {
        toast.error('Failed to delete account', {
          description: error.message,
        });
      }
    } finally {
      setIsDeletingAccount(false);
      setShowDeleteDialog(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Profile Information */}
      <Card>
        <CardHeader>
          <CardTitle>Profile Information</CardTitle>
          <CardDescription>
            Update your account profile information
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleSubmitProfile(onSubmitProfile)}
            className="space-y-4"
          >
            {/* Full Name */}
            <div className="space-y-2">
              <Label htmlFor="full_name">Full Name</Label>
              <Input
                id="full_name"
                type="text"
                disabled={isSavingProfile}
                {...registerProfile('full_name', {
                  required: 'Full name is required',
                })}
              />
              {profileErrors.full_name && (
                <p className="text-sm text-destructive">
                  {profileErrors.full_name.message}
                </p>
              )}
            </div>

            {/* Email */}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                disabled={isSavingProfile}
                {...registerProfile('email', {
                  required: 'Email is required',
                  pattern: {
                    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                    message: 'Invalid email address',
                  },
                })}
              />
              {profileErrors.email && (
                <p className="text-sm text-destructive">
                  {profileErrors.email.message}
                </p>
              )}
            </div>

            <Button type="submit" disabled={isSavingProfile}>
              {isSavingProfile ? (
                <>
                  <span className="mr-2">Saving...</span>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Save Changes
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Change Password */}
      <Card>
        <CardHeader>
          <CardTitle>Change Password</CardTitle>
          <CardDescription>Update your account password</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleSubmitPassword(onSubmitPassword)}
            className="space-y-4"
          >
            {/* Current Password */}
            <div className="space-y-2">
              <Label htmlFor="current_password">Current Password</Label>
              <Input
                id="current_password"
                type="password"
                disabled={isSavingPassword}
                {...registerPassword('current_password', {
                  required: 'Current password is required',
                })}
              />
              {passwordErrors.current_password && (
                <p className="text-sm text-destructive">
                  {passwordErrors.current_password.message}
                </p>
              )}
            </div>

            {/* New Password */}
            <div className="space-y-2">
              <Label htmlFor="new_password">New Password</Label>
              <Input
                id="new_password"
                type="password"
                disabled={isSavingPassword}
                {...registerPassword('new_password', {
                  required: 'New password is required',
                  minLength: {
                    value: 8,
                    message: 'Password must be at least 8 characters',
                  },
                })}
              />
              {passwordErrors.new_password && (
                <p className="text-sm text-destructive">
                  {passwordErrors.new_password.message}
                </p>
              )}
            </div>

            {/* Confirm Password */}
            <div className="space-y-2">
              <Label htmlFor="confirm_password">Confirm New Password</Label>
              <Input
                id="confirm_password"
                type="password"
                disabled={isSavingPassword}
                {...registerPassword('confirm_password', {
                  required: 'Please confirm your password',
                  validate: (value) =>
                    value === newPassword || 'Passwords do not match',
                })}
              />
              {passwordErrors.confirm_password && (
                <p className="text-sm text-destructive">
                  {passwordErrors.confirm_password.message}
                </p>
              )}
            </div>

            <Button type="submit" disabled={isSavingPassword}>
              {isSavingPassword ? (
                <>
                  <span className="mr-2">Updating...</span>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                </>
              ) : (
                'Update Password'
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Notification Preferences */}
      {preferences && (
        <Card>
          <CardHeader>
            <CardTitle>Notification Preferences</CardTitle>
            <CardDescription>
              Manage your email notification settings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {Object.entries({
              email_on_job_complete: 'Job completed',
              email_on_job_failed: 'Job failed',
              email_on_low_credits: 'Low credits warning',
              email_on_subscription_changes: 'Subscription changes',
              email_marketing: 'Marketing emails',
            }).map(([key, label]) => (
              <div key={key} className="flex items-center justify-between">
                <Label htmlFor={key} className="cursor-pointer">
                  {label}
                </Label>
                <Switch
                  id={key}
                  checked={preferences[key as keyof NotificationPreferences]}
                  onCheckedChange={(checked) =>
                    handlePreferenceToggle(
                      key as keyof NotificationPreferences,
                      checked
                    )
                  }
                  disabled={isSavingPreferences}
                />
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Danger Zone */}
      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="text-destructive flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Danger Zone
          </CardTitle>
          <CardDescription>
            Irreversible actions that permanently affect your account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
            <DialogTrigger asChild>
              <Button variant="destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Delete Account
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Are you absolutely sure?</DialogTitle>
                <DialogDescription>
                  This action cannot be undone. This will permanently delete your
                  account and remove all your data from our servers.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setShowDeleteDialog(false)}
                  disabled={isDeletingAccount}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleDeleteAccount}
                  disabled={isDeletingAccount}
                >
                  {isDeletingAccount ? (
                    <>
                      <span className="mr-2">Deleting...</span>
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    </>
                  ) : (
                    'Delete Account'
                  )}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>
    </div>
  );
}
