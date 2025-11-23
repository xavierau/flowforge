"""
Workflow API endpoints.

Provides RESTful API for:
- Workflow CRUD operations
- Workflow execution management
- Node execution tracking
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies.auth import require_permission_flexible
from app.models import User
from app.models.workflow import Workflow, WorkflowVersion
from app.schemas.workflow import (
    ExecuteWorkflowRequest,
    WorkflowCreateRequest,
    WorkflowExecutionListResponse,
    WorkflowExecutionResponse,
    WorkflowListResponse,
    WorkflowNodeExecutionResponse,
    WorkflowResponse,
    WorkflowUpdateRequest,
    WorkflowVersionResponse,
)
from app.services.conductor_client import ConductorClient
from app.services.workflow_execution_service import (
    WorkflowExecutionService,
    WorkflowExecutionServiceError,
)
from app.services.workflow_service import WorkflowService, WorkflowServiceError

router = APIRouter()


# ============================================================================
# Workflow CRUD Endpoints
# ============================================================================


@router.post(
    "/workflows",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workflow(
    request: WorkflowCreateRequest,
    current_user: User = Depends(require_permission_flexible("workflows:create")),
    db: Session = Depends(get_db),
):
    """
    Create a new workflow.

    Creates a workflow with initial version (v1).

    **Required Permission:** `workflows:create`

    **Supports:** JWT + API tokens
    """
    try:
        service = WorkflowService(db)
        workflow, workflow_version = await service.create_workflow(
            tenant_id=current_user.tenant_id,
            request=request,
        )

        # Build response with current version
        response_data = WorkflowResponse.model_validate(workflow)
        response_data.current_version = WorkflowVersionResponse.model_validate(
            workflow_version
        )

        return response_data

    except WorkflowServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow: {str(e)}",
        )


@router.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(require_permission_flexible("workflows:read")),
    db: Session = Depends(get_db),
):
    """
    List workflows for the current tenant.

    Supports pagination and filtering by active status.

    **Required Permission:** `workflows:read`

    **Supports:** JWT + API tokens
    """
    try:
        service = WorkflowService(db)
        workflows, total = service.list_workflows(
            tenant_id=current_user.tenant_id,
            page=page,
            page_size=page_size,
            is_active=is_active,
        )

        # Load current versions for each workflow
        workflow_responses = []
        for workflow in workflows:
            current_version = service.get_current_workflow_version(
                workflow_id=workflow.id,
                tenant_id=current_user.tenant_id,
            )

            response_data = WorkflowResponse.model_validate(workflow)
            if current_version:
                response_data.current_version = (
                    WorkflowVersionResponse.model_validate(current_version)
                )

            workflow_responses.append(response_data)

        return WorkflowListResponse(
            workflows=workflow_responses,
            total=total,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {str(e)}",
        )


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    current_user: User = Depends(require_permission_flexible("workflows:read")),
    db: Session = Depends(get_db),
):
    """
    Get a workflow by ID.

    Returns workflow with current version details.

    **Required Permission:** `workflows:read`

    **Supports:** JWT + API tokens
    """
    try:
        service = WorkflowService(db)
        workflow = service.get_workflow(
            workflow_id=workflow_id,
            tenant_id=current_user.tenant_id,
        )

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found",
            )

        # Load current version
        current_version = service.get_current_workflow_version(
            workflow_id=workflow.id,
            tenant_id=current_user.tenant_id,
        )

        response_data = WorkflowResponse.model_validate(workflow)
        if current_version:
            response_data.current_version = WorkflowVersionResponse.model_validate(
                current_version
            )

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow: {str(e)}",
        )


@router.put("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    request: WorkflowUpdateRequest,
    current_user: User = Depends(require_permission_flexible("workflows:update")),
    db: Session = Depends(get_db),
):
    """
    Update a workflow.

    If definition is provided, creates a new version.

    **Required Permission:** `workflows:update`

    **Supports:** JWT + API tokens
    """
    try:
        service = WorkflowService(db)
        workflow, new_version = await service.update_workflow(
            workflow_id=workflow_id,
            tenant_id=current_user.tenant_id,
            request=request,
        )

        # Load current version
        current_version = service.get_current_workflow_version(
            workflow_id=workflow.id,
            tenant_id=current_user.tenant_id,
        )

        response_data = WorkflowResponse.model_validate(workflow)
        if current_version:
            response_data.current_version = WorkflowVersionResponse.model_validate(
                current_version
            )

        return response_data

    except WorkflowServiceError as e:
        # Check if it's a not found error
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update workflow: {str(e)}",
        )


@router.delete("/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    current_user: User = Depends(require_permission_flexible("workflows:delete")),
    db: Session = Depends(get_db),
):
    """
    Delete a workflow (soft delete).

    Sets `is_active=False` instead of permanently deleting.

    **Required Permission:** `workflows:delete`

    **Supports:** JWT + API tokens
    """
    try:
        service = WorkflowService(db)
        deleted = await service.delete_workflow(
            workflow_id=workflow_id,
            tenant_id=current_user.tenant_id,
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found",
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workflow: {str(e)}",
        )


# ============================================================================
# Workflow Execution Endpoints
# ============================================================================


@router.post(
    "/workflows/{workflow_id}/execute",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def execute_workflow(
    workflow_id: UUID,
    request: ExecuteWorkflowRequest,
    current_user: User = Depends(require_permission_flexible("workflows:execute")),
    db: Session = Depends(get_db),
):
    """
    Execute a workflow.

    Starts a new workflow execution in Netflix Conductor.

    **Required Permission:** `workflows:execute`

    **Supports:** JWT + API tokens
    """
    try:
        async with ConductorClient() as conductor_client:
            service = WorkflowExecutionService(db, conductor_client)

            execution = await service.execute_workflow(
                workflow_id=workflow_id,
                tenant_id=current_user.tenant_id,
                input_data=request.input_data,
                version_number=request.version_number,
            )

            return WorkflowExecutionResponse.model_validate(execution)

    except WorkflowExecutionServiceError as e:
        # Check if it's a not found error
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute workflow: {str(e)}",
        )


@router.get(
    "/workflows/executions/{execution_id}", response_model=WorkflowExecutionResponse
)
async def get_execution_status(
    execution_id: UUID,
    current_user: User = Depends(require_permission_flexible("workflows:read")),
    db: Session = Depends(get_db),
):
    """
    Get workflow execution status.

    Syncs status from Conductor if execution is still running.

    **Required Permission:** `workflows:read`

    **Supports:** JWT + API tokens
    """
    try:
        async with ConductorClient() as conductor_client:
            service = WorkflowExecutionService(db, conductor_client)

            execution = await service.get_execution_status(
                execution_id=execution_id,
                tenant_id=current_user.tenant_id,
            )

            if not execution:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Execution not found",
                )

            return WorkflowExecutionResponse.model_validate(execution)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution status: {str(e)}",
        )


@router.delete(
    "/workflows/executions/{execution_id}",
    response_model=WorkflowExecutionResponse,
)
async def cancel_execution(
    execution_id: UUID,
    current_user: User = Depends(require_permission_flexible("workflows:execute")),
    db: Session = Depends(get_db),
):
    """
    Cancel a running workflow execution.

    Terminates the execution in Conductor and marks all pending nodes as SKIPPED.

    **Required Permission:** `workflows:execute`

    **Supports:** JWT + API tokens
    """
    try:
        async with ConductorClient() as conductor_client:
            service = WorkflowExecutionService(db, conductor_client)

            execution = await service.cancel_execution(
                execution_id=execution_id,
                tenant_id=current_user.tenant_id,
            )

            if not execution:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Execution not found",
                )

            return WorkflowExecutionResponse.model_validate(execution)

    except WorkflowExecutionServiceError as e:
        # Check if it's a not found error
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        # Check if it's a state error
        if "cannot cancel" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel execution: {str(e)}",
        )


@router.get(
    "/workflows/{workflow_id}/executions",
    response_model=WorkflowExecutionListResponse,
)
async def list_workflow_executions(
    workflow_id: UUID,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_permission_flexible("workflows:read")),
    db: Session = Depends(get_db),
):
    """
    List executions for a workflow.

    Returns paginated list of workflow executions.

    **Required Permission:** `workflows:read`

    **Supports:** JWT + API tokens
    """
    try:
        async with ConductorClient() as conductor_client:
            service = WorkflowExecutionService(db, conductor_client)

            executions, total = service.list_workflow_executions(
                workflow_id=workflow_id,
                tenant_id=current_user.tenant_id,
                page=page,
                page_size=page_size,
            )

            execution_responses = [
                WorkflowExecutionResponse.model_validate(execution)
                for execution in executions
            ]

            return WorkflowExecutionListResponse(
                executions=execution_responses,
                total=total,
                page=page,
                page_size=page_size,
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list executions: {str(e)}",
        )


@router.get(
    "/workflows/executions/{execution_id}/nodes",
    response_model=list[WorkflowNodeExecutionResponse],
)
async def get_node_executions(
    execution_id: UUID,
    current_user: User = Depends(require_permission_flexible("workflows:read")),
    db: Session = Depends(get_db),
):
    """
    Get node execution details for a workflow execution.

    Returns all node executions ordered by execution order.

    **Required Permission:** `workflows:read`

    **Supports:** JWT + API tokens
    """
    try:
        async with ConductorClient() as conductor_client:
            service = WorkflowExecutionService(db, conductor_client)

            node_executions = service.get_node_executions(
                execution_id=execution_id,
                tenant_id=current_user.tenant_id,
            )

            return [
                WorkflowNodeExecutionResponse.model_validate(node_exec)
                for node_exec in node_executions
            ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get node executions: {str(e)}",
        )


@router.post(
    "/workflows/test-node",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def test_node(
    current_user: User = Depends(require_permission_flexible("workflows:create")),
    db: Session = Depends(get_db),
):
    """
    Test a single workflow node (NOT IMPLEMENTED).

    This endpoint is reserved for future implementation of single-node testing.

    **Required Permission:** `workflows:create`

    **Supports:** JWT + API tokens
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Single node testing not yet implemented",
    )
