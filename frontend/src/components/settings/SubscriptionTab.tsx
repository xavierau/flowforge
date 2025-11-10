/**
 * Subscription Tab Component
 *
 * Manages subscription and billing with:
 * - Current plan display
 * - Plan features comparison
 * - Credit balance and usage stats
 * - Upgrade/downgrade options
 *
 * Following React best practices:
 * - Single responsibility: handles only subscription management
 * - useEffect with cleanup for data fetching
 * - Composition: separate components for plan cards
 * - Proper loading and error states
 */

import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import {
  CreditCard,
  TrendingUp,
  Zap,
  Check,
  FileText,
  Activity,
} from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';

import {
  getCurrentSubscription,
  getPlanFeatures,
  getUsageStatistics,
  changePlan,
  SubscriptionApiError,
} from '@/services/subscription.service';
import type {
  Subscription,
  PlanFeatures,
  UsageStatistics,
  SubscriptionPlan,
} from '@/types/profile';

/**
 * Format number with commas
 */
function formatNumber(num: number): string {
  return num.toLocaleString();
}

/**
 * Get plan badge variant
 */
function getPlanBadgeVariant(
  plan: string
): 'default' | 'secondary' | 'destructive' {
  switch (plan) {
    case 'free':
      return 'secondary';
    case 'pro':
      return 'default';
    case 'enterprise':
      return 'destructive';
    default:
      return 'secondary';
  }
}

/**
 * Subscription Tab Component
 */
export function SubscriptionTab() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [plans, setPlans] = useState<PlanFeatures[]>([]);
  const [usage, setUsage] = useState<UsageStatistics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isChangingPlan, setIsChangingPlan] = useState<string | null>(null);

  /**
   * Fetch subscription data on mount
   * useEffect with cleanup for aborting in-flight requests
   */
  useEffect(() => {
    const abortController = new AbortController();

    async function fetchSubscriptionData() {
      try {
        const [subData, plansData, usageData] = await Promise.all([
          getCurrentSubscription(),
          getPlanFeatures(),
          getUsageStatistics(),
        ]);

        if (!abortController.signal.aborted) {
          setSubscription(subData);
          setPlans(plansData);
          setUsage(usageData);
        }
      } catch (error) {
        if (!abortController.signal.aborted) {
          if (error instanceof SubscriptionApiError) {
            toast.error('Failed to load subscription data', {
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

    fetchSubscriptionData();

    return () => {
      abortController.abort();
    };
  }, []);

  /**
   * Handle plan change
   */
  const handleChangePlan = async (newPlan: SubscriptionPlan) => {
    if (!subscription) return;

    setIsChangingPlan(newPlan);

    try {
      const updatedSubscription = await changePlan(newPlan);

      setSubscription(updatedSubscription);

      toast.success('Plan updated', {
        description: `Your plan has been changed to ${newPlan}.`,
      });
    } catch (error) {
      if (error instanceof SubscriptionApiError) {
        toast.error('Failed to change plan', {
          description: error.message,
        });
      }
    } finally {
      setIsChangingPlan(null);
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
      {/* Current Subscription Overview */}
      {subscription && (
        <div className="grid gap-6 md:grid-cols-3">
          {/* Current Plan Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Current Plan</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Badge variant={getPlanBadgeVariant(subscription.plan)}>
                  {subscription.plan.toUpperCase()}
                </Badge>
                <p className="text-2xl font-bold">
                  {subscription.plan === 'free' ? 'Free' : '$99'}
                  {subscription.plan !== 'free' && (
                    <span className="text-sm font-normal text-muted-foreground">
                      /month
                    </span>
                  )}
                </p>
                <p className="text-xs text-muted-foreground">
                  Status: {subscription.status}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Credits Balance Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Zap className="h-4 w-4" />
                Credits Balance
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <p className="text-2xl font-bold">
                  {formatNumber(subscription.credits_balance)}
                </p>
                <Progress
                  value={
                    (subscription.credits_balance /
                      (subscription.credits_balance + subscription.credits_used)) *
                    100
                  }
                  className="h-2"
                />
                <p className="text-xs text-muted-foreground">
                  {formatNumber(subscription.credits_used)} used this month
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Usage Stats Card */}
          {usage && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Activity className="h-4 w-4" />
                  Usage This Month
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Documents</span>
                  <span className="text-sm font-medium">
                    {formatNumber(usage.documents_processed)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">API Calls</span>
                  <span className="text-sm font-medium">
                    {formatNumber(usage.api_calls_count)}
                  </span>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      <Separator />

      {/* Plan Comparison */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Available Plans</h3>
        <div className="grid gap-6 md:grid-cols-3">
          {plans.map((plan) => (
            <Card
              key={plan.plan}
              className={
                subscription?.plan === plan.plan
                  ? 'ring-2 ring-primary'
                  : undefined
              }
            >
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  {plan.name}
                  {subscription?.plan === plan.plan && (
                    <Badge variant="default">Current</Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Pricing */}
                <div>
                  <p className="text-3xl font-bold">
                    {plan.price === 0 ? 'Free' : `$${plan.price}`}
                  </p>
                  {plan.price > 0 && (
                    <p className="text-sm text-muted-foreground">
                      per {plan.billing_period}
                    </p>
                  )}
                </div>

                <Separator />

                {/* Features */}
                <div className="space-y-2">
                  {plan.features.map((feature, index) => (
                    <div key={index} className="flex items-start gap-2">
                      <Check className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                      <span className="text-sm">{feature}</span>
                    </div>
                  ))}
                </div>

                {/* Limits */}
                <div className="space-y-1 pt-2">
                  <p className="text-xs text-muted-foreground">
                    <FileText className="inline h-3 w-3 mr-1" />
                    {formatNumber(plan.max_documents_per_month)} documents/month
                  </p>
                  <p className="text-xs text-muted-foreground">
                    <CreditCard className="inline h-3 w-3 mr-1" />
                    {formatNumber(plan.credits_per_month)} credits/month
                  </p>
                </div>

                {/* Action Button */}
                {subscription?.plan !== plan.plan && (
                  <Button
                    className="w-full"
                    variant={plan.plan === 'pro' ? 'default' : 'outline'}
                    onClick={() => handleChangePlan(plan.plan)}
                    disabled={isChangingPlan !== null}
                  >
                    {isChangingPlan === plan.plan ? (
                      <>
                        <span className="mr-2">Processing...</span>
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      </>
                    ) : subscription &&
                      plan.price > plans.find((p) => p.plan === subscription.plan)?.price! ? (
                      <>
                        <TrendingUp className="mr-2 h-4 w-4" />
                        Upgrade
                      </>
                    ) : (
                      'Downgrade'
                    )}
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
