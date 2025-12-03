/**
 * WorkflowView - Read-only workflow detail page
 *
 * Displays workflow metadata and visual canvas preview.
 * Provides actions for editing, cloning, viewing executions, and archiving.
 */

import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import {
  ArrowLeft,
  Pencil,
  Play,
  Copy,
  Archive,
  ArchiveRestore,
  Loader2,
} from 'lucide-react';

import { Page, PageHeader, PageContent } from '@/components/layout';
import { WorkflowCanvas } from '@/components/workflow/WorkflowCanvas';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  getWorkflow,
  cloneWorkflow,
  archiveWorkflow,
  restoreWorkflow,
} from '@/services/workflow.service';
import type { WorkflowResponse, WorkflowDefinition } from '@/types/workflow';

/**
 * WorkflowView displays a read-only view of a workflow with:
 * - Workflow metadata (version, status, dates)
 * - Visual canvas preview
 * - Action buttons for editing, cloning, archiving
 */
export function WorkflowView() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  const [workflow, setWorkflow] = useState<WorkflowResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCloning, setIsCloning] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);

  /**
   * Fetch workflow data on mount
   */
  const loadWorkflow = useCallback(async () => {
    if (!id) {
      toast.error('Workflow ID is required');
      navigate('/workflows');
      return;
    }

    try {
      setIsLoading(true);
      const data = await getWorkflow(id);
      setWorkflow(data);
    } catch (error) {
      toast.error('Failed to load workflow', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
      navigate('/workflows');
    } finally {
      setIsLoading(false);
    }
  }, [id, navigate]);

  useEffect(() => {
    loadWorkflow();
  }, [loadWorkflow]);

  /**
   * Clone workflow and navigate to edit page
   */
  const handleClone = async () => {
    if (!id) return;

    try {
      setIsCloning(true);
      const newWorkflow = await cloneWorkflow(id);
      toast.success('Workflow cloned successfully');
      navigate(`/workflows/${newWorkflow.id}/edit`);
    } catch (error) {
      toast.error('Failed to clone workflow', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsCloning(false);
    }
  };

  /**
   * Archive or restore workflow based on current state
   */
  const handleArchiveToggle = async () => {
    if (!id || !workflow) return;

    try {
      setIsArchiving(true);
      if (workflow.isArchived) {
        await restoreWorkflow(id);
        toast.success('Workflow restored successfully');
      } else {
        await archiveWorkflow(id);
        toast.success('Workflow archived successfully');
      }
      await loadWorkflow();
    } catch (error) {
      toast.error(
        workflow.isArchived
          ? 'Failed to restore workflow'
          : 'Failed to archive workflow',
        {
          description: error instanceof Error ? error.message : 'Unknown error',
        }
      );
    } finally {
      setIsArchiving(false);
    }
  };

  /**
   * Get workflow definition from current version
   */
  const getDefinition = (): WorkflowDefinition | null => {
    return workflow?.currentVersion?.definition || null;
  };

  /**
   * Get status badge based on workflow state
   */
  const getStatusBadge = () => {
    if (!workflow) return null;

    if (workflow.isArchived) {
      return (
        <Badge variant="outline" className="bg-gray-100 text-gray-600">
          Archived
        </Badge>
      );
    }

    if (workflow.isActive) {
      return (
        <Badge variant="default" className="bg-green-100 text-green-700">
          Active
        </Badge>
      );
    }

    return (
      <Badge variant="secondary" className="bg-yellow-100 text-yellow-700">
        Draft
      </Badge>
    );
  };

  // Loading state
  if (isLoading) {
    return (
      <Page>
        <PageContent>
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </PageContent>
      </Page>
    );
  }

  // No workflow found
  if (!workflow) {
    return null;
  }

  const definition = getDefinition();

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Workflows', href: '/workflows' },
          { label: workflow.name },
        ]}
        title={workflow.name}
        subtitle={workflow.description || 'No description'}
      />
      <PageContent>
        {/* Action Buttons */}
        <div className="flex gap-2 mb-6">
          <Button variant="outline" onClick={() => navigate('/workflows')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <Button onClick={() => navigate(`/workflows/${id}/edit`)}>
            <Pencil className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <Button
            variant="outline"
            onClick={() => navigate(`/workflows/${id}/executions`)}
          >
            <Play className="mr-2 h-4 w-4" />
            Executions
          </Button>
          <Button
            variant="outline"
            onClick={handleClone}
            disabled={isCloning}
          >
            {isCloning ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Copy className="mr-2 h-4 w-4" />
            )}
            Clone
          </Button>
          <Button
            variant="outline"
            onClick={handleArchiveToggle}
            disabled={isArchiving}
          >
            {isArchiving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : workflow.isArchived ? (
              <ArchiveRestore className="mr-2 h-4 w-4" />
            ) : (
              <Archive className="mr-2 h-4 w-4" />
            )}
            {workflow.isArchived ? 'Restore' : 'Archive'}
          </Button>
        </div>

        {/* Metadata Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Workflow Information</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm font-medium text-muted-foreground">
                Version
              </div>
              <div>v{workflow.currentVersionNumber}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground">
                Status
              </div>
              <div className="mt-1">{getStatusBadge()}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground">
                Created
              </div>
              <div>{new Date(workflow.createdAt).toLocaleDateString()}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground">
                Updated
              </div>
              <div>{new Date(workflow.updatedAt).toLocaleDateString()}</div>
            </div>
          </CardContent>
        </Card>

        {/* Canvas Preview */}
        <Card>
          <CardHeader>
            <CardTitle>Workflow Canvas</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[500px] border rounded-lg overflow-hidden">
              {definition ? (
                <WorkflowCanvas
                  nodes={definition.nodes}
                  edges={definition.edges}
                  readOnly
                />
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  No workflow definition available
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </PageContent>
    </Page>
  );
}
