/**
 * WorkflowEdit - Wrapper component for editing existing workflows
 *
 * Responsibilities:
 * - Load workflow data from API based on URL parameter
 * - Display loading state while fetching
 * - Handle and display errors
 * - Render WorkflowBuilder once data is loaded
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import { WorkflowBuilder } from '@/pages/WorkflowBuilder';
import { useWorkflowStore } from '@/store/workflowStore';
import { Button } from '@/components/ui/button';

export function WorkflowEdit() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadWorkflowFromApi = useWorkflowStore((state) => state.loadWorkflowFromApi);

  useEffect(() => {
    if (!id) {
      navigate('/workflows');
      return;
    }

    const loadWorkflow = async () => {
      try {
        setIsLoading(true);
        setError(null);
        await loadWorkflowFromApi(id);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load workflow';
        setError(message);
        toast.error(message);
      } finally {
        setIsLoading(false);
      }
    };

    loadWorkflow();
  }, [id, loadWorkflowFromApi, navigate]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading workflow...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-destructive mb-4">{error}</p>
          <Button onClick={() => navigate('/workflows')}>Back to Workflows</Button>
        </div>
      </div>
    );
  }

  // Render the existing WorkflowBuilder - it will use the loaded state from the store
  return <WorkflowBuilder />;
}
