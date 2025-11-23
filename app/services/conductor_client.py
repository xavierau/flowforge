"""
Netflix Conductor client service.

Handles all interactions with the Conductor workflow orchestration engine via REST API.
Conductor API documentation: https://conductor.netflix.com/documentation/api/
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import httpx

from app.config import settings
from app.models.enums import (
    NodeType,
    WorkflowExecutionStatus,
    WorkflowNodeExecutionStatus,
)
from app.schemas.workflow import WorkflowDefinition, WorkflowNode

logger = logging.getLogger(__name__)


class ConductorClientError(Exception):
    """Base exception for Conductor client errors."""

    pass


class ConductorClient:
    """
    Client for interacting with Netflix Conductor server.

    This client handles:
    - Translating our workflow definitions to Conductor format
    - Registering workflows with Conductor
    - Starting workflow executions
    - Polling execution status
    - Mapping Conductor status to our status enums
    """

    def __init__(
        self,
        conductor_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """
        Initialize Conductor client.

        Args:
            conductor_url: Base URL of Conductor server (defaults to settings)
            timeout: Request timeout in seconds (defaults to settings)
        """
        self.conductor_url = (conductor_url or settings.conductor_url).rstrip("/")
        self.timeout = timeout or settings.conductor_timeout
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    def translate_workflow_to_conductor(
        self,
        workflow_id: UUID,
        workflow_name: str,
        version_number: int,
        definition: WorkflowDefinition,
    ) -> Dict[str, Any]:
        """
        Translate our workflow definition to Conductor workflow format.

        Our format: Visual workflow with nodes and edges
        Conductor format: Linear task list with dependencies

        Args:
            workflow_id: Our internal workflow ID
            workflow_name: Workflow name
            version_number: Version number
            definition: Our workflow definition (nodes + edges)

        Returns:
            Conductor workflow definition dict

        Raises:
            ConductorClientError: If workflow cannot be translated
        """
        try:
            # Determine execution order using topological sort
            execution_order = self._determine_execution_order(definition)

            # Convert nodes to Conductor tasks
            conductor_tasks = []
            for i, node_id in enumerate(execution_order):
                node = next((n for n in definition.nodes if n.id == node_id), None)
                if not node:
                    continue

                task = self._node_to_conductor_task(node, i)
                conductor_tasks.append(task)

            # Build Conductor workflow definition
            conductor_workflow = {
                "name": f"{workflow_name}_v{version_number}",
                "description": f"Workflow {workflow_name} version {version_number}",
                "version": version_number,
                "tasks": conductor_tasks,
                "inputParameters": [],
                "outputParameters": {},
                "schemaVersion": 2,
                "restartable": True,
                "ownerEmail": "system@workflow-engine.com",
                "timeoutPolicy": "ALERT_ONLY",
                "timeoutSeconds": 3600,  # 1 hour default timeout
            }

            return conductor_workflow

        except Exception as e:
            logger.error(f"Failed to translate workflow to Conductor format: {e}")
            raise ConductorClientError(f"Workflow translation failed: {e}")

    def _determine_execution_order(
        self, definition: WorkflowDefinition
    ) -> List[str]:
        """
        Determine node execution order using topological sort.

        Args:
            definition: Workflow definition with nodes and edges

        Returns:
            List of node IDs in execution order

        Raises:
            ConductorClientError: If workflow has cycles
        """
        # Build adjacency list from edges
        graph: Dict[str, List[str]] = {node.id: [] for node in definition.nodes}
        in_degree: Dict[str, int] = {node.id: 0 for node in definition.nodes}

        for edge in definition.edges:
            graph[edge.source].append(edge.target)
            in_degree[edge.target] += 1

        # Find all nodes with no incoming edges (entry points)
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]

        # Process nodes in topological order
        result = []
        while queue:
            current = queue.pop(0)
            result.append(current)

            # Reduce in-degree for neighbors
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for cycles
        if len(result) != len(definition.nodes):
            raise ConductorClientError("Workflow contains cycles")

        return result

    def _node_to_conductor_task(
        self, node: WorkflowNode, order: int
    ) -> Dict[str, Any]:
        """
        Convert a workflow node to a Conductor task definition.

        Args:
            node: Workflow node
            order: Execution order index

        Returns:
            Conductor task dict
        """
        node_type = node.data.type

        # Base task structure
        task = {
            "name": f"{node_type}_{node.id}",
            "taskReferenceName": node.id,
            "inputParameters": {
                "nodeId": node.id,
                "nodeType": node_type,
                "nodeLabel": node.data.label,
                "nodeConfig": (
                    node.data.config.model_dump()
                    if hasattr(node.data, "config")
                    else {}
                ),
            },
            "type": "SIMPLE",  # All our nodes are worker tasks
            "optional": False,
        }

        # Map node types to Conductor task types
        if node_type == NodeType.HTTP_TRIGGER:
            # HTTP Trigger is a pass-through task - doesn't execute anything
            # It's just the workflow entry point, passes input to next node
            task["type"] = "SIMPLE"
            task["inputParameters"]["trigger_type"] = "http"
            # Mark as optional so workflow continues even if no worker picks it up
            task["optional"] = True
        elif node_type == NodeType.HTTP_REQUEST:
            task["type"] = "HTTP"
        elif node_type == NodeType.IF:
            # Conditional branching
            task["type"] = "SWITCH"
            task["evaluatorType"] = "javascript"
            task["expression"] = node.data.config.condition

        return task

    async def register_workflow(
        self, workflow_def: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Register a workflow definition with Conductor.

        Args:
            workflow_def: Conductor workflow definition

        Returns:
            Tuple of (success, error_message)
        """
        try:
            url = f"{self.conductor_url}/api/metadata/workflow"
            response = await self.client.post(
                url,
                json=workflow_def,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code in (200, 201, 204):
                logger.info(
                    f"Successfully registered workflow: {workflow_def['name']}"
                )
                return True, None
            else:
                error_msg = f"Failed to register workflow: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg

        except Exception as e:
            error_msg = f"Error registering workflow: {e}"
            logger.error(error_msg)
            return False, error_msg

    async def start_workflow(
        self,
        workflow_name: str,
        version: int,
        input_data: Dict[str, Any],
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Start a workflow execution in Conductor.

        Args:
            workflow_name: Name of workflow to start
            version: Workflow version
            input_data: Input parameters for workflow

        Returns:
            Tuple of (workflow_id, error_message)
        """
        try:
            url = f"{self.conductor_url}/api/workflow"
            payload = {
                "name": workflow_name,
                "version": version,
                "input": input_data,
            }

            response = await self.client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code in (200, 201):
                # Response is the workflow ID
                conductor_workflow_id = response.text.strip('"')
                logger.info(
                    f"Started Conductor workflow: {conductor_workflow_id}"
                )
                return conductor_workflow_id, None
            else:
                error_msg = f"Failed to start workflow: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return None, error_msg

        except Exception as e:
            error_msg = f"Error starting workflow: {e}"
            logger.error(error_msg)
            return None, error_msg

    async def get_execution_status(
        self, conductor_workflow_id: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Get workflow execution status from Conductor.

        Args:
            conductor_workflow_id: Conductor workflow execution ID

        Returns:
            Tuple of (execution_data, error_message)
            execution_data contains: status, output, tasks, etc.
        """
        try:
            url = f"{self.conductor_url}/api/workflow/{conductor_workflow_id}?includeTasks=true"
            response = await self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                return data, None
            elif response.status_code == 404:
                return None, f"Workflow not found: {conductor_workflow_id}"
            else:
                error_msg = f"Failed to get workflow status: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return None, error_msg

        except Exception as e:
            error_msg = f"Error getting workflow status: {e}"
            logger.error(error_msg)
            return None, error_msg

    async def cancel_workflow(
        self, conductor_workflow_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Cancel a running workflow execution.

        Args:
            conductor_workflow_id: Conductor workflow execution ID

        Returns:
            Tuple of (success, error_message)
        """
        try:
            url = f"{self.conductor_url}/api/workflow/{conductor_workflow_id}"
            response = await self.client.delete(url)

            if response.status_code in (200, 204):
                logger.info(f"Cancelled Conductor workflow: {conductor_workflow_id}")
                return True, None
            else:
                error_msg = f"Failed to cancel workflow: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg

        except Exception as e:
            error_msg = f"Error cancelling workflow: {e}"
            logger.error(error_msg)
            return False, error_msg

    def map_conductor_status_to_ours(
        self, conductor_status: str
    ) -> WorkflowExecutionStatus:
        """
        Map Conductor workflow status to our WorkflowExecutionStatus enum.

        Conductor statuses: RUNNING, COMPLETED, FAILED, TIMED_OUT, TERMINATED, PAUSED

        Args:
            conductor_status: Conductor workflow status

        Returns:
            Our WorkflowExecutionStatus enum value
        """
        status_map = {
            "RUNNING": WorkflowExecutionStatus.RUNNING,
            "COMPLETED": WorkflowExecutionStatus.COMPLETED,
            "FAILED": WorkflowExecutionStatus.FAILED,
            "TIMED_OUT": WorkflowExecutionStatus.TIMEOUT,
            "TERMINATED": WorkflowExecutionStatus.CANCELLED,
            "PAUSED": WorkflowExecutionStatus.PAUSED,
        }

        return status_map.get(
            conductor_status.upper(), WorkflowExecutionStatus.FAILED
        )

    def map_conductor_task_status_to_ours(
        self, conductor_status: str
    ) -> WorkflowNodeExecutionStatus:
        """
        Map Conductor task status to our WorkflowNodeExecutionStatus enum.

        Conductor task statuses: SCHEDULED, IN_PROGRESS, COMPLETED, FAILED,
                                 TIMED_OUT, SKIPPED, CANCELED

        Args:
            conductor_status: Conductor task status

        Returns:
            Our WorkflowNodeExecutionStatus enum value
        """
        status_map = {
            "SCHEDULED": WorkflowNodeExecutionStatus.PENDING,
            "IN_PROGRESS": WorkflowNodeExecutionStatus.RUNNING,
            "COMPLETED": WorkflowNodeExecutionStatus.COMPLETED,
            "FAILED": WorkflowNodeExecutionStatus.FAILED,
            "TIMED_OUT": WorkflowNodeExecutionStatus.FAILED,
            "SKIPPED": WorkflowNodeExecutionStatus.SKIPPED,
            "CANCELED": WorkflowNodeExecutionStatus.SKIPPED,
        }

        return status_map.get(
            conductor_status.upper(), WorkflowNodeExecutionStatus.FAILED
        )
