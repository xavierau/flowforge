/**
 * AcceptInvitation Page Component
 *
 * Allows invited users to complete their account setup by:
 * - Setting their password
 * - Optionally updating their full name
 * - Auto-login after successful acceptance
 *
 * Following React best practices:
 * - Single responsibility: handles only invitation acceptance flow
 * - Proper password strength calculation (derived state via useMemo)
 * - Form state managed by react-hook-form
 * - Reusable password strength indicator component
 */

import { useState, useMemo } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { UserPlus, Lock, User, AlertCircle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

import { acceptInvitation, storeTokens, AuthApiError } from '@/services/auth.service';
import type { AcceptInvitationRequest } from '@/types/auth';

interface AcceptInvitationFormData {
  full_name: string;
  password: string;
  confirmPassword: string;
}

type PasswordStrength = 'weak' | 'fair' | 'good' | 'strong';

interface PasswordStrengthInfo {
  strength: PasswordStrength;
  score: number;
  color: string;
  label: string;
}

/**
 * Calculate password strength (pure function, no side effects)
 */
function calculatePasswordStrength(password: string): PasswordStrengthInfo {
  if (!password) {
    return { strength: 'weak', score: 0, color: 'bg-gray-300', label: '' };
  }

  let score = 0;

  // Length check
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;

  // Character variety checks
  if (/[a-z]/.test(password)) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/[0-9]/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  // Determine strength level
  if (score <= 2) {
    return {
      strength: 'weak',
      score: 25,
      color: 'bg-red-500',
      label: 'Weak',
    };
  } else if (score <= 4) {
    return {
      strength: 'fair',
      score: 50,
      color: 'bg-orange-500',
      label: 'Fair',
    };
  } else if (score <= 5) {
    return {
      strength: 'good',
      score: 75,
      color: 'bg-yellow-500',
      label: 'Good',
    };
  } else {
    return {
      strength: 'strong',
      score: 100,
      color: 'bg-green-500',
      label: 'Strong',
    };
  }
}

/**
 * Password Strength Indicator Component
 * Separated for single responsibility and reusability
 */
interface PasswordStrengthIndicatorProps {
  password: string;
}

function PasswordStrengthIndicator({ password }: PasswordStrengthIndicatorProps) {
  // Use useMemo for expensive calculation (follows best practices)
  const strengthInfo = useMemo(
    () => calculatePasswordStrength(password),
    [password]
  );

  if (!password) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">Password strength:</span>
        <span className="font-medium">{strengthInfo.label}</span>
      </div>
      <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${strengthInfo.color}`}
          style={{ width: `${strengthInfo.score}%` }}
        />
      </div>
    </div>
  );
}

/**
 * Invalid Token Error Card Component
 */
function InvalidTokenCard() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <div className="flex items-center justify-center mb-4">
            <div className="rounded-full bg-destructive p-3">
              <AlertCircle className="h-6 w-6 text-destructive-foreground" />
            </div>
          </div>
          <CardTitle className="text-2xl text-center">Invalid Invitation Link</CardTitle>
          <CardDescription className="text-center">
            The invitation link is missing or invalid. Please check your email for the correct link or contact your administrator.
          </CardDescription>
        </CardHeader>
        <CardFooter className="flex flex-col space-y-4">
          <Link to="/login" className="w-full">
            <Button variant="outline" className="w-full">
              Go to Login
            </Button>
          </Link>
        </CardFooter>
      </Card>
    </div>
  );
}

/**
 * AcceptInvitation Page Component
 */
export function AcceptInvitation() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [isLoading, setIsLoading] = useState(false);

  // Extract token from URL
  const token = searchParams.get('token');

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<AcceptInvitationFormData>({
    defaultValues: {
      full_name: '',
      password: '',
      confirmPassword: '',
    },
  });

  const password = watch('password');

  // If no token, show error state
  if (!token) {
    return <InvalidTokenCard />;
  }

  /**
   * Handle form submission
   * - Accepts invitation via API
   * - Stores tokens on success
   * - Auto-login and redirect
   * - Shows error toast on failure
   */
  const onSubmit = async (data: AcceptInvitationFormData) => {
    setIsLoading(true);

    try {
      const requestData: AcceptInvitationRequest = {
        token,
        password: data.password,
      };

      // Only include full_name if provided
      if (data.full_name.trim()) {
        requestData.full_name = data.full_name.trim();
      }

      const response = await acceptInvitation(requestData);

      // Store authentication tokens (auto-login)
      storeTokens(response.access_token, response.refresh_token);

      // Show success message
      toast.success('Account setup complete', {
        description: `Welcome, ${response.user.full_name}!`,
      });

      // Redirect to dashboard
      navigate('/dashboard');
    } catch (error) {
      // Handle API errors with specific messages
      if (error instanceof AuthApiError) {
        if (error.statusCode === 400) {
          toast.error('Invalid or expired invitation', {
            description: 'The invitation link may have expired or already been used. Please contact your administrator.',
          });
        } else if (error.statusCode === 404) {
          toast.error('Invitation not found', {
            description: 'This invitation does not exist. Please check your email for the correct link.',
          });
        } else if (error.statusCode === 422) {
          toast.error('Validation error', {
            description: 'Please check your input and try again.',
          });
        } else {
          toast.error('Account setup failed', {
            description: error.message,
          });
        }
      } else {
        // Network or unexpected errors
        toast.error('Connection error', {
          description: 'Please check your internet connection and try again.',
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <div className="flex items-center justify-center mb-4">
            <div className="rounded-full bg-primary p-3">
              <UserPlus className="h-6 w-6 text-primary-foreground" />
            </div>
          </div>
          <CardTitle className="text-2xl text-center">Complete Your Account Setup</CardTitle>
          <CardDescription className="text-center">
            Set your password to get started
          </CardDescription>
        </CardHeader>

        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-4">
            {/* Full Name Field (Optional) */}
            <div className="space-y-2">
              <Label htmlFor="full_name">Full Name (Optional)</Label>
              <div className="relative">
                <User className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="full_name"
                  type="text"
                  placeholder="John Doe"
                  className="pl-10"
                  disabled={isLoading}
                  aria-invalid={errors.full_name ? 'true' : 'false'}
                  aria-describedby={errors.full_name ? 'full_name-error' : undefined}
                  {...register('full_name', {
                    minLength: {
                      value: 2,
                      message: 'Name must be at least 2 characters',
                    },
                  })}
                />
              </div>
              {errors.full_name && (
                <p id="full_name-error" className="text-sm text-destructive">
                  {errors.full_name.message}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                Leave blank to keep your current name
              </p>
            </div>

            {/* Password Field */}
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  placeholder="Create a strong password"
                  className="pl-10"
                  disabled={isLoading}
                  aria-invalid={errors.password ? 'true' : 'false'}
                  aria-describedby={errors.password ? 'password-error' : undefined}
                  {...register('password', {
                    required: 'Password is required',
                    minLength: {
                      value: 8,
                      message: 'Password must be at least 8 characters',
                    },
                  })}
                />
              </div>
              {errors.password && (
                <p id="password-error" className="text-sm text-destructive">
                  {errors.password.message}
                </p>
              )}
              <PasswordStrengthIndicator password={password} />
            </div>

            {/* Confirm Password Field */}
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="Re-enter your password"
                  className="pl-10"
                  disabled={isLoading}
                  aria-invalid={errors.confirmPassword ? 'true' : 'false'}
                  aria-describedby={
                    errors.confirmPassword ? 'confirmPassword-error' : undefined
                  }
                  {...register('confirmPassword', {
                    required: 'Please confirm your password',
                    validate: (value) =>
                      value === password || 'Passwords do not match',
                  })}
                />
              </div>
              {errors.confirmPassword && (
                <p id="confirmPassword-error" className="text-sm text-destructive">
                  {errors.confirmPassword.message}
                </p>
              )}
            </div>
          </CardContent>

          <CardFooter className="flex flex-col space-y-4">
            <Button
              type="submit"
              className="w-full"
              disabled={isLoading}
              aria-busy={isLoading}
            >
              {isLoading ? (
                <>
                  <span className="mr-2">Setting up account...</span>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                </>
              ) : (
                'Complete Setup'
              )}
            </Button>

            <p className="text-sm text-muted-foreground text-center">
              Already have an account?{' '}
              <Link
                to="/login"
                className="text-primary font-medium hover:underline"
                tabIndex={isLoading ? -1 : 0}
              >
                Sign in
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
