/**
 * Reset Password Page Component
 *
 * Provides password reset functionality with:
 * - Token extraction from URL query parameters
 * - Password validation via react-hook-form
 * - Password strength indicator
 * - Password confirmation matching
 * - Loading states during API calls
 * - Error handling with toast notifications
 * - Success state with redirect to login
 * - Accessible form structure
 *
 * Following React best practices:
 * - Single responsibility: handles only password reset flow
 * - Proper password strength calculation (derived state, not useEffect)
 * - Form state managed by react-hook-form
 * - Modular password strength component
 */

import { useState, useMemo, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { Lock, KeyRound, ArrowLeft, CheckCircle, AlertCircle } from 'lucide-react';

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

import { resetPassword, AuthApiError } from '@/services/auth.service';

interface ResetPasswordFormData {
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
 * Reset Password Page Component
 */
export function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [tokenError, setTokenError] = useState<string | null>(null);

  const token = searchParams.get('token');

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<ResetPasswordFormData>({
    defaultValues: {
      password: '',
      confirmPassword: '',
    },
  });

  const password = watch('password');

  // Check for valid token on mount
  useEffect(() => {
    if (!token) {
      setTokenError('Invalid or missing reset token. Please request a new password reset link.');
    }
  }, [token]);

  /**
   * Handle form submission
   * - Resets password via API
   * - Shows success state on completion
   * - Redirects to login after success
   * - Shows error toast on failure
   */
  const onSubmit = async (data: ResetPasswordFormData) => {
    if (!token) {
      toast.error('Invalid token', {
        description: 'Please request a new password reset link.',
      });
      return;
    }

    setIsLoading(true);

    try {
      await resetPassword({
        token,
        password: data.password,
      });

      setIsSuccess(true);

      toast.success('Password reset successful', {
        description: 'You can now log in with your new password.',
      });

      // Redirect to login after a short delay
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (error) {
      // Handle API errors with specific messages
      if (error instanceof AuthApiError) {
        if (error.statusCode === 400 || error.statusCode === 404) {
          setTokenError('This reset link has expired or is invalid. Please request a new one.');
          toast.error('Invalid or expired link', {
            description: 'Please request a new password reset link.',
          });
        } else if (error.statusCode === 422) {
          toast.error('Validation error', {
            description: 'Password does not meet requirements.',
          });
        } else {
          toast.error('Password reset failed', {
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

  // Invalid token state
  if (tokenError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="space-y-1">
            <div className="flex items-center justify-center mb-4">
              <div className="rounded-full bg-red-100 p-3">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
            </div>
            <CardTitle className="text-2xl text-center">Invalid link</CardTitle>
            <CardDescription className="text-center">
              {tokenError}
            </CardDescription>
          </CardHeader>

          <CardFooter className="flex flex-col space-y-4">
            <Button
              className="w-full"
              onClick={() => navigate('/forgot-password')}
            >
              Request new reset link
            </Button>

            <Link
              to="/login"
              className="flex items-center justify-center text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to login
            </Link>
          </CardFooter>
        </Card>
      </div>
    );
  }

  // Success state
  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="space-y-1">
            <div className="flex items-center justify-center mb-4">
              <div className="rounded-full bg-green-100 p-3">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
            </div>
            <CardTitle className="text-2xl text-center">Password reset successful</CardTitle>
            <CardDescription className="text-center">
              Your password has been successfully reset
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground text-center">
              Redirecting you to the login page...
            </p>
          </CardContent>

          <CardFooter className="flex flex-col space-y-4">
            <Button
              className="w-full"
              onClick={() => navigate('/login')}
            >
              Continue to login
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  // Reset form state
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <div className="flex items-center justify-center mb-4">
            <div className="rounded-full bg-primary p-3">
              <KeyRound className="h-6 w-6 text-primary-foreground" />
            </div>
          </div>
          <CardTitle className="text-2xl text-center">Reset your password</CardTitle>
          <CardDescription className="text-center">
            Enter your new password below
          </CardDescription>
        </CardHeader>

        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-4">
            {/* Password Field */}
            <div className="space-y-2">
              <Label htmlFor="password">New Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your new password"
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
              <Label htmlFor="confirmPassword">Confirm New Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="Re-enter your new password"
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
                  <span className="mr-2">Resetting password...</span>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                </>
              ) : (
                'Reset password'
              )}
            </Button>

            <Link
              to="/login"
              className="flex items-center justify-center text-sm text-muted-foreground hover:text-foreground transition-colors"
              tabIndex={isLoading ? -1 : 0}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to login
            </Link>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
