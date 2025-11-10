/**
 * Signup Page Component
 *
 * Provides user registration with:
 * - Form validation via react-hook-form
 * - Password strength indicator
 * - Password confirmation matching
 * - Loading states during API calls
 * - Error handling with toast notifications
 * - Auto-login after successful registration
 * - Accessible form structure
 *
 * Following React best practices:
 * - Single responsibility: handles only signup flow
 * - Proper password strength calculation (derived state, not useEffect)
 * - Form state managed by react-hook-form
 * - Modular password strength component
 */

import { useState, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { UserPlus, Mail, Lock, User, Building } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

import { signup, storeTokens, AuthApiError } from '@/services/auth.service';
import type { SignupRequest } from '@/types/auth';

interface SignupFormData extends SignupRequest {
  confirmPassword: string;
  acceptTerms: boolean;
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
 * Signup Page Component
 */
export function Signup() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
  } = useForm<SignupFormData>({
    defaultValues: {
      email: '',
      password: '',
      confirmPassword: '',
      full_name: '',
      tenant_name: '',
      acceptTerms: false,
    },
  });

  const password = watch('password');
  const acceptTerms = watch('acceptTerms');

  /**
   * Handle form submission
   * - Validates data via API
   * - Stores tokens on success
   * - Auto-login and redirect
   * - Shows error toast on failure
   */
  const onSubmit = async (data: SignupFormData) => {
    setIsLoading(true);

    try {
      const response = await signup({
        email: data.email,
        password: data.password,
        full_name: data.full_name,
        tenant_name: data.tenant_name,
      });

      // Store authentication tokens (auto-login)
      storeTokens(response.access_token, response.refresh_token);

      // Show success message
      toast.success('Account created successfully', {
        description: `Welcome, ${response.user.full_name}!`,
      });

      // Redirect to dashboard
      navigate('/dashboard');
    } catch (error) {
      // Handle API errors with specific messages
      if (error instanceof AuthApiError) {
        if (error.statusCode === 409) {
          toast.error('Email already registered', {
            description: 'Please use a different email or sign in.',
          });
        } else if (error.statusCode === 422) {
          toast.error('Validation error', {
            description: 'Please check your input and try again.',
          });
        } else {
          toast.error('Registration failed', {
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
          <CardTitle className="text-2xl text-center">Create an account</CardTitle>
          <CardDescription className="text-center">
            Enter your information to get started
          </CardDescription>
        </CardHeader>

        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-4">
            {/* Full Name Field */}
            <div className="space-y-2">
              <Label htmlFor="full_name">Full Name</Label>
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
                    required: 'Full name is required',
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
            </div>

            {/* Email Field */}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="name@example.com"
                  className="pl-10"
                  disabled={isLoading}
                  aria-invalid={errors.email ? 'true' : 'false'}
                  aria-describedby={errors.email ? 'email-error' : undefined}
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
                <p id="email-error" className="text-sm text-destructive">
                  {errors.email.message}
                </p>
              )}
            </div>

            {/* Company/Tenant Name Field */}
            <div className="space-y-2">
              <Label htmlFor="tenant_name">Company Name</Label>
              <div className="relative">
                <Building className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="tenant_name"
                  type="text"
                  placeholder="Acme Inc."
                  className="pl-10"
                  disabled={isLoading}
                  aria-invalid={errors.tenant_name ? 'true' : 'false'}
                  aria-describedby={errors.tenant_name ? 'tenant_name-error' : undefined}
                  {...register('tenant_name', {
                    required: 'Company name is required',
                    minLength: {
                      value: 2,
                      message: 'Company name must be at least 2 characters',
                    },
                  })}
                />
              </div>
              {errors.tenant_name && (
                <p id="tenant_name-error" className="text-sm text-destructive">
                  {errors.tenant_name.message}
                </p>
              )}
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

            {/* Terms Acceptance Checkbox */}
            <div className="flex items-start space-x-2">
              <Checkbox
                id="acceptTerms"
                checked={acceptTerms}
                onCheckedChange={(checked) =>
                  setValue('acceptTerms', checked === true)
                }
                disabled={isLoading}
                aria-label="Accept terms and conditions"
                aria-invalid={errors.acceptTerms ? 'true' : 'false'}
                aria-describedby={errors.acceptTerms ? 'terms-error' : undefined}
              />
              <div className="space-y-1">
                <Label
                  htmlFor="acceptTerms"
                  className="text-sm font-normal cursor-pointer leading-none"
                >
                  I agree to the{' '}
                  <Link
                    to="/terms"
                    className="text-primary hover:underline"
                    tabIndex={isLoading ? -1 : 0}
                  >
                    Terms of Service
                  </Link>{' '}
                  and{' '}
                  <Link
                    to="/privacy"
                    className="text-primary hover:underline"
                    tabIndex={isLoading ? -1 : 0}
                  >
                    Privacy Policy
                  </Link>
                </Label>
                {errors.acceptTerms && (
                  <p id="terms-error" className="text-sm text-destructive">
                    {errors.acceptTerms.message}
                  </p>
                )}
              </div>
            </div>
          </CardContent>

          <CardFooter className="flex flex-col space-y-4">
            <Button
              type="submit"
              className="w-full"
              disabled={isLoading || !acceptTerms}
              aria-busy={isLoading}
            >
              {isLoading ? (
                <>
                  <span className="mr-2">Creating account...</span>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                </>
              ) : (
                'Create account'
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
