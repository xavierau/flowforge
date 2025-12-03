"""
Conductor workflow definitions for HITL integration.

This module provides workflow definitions and task definitions for
Human-in-the-Loop (HITL) document extraction workflows.

Available Workflows:
- EXTRACTION_WITH_CONFIDENCE_ROUTING: Auto-approves high-confidence extractions
- EXTRACTION_WITH_MANUAL_REVIEW: Always routes to human review
- BATCH_EXTRACTION_WITH_SELECTIVE_REVIEW: Reviews only low-confidence items
- CONFIGURABLE_HITL_WORKFLOW: Fully configurable HITL options

Utility Functions:
- get_workflow_definition(name): Get workflow by name
- get_all_workflow_definitions(): Get all workflows
- get_all_task_definitions(): Get all task definitions
"""

from .extraction_with_hitl import (
    # Workflow definitions
    EXTRACTION_WITH_CONFIDENCE_ROUTING,
    EXTRACTION_WITH_MANUAL_REVIEW,
    BATCH_EXTRACTION_WITH_SELECTIVE_REVIEW,
    CONFIGURABLE_HITL_WORKFLOW,
    # Task definitions
    TASK_DEFINITIONS,
    # Registry
    WORKFLOW_REGISTRY,
    # Utility functions
    get_workflow_definition,
    get_all_workflow_definitions,
    get_all_task_definitions,
)

__all__ = [
    # Workflow definitions
    "EXTRACTION_WITH_CONFIDENCE_ROUTING",
    "EXTRACTION_WITH_MANUAL_REVIEW",
    "BATCH_EXTRACTION_WITH_SELECTIVE_REVIEW",
    "CONFIGURABLE_HITL_WORKFLOW",
    # Task definitions
    "TASK_DEFINITIONS",
    # Registry
    "WORKFLOW_REGISTRY",
    # Utility functions
    "get_workflow_definition",
    "get_all_workflow_definitions",
    "get_all_task_definitions",
]
