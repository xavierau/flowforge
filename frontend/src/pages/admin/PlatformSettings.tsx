/**
 * Platform Settings Page
 *
 * Allows super admins to configure system-wide settings like trial credits amount.
 */

import { useState, useEffect } from 'react';
import { Page, PageHeader, PageContent } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Save, AlertCircle, CheckCircle2 } from 'lucide-react';
import { getPlatformSettings, updatePlatformSetting } from '@/services/admin.service';
import type { PlatformSetting } from '@/types/admin';

export function PlatformSettings() {
  const [settings, setSettings] = useState<PlatformSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form state
  const [trialCredits, setTrialCredits] = useState<number>(100);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getPlatformSettings();
      setSettings(response.settings);

      // Find trial credits setting
      const trialCreditsSetting = response.settings.find(
        (s) => s.key === 'trial_credits_amount'
      );
      if (trialCreditsSetting) {
        setTrialCredits(Number(trialCreditsSetting.value) || 100);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveTrialCredits = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccessMessage(null);

      // Validate
      if (trialCredits < 0) {
        setError('Trial credits must be a non-negative number');
        return;
      }

      await updatePlatformSetting(
        'trial_credits_amount',
        trialCredits,
        'Number of credits automatically granted to new tenants on signup'
      );

      setSuccessMessage(
        `Trial credits amount updated to ${trialCredits}. New tenants will now receive ${trialCredits} credits on signup.`
      );

      // Reload settings to confirm
      await loadSettings();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update setting');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Page>
        <PageHeader title="Platform Settings" subtitle="Configure system-wide settings" />
        <PageContent>
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </PageContent>
      </Page>
    );
  }

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Admin', href: '/admin/dashboard' },
          { label: 'Platform Settings' },
        ]}
        title="Platform Settings"
        subtitle="Configure system-wide settings and defaults"
      />

      <PageContent>
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {successMessage && (
          <Alert className="mb-6 border-green-500 bg-green-50 text-green-900">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <AlertDescription>{successMessage}</AlertDescription>
          </Alert>
        )}

        {/* Trial Credits Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Trial Credits</CardTitle>
            <CardDescription>
              Configure the number of credits automatically granted to new tenants on signup
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="trial-credits">Trial Credits Amount</Label>
              <Input
                id="trial-credits"
                type="number"
                min="0"
                step="1"
                value={trialCredits}
                onChange={(e) => setTrialCredits(parseInt(e.target.value, 10) || 0)}
                className="max-w-xs"
                disabled={saving}
              />
              <p className="text-sm text-muted-foreground">
                New tenants will receive this amount of credits when they sign up. Current value:{' '}
                <strong>{trialCredits} credits</strong>
              </p>
            </div>

            <Button onClick={handleSaveTrialCredits} disabled={saving}>
              {saving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Save Changes
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Other Settings (Future Expansion) */}
        <div className="mt-6 text-sm text-muted-foreground">
          <p>Additional settings can be configured here in the future.</p>
        </div>
      </PageContent>
    </Page>
  );
}
