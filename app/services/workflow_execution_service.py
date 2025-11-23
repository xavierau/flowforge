"""
Workflow execution service for orchestrating workflow runs with Netflix Conductor.

Handles:
- Starting workflow executions
- Syncing execution status from Conductor
- Tracking node-level execution details
- Canceling executions
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.enums import WorkflowExecutionStatus, WorkflowNodeExecutionStatus
from app.models.workflow import (
    Workflow,
    WorkflowExecution,
    WorkflowNodeExecution,
    WorkflowVersion,
)
from app.services.conductor_client import ConductorClient

logger = logging.getLogger(__name__)


class WorkflowExecutionServiceError(Exception):
    """Base exception for workflow execution service errors."""

    pass


class WorkflowExecutionService:
    """
    Service for workflow execution orchestration.

    This service:
    - Starts workflow executions in Netflix Conductor
    - Tracks execution status in our database
    - Syncs execution state from Conductor
    - Manages node-level execution tracking
    """

    def __init__(
        self, db: Session, conductor_client: Optional[ConductorClient] = None
    ):
        """
        Initialize workflow execution service.

        Args:
            db: Database session
            conductor_client: Conductor client (created if not provided)
        """
        self.db = db
        self.conductor_client = conductor_client or ConductorClient()

    async def execute_workflow(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        input_data: Dict,
        version_number: Optional[int] = None,
    ) -> WorkflowExecution:
        """
        Start a new workflow execution.

        Steps:
        1. Validate workflow exists and get version
        2. Register workflow with Conductor (if not already registered)
        3. Create WorkflowExecution record (status=PENDING)
        4. Start execution in Conductor
        5. Update execution with conductor_workflow_id (status=RUNNING)
        6. Create initial node execution records

        Args:
            workflow_id: Workflow ID
            tenant_id: Tenant ID
            input_data: Input data for workflow execution
            version_number: Specific version to execute (defaults to current version)

        Returns:
            WorkflowExecution record

        Raises:
            WorkflowExecutionServiceError: If execution cannot be started
        """
        try:
            # 1. Get workflow with tenant isolation
            workflow = (
                self.db.query(Workflow)
                .filter(
                    and_(
                        Workflow.id == workflow_id,
                        Workflow.tenant_id == tenant_id,
                        Workflow.is_active == True,
                    )
                )
                .first()
            )

            if not workflow:
                raise WorkflowExecutionServiceError("Workflow not found or inactive")

            # 2. Get workflow version
            if version_number is None:
                version_number = workflow.current_version_number

            workflow_version = (
                self.db.query(WorkflowVersion)
                .filter(
                    and_(
                        WorkflowVersion.workflow_id == workflow_id,
                        WorkflowVersion.version_number == version_number,
                    )
                )
                .first()
            )

            if not workflow_version:
                raise WorkflowExecutionServiceError(
                    f"Workflow version {version_number} not found"
                )

            # 3. Register workflow with Conductor (idempotent)
            await self._ensure_workflow_registered(workflow, workflow_version)

            # 4. Create WorkflowExecution record (PENDING)
            execution = WorkflowExecution(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                workflow_version_id=workflow_version.id,
                status=WorkflowExecutionStatus.PENDING.value,
                input_data=input_data,
            )
            self.db.add(execution)
            self.db.flush()  # Get execution ID

            # 5. Start execution in Conductor
            conductor_workflow_id, error = await self.conductor_client.start_workflow(
                workflow_name=workflow_version.conductor_workflow_name,
                version=version_number,
                input_data=input_data,
            )

            if error or not conductor_workflow_id:
                execution.status = WorkflowExecutionStatus.FAILED.value
                execution.error_message = f"Failed to start Conductor workflow: {error}"
                self.db.commit()
                raise WorkflowExecutionServiceError(execution.error_message)

            # 6. Update execution with Conductor ID and status
            execution.conductor_workflow_id = conductor_workflow_id
            execution.status = WorkflowExecutionStatus.RUNNING.value
            execution.started_at = datetime.utcnow()

            # 7. Create initial node execution records (all PENDING)
            await self._create_initial_node_executions(execution, workflow_version)

            self.db.commit()
            self.db.refresh(execution)

            logger.info(
                f"Started workflow execution {execution.id} "
                f"(conductor: {conductor_workflow_id}, tenant: {tenant_id})"
            )

            return execution

        except WorkflowExecutionServiceError:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error executing workflow: {e}")
            raise WorkflowExecutionServiceError(f"Failed to execute workflow: {e}")

    async def get_execution_status(
        self, execution_id: UUID, tenant_id: UUID
    ) -> Optional[WorkflowExecution]:
        """
        Get workflow execution status with sync from Conductor.

        This method:
        1. Queries execution from database
        2. Syncs status from Conductor if execution is still running
        3. Returns updated execution

        Args:
            execution_id: Execution ID
            tenant_id: Tenant ID

        Returns:
            WorkflowExecution or None if not found
        """
        # Get execution with tenant isolation
        execution = (
            self.db.query(WorkflowExecution)
            .filter(
                and_(
                    WorkflowExecution.id == execution_id,
                    WorkflowExecution.tenant_id == tenant_id,
                )
            )
            .first()
        )

        if not execution:
            return None

        # Sync status from Conductor if execution is not in terminal state
        terminal_statuses = [
            WorkflowExecutionStatus.COMPLETED.value,
            WorkflowExecutionStatus.FAILED.value,
            WorkflowExecutionStatus.CANCELLED.value,
            WorkflowExecutionStatus.TIMEOUT.value,
        ]

        if execution.status not in terminal_statuses and execution.conductor_workflow_id:
            try:
                await self._sync_execution_status(execution)
                self.db.commit()
                self.db.refresh(execution)
            except Exception as e:
                logger.error(f"Error syncing execution status: {e}")
                # Don't fail the request, just log the error

        return execution

    async def cancel_execution(
        self, execution_id: UUID, tenant_id: UUID
    ) -> Optional[WorkflowExecution]:
        """
        Cancel a running workflow execution.

        Args:
            execution_id: Execution ID
            tenant_id: Tenant ID

        Returns:
            Updated WorkflowExecution or None if not found

        Raises:
            WorkflowExecutionServiceError: If cancellation fails
        """
        try:
            # Get execution with tenant isolation
            execution = (
                self.db.query(WorkflowExecution)
                .filter(
                    and_(
                        WorkflowExecution.id == execution_id,
                        WorkflowExecution.tenant_id == tenant_id,
                    )
                )
                .first()
            )

            if not execution:
                return None

            # Check if execution is in a cancellable state
            cancellable_statuses = [
                WorkflowExecutionStatus.PENDING.value,
                WorkflowExecutionStatus.RUNNING.value,
                WorkflowExecutionStatus.PAUSED.value,
            ]

            if execution.status not in cancellable_statuses:
                raise WorkflowExecutionServiceError(
                    f"Cannot cancel execution in status: {execution.status}"
                )

            # Cancel in Conductor if execution has started
            if execution.conductor_workflow_id:
                success, error = await self.conductor_client.cancel_workflow(
                    execution.conductor_workflow_id
                )

                if not success:
                    raise WorkflowExecutionServiceError(
                        f"Failed to cancel Conductor workflow: {error}"
                    )

            # Update execution status
            execution.status = WorkflowExecutionStatus.CANCELLED.value
            execution.completed_at = datetime.utcnow()

            # Update all pending/running node executions to SKIPPED
            self.db.query(WorkflowNodeExecution).filter(
                and_(
                    WorkflowNodeExecution.workflow_execution_id == execution_id,
                    WorkflowNodeExecution.status.in_(
                        [
                            WorkflowNodeExecutionStatus.PENDING.value,
                            WorkflowNodeExecutionStatus.RUNNING.value,
                        ]
                    ),
                )
            ).update(
                {
                    WorkflowNodeExecution.status: WorkflowNodeExecutionStatus.SKIPPED.value,
                    WorkflowNodeExecution.completed_at: datetime.utcnow(),
                }
            )

            self.db.commit()
            self.db.refresh(execution)

            logger.info(
                f"Cancelled workflow execution {execution_id} (tenant: {tenant_id})"
            )

            return execution

        except WorkflowExecutionServiceError:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cancelling execution: {e}")
            raise WorkflowExecutionServiceError(f"Failed to cancel execution: {e}")

    def list_workflow_executions(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[WorkflowExecution], int]:
        """
        List executions for a workflow with pagination.

        Args:
            workflow_id: Workflow ID
            tenant_id: Tenant ID
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Tuple of (executions list, total count)
        """
        # Verify workflow belongs to tenant
        workflow = (
            self.db.query(Workflow)
            .filter(
                and_(
                    Workflow.id == workflow_id,
                    Workflow.tenant_id == tenant_id,
                )
            )
            .first()
        )

        if not workflow:
            return [], 0

        query = self.db.query(WorkflowExecution).filter(
            WorkflowExecution.workflow_id == workflow_id
        )

        # Get total count
        total = query.count()

        # Paginate
        executions = (
            query.order_by(WorkflowExecution.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return executions, total

    def get_node_executions(
        self, execution_id: UUID, tenant_id: UUID
    ) -> List[WorkflowNodeExecution]:
        """
        Get all node executions for a workflow execution.

        Args:
            execution_id: Execution ID
            tenant_id: Tenant ID

        Returns:
            List of WorkflowNodeExecution records (ordered by execution_order)
        """
        # Verify execution belongs to tenant
        execution = (
            self.db.query(WorkflowExecution)
            .filter(
                and_(
                    WorkflowExecution.id == execution_id,
                    WorkflowExecution.tenant_id == tenant_id,
                )
            )
            .first()
        )

        if not execution:
            return []

        return (
            self.db.query(WorkflowNodeExecution)
            .filter(WorkflowNodeExecution.workflow_execution_id == execution_id)
            .order_by(WorkflowNodeExecution.execution_order)
            .all()
        )

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    async def _ensure_workflow_registered(
        self, workflow: Workflow, workflow_version: WorkflowVersion
    ):
        """
        Ensure workflow is registered with Conductor.

        This is idempotent - if workflow is already registered, it will be updated.

        Args:
            workflow: Workflow model
            workflow_version: WorkflowVersion model

        Raises:
            WorkflowExecutionServiceError: If registration fails
        """
        try:
            # Translate workflow definition to Conductor format
            from app.schemas.workflow import WorkflowDefinition

            definition = WorkflowDefinition(**workflow_version.definition)

            conductor_def = self.conductor_client.translate_workflow_to_conductor(
                workflow_id=workflow.id,
                workflow_name=workflow.name,
                version_number=workflow_version.version_number,
                definition=definition,
            )

            # Register with Conductor
            success, error = await self.conductor_client.register_workflow(
                conductor_def
            )

            if not success:
                raise WorkflowExecutionServiceError(
                    f"Failed to register workflow with Conductor: {error}"
                )

        except Exception as e:
            logger.error(f"Error registering workflow: {e}")
            raise WorkflowExecutionServiceError(f"Workflow registration failed: {e}")

    async def _create_initial_node_executions(
        self, execution: WorkflowExecution, workflow_version: WorkflowVersion
    ):
        """
        Create initial node execution records for all nodes in workflow.

        All nodes start in PENDING status.

        Args:
            execution: WorkflowExecution record
            workflow_version: WorkflowVersion record
        """
        definition_data = workflow_version.definition
        nodes = definition_data.get("nodes", [])

        # Determine execution order
        from app.schemas.workflow import WorkflowDefinition

        definition = WorkflowDefinition(**definition_data)
        execution_order = self.conductor_client._determine_execution_order(definition)

        # Create node execution records
        for i, node_id in enumerate(execution_order):
            # Find node in definition
            node_data = next((n for n in nodes if n["id"] == node_id), None)
            if not node_data:
                continue

            node_execution = WorkflowNodeExecution(
                workflow_execution_id=execution.id,
                node_id=node_id,
                node_type=node_data["data"]["type"],
                node_label=node_data["data"]["label"],
                status=WorkflowNodeExecutionStatus.PENDING.value,
                execution_order=i,
            )
            self.db.add(node_execution)

    async def _sync_execution_status(self, execution: WorkflowExecution):
        """
        Sync execution status from Conductor.

        Updates:
        - Execution status
        - Output data (if completed)
        - Error information (if failed)
        - Node execution status

        Args:
            execution: WorkflowExecution record (will be updated)
        """
        if not execution.conductor_workflow_id:
            return

        # Get status from Conductor
        conductor_data, error = await self.conductor_client.get_execution_status(
            execution.conductor_workflow_id
        )

        if error or not conductor_data:
            logger.warning(
                f"Could not get Conductor status for execution {execution.id}: {error}"
            )
            return

        # Map Conductor status to our status
        conductor_status = conductor_data.get("status")
        if not conductor_status:
            return

        mapped_status = self.conductor_client.map_conductor_status_to_ours(
            conductor_status
        )

        # Update execution status
        old_status = execution.status
        execution.status = mapped_status.value

        # Update completed_at if execution finished
        if mapped_status in [
            WorkflowExecutionStatus.COMPLETED,
            WorkflowExecutionStatus.FAILED,
            WorkflowExecutionStatus.CANCELLED,
            WorkflowExecutionStatus.TIMEOUT,
        ]:
            if not execution.completed_at:
                execution.completed_at = datetime.utcnow()

            # Update output data for completed workflows
            if mapped_status == WorkflowExecutionStatus.COMPLETED:
                execution.output_data = conductor_data.get("output", {})

            # Update error information for failed workflows
            if mapped_status == WorkflowExecutionStatus.FAILED:
                execution.error_message = conductor_data.get("reasonForIncompletion")

        # Sync node execution status
        await self._sync_node_executions(execution, conductor_data)

        logger.info(
            f"Synced execution {execution.id}: {old_status} → {execution.status}"
        )

    async def _sync_node_executions(
        self, execution: WorkflowExecution, conductor_data: Dict
    ):
        """
        Sync node execution status from Conductor task status.

        Args:
            execution: WorkflowExecution record
            conductor_data: Conductor workflow execution data
        """
        tasks = conductor_data.get("tasks", [])
        if not tasks:
            return

        # Get all node executions for this workflow execution
        node_executions = (
            self.db.query(WorkflowNodeExecution)
            .filter(WorkflowNodeExecution.workflow_execution_id == execution.id)
            .all()
        )

        # Map node_id to node_execution
        node_exec_map = {ne.node_id: ne for ne in node_executions}

        # Update node executions from Conductor task status
        for task in tasks:
            task_ref_name = task.get("referenceTaskName")
            if not task_ref_name or task_ref_name not in node_exec_map:
                continue

            node_exec = node_exec_map[task_ref_name]

            # Map Conductor task status to our status
            task_status = task.get("status")
            if task_status:
                mapped_status = (
                    self.conductor_client.map_conductor_task_status_to_ours(
                        task_status
                    )
                )
                node_exec.status = mapped_status.value

            # Update timestamps
            if task.get("startTime") and not node_exec.started_at:
                # Convert milliseconds to datetime
                node_exec.started_at = datetime.utcfromtimestamp(
                    task["startTime"] / 1000
                )

            if task.get("endTime") and not node_exec.completed_at:
                node_exec.completed_at = datetime.utcfromtimestamp(
                    task["endTime"] / 1000
                )

            # Update input/output data
            if task.get("inputData"):
                node_exec.input_data = task["inputData"]

            if task.get("outputData"):
                node_exec.output_data = task["outputData"]

            # Update error information
            if task.get("reasonForIncompletion"):
                node_exec.error_message = task["reasonForIncompletion"]

    async def close(self):
        """Close the Conductor client connection."""
        if self.conductor_client:
            await self.conductor_client.close()

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
