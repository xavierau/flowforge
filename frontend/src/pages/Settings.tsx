/**
 * Settings Page Component
 *
 * Multi-tab settings interface with:
 * - User Invitation management
 * - Subscription and billing management
 * - Account settings and preferences
 *
 * Following React best practices:
 * - Component composition: extracted tab content to separate components
 * - Single responsibility: each tab handles one concern
 * - useEffect cleanup for data fetching
 * - Controlled forms with react-hook-form
 * - Proper error handling and loading states
 */

import { useState } from 'react';
import { Settings as SettingsIcon } from 'lucide-react';

import { Page } from '@/components/layout/Page';
import { PageHeader } from '@/components/layout/PageHeader';
import { PageContent } from '@/components/layout/PageContent';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import { UserInvitationTab } from '@/components/settings/UserInvitationTab';
import { SubscriptionTab } from '@/components/settings/SubscriptionTab';
import { AccountSettingsTab } from '@/components/settings/AccountSettingsTab';

/**
 * Settings Page Component
 *
 * Provides tabbed interface for:
 * 1. User invitations
 * 2. Subscription management
 * 3. Account settings
 */
export function Settings() {
  const [activeTab, setActiveTab] = useState('invitations');

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Settings' },
        ]}
        title="Settings"
        subtitle="Manage your account, team, and subscription"
      />

      <PageContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="invitations">User Invitation</TabsTrigger>
            <TabsTrigger value="subscription">Subscription</TabsTrigger>
            <TabsTrigger value="account">Account Settings</TabsTrigger>
          </TabsList>

          <TabsContent value="invitations" className="space-y-6">
            <UserInvitationTab />
          </TabsContent>

          <TabsContent value="subscription" className="space-y-6">
            <SubscriptionTab />
          </TabsContent>

          <TabsContent value="account" className="space-y-6">
            <AccountSettingsTab />
          </TabsContent>
        </Tabs>
      </PageContent>
    </Page>
  );
}
