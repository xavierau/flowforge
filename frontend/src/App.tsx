import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Dashboard } from '@/pages/Dashboard';
import { BillingDetails } from '@/pages/BillingDetails';
import { SchemaBuilder } from '@/pages/SchemaBuilder';
import { Login } from '@/pages/Login';
import { Signup } from '@/pages/Signup';
import { SchemaList } from '@/pages/schemas/SchemaList';
import { SchemaDetail } from '@/pages/schemas/SchemaDetail';
import { JobList } from '@/pages/jobs/JobList';
import { JobCreate } from '@/pages/jobs/JobCreate';
import { JobDetail } from '@/pages/jobs/JobDetail';
import { JobResults } from '@/pages/jobs/JobResults';
import { ApiTokens } from '@/pages/ApiTokens';
import { Profile } from '@/pages/Profile';
import { Settings } from '@/pages/Settings';
import { AdminDashboard } from '@/pages/admin/AdminDashboard';
import { TenantList } from '@/pages/admin/TenantList';
import { TenantDetail } from '@/pages/admin/TenantDetail';
import { UserList } from '@/pages/admin/UserList';
import { PlatformSettings } from '@/pages/admin/PlatformSettings';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { AuthenticatedLayout } from '@/components/layout';
import { Toaster } from '@/components/ui/sonner';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
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
      </Routes>
      <Toaster />
    </BrowserRouter>
  );
}

export default App;
