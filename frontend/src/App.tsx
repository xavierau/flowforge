import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { AuthenticatedLayout } from '@/components/layout';
import { Toaster } from '@/components/ui/sonner';

// Loading fallback component
const LoadingFallback = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
      <p className="text-muted-foreground">Loading...</p>
    </div>
  </div>
);

// Lazy load all pages for code splitting
const Login = lazy(() => import('@/pages/Login').then(m => ({ default: m.Login })));
const Signup = lazy(() => import('@/pages/Signup').then(m => ({ default: m.Signup })));
const ForgotPassword = lazy(() => import('@/pages/ForgotPassword').then(m => ({ default: m.ForgotPassword })));
const ResetPassword = lazy(() => import('@/pages/ResetPassword').then(m => ({ default: m.ResetPassword })));
const AcceptInvitation = lazy(() => import('@/pages/AcceptInvitation').then(m => ({ default: m.AcceptInvitation })));
const Dashboard = lazy(() => import('@/pages/Dashboard').then(m => ({ default: m.Dashboard })));
const BillingDetails = lazy(() => import('@/pages/BillingDetails').then(m => ({ default: m.BillingDetails })));
const SchemaBuilder = lazy(() => import('@/pages/SchemaBuilder').then(m => ({ default: m.SchemaBuilder })));
const SchemaList = lazy(() => import('@/pages/schemas/SchemaList').then(m => ({ default: m.SchemaList })));
const SchemaDetail = lazy(() => import('@/pages/schemas/SchemaDetail').then(m => ({ default: m.SchemaDetail })));
const JobList = lazy(() => import('@/pages/jobs/JobList').then(m => ({ default: m.JobList })));
const JobCreate = lazy(() => import('@/pages/jobs/JobCreate').then(m => ({ default: m.JobCreate })));
const JobDetail = lazy(() => import('@/pages/jobs/JobDetail').then(m => ({ default: m.JobDetail })));
const JobResults = lazy(() => import('@/pages/jobs/JobResults').then(m => ({ default: m.JobResults })));
const ApiTokens = lazy(() => import('@/pages/ApiTokens').then(m => ({ default: m.ApiTokens })));
const Profile = lazy(() => import('@/pages/Profile').then(m => ({ default: m.Profile })));
const Settings = lazy(() => import('@/pages/Settings').then(m => ({ default: m.Settings })));
const WorkflowBuilder = lazy(() => import('@/pages/WorkflowBuilder').then(m => ({ default: m.WorkflowBuilder })));
const WorkflowList = lazy(() => import('@/pages/workflows/WorkflowList').then(m => ({ default: m.WorkflowList })));
const WorkflowView = lazy(() => import('@/pages/workflows/WorkflowView').then(m => ({ default: m.WorkflowView })));
const WorkflowEdit = lazy(() => import('@/pages/workflows/WorkflowEdit').then(m => ({ default: m.WorkflowEdit })));
const ExecutionList = lazy(() => import('@/pages/workflows/ExecutionList').then(m => ({ default: m.ExecutionList })));
const ExecutionDetail = lazy(() => import('@/pages/workflows/ExecutionDetail').then(m => ({ default: m.ExecutionDetail })));
const ReviewQueue = lazy(() => import('@/pages/ReviewQueue').then(m => ({ default: m.ReviewQueue })));
const ReviewDetail = lazy(() => import('@/pages/ReviewDetail').then(m => ({ default: m.ReviewDetail })));
const Credentials = lazy(() => import('@/pages/Credentials').then(m => ({ default: m.Credentials })));
const InboundEmailList = lazy(() => import('@/pages/inbound-emails/InboundEmailList').then(m => ({ default: m.InboundEmailList })));
const InboundEmailForm = lazy(() => import('@/pages/inbound-emails/InboundEmailForm').then(m => ({ default: m.InboundEmailForm })));
const InboundEmailDetail = lazy(() => import('@/pages/inbound-emails/InboundEmailDetail').then(m => ({ default: m.InboundEmailDetail })));
const AdminDashboard = lazy(() => import('@/pages/admin/AdminDashboard').then(m => ({ default: m.AdminDashboard })));
const TenantList = lazy(() => import('@/pages/admin/TenantList').then(m => ({ default: m.TenantList })));
const TenantDetail = lazy(() => import('@/pages/admin/TenantDetail').then(m => ({ default: m.TenantDetail })));
const UserList = lazy(() => import('@/pages/admin/UserList').then(m => ({ default: m.UserList })));
const PlatformSettings = lazy(() => import('@/pages/admin/PlatformSettings').then(m => ({ default: m.PlatformSettings })));
const PricingManagement = lazy(() => import('@/pages/admin/PricingManagement').then(m => ({ default: m.PricingManagement })));
const PlatformApplications = lazy(() => import('@/pages/admin/PlatformApplications').then(m => ({ default: m.PlatformApplications })));
const PlatformApplicationDetail = lazy(() => import('@/pages/admin/PlatformApplicationDetail').then(m => ({ default: m.PlatformApplicationDetail })));

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingFallback />}>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/accept-invitation" element={<AcceptInvitation />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <AuthenticatedLayout>
                  <Dashboard />
                </AuthenticatedLayout>
              </ProtectedRoute>
            }
          />
        <Route
          path="/billing"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <BillingDetails />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/schema-builder"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <SchemaBuilder />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/schemas"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <SchemaList />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/schemas/:id"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <SchemaDetail />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/jobs"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <JobList />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/jobs/new"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <JobCreate />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/jobs/:id"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <JobDetail />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/jobs/:id/results"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <JobResults />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/documents"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <div className="p-6">
                  <h1 className="text-3xl font-bold">Documents</h1>
                  <p className="text-muted-foreground mt-2">Coming soon...</p>
                </div>
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/tokens"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <ApiTokens />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/credentials"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <Credentials />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <Profile />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <Settings />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        {/* Workflow Routes */}
        <Route
          path="/workflows"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <WorkflowList />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/workflows/new"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <WorkflowBuilder />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/workflows/:id"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <WorkflowView />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/workflows/:id/edit"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <WorkflowEdit />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/workflows/:id/executions"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <ExecutionList />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/workflows/executions/:id"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <ExecutionDetail />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        {/* Review Routes - HITL System */}
        <Route
          path="/reviews"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <ReviewQueue />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/reviews/:reviewId"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <ReviewDetail />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        {/* Inbound Email Routes */}
        <Route
          path="/inbound-emails"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <InboundEmailList />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/inbound-emails/new"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <InboundEmailForm />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/inbound-emails/:id"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <InboundEmailDetail />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/inbound-emails/:id/edit"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <InboundEmailForm />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        {/* Admin Routes - Require platform_admin role */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute requiredRole="platform_admin">
              <AuthenticatedLayout>
                <AdminDashboard />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/tenants"
          element={
            <ProtectedRoute requiredRole="platform_admin">
              <AuthenticatedLayout>
                <TenantList />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/tenants/:tenantId"
          element={
            <ProtectedRoute requiredRole="platform_admin">
              <AuthenticatedLayout>
                <TenantDetail />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute requiredRole="platform_admin">
              <AuthenticatedLayout>
                <UserList />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/settings"
          element={
            <ProtectedRoute requiredRole="platform_admin">
              <AuthenticatedLayout>
                <PlatformSettings />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/pricing"
          element={
            <ProtectedRoute requiredRole="platform_admin">
              <AuthenticatedLayout>
                <PricingManagement />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/platform"
          element={
            <ProtectedRoute requiredRole="platform_admin">
              <AuthenticatedLayout>
                <PlatformApplications />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/platform/:id"
          element={
            <ProtectedRoute requiredRole="platform_admin">
              <AuthenticatedLayout>
                <PlatformApplicationDetail />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        </Routes>
      </Suspense>
      <Toaster />
    </BrowserRouter>
  );
}

export default App;
