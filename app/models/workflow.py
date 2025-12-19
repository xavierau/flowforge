"""Workflow models for visual workflow builder with Netflix Conductor integration."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
import uuid

from app.database import Base
from app.models.enums import (
    NodeType,
    WorkflowExecutionStatus,
    WorkflowNodeExecutionStatus,
)


class Workflow(Base):
    """
    Workflow model - represents a workflow definition created by users.

    A workflow is a directed graph of nodes (tasks) connected by edges.
    Each workflow can have multiple versions for change tracking.
    """

    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_archived = Column(Boolean, nullable=False, default=False)

    # Current active version (for quick access)
    current_version_number = Column(Integer, nullable=False, default=1)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="workflows")
    versions = relationship(
        "WorkflowVersion", back_populates="workflow", cascade="all, delete-orphan"
    )
    executions = relationship(
        "WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_workflows_tenant_id", "tenant_id"),
        Index("idx_workflows_is_active", "is_active"),
        Index("idx_workflows_is_archived", "is_archived"),
        Index("idx_workflows_created_at", "created_at"),
    )

    @validates("name")
    def validate_name(self, key, value):
        """Validate workflow name is not empty."""
        if not value or not value.strip():
            raise ValueError("Workflow name cannot be empty")
        return value.strip()

    def __repr__(self):
        return f"<Workflow(id={self.id}, name={self.name}, version={self.current_version_number})>"


class WorkflowVersion(Base):
    """
    WorkflowVersion model - stores versioned workflow definitions.

    Each time a workflow is updated, a new version is created.
    The definition contains the complete node and edge configuration.
    """

    __tablename__ = "workflow_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)

    # Complete workflow definition (nodes + edges)
    # Structure matches frontend Workflow type:
    # {
    #   "nodes": [{"id": "...", "type": "...", "position": {...}, "data": {...}}, ...],
    #   "edges": [{"id": "...", "source": "...", "target": "...", ...}, ...]
    # }
    definition = Column(JSONB, nullable=False)

    # Default model settings for pipeline nodes
    # Structure:
    # {
    #   "extraction": {"provider": "google", "model": "gemini-2.5-flash"},
    #   "markdown_converter": {"converter": "gemini_vision", "model": "gemini-2.5-flash"},
    #   "llm": {"provider": "google", "model": "gemini-2.5-flash"}
    # }
    model_defaults = Column(JSONB, nullable=True)

    # Netflix Conductor workflow name (generated from workflow name + version)
    conductor_workflow_name = Column(String(255), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    workflow = relationship("Workflow", back_populates="versions")

    # Indexes
    __table_args__ = (
        Index("idx_workflow_versions_workflow_id", "workflow_id"),
        Index(
            "idx_workflow_versions_unique",
            "workflow_id",
            "version_number",
            unique=True,
        ),
    )

    @validates("definition")
    def validate_definition(self, key, value):
        """Validate workflow definition has required fields."""
        if not isinstance(value, dict):
            raise ValueError("Workflow definition must be a dictionary")
        if "nodes" not in value or not isinstance(value["nodes"], list):
            raise ValueError("Workflow definition must contain 'nodes' array")
        if "edges" not in value or not isinstance(value["edges"], list):
            raise ValueError("Workflow definition must contain 'edges' array")
        return value

    @validates("version_number")
    def validate_version_number(self, key, value):
        """Validate version number is positive."""
        if value < 1:
            raise ValueError("Version number must be >= 1")
        return value

    def __repr__(self):
        return f"<WorkflowVersion(id={self.id}, workflow_id={self.workflow_id}, version={self.version_number})>"


class WorkflowExecution(Base):
    """
    WorkflowExecution model - tracks individual workflow execution runs.

    Each execution is triggered by a webhook or manual trigger.
    Integrates with Netflix Conductor for distributed execution.
    """

    __tablename__ = "workflow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Execution status
    status = Column(
        String(50),
        nullable=False,
        default=WorkflowExecutionStatus.PENDING.value,
        index=True,
    )

    # Netflix Conductor workflow execution ID
    conductor_workflow_id = Column(String(255), nullable=True, index=True)

    # Input data passed to workflow (from webhook/trigger)
    input_data = Column(JSONB, nullable=False, default=dict)

    # Output data from workflow execution
    output_data = Column(JSONB, nullable=True)

    # Error information if execution failed
    error_message = Column(Text, nullable=True)
    error_trace = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="workflow_executions")
    workflow = relationship("Workflow", back_populates="executions")
    workflow_version = relationship("WorkflowVersion")
    node_executions = relationship(
        "WorkflowNodeExecution",
        back_populates="workflow_execution",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_workflow_executions_tenant_id", "tenant_id"),
        Index("idx_workflow_executions_workflow_id", "workflow_id"),
        Index("idx_workflow_executions_status", "status"),
        Index("idx_workflow_executions_created_at", "created_at"),
        Index("idx_workflow_executions_conductor_id", "conductor_workflow_id"),
    )

    @validates("status")
    def validate_status(self, key, value):
        """Validate execution status is valid enum value."""
        if isinstance(value, WorkflowExecutionStatus):
            return value.value
        if value not in [s.value for s in WorkflowExecutionStatus]:
            raise ValueError(f"Invalid workflow execution status: {value}")
        return value

    @validates("input_data")
    def validate_input_data(self, key, value):
        """Validate input data is a dictionary."""
        if not isinstance(value, dict):
            raise ValueError("Input data must be a dictionary")
        return value

    def __repr__(self):
        return f"<WorkflowExecution(id={self.id}, workflow_id={self.workflow_id}, status={self.status})>"


class WorkflowNodeExecution(Base):
    """
    WorkflowNodeExecution model - tracks individual node execution within a workflow run.

    Each node in the workflow has its own execution record with status,
    input/output data, and timing information.
    """

    __tablename__ = "workflow_node_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Node information from workflow definition
    node_id = Column(String(255), nullable=False)  # ID from workflow definition
    node_type = Column(String(50), nullable=False)  # NodeType enum value
    node_label = Column(String(255), nullable=False)

    # Execution status
    status = Column(
        String(50),
        nullable=False,
        default=WorkflowNodeExecutionStatus.PENDING.value,
        index=True,
    )

    # Execution order within the workflow
    execution_order = Column(Integer, nullable=True)

    # Input data for this node (resolved from previous nodes)
    input_data = Column(JSONB, nullable=True)

    # Output data from this node (for next nodes)
    output_data = Column(JSONB, nullable=True)

    # Error information if node execution failed
    error_message = Column(Text, nullable=True)
    error_trace = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    workflow_execution = relationship(
        "WorkflowExecution", back_populates="node_executions"
    )

    # Indexes
    __table_args__ = (
        Index("idx_workflow_node_executions_workflow_execution_id", "workflow_execution_id"),
        Index("idx_workflow_node_executions_node_id", "node_id"),
        Index("idx_workflow_node_executions_status", "status"),
        Index("idx_workflow_node_executions_created_at", "created_at"),
        Index(
            "idx_workflow_node_executions_unique",
            "workflow_execution_id",
            "node_id",
            unique=True,
        ),
    )

    @validates("status")
    def validate_status(self, key, value):
        """Validate node execution status is valid enum value."""
        if isinstance(value, WorkflowNodeExecutionStatus):
            return value.value
        if value not in [s.value for s in WorkflowNodeExecutionStatus]:
            raise ValueError(f"Invalid workflow node execution status: {value}")
        return value

    @validates("node_type")
    def validate_node_type(self, key, value):
        """Validate node type is valid enum value."""
        if isinstance(value, NodeType):
            return value.value
        if value not in [t.value for t in NodeType]:
            raise ValueError(f"Invalid node type: {value}")
        return value

    def __repr__(self):
        return f"<WorkflowNodeExecution(id={self.id}, node_id={self.node_id}, status={self.status})>"
