"""
Execution Tracker Service

Tracks workflow execution state in the database.
Updates WorkflowNodeExecution records with status, input/output data, and timing.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.models.workflow import WorkflowExecution, WorkflowNodeExecution
from app.models.enums import WorkflowExecutionStatus, WorkflowNodeStatus


class ExecutionTracker:
    """
    Service for tracking workflow and node execution state.

    Updates database records with execution progress, results, and errors.
    """

    def __init__(self, db: Session):
        """
        Initialize execution tracker.

        Args:
            db: Database session
        """
        self.db = db

    def start_workflow_execution(
        self,
        workflow_id: str,
        tenant_id: str,
        trigger_data: Optional[Dict[str, Any]] = None
    ) -> WorkflowExecution:
        """
        Create and start a new workflow execution.

        Args:
            workflow_id: Workflow definition ID
            tenant_id: Tenant ID
            trigger_data: Initial trigger data

        Returns:
            Created WorkflowExecution record
        """
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            status=WorkflowExecutionStatus.RUNNING,
            started_at=datetime.utcnow(),
            trigger_data=trigger_data or {},
        )

        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)

        return execution

    def complete_workflow_execution(
        self,
        execution_id: str,
        status: WorkflowExecutionStatus,
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """
        Mark workflow execution as completed.

        Args:
            execution_id: Workflow execution ID
            status: Final status
            output_data: Output data from workflow
            error: Error message if failed
        """
        execution = self.db.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id
        ).first()

        if not execution:
            raise ValueError(f"Workflow execution not found: {execution_id}")

        execution.status = status
        execution.completed_at = datetime.utcnow()

        if output_data:
            execution.output_data = output_data

        if error:
            execution.error = error

        self.db.commit()

    def start_node_execution(
        self,
        execution_id: str,
        node_id: str,
        conductor_task_id: str,
        input_data: Optional[Dict[str, Any]] = None
    ) -> WorkflowNodeExecution:
        """
        Create and start a node execution.

        Args:
            execution_id: Workflow execution ID
            node_id: Node ID from workflow definition
            conductor_task_id: Conductor task ID
            input_data: Input data for the node

        Returns:
            Created WorkflowNodeExecution record
        """
        node_execution = WorkflowNodeExecution(
            execution_id=execution_id,
            node_id=node_id,
            conductor_task_id=conductor_task_id,
            status=WorkflowNodeStatus.RUNNING,
            started_at=datetime.utcnow(),
            input_data=input_data or {},
        )

        self.db.add(node_execution)
        self.db.commit()
        self.db.refresh(node_execution)

        return node_execution

    def update_node_status(
        self,
        conductor_task_id: str,
        status: WorkflowNodeStatus
    ):
        """
        Update node execution status.

        Args:
            conductor_task_id: Conductor task ID
            status: New status
        """
        node_execution = self.db.query(WorkflowNodeExecution).filter(
            WorkflowNodeExecution.conductor_task_id == conductor_task_id
        ).first()

        if not node_execution:
            raise ValueError(
                f"Node execution not found for task: {conductor_task_id}"
            )

        node_execution.status = status
        self.db.commit()

    def complete_node_execution(
        self,
        conductor_task_id: str,
        status: WorkflowNodeStatus,
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """
        Mark node execution as completed.

        Args:
            conductor_task_id: Conductor task ID
            status: Final status
            output_data: Output data from node
            error: Error message if failed
        """
        node_execution = self.db.query(WorkflowNodeExecution).filter(
            WorkflowNodeExecution.conductor_task_id == conductor_task_id
        ).first()

        if not node_execution:
            raise ValueError(
                f"Node execution not found for task: {conductor_task_id}"
            )

        node_execution.status = status
        node_execution.completed_at = datetime.utcnow()

        if output_data:
            node_execution.output_data = output_data

        if error:
            node_execution.error = error

        # Calculate duration
        if node_execution.started_at:
            duration = (node_execution.completed_at - node_execution.started_at).total_seconds()
            node_execution.duration_seconds = duration

        self.db.commit()

    def get_execution_state(self, execution_id: str) -> Dict[str, Any]:
        """
        Get current execution state including all node outputs.

        Args:
            execution_id: Workflow execution ID

        Returns:
            Dictionary with execution status and node outputs
        """
        execution = self.db.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id
        ).first()

        if not execution:
            raise ValueError(f"Workflow execution not found: {execution_id}")

        # Collect node outputs
        node_outputs = {}
        for node_exec in execution.node_executions:
            if node_exec.output_data:
                node_outputs[node_exec.node_id] = node_exec.output_data

        return {
            "execution_id": execution.id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "trigger_data": execution.trigger_data,
            "output_data": execution.output_data,
            "node_outputs": node_outputs,
            "error": execution.error,
        }

    def get_node_outputs(self, execution_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all node outputs for expression resolution.

        Args:
            execution_id: Workflow execution ID

        Returns:
            Dictionary mapping node IDs to their output data
        """
        execution = self.db.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id
        ).first()

        if not execution:
            return {}

        node_outputs = {}
        for node_exec in execution.node_executions:
            if node_exec.status == WorkflowNodeStatus.COMPLETED and node_exec.output_data:
                node_outputs[node_exec.node_id] = node_exec.output_data

        return node_outputs
