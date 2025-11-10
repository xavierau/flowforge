/**
 * Login Page Component
 *
 * Provides user authentication with:
 * - Email/password validation via react-hook-form
 * - Loading states during API calls
 * - Error handling with toast notifications
 * - Token storage and redirect on success
 * - Accessible form structure
 *
 * Following React best practices:
 * - Single responsibility: handles only login flow
 * - Proper useEffect cleanup (none needed - no subscriptions)
 * - Form state managed by react-hook-form (external system sync)
 */

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { LogIn, Mail, Lock } from 'lucide-react';

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

import { login, storeTokens, AuthApiError } from '@/services/auth.service';
import type { LoginRequest } from '@/types/auth';

interface LoginFormData extends LoginRequest {
  rememberMe: boolean;
}

/**
 * Login Page Component
 */
export function Login() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
  } = useForm<LoginFormData>({
    defaultValues: {
      email: '',
      password: '',
      rememberMe: false,
    },
  });

  const rememberMe = watch('rememberMe');

  /**
   * Handle form submission
   * - Validates credentials via API
   * - Stores tokens on success
   * - Redirects to schema builder
   * - Shows error toast on failure
   */
  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true);

    try {
      const response = await login({
        email: data.email,
        password: data.password,
      });

      // Store authentication tokens
      storeTokens(response.access_token, response.refresh_token);

      // Show success message
      toast.success('Login successful', {
        description: `Welcome back, ${response.user.full_name}!`,
      });

      // Redirect to dashboard
      navigate('/dashboard');
    } catch (error) {
      // Handle API errors with specific messages
      if (error instanceof AuthApiError) {
        if (error.statusCode === 401) {
          toast.error('Invalid credentials', {
            description: 'Please check your email and password.',
          });
        } else if (error.statusCode === 422) {
          toast.error('Validation error', {
            description: 'Please check your input and try again.',
          });
        } else {
          toast.error('Login failed', {
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
              <LogIn className="h-6 w-6 text-primary-foreground" />
            </div>
          </div>
          <CardTitle className="text-2xl text-center">Welcome back</CardTitle>
          <CardDescription className="text-center">
            Enter your credentials to access your account
          </CardDescription>
        </CardHeader>

        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-4">
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

            {/* Password Field */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link
                  to="/forgot-password"
                  className="text-sm text-primary hover:underline"
                  tabIndex={isLoading ? -1 : 0}
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
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
            </div>

            {/* Remember Me Checkbox */}
            <div className="flex items-center space-x-2">
              <Checkbox
                id="rememberMe"
                checked={rememberMe}
                onCheckedChange={(checked) =>
                  setValue('rememberMe', checked === true)
                }
                disabled={isLoading}
                aria-label="Remember me"
              />
              <Label
                htmlFor="rememberMe"
                className="text-sm font-normal cursor-pointer"
              >
                Remember me
              </Label>
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
                  <span className="mr-2">Signing in...</span>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                </>
              ) : (
                'Sign in'
              )}
            </Button>

            <p className="text-sm text-muted-foreground text-center">
              Don't have an account?{' '}
              <Link
                to="/signup"
                className="text-primary font-medium hover:underline"
                tabIndex={isLoading ? -1 : 0}
              >
                Sign up
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
