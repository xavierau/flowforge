"""
Conductor Workflow Definitions for Extraction with HITL.

This module contains complete workflow definitions that integrate document extraction
with human-in-the-loop review based on confidence scores.

Workflow Patterns:
1. Extraction with Confidence-Based Routing: Auto-approves high-confidence extractions
2. Extraction with Manual Review: Always routes to human review
3. Batch Extraction with Selective Review: Reviews only low-confidence items
4. Configurable HITL Workflow: Flexible threshold and routing configuration

HUMAN Task Integration:
- HUMAN_REVIEW tasks are picked up by HumanReviewWorker
- Worker creates ReviewRequest in database and returns IN_PROGRESS
- Workflow pauses until review is submitted via API
- ConductorHITLService completes task with corrected_data
- Workflow resumes with human-verified data

Workflow Input Parameters:
- document_id: Document to process
- extraction_job_id: Extraction job ID
- extraction_schema: JSON schema for extraction
- provider: VLLM provider (google, openai, deepseek)
- model: VLLM model name (optional)
- confidence_threshold: Threshold for human review (default: 0.70)
- review_instructions: Instructions for human reviewer

Workflow Output Parameters:
- extraction_job_id: Processed job ID
- confidence_score: AI confidence score
- review_required: Whether human review was needed
- final_data: Final extracted data (corrected if reviewed)
- quality_score: Quality score from review
"""

from typing import Dict, Any, List


# =============================================================================
# Workflow 1: Extraction with Confidence-Based Routing
# =============================================================================

EXTRACTION_WITH_CONFIDENCE_ROUTING: Dict[str, Any] = {
    "name": "document_extraction_with_review",
    "description": "Extract document data and route to human review if confidence is low",
    "version": 1,
    "tasks": [
        # Step 1: Extract document using VLLM
        {
            "name": "extract_document",
            "taskReferenceName": "extract_task",
            "type": "SIMPLE",
            "inputParameters": {
                "document_id": "${workflow.input.document_id}",
                "schema": "${workflow.input.extraction_schema}",
                "provider": "${workflow.input.provider}",
                "model": "${workflow.input.model}"
            }
        },
        # Step 2: Route based on confidence score
        {
            "name": "check_confidence",
            "taskReferenceName": "confidence_check",
            "type": "SWITCH",
            "evaluatorType": "javascript",
            "expression": "$.extract_task.output.data.confidence_score < ($.workflow.input.confidence_threshold || 0.70) ? 'needs_review' : 'auto_approve'",
            "decisionCases": {
                # Low confidence path: Human review required
                "needs_review": [
                    {
                        "name": "HUMAN_REVIEW",
                        "taskReferenceName": "human_review_task",
                        "type": "SIMPLE",  # Will be handled by HumanReviewWorker
                        "inputParameters": {
                            "extraction_job_id": "${workflow.input.extraction_job_id}",
                            "confidence_score": "${extract_task.output.data.confidence_score}",
                            "trigger_reason": "low_confidence",
                            # Conductor metadata auto-populated by worker
                        }
                    },
                    {
                        "name": "finalize_with_corrections",
                        "taskReferenceName": "finalize_corrections",
                        "type": "SIMPLE",
                        "inputParameters": {
                            "extraction_job_id": "${workflow.input.extraction_job_id}",
                            "corrected_data": "${human_review_task.output.corrected_data}",
                            "corrections_count": "${human_review_task.output.corrections_count}",
                            "review_request_id": "${human_review_task.output.review_request_id}"
                        }
                    }
                ],
                # High confidence path: Auto-approve
                "auto_approve": [
                    {
                        "name": "auto_approve",
                        "taskReferenceName": "auto_approve_task",
                        "type": "SIMPLE",
                        "inputParameters": {
                            "extraction_job_id": "${workflow.input.extraction_job_id}",
                            "approval_reason": "high_confidence",
                            "confidence_score": "${extract_task.output.data.confidence_score}"
                        }
                    }
                ]
            },
            "defaultCase": [
                # Default to auto-approve if expression fails
                {
                    "name": "auto_approve",
                    "taskReferenceName": "default_approve_task",
                    "type": "SIMPLE",
                    "inputParameters": {
                        "extraction_job_id": "${workflow.input.extraction_job_id}",
                        "approval_reason": "default_path",
                        "confidence_score": "${extract_task.output.data.confidence_score}"
                    }
                }
            ]
        }
    ],
    "inputParameters": [
        "document_id",
        "extraction_job_id",
        "extraction_schema",
        "provider",
        "model",
        "confidence_threshold"
    ],
    "outputParameters": {
        "extraction_job_id": "${workflow.input.extraction_job_id}",
        "confidence_score": "${extract_task.output.data.confidence_score}",
        "review_required": "${confidence_check.decisionCaseValue}",
        "final_data": "${human_review_task.output.corrected_data != null ? human_review_task.output.corrected_data : extract_task.output.data.extracted_data}",
        "quality_score": "${human_review_task.output.quality_score}"
    },
    "schemaVersion": 2,
    "restartable": True,
    "workflowStatusListenerEnabled": True,
    "timeoutPolicy": "ALERT_ONLY",
    "timeoutSeconds": 3600  # 1 hour timeout
}


# =============================================================================
# Workflow 2: Extraction with Manual Review (Always Review)
# =============================================================================

EXTRACTION_WITH_MANUAL_REVIEW: Dict[str, Any] = {
    "name": "document_extraction_manual_review",
    "description": "Extract document data and always route to human review",
    "version": 1,
    "tasks": [
        # Step 1: Extract document
        {
            "name": "extract_document",
            "taskReferenceName": "extract_task",
            "type": "SIMPLE",
            "inputParameters": {
                "document_id": "${workflow.input.document_id}",
                "schema": "${workflow.input.extraction_schema}",
                "provider": "${workflow.input.provider}",
                "model": "${workflow.input.model}"
            }
        },
        # Step 2: Always send to human review
        {
            "name": "HUMAN_REVIEW",
            "taskReferenceName": "human_review_task",
            "type": "SIMPLE",
            "inputParameters": {
                "extraction_job_id": "${workflow.input.extraction_job_id}",
                "confidence_score": "${extract_task.output.data.confidence_score}",
                "trigger_reason": "manual_review_required",
                "instructions": "${workflow.input.review_instructions}"
            }
        },
        # Step 3: Finalize with corrections
        {
            "name": "finalize_with_corrections",
            "taskReferenceName": "finalize_corrections",
            "type": "SIMPLE",
            "inputParameters": {
                "extraction_job_id": "${workflow.input.extraction_job_id}",
                "corrected_data": "${human_review_task.output.corrected_data}",
                "corrections_count": "${human_review_task.output.corrections_count}",
                "review_request_id": "${human_review_task.output.review_request_id}"
            }
        }
    ],
    "inputParameters": [
        "document_id",
        "extraction_job_id",
        "extraction_schema",
        "provider",
        "model",
        "review_instructions"
    ],
    "outputParameters": {
        "extraction_job_id": "${workflow.input.extraction_job_id}",
        "confidence_score": "${extract_task.output.data.confidence_score}",
        "corrected_data": "${human_review_task.output.corrected_data}",
        "corrections_count": "${human_review_task.output.corrections_count}",
        "quality_score": "${human_review_task.output.quality_score}"
    },
    "schemaVersion": 2,
    "restartable": True,
    "workflowStatusListenerEnabled": True,
    "timeoutPolicy": "ALERT_ONLY",
    "timeoutSeconds": 7200  # 2 hour timeout
}


# =============================================================================
# Workflow 3: Batch Extraction with Selective Review
# =============================================================================

BATCH_EXTRACTION_WITH_SELECTIVE_REVIEW: Dict[str, Any] = {
    "name": "batch_extraction_with_selective_review",
    "description": "Process multiple documents and review only low-confidence extractions",
    "version": 1,
    "tasks": [
        # Dynamic fork for parallel document processing
        {
            "name": "extract_documents_fork",
            "taskReferenceName": "extract_fork",
            "type": "FORK_JOIN_DYNAMIC",
            "inputParameters": {
                "dynamicTasks": "${workflow.input.documents}",
                "dynamicTasksInput": "${workflow.input.documents}"
            },
            "dynamicForkTasksParam": "dynamicTasks",
            "dynamicForkTasksInputParamName": "dynamicTasksInput"
        },
        # Join results
        {
            "name": "join_results",
            "taskReferenceName": "join_task",
            "type": "JOIN",
            "joinOn": []  # Dynamic based on fork
        },
        # Aggregate and filter for review
        {
            "name": "aggregate_results",
            "taskReferenceName": "aggregate_task",
            "type": "SIMPLE",
            "inputParameters": {
                "extraction_results": "${join_task.output}",
                "confidence_threshold": "${workflow.input.confidence_threshold}"
            }
        }
    ],
    "inputParameters": [
        "documents",  # Array of {document_id, extraction_job_id}
        "extraction_schema",
        "provider",
        "model",
        "confidence_threshold"
    ],
    "outputParameters": {
        "total_documents": "${workflow.input.documents.length}",
        "aggregated_results": "${aggregate_task.output.results}",
        "reviews_required": "${aggregate_task.output.reviews_required}"
    },
    "schemaVersion": 2,
    "restartable": True,
    "workflowStatusListenerEnabled": True,
    "timeoutPolicy": "ALERT_ONLY",
    "timeoutSeconds": 10800  # 3 hour timeout for batch processing
}


# =============================================================================
# Workflow 4: Configurable HITL Workflow
# =============================================================================

CONFIGURABLE_HITL_WORKFLOW: Dict[str, Any] = {
    "name": "configurable_extraction_with_hitl",
    "description": "Fully configurable extraction workflow with HITL options",
    "version": 1,
    "tasks": [
        # Step 1: Extract document
        {
            "name": "extract_document",
            "taskReferenceName": "extract_task",
            "type": "SIMPLE",
            "inputParameters": {
                "document_id": "${workflow.input.document_id}",
                "schema": "${workflow.input.extraction_schema}",
                "provider": "${workflow.input.provider}",
                "model": "${workflow.input.model}"
            }
        },
        # Step 2: Check if review is needed based on configuration
        {
            "name": "check_review_needed",
            "taskReferenceName": "review_check",
            "type": "SWITCH",
            "evaluatorType": "javascript",
            "expression": """
                (function() {
                    var config = $.workflow.input.hitl_config || {};
                    var confidence = $.extract_task.output.data.confidence_score || 0;
                    var threshold = config.confidence_threshold || 0.70;
                    var forceReview = config.force_review || false;
                    var skipReview = config.skip_review || false;

                    if (skipReview) return 'skip';
                    if (forceReview) return 'review';
                    if (confidence < threshold) return 'review';
                    return 'skip';
                })()
            """,
            "decisionCases": {
                "review": [
                    {
                        "name": "HUMAN_REVIEW",
                        "taskReferenceName": "human_review_task",
                        "type": "SIMPLE",
                        "inputParameters": {
                            "extraction_job_id": "${workflow.input.extraction_job_id}",
                            "confidence_score": "${extract_task.output.data.confidence_score}",
                            "trigger_reason": "${workflow.input.hitl_config.force_review ? 'manual_request' : 'low_confidence'}",
                            "priority": "${workflow.input.hitl_config.priority}",
                            "instructions": "${workflow.input.hitl_config.instructions}",
                            "assignment_strategy": "${workflow.input.hitl_config.assignment_strategy}",
                            "reviewer_pool": "${workflow.input.hitl_config.reviewer_pool}"
                        }
                    },
                    {
                        "name": "finalize_with_corrections",
                        "taskReferenceName": "finalize_corrections",
                        "type": "SIMPLE",
                        "inputParameters": {
                            "extraction_job_id": "${workflow.input.extraction_job_id}",
                            "corrected_data": "${human_review_task.output.corrected_data}",
                            "corrections_count": "${human_review_task.output.corrections_count}",
                            "review_request_id": "${human_review_task.output.review_request_id}"
                        }
                    }
                ],
                "skip": [
                    {
                        "name": "auto_approve",
                        "taskReferenceName": "auto_approve_task",
                        "type": "SIMPLE",
                        "inputParameters": {
                            "extraction_job_id": "${workflow.input.extraction_job_id}",
                            "approval_reason": "review_skipped",
                            "confidence_score": "${extract_task.output.data.confidence_score}"
                        }
                    }
                ]
            }
        }
    ],
    "inputParameters": [
        "document_id",
        "extraction_job_id",
        "extraction_schema",
        "provider",
        "model",
        "hitl_config"  # {confidence_threshold, force_review, skip_review, priority, instructions, assignment_strategy, reviewer_pool}
    ],
    "outputParameters": {
        "extraction_job_id": "${workflow.input.extraction_job_id}",
        "confidence_score": "${extract_task.output.data.confidence_score}",
        "review_performed": "${review_check.decisionCaseValue == 'review'}",
        "final_data": "${human_review_task.output.corrected_data != null ? human_review_task.output.corrected_data : extract_task.output.data.extracted_data}",
        "quality_score": "${human_review_task.output.quality_score}"
    },
    "schemaVersion": 2,
    "restartable": True,
    "workflowStatusListenerEnabled": True,
    "timeoutPolicy": "ALERT_ONLY",
    "timeoutSeconds": 7200
}


# =============================================================================
# Task Definitions (to be registered with Conductor)
# =============================================================================

TASK_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "extract_document",
        "description": "Extract structured data from document using VLLM",
        "retryCount": 3,
        "retryLogic": "FIXED",
        "retryDelaySeconds": 60,
        "timeoutSeconds": 300,
        "timeoutPolicy": "TIME_OUT_WF",
        "responseTimeoutSeconds": 300,
        "inputKeys": ["document_id", "schema", "provider", "model"],
        "outputKeys": ["extracted_data", "confidence_score", "pages_processed", "total_tokens"]
    },
    {
        "name": "HUMAN_REVIEW",
        "description": "Human review of extraction results",
        "retryCount": 0,  # No retries for HUMAN tasks
        "timeoutSeconds": 14400,  # 4 hour timeout
        "timeoutPolicy": "ALERT_ONLY",  # Don't fail, just alert
        "responseTimeoutSeconds": 14400,
        "inputKeys": [
            "extraction_job_id",
            "confidence_score",
            "trigger_reason",
            "priority",
            "instructions",
            "assignment_strategy",
            "reviewer_pool"
        ],
        "outputKeys": [
            "review_request_id",
            "corrected_data",
            "corrections_count",
            "quality_score",
            "review_notes",
            "corrections"
        ]
    },
    {
        "name": "auto_approve",
        "description": "Auto-approve high-confidence extraction",
        "retryCount": 3,
        "retryLogic": "FIXED",
        "retryDelaySeconds": 10,
        "timeoutSeconds": 60,
        "timeoutPolicy": "TIME_OUT_WF",
        "responseTimeoutSeconds": 60,
        "inputKeys": ["extraction_job_id", "approval_reason", "confidence_score"],
        "outputKeys": ["approval_status", "approved_at", "final_data"]
    },
    {
        "name": "finalize_with_corrections",
        "description": "Finalize extraction with human corrections",
        "retryCount": 3,
        "retryLogic": "FIXED",
        "retryDelaySeconds": 10,
        "timeoutSeconds": 120,
        "timeoutPolicy": "TIME_OUT_WF",
        "responseTimeoutSeconds": 120,
        "inputKeys": ["extraction_job_id", "corrected_data", "corrections_count", "review_request_id"],
        "outputKeys": ["finalization_status", "finalized_at", "final_data"]
    },
    {
        "name": "aggregate_results",
        "description": "Aggregate results from batch extraction",
        "retryCount": 3,
        "retryLogic": "FIXED",
        "retryDelaySeconds": 10,
        "timeoutSeconds": 120,
        "timeoutPolicy": "TIME_OUT_WF",
        "responseTimeoutSeconds": 120,
        "inputKeys": ["extraction_results", "confidence_threshold"],
        "outputKeys": ["results", "summary", "reviews_required"]
    }
]


# =============================================================================
# Workflow Registry
# =============================================================================

WORKFLOW_REGISTRY: Dict[str, Dict[str, Any]] = {
    "document_extraction_with_review": EXTRACTION_WITH_CONFIDENCE_ROUTING,
    "document_extraction_manual_review": EXTRACTION_WITH_MANUAL_REVIEW,
    "batch_extraction_with_selective_review": BATCH_EXTRACTION_WITH_SELECTIVE_REVIEW,
    "configurable_extraction_with_hitl": CONFIGURABLE_HITL_WORKFLOW,
}


def get_workflow_definition(workflow_name: str) -> Dict[str, Any]:
    """
    Get workflow definition by name.

    Args:
        workflow_name: Name of the workflow

    Returns:
        Workflow definition dictionary

    Raises:
        ValueError: If workflow not found
    """
    if workflow_name not in WORKFLOW_REGISTRY:
        available = ", ".join(WORKFLOW_REGISTRY.keys())
        raise ValueError(
            f"Workflow '{workflow_name}' not found. Available: {available}"
        )
    return WORKFLOW_REGISTRY[workflow_name]


def get_all_workflow_definitions() -> List[Dict[str, Any]]:
    """
    Get all workflow definitions.

    Returns:
        List of all workflow definitions
    """
    return list(WORKFLOW_REGISTRY.values())


def get_all_task_definitions() -> List[Dict[str, Any]]:
    """
    Get all task definitions for HITL workflows.

    Returns:
        List of all task definitions
    """
    return TASK_DEFINITIONS
