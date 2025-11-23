"""
Workflow service for CRUD operations.

Handles workflow creation, updates, versioning, and validation.
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.workflow import Workflow, WorkflowVersion
from app.models.enums import NodeType
from app.schemas.workflow import (
    WorkflowCreateRequest,
    WorkflowDefinition,
    WorkflowUpdateRequest,
)
from app.services.conductor_client import ConductorClient

logger = logging.getLogger(__name__)


class WorkflowServiceError(Exception):
    """Base exception for workflow service errors."""

    pass


class WorkflowService:
    """
    Service for workflow CRUD operations.

    Handles:
    - Creating workflows with versioning
    - Updating workflows (creates new versions)
    - Validating workflow definitions
    - Tenant isolation
    """

    def __init__(self, db: Session, conductor_client: Optional[ConductorClient] = None):
        """
        Initialize workflow service.

        Args:
            db: Database session
            conductor_client: Conductor client (optional, created if not provided)
        """
        self.db = db
        self.conductor_client = conductor_client

    async def create_workflow(
        self,
        tenant_id: UUID,
        request: WorkflowCreateRequest,
    ) -> Tuple[Workflow, WorkflowVersion]:
        """
        Create a new workflow with initial version.

        Args:
            tenant_id: Tenant ID
            request: Workflow creation request

        Returns:
            Tuple of (Workflow, WorkflowVersion)

        Raises:
            WorkflowServiceError: If creation fails
        """
        try:
            # Validate workflow definition
            validation_errors = self.validate_workflow_definition(request.definition)
            if validation_errors:
                raise WorkflowServiceError(
                    f"Workflow validation failed: {'; '.join(validation_errors)}"
                )

            # Create workflow
            workflow = Workflow(
                tenant_id=tenant_id,
                name=request.name,
                description=request.description,
                current_version_number=1,
            )
            self.db.add(workflow)
            self.db.flush()  # Get workflow ID

            # Create initial version
            workflow_version = WorkflowVersion(
                workflow_id=workflow.id,
                version_number=1,
                definition=request.definition.model_dump(by_alias=False),
                conductor_workflow_name=f"{request.name}_v1",
            )
            self.db.add(workflow_version)
            self.db.commit()
            self.db.refresh(workflow)
            self.db.refresh(workflow_version)

            logger.info(
                f"Created workflow {workflow.id} (tenant: {tenant_id})"
            )
            return workflow, workflow_version

        except WorkflowServiceError:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating workflow: {e}")
            raise WorkflowServiceError(f"Failed to create workflow: {e}")

    async def update_workflow(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        request: WorkflowUpdateRequest,
    ) -> Tuple[Workflow, Optional[WorkflowVersion]]:
        """
        Update an existing workflow.

        If definition is provided, creates a new version.

        Args:
            workflow_id: Workflow ID
            tenant_id: Tenant ID
            request: Workflow update request

        Returns:
            Tuple of (updated Workflow, new WorkflowVersion or None)

        Raises:
            WorkflowServiceError: If workflow not found or update fails
        """
        try:
            # Get workflow with tenant isolation
            workflow = (
                self.db.query(Workflow)
                .filter(
                    and_(Workflow.id == workflow_id, Workflow.tenant_id == tenant_id)
                )
                .first()
            )

            if not workflow:
                raise WorkflowServiceError("Workflow not found")

            # Update basic fields
            if request.name is not None:
                workflow.name = request.name
            if request.description is not None:
                workflow.description = request.description
            if request.is_active is not None:
                workflow.is_active = request.is_active

            workflow.updated_at = datetime.utcnow()

            new_version = None
            if request.definition is not None:
                # Validate new definition
                validation_errors = self.validate_workflow_definition(
                    request.definition
                )
                if validation_errors:
                    raise WorkflowServiceError(
                        f"Workflow validation failed: {'; '.join(validation_errors)}"
                    )

                # Create new version
                next_version_number = workflow.current_version_number + 1
                new_version = WorkflowVersion(
                    workflow_id=workflow.id,
                    version_number=next_version_number,
                    definition=request.definition.model_dump(by_alias=False),
                    conductor_workflow_name=f"{workflow.name}_v{next_version_number}",
                )
                self.db.add(new_version)
                workflow.current_version_number = next_version_number

            self.db.commit()
            self.db.refresh(workflow)
            if new_version:
                self.db.refresh(new_version)

            logger.info(
                f"Updated workflow {workflow_id} (tenant: {tenant_id})"
            )
            return workflow, new_version

        except WorkflowServiceError:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating workflow: {e}")
            raise WorkflowServiceError(f"Failed to update workflow: {e}")

    def get_workflow(
        self, workflow_id: UUID, tenant_id: UUID
    ) -> Optional[Workflow]:
        """
        Get a workflow by ID with tenant isolation.

        Args:
            workflow_id: Workflow ID
            tenant_id: Tenant ID

        Returns:
            Workflow or None if not found
        """
        return (
            self.db.query(Workflow)
            .filter(and_(Workflow.id == workflow_id, Workflow.tenant_id == tenant_id))
            .first()
        )

    def list_workflows(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[Workflow], int]:
        """
        List workflows for a tenant with pagination.

        Args:
            tenant_id: Tenant ID
            page: Page number (1-indexed)
            page_size: Items per page
            is_active: Filter by active status (optional)

        Returns:
            Tuple of (workflows list, total count)
        """
        query = self.db.query(Workflow).filter(Workflow.tenant_id == tenant_id)

        if is_active is not None:
            query = query.filter(Workflow.is_active == is_active)

        # Get total count
        total = query.count()

        # Paginate
        workflows = (
            query.order_by(Workflow.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return workflows, total

    def get_workflow_version(
        self,
        workflow_id: UUID,
        version_number: int,
        tenant_id: UUID,
    ) -> Optional[WorkflowVersion]:
        """
        Get a specific workflow version with tenant isolation.

        Args:
            workflow_id: Workflow ID
            version_number: Version number
            tenant_id: Tenant ID

        Returns:
            WorkflowVersion or None if not found
        """
        # First verify workflow belongs to tenant
        workflow = self.get_workflow(workflow_id, tenant_id)
        if not workflow:
            return None

        return (
            self.db.query(WorkflowVersion)
            .filter(
                and_(
                    WorkflowVersion.workflow_id == workflow_id,
                    WorkflowVersion.version_number == version_number,
                )
            )
            .first()
        )

    def get_current_workflow_version(
        self, workflow_id: UUID, tenant_id: UUID
    ) -> Optional[WorkflowVersion]:
        """
        Get the current active version of a workflow.

        Args:
            workflow_id: Workflow ID
            tenant_id: Tenant ID

        Returns:
            WorkflowVersion or None if not found
        """
        workflow = self.get_workflow(workflow_id, tenant_id)
        if not workflow:
            return None

        return (
            self.db.query(WorkflowVersion)
            .filter(
                and_(
                    WorkflowVersion.workflow_id == workflow_id,
                    WorkflowVersion.version_number == workflow.current_version_number,
                )
            )
            .first()
        )

    async def delete_workflow(
        self, workflow_id: UUID, tenant_id: UUID
    ) -> bool:
        """
        Delete a workflow (soft delete by setting is_active=False).

        Args:
            workflow_id: Workflow ID
            tenant_id: Tenant ID

        Returns:
            True if deleted, False if not found
        """
        workflow = self.get_workflow(workflow_id, tenant_id)
        if not workflow:
            return False

        workflow.is_active = False
        workflow.updated_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Deleted workflow {workflow_id} (tenant: {tenant_id})")
        return True

    def validate_workflow_definition(
        self, definition: WorkflowDefinition
    ) -> List[str]:
        """
        Validate a workflow definition.

        Checks:
        1. At least one node exists
        2. Exactly one HTTP Trigger node
        3. All edges reference valid nodes
        4. No cycles in the graph
        5. All nodes are reachable from HTTP Trigger

        Args:
            definition: Workflow definition to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check 1: At least one node
        if not definition.nodes:
            errors.append("Workflow must contain at least one node")
            return errors

        # Check 2: Exactly one HTTP Trigger node
        trigger_nodes = [
            n for n in definition.nodes if n.data.type == NodeType.HTTP_TRIGGER
        ]
        if len(trigger_nodes) == 0:
            errors.append("Workflow must have exactly one HTTP Trigger node")
        elif len(trigger_nodes) > 1:
            errors.append("Workflow can only have one HTTP Trigger node")

        # Check 3: All edges reference valid nodes
        node_ids = {n.id for n in definition.nodes}
        for edge in definition.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge references non-existent source node: {edge.source}")
            if edge.target not in node_ids:
                errors.append(f"Edge references non-existent target node: {edge.target}")

        # Check 4: No cycles (using DFS)
        if not self._has_cycles(definition):
            # Check 5: All nodes reachable from trigger
            if trigger_nodes:
                trigger_id = trigger_nodes[0].id
                reachable = self._get_reachable_nodes(definition, trigger_id)
                unreachable = node_ids - reachable
                if unreachable:
                    errors.append(
                        f"Nodes not reachable from trigger: {', '.join(unreachable)}"
                    )
        else:
            errors.append("Workflow contains cycles")

        return errors

    def _has_cycles(self, definition: WorkflowDefinition) -> bool:
        """
        Check if workflow definition has cycles using DFS.

        Args:
            definition: Workflow definition

        Returns:
            True if cycles exist, False otherwise
        """
        # Build adjacency list
        graph = {n.id: [] for n in definition.nodes}
        for edge in definition.edges:
            graph[edge.source].append(edge.target)

        # DFS with visited and recursion stack
        visited = set()
        rec_stack = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in graph[node_id]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node in definition.nodes:
            if node.id not in visited:
                if dfs(node.id):
                    return True

        return False

    def _get_reachable_nodes(
        self, definition: WorkflowDefinition, start_node_id: str
    ) -> set:
        """
        Get all nodes reachable from a starting node using BFS.

        Args:
            definition: Workflow definition
            start_node_id: Starting node ID

        Returns:
            Set of reachable node IDs (including start node)
        """
        # Build adjacency list
        graph = {n.id: [] for n in definition.nodes}
        for edge in definition.edges:
            graph[edge.source].append(edge.target)

        # BFS
        visited = {start_node_id}
        queue = [start_node_id]

        while queue:
            current = queue.pop(0)
            for neighbor in graph[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return visited
