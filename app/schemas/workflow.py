"""Workflow-related Pydantic schemas.

These schemas match the frontend TypeScript types exactly, with camelCase ↔ snake_case conversion.
"""

from datetime import datetime
from typing import Any, List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.enums import (
    NodeType,
    HttpMethod,
    WorkflowExecutionStatus,
    WorkflowNodeExecutionStatus,
)


# ============================================================================
# Node Configuration Schemas (match frontend exactly)
# ============================================================================


class ValidationError(BaseModel):
    """Validation error structure."""

    field: str
    message: str


class BaseNodeData(BaseModel):
    """Base node data interface with common properties."""

    label: str
    type: NodeType
    is_valid: bool = Field(default=True, alias="isValid")
    errors: List[ValidationError] = Field(default_factory=list)
    output_data: Optional[dict[str, Any]] = Field(None, alias="outputData")

    class Config:
        populate_by_name = True
        use_enum_values = True


class HttpTriggerNodeData(BaseNodeData):
    """HttpTrigger node configuration."""

    type: Literal[NodeType.HTTP_TRIGGER] = NodeType.HTTP_TRIGGER


class ExtractionNodeConfig(BaseModel):
    """Extraction node configuration."""

    file_source: Literal["previous_node", "url", "base64"] = Field(alias="fileSource")
    prompt: str
    schema_id: str = Field(alias="schemaId")

    class Config:
        populate_by_name = True


class ExtractionNodeData(BaseNodeData):
    """Extraction node configuration."""

    type: Literal[NodeType.EXTRACTION] = NodeType.EXTRACTION
    config: ExtractionNodeConfig


class PythonRunnerNodeConfig(BaseModel):
    """PythonRunner node configuration."""

    code: str


class PythonRunnerNodeData(BaseNodeData):
    """PythonRunner node configuration."""

    type: Literal[NodeType.PYTHON_RUNNER] = NodeType.PYTHON_RUNNER
    config: PythonRunnerNodeConfig


class HttpHeader(BaseModel):
    """HTTP header key-value pair."""

    key: str
    value: str
    enabled: bool = True


class HttpRequestNodeConfig(BaseModel):
    """HttpRequest node configuration."""

    url: str
    method: HttpMethod
    headers: List[HttpHeader] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class HttpRequestNodeData(BaseNodeData):
    """HttpRequest node configuration."""

    type: Literal[NodeType.HTTP_REQUEST] = NodeType.HTTP_REQUEST
    config: HttpRequestNodeConfig


class IfNodeConfig(BaseModel):
    """If node configuration."""

    condition: str


class IfNodeData(BaseNodeData):
    """If node configuration."""

    type: Literal[NodeType.IF] = NodeType.IF
    config: IfNodeConfig


# Union type for all node data types
WorkflowNodeData = Union[
    HttpTriggerNodeData,
    ExtractionNodeData,
    PythonRunnerNodeData,
    HttpRequestNodeData,
    IfNodeData,
]


# ============================================================================
# Workflow Node and Edge Schemas
# ============================================================================


class Position(BaseModel):
    """Node position on canvas."""

    x: float
    y: float


class WorkflowNode(BaseModel):
    """Workflow node with typed data (matches @xyflow/react Node)."""

    id: str
    type: str
    position: Position
    data: WorkflowNodeData

    class Config:
        use_enum_values = True


class WorkflowEdge(BaseModel):
    """Workflow edge (connection between nodes)."""

    id: str
    source: str
    target: str
    # Optional edge properties for conditional branching
    source_handle: Optional[str] = Field(None, alias="sourceHandle")
    target_handle: Optional[str] = Field(None, alias="targetHandle")
    label: Optional[str] = None
    type: Optional[str] = None

    class Config:
        populate_by_name = True


class WorkflowDefinition(BaseModel):
    """Complete workflow definition (stored in WorkflowVersion.definition)."""

    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]

    @field_validator("nodes")
    @classmethod
    def validate_nodes(cls, v):
        """Validate nodes array is not empty."""
        if not v:
            raise ValueError("Workflow must contain at least one node")
        return v


# ============================================================================
# Workflow CRUD Schemas
# ============================================================================


class WorkflowCreateRequest(BaseModel):
    """Request to create a new workflow."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    definition: WorkflowDefinition


class WorkflowUpdateRequest(BaseModel):
    """Request to update an existing workflow."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    definition: Optional[WorkflowDefinition] = None
    is_active: Optional[bool] = Field(None, alias="isActive")

    class Config:
        populate_by_name = True


class WorkflowVersionResponse(BaseModel):
    """Workflow version response."""

    id: UUID
    workflow_id: UUID = Field(alias="workflowId")
    version_number: int = Field(alias="versionNumber")
    definition: WorkflowDefinition
    conductor_workflow_name: Optional[str] = Field(None, alias="conductorWorkflowName")
    created_at: datetime = Field(alias="createdAt")

    class Config:
        populate_by_name = True
        from_attributes = True


class WorkflowResponse(BaseModel):
    """Workflow response with current version."""

    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    name: str
    description: Optional[str]
    is_active: bool = Field(alias="isActive")
    current_version_number: int = Field(alias="currentVersionNumber")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    # Include current version details
    current_version: Optional[WorkflowVersionResponse] = Field(None, alias="currentVersion")

    class Config:
        populate_by_name = True
        from_attributes = True


class WorkflowListResponse(BaseModel):
    """Paginated list of workflows."""

    workflows: List[WorkflowResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")

    class Config:
        populate_by_name = True


# ============================================================================
# Workflow Execution Schemas
# ============================================================================


class ExecuteWorkflowRequest(BaseModel):
    """Request to execute a workflow."""

    input_data: dict[str, Any] = Field(default_factory=dict, alias="inputData")
    # Optional: specify version to execute (defaults to current version)
    version_number: Optional[int] = Field(None, alias="versionNumber")

    class Config:
        populate_by_name = True


class WorkflowNodeExecutionResponse(BaseModel):
    """Individual node execution response."""

    id: UUID
    node_id: str = Field(alias="nodeId")
    node_type: str = Field(alias="nodeType")
    node_label: str = Field(alias="nodeLabel")
    status: WorkflowNodeExecutionStatus
    execution_order: Optional[int] = Field(None, alias="executionOrder")
    input_data: Optional[dict[str, Any]] = Field(None, alias="inputData")
    output_data: Optional[dict[str, Any]] = Field(None, alias="outputData")
    error_message: Optional[str] = Field(None, alias="errorMessage")
    created_at: datetime = Field(alias="createdAt")
    started_at: Optional[datetime] = Field(None, alias="startedAt")
    completed_at: Optional[datetime] = Field(None, alias="completedAt")

    class Config:
        populate_by_name = True
        from_attributes = True
        use_enum_values = True


class WorkflowExecutionResponse(BaseModel):
    """Workflow execution response."""

    id: UUID
    workflow_id: UUID = Field(alias="workflowId")
    workflow_version_id: UUID = Field(alias="workflowVersionId")
    status: WorkflowExecutionStatus
    conductor_workflow_id: Optional[str] = Field(None, alias="conductorWorkflowId")
    input_data: dict[str, Any] = Field(alias="inputData")
    output_data: Optional[dict[str, Any]] = Field(None, alias="outputData")
    error_message: Optional[str] = Field(None, alias="errorMessage")
    created_at: datetime = Field(alias="createdAt")
    started_at: Optional[datetime] = Field(None, alias="startedAt")
    completed_at: Optional[datetime] = Field(None, alias="completedAt")
    # Include node executions when requested
    node_executions: Optional[List[WorkflowNodeExecutionResponse]] = Field(
        None, alias="nodeExecutions"
    )

    class Config:
        populate_by_name = True
        from_attributes = True
        use_enum_values = True


class WorkflowExecutionListResponse(BaseModel):
    """Paginated list of workflow executions."""

    executions: List[WorkflowExecutionResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")

    class Config:
        populate_by_name = True


# ============================================================================
# Webhook Schemas (for HTTP Trigger nodes)
# ============================================================================


class WorkflowWebhookRequest(BaseModel):
    """
    Webhook payload for triggering workflows via HTTP Trigger node.

    This matches the runtime data structure expected by HttpTrigger nodes.
    """

    prompt: str
    file_url: Optional[str] = Field(None, alias="fileUrl")
    base64: Optional[str] = None
    callback_url: Optional[str] = Field(None, alias="callbackUrl")
    # Additional arbitrary data
    data: dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
