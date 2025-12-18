/**
 * Forgot Password Page Component
 *
 * Provides password reset request functionality with:
 * - Email validation via react-hook-form
 * - Loading states during API calls
 * - Error handling with toast notifications
 * - Success state showing email sent confirmation
 * - Accessible form structure
 *
 * Following React best practices:
 * - Single responsibility: handles only forgot password flow
 * - Proper state management for success/loading states
 * - Form state managed by react-hook-form (external system sync)
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { Mail, KeyRound, ArrowLeft, CheckCircle } from 'lucide-react';

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

import { forgotPassword, AuthApiError } from '@/services/auth.service';
import type { ForgotPasswordRequest } from '@/types/auth';

/**
 * Forgot Password Page Component
 */
export function ForgotPassword() {
  const [isLoading, setIsLoading] = useState(false);
  const [isEmailSent, setIsEmailSent] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordRequest>({
    defaultValues: {
      email: '',
    },
  });

  /**
   * Handle form submission
   * - Requests password reset via API
   * - Shows success state on completion
   * - Shows error toast on failure
   */
  const onSubmit = async (data: ForgotPasswordRequest) => {
    setIsLoading(true);

    try {
      await forgotPassword(data);

      // Store email for display and show success state
      setSubmittedEmail(data.email);
      setIsEmailSent(true);

      toast.success('Reset link sent', {
        description: 'Check your email for password reset instructions.',
      });
    } catch (error) {
      // Handle API errors with specific messages
      if (error instanceof AuthApiError) {
        if (error.statusCode === 404) {
          // Don't reveal if email exists or not for security
          // Still show success to prevent email enumeration attacks
          setSubmittedEmail(data.email);
          setIsEmailSent(true);
          toast.success('Reset link sent', {
            description: 'If an account exists with this email, you will receive reset instructions.',
          });
        } else if (error.statusCode === 422) {
          toast.error('Validation error', {
            description: 'Please enter a valid email address.',
          });
        } else if (error.statusCode === 429) {
          toast.error('Too many requests', {
            description: 'Please wait a few minutes before trying again.',
          });
        } else {
          toast.error('Request failed', {
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

  // Success state - email sent confirmation
  if (isEmailSent) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="space-y-1">
            <div className="flex items-center justify-center mb-4">
              <div className="rounded-full bg-green-100 p-3">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
            </div>
            <CardTitle className="text-2xl text-center">Check your email</CardTitle>
            <CardDescription className="text-center">
              We've sent a password reset link to
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <p className="text-center font-medium text-foreground">
              {submittedEmail}
            </p>
            <p className="text-sm text-muted-foreground text-center">
              Click the link in the email to reset your password. If you don't see it, check your spam folder.
            </p>
          </CardContent>

          <CardFooter className="flex flex-col space-y-4">
            <Button
              variant="outline"
              className="w-full"
              onClick={() => {
                setIsEmailSent(false);
                setSubmittedEmail('');
              }}
            >
              Send another link
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

  // Request form state
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <div className="flex items-center justify-center mb-4">
            <div className="rounded-full bg-primary p-3">
              <KeyRound className="h-6 w-6 text-primary-foreground" />
            </div>
          </div>
          <CardTitle className="text-2xl text-center">Forgot password?</CardTitle>
          <CardDescription className="text-center">
            No worries, we'll send you reset instructions
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
                  <span className="mr-2">Sending...</span>
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
