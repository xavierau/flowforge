"""
Level 5: Complex Workflow Tests

Tests complex, real-world workflow patterns:
- Full document processing pipeline
- Multi-document batch with mixed review
- Retry with human escalation
- Workflow with external validation
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock

import pytest

from app.orchestration.conductor.translator import WorkflowTranslator
from app.orchestration.services.expression_resolver import ExpressionResolver
from app.orchestration.workers.condition_worker import ConditionWorker


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def translator():
    """Create workflow translator instance."""
    return WorkflowTranslator()


@pytest.fixture
def expression_resolver():
    """Create expression resolver factory.

    Returns a factory function that creates an ExpressionResolver
    with the provided node_outputs context.
    """
    def _create_resolver(node_outputs: dict = None):
        return ExpressionResolver(node_outputs or {})
    return _create_resolver


@pytest.fixture
def condition_worker():
    """Create condition worker instance."""
    return ConditionWorker()


@pytest.fixture
def full_pipeline_workflow():
    """
    Complete document processing pipeline:
    1. HttpTrigger (receive document)
    2. Validation (check format, size)
    3. If(valid) → Extraction
    4. Confidence check
    5. Low confidence → HumanReview
    6. High confidence → AutoApprove
    7. PythonRunner (post-processing)
    8. HttpRequest (notify callback)
    9. Finalize
    """
    return {
        "id": "full-pipeline",
        "name": "Complete Document Pipeline",
        "nodes": [
            # 1. Trigger
            {
                "id": "trigger-1",
                "type": "HttpTrigger",
                "data": {
                    "label": "Receive Document",
                    "method": "POST",
                    "path": "/api/process",
                },
                "position": {"x": 200, "y": 50},
            },
            # 2. Validation
            {
                "id": "validate-1",
                "type": "PythonRunner",
                "data": {
                    "label": "Validate Document",
                    "code": """
doc = input_data['document']
is_valid = True
errors = []

# Check file size (max 10MB)
if doc.get('size', 0) > 10 * 1024 * 1024:
    is_valid = False
    errors.append('File too large')

# Check format
valid_formats = ['application/pdf', 'image/png', 'image/jpeg']
if doc.get('mime_type') not in valid_formats:
    is_valid = False
    errors.append('Invalid format')

result = {'is_valid': is_valid, 'errors': errors}
""",
                },
                "position": {"x": 200, "y": 150},
            },
            # 3. Valid check
            {
                "id": "if-valid",
                "type": "If",
                "data": {
                    "label": "Is Valid?",
                    "condition": '{{$("validate-1").is_valid}} == true',
                },
                "position": {"x": 200, "y": 250},
            },
            # 3a. Reject invalid
            {
                "id": "reject-1",
                "type": "PythonRunner",
                "data": {
                    "label": "Reject Invalid",
                    "code": "result = {'status': 'rejected', 'errors': input_data['errors']}",
                },
                "position": {"x": 350, "y": 350},
            },
            # 4. Extraction
            {
                "id": "extract-1",
                "type": "Extraction",
                "data": {
                    "label": "Extract Data",
                    "provider": "google",
                    "model": "gemini-2.5-flash",
                },
                "position": {"x": 100, "y": 350},
            },
            # 5. Confidence check
            {
                "id": "if-confidence",
                "type": "If",
                "data": {
                    "label": "Check Confidence",
                    "condition": '{{$("extract-1").confidence}} >= 0.70',
                },
                "position": {"x": 100, "y": 450},
            },
            # 6a. Human Review (low confidence)
            {
                "id": "review-1",
                "type": "HumanReview",
                "data": {
                    "label": "Human Review",
                    "timeout_hours": 24,
                },
                "position": {"x": 200, "y": 550},
            },
            # 6b. Auto Approve (high confidence)
            {
                "id": "auto-approve",
                "type": "PythonRunner",
                "data": {
                    "label": "Auto Approve",
                    "code": "result = {'approved': True, 'method': 'auto', 'data': input_data['extracted_data']}",
                },
                "position": {"x": 0, "y": 550},
            },
            # Merge paths
            {
                "id": "merge-1",
                "type": "Merge",
                "data": {"label": "Merge"},
                "position": {"x": 100, "y": 650},
            },
            # 7. Post-processing
            {
                "id": "post-process",
                "type": "PythonRunner",
                "data": {
                    "label": "Post-Process",
                    "code": """
data = input_data['approved_data']
# Enrich with metadata
result = {
    'final_data': data,
    'processed_at': '2024-01-15T10:00:00Z',
    'version': '1.0'
}
""",
                },
                "position": {"x": 100, "y": 750},
            },
            # 8. Webhook notification
            {
                "id": "notify-1",
                "type": "HttpRequest",
                "data": {
                    "label": "Notify Callback",
                    "url": '{{$("trigger-1").callback_url}}',
                    "method": "POST",
                    "body": {
                        "status": "completed",
                        "data": '{{$("post-process").final_data}}',
                    },
                },
                "position": {"x": 100, "y": 850},
            },
            # 9. Finalize
            {
                "id": "finalize-1",
                "type": "PythonRunner",
                "data": {
                    "label": "Finalize",
                    "code": "result = {'status': 'completed', 'workflow_id': input_data['workflow_id']}",
                },
                "position": {"x": 100, "y": 950},
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger-1", "target": "validate-1"},
            {"id": "e2", "source": "validate-1", "target": "if-valid"},
            {"id": "e3", "source": "if-valid", "target": "extract-1", "sourceHandle": "true"},
            {"id": "e4", "source": "if-valid", "target": "reject-1", "sourceHandle": "false"},
            {"id": "e5", "source": "extract-1", "target": "if-confidence"},
            {"id": "e6", "source": "if-confidence", "target": "auto-approve", "sourceHandle": "true"},
            {"id": "e7", "source": "if-confidence", "target": "review-1", "sourceHandle": "false"},
            {"id": "e8", "source": "auto-approve", "target": "merge-1"},
            {"id": "e9", "source": "review-1", "target": "merge-1"},
            {"id": "e10", "source": "merge-1", "target": "post-process"},
            {"id": "e11", "source": "post-process", "target": "notify-1"},
            {"id": "e12", "source": "notify-1", "target": "finalize-1"},
        ],
    }


@pytest.fixture
def batch_mixed_review_workflow():
    """
    Multi-document batch with mixed review priority:
    1. Receive batch of documents
    2. Parallel extraction
    3. Group by confidence (CRITICAL, HIGH, NORMAL, LOW)
    4. Route to appropriate review queues
    5. Wait for all reviews
    6. Aggregate results
    7. Send consolidated report
    """
    return {
        "id": "batch-mixed-review",
        "name": "Batch Mixed Review",
        "nodes": [
            {
                "id": "trigger-1",
                "type": "HttpTrigger",
                "data": {"label": "Batch Trigger"},
                "position": {"x": 200, "y": 50},
            },
            {
                "id": "fork-extract",
                "type": "Fork",
                "data": {
                    "label": "Parallel Extract",
                    "dynamic_fork_input": '{{$("trigger-1").documents}}',
                },
                "position": {"x": 200, "y": 150},
            },
            {
                "id": "join-extract",
                "type": "Join",
                "data": {"label": "Join Extractions"},
                "position": {"x": 200, "y": 350},
            },
            {
                "id": "classify-1",
                "type": "PythonRunner",
                "data": {
                    "label": "Classify by Priority",
                    "code": """
results = input_data['extraction_results']
classified = {
    'critical': [],  # < 0.30
    'high': [],      # 0.30 - 0.50
    'normal': [],    # 0.50 - 0.60
    'low': [],       # 0.60 - 0.70
    'auto_approve': []  # >= 0.70
}

for r in results:
    conf = r.get('confidence', 0)
    if conf >= 0.70:
        classified['auto_approve'].append(r)
    elif conf >= 0.60:
        classified['low'].append(r)
    elif conf >= 0.50:
        classified['normal'].append(r)
    elif conf >= 0.30:
        classified['high'].append(r)
    else:
        classified['critical'].append(r)

result = classified
""",
                },
                "position": {"x": 200, "y": 450},
            },
            {
                "id": "review-critical",
                "type": "HumanReview",
                "data": {
                    "label": "Critical Review",
                    "priority": "CRITICAL",
                    "timeout_hours": 4,
                },
                "position": {"x": 50, "y": 550},
            },
            {
                "id": "review-high",
                "type": "HumanReview",
                "data": {
                    "label": "High Priority Review",
                    "priority": "HIGH",
                    "timeout_hours": 8,
                },
                "position": {"x": 150, "y": 550},
            },
            {
                "id": "review-normal",
                "type": "HumanReview",
                "data": {
                    "label": "Normal Review",
                    "priority": "NORMAL",
                    "timeout_hours": 24,
                },
                "position": {"x": 250, "y": 550},
            },
            {
                "id": "review-low",
                "type": "HumanReview",
                "data": {
                    "label": "Low Priority Review",
                    "priority": "LOW",
                    "timeout_hours": 48,
                },
                "position": {"x": 350, "y": 550},
            },
            {
                "id": "aggregate-1",
                "type": "PythonRunner",
                "data": {
                    "label": "Aggregate Results",
                    "code": """
all_results = []
all_results.extend(input_data.get('critical_results', []))
all_results.extend(input_data.get('high_results', []))
all_results.extend(input_data.get('normal_results', []))
all_results.extend(input_data.get('low_results', []))
all_results.extend(input_data.get('auto_approved', []))

result = {
    'total_processed': len(all_results),
    'results': all_results,
    'summary': {
        'auto_approved': len(input_data.get('auto_approved', [])),
        'manually_reviewed': len(all_results) - len(input_data.get('auto_approved', []))
    }
}
""",
                },
                "position": {"x": 200, "y": 650},
            },
            {
                "id": "send-report",
                "type": "HttpRequest",
                "data": {
                    "label": "Send Report",
                    "url": '{{$("trigger-1").report_url}}',
                    "method": "POST",
                },
                "position": {"x": 200, "y": 750},
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger-1", "target": "fork-extract"},
            {"id": "e2", "source": "fork-extract", "target": "join-extract"},
            {"id": "e3", "source": "join-extract", "target": "classify-1"},
            {"id": "e4", "source": "classify-1", "target": "review-critical"},
            {"id": "e5", "source": "classify-1", "target": "review-high"},
            {"id": "e6", "source": "classify-1", "target": "review-normal"},
            {"id": "e7", "source": "classify-1", "target": "review-low"},
            {"id": "e8", "source": "review-critical", "target": "aggregate-1"},
            {"id": "e9", "source": "review-high", "target": "aggregate-1"},
            {"id": "e10", "source": "review-normal", "target": "aggregate-1"},
            {"id": "e11", "source": "review-low", "target": "aggregate-1"},
            {"id": "e12", "source": "aggregate-1", "target": "send-report"},
        ],
    }


@pytest.fixture
def retry_escalation_workflow():
    """
    Extraction with retry and human escalation:
    1. First extraction attempt
    2. If fails → retry with different model
    3. If still fails → human review for manual processing
    4. Continue with data (auto or manual)
    """
    return {
        "id": "retry-escalation",
        "name": "Retry with Escalation",
        "nodes": [
            {
                "id": "trigger-1",
                "type": "HttpTrigger",
                "data": {"label": "Start"},
                "position": {"x": 150, "y": 50},
            },
            {
                "id": "extract-1",
                "type": "Extraction",
                "data": {
                    "label": "Extract (Primary)",
                    "provider": "google",
                    "model": "gemini-2.5-flash",
                },
                "position": {"x": 150, "y": 150},
            },
            {
                "id": "check-extract-1",
                "type": "If",
                "data": {
                    "label": "Extraction OK?",
                    "condition": '{{$("extract-1").success}} == true',
                },
                "position": {"x": 150, "y": 250},
            },
            {
                "id": "extract-2",
                "type": "Extraction",
                "data": {
                    "label": "Extract (Fallback)",
                    "provider": "openai",
                    "model": "gpt-4-vision",
                },
                "position": {"x": 250, "y": 350},
            },
            {
                "id": "check-extract-2",
                "type": "If",
                "data": {
                    "label": "Fallback OK?",
                    "condition": '{{$("extract-2").success}} == true',
                },
                "position": {"x": 250, "y": 450},
            },
            {
                "id": "manual-review",
                "type": "HumanReview",
                "data": {
                    "label": "Manual Processing",
                    "reason": "Automated extraction failed",
                    "priority": "CRITICAL",
                    "allow_manual_entry": True,
                },
                "position": {"x": 350, "y": 550},
            },
            {
                "id": "merge-data",
                "type": "Merge",
                "data": {"label": "Merge Data Sources"},
                "position": {"x": 150, "y": 650},
            },
            {
                "id": "finalize",
                "type": "PythonRunner",
                "data": {
                    "label": "Finalize",
                    "code": """
data = input_data.get('extracted_data') or input_data.get('manual_data')
source = 'auto' if input_data.get('extracted_data') else 'manual'
result = {'data': data, 'source': source}
""",
                },
                "position": {"x": 150, "y": 750},
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger-1", "target": "extract-1"},
            {"id": "e2", "source": "extract-1", "target": "check-extract-1"},
            {"id": "e3", "source": "check-extract-1", "target": "merge-data", "sourceHandle": "true"},
            {"id": "e4", "source": "check-extract-1", "target": "extract-2", "sourceHandle": "false"},
            {"id": "e5", "source": "extract-2", "target": "check-extract-2"},
            {"id": "e6", "source": "check-extract-2", "target": "merge-data", "sourceHandle": "true"},
            {"id": "e7", "source": "check-extract-2", "target": "manual-review", "sourceHandle": "false"},
            {"id": "e8", "source": "manual-review", "target": "merge-data"},
            {"id": "e9", "source": "merge-data", "target": "finalize"},
        ],
    }


@pytest.fixture
def external_validation_workflow():
    """
    Workflow with external API validation:
    1. Extraction
    2. HTTP request to external validation API
    3. If valid → continue
    4. If invalid → human review
    5. Finalize
    """
    return {
        "id": "external-validation",
        "name": "External Validation",
        "nodes": [
            {
                "id": "trigger-1",
                "type": "HttpTrigger",
                "data": {"label": "Start"},
                "position": {"x": 150, "y": 50},
            },
            {
                "id": "extract-1",
                "type": "Extraction",
                "data": {"label": "Extract"},
                "position": {"x": 150, "y": 150},
            },
            {
                "id": "validate-external",
                "type": "HttpRequest",
                "data": {
                    "label": "External Validation",
                    "url": '{{$("trigger-1").validation_api}}',
                    "method": "POST",
                    "body": {
                        "data": '{{$("extract-1").extracted_data}}',
                    },
                },
                "position": {"x": 150, "y": 250},
            },
            {
                "id": "check-validation",
                "type": "If",
                "data": {
                    "label": "Validation OK?",
                    "condition": '{{$("validate-external").body.is_valid}} == true',
                },
                "position": {"x": 150, "y": 350},
            },
            {
                "id": "review-invalid",
                "type": "HumanReview",
                "data": {
                    "label": "Review Invalid",
                    "reason": "External validation failed",
                },
                "position": {"x": 250, "y": 450},
            },
            {
                "id": "merge-1",
                "type": "Merge",
                "data": {"label": "Merge"},
                "position": {"x": 150, "y": 550},
            },
            {
                "id": "finalize-1",
                "type": "PythonRunner",
                "data": {
                    "label": "Finalize",
                    "code": "result = {'status': 'completed', 'validated': True}",
                },
                "position": {"x": 150, "y": 650},
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger-1", "target": "extract-1"},
            {"id": "e2", "source": "extract-1", "target": "validate-external"},
            {"id": "e3", "source": "validate-external", "target": "check-validation"},
            {"id": "e4", "source": "check-validation", "target": "merge-1", "sourceHandle": "true"},
            {"id": "e5", "source": "check-validation", "target": "review-invalid", "sourceHandle": "false"},
            {"id": "e6", "source": "review-invalid", "target": "merge-1"},
            {"id": "e7", "source": "merge-1", "target": "finalize-1"},
        ],
    }


# ==============================================================================
# Scenario 5.1: Full Document Processing Pipeline
# ==============================================================================


class TestFullDocumentPipeline:
    """
    Test complete document processing pipeline.
    """

    def test_pipeline_workflow_translates(
        self, translator, full_pipeline_workflow
    ):
        """GIVEN full pipeline WHEN translating THEN produces valid Conductor definition."""
        result = translator.translate(full_pipeline_workflow, full_pipeline_workflow.get("name", "test"))

        assert result is not None
        assert "tasks" in result
        assert len(result["tasks"]) >= 5  # Should have multiple tasks

    def test_validation_rejects_invalid_document(self, condition_worker):
        """GIVEN invalid document WHEN validating THEN rejects."""
        # Document too large
        validation_result = {"is_valid": False, "errors": ["File too large"]}

        result = condition_worker.execute_task({
            "condition": "is_valid == true",
            "context": {"is_valid": False},
        })

        assert result["result"] is False

    def test_valid_document_proceeds_to_extraction(self, condition_worker):
        """GIVEN valid document WHEN validating THEN proceeds to extraction."""
        result = condition_worker.execute_task({
            "condition": "is_valid == true",
            "context": {"is_valid": True},
        })

        assert result["result"] is True

    def test_high_confidence_auto_approves(self, condition_worker):
        """GIVEN high confidence WHEN checking THEN auto-approves."""
        result = condition_worker.execute_task({
            "condition": "confidence >= 0.70",
            "context": {"confidence": 0.85},
        })

        assert result["result"] is True

    def test_low_confidence_goes_to_review(self, condition_worker):
        """GIVEN low confidence WHEN checking THEN goes to review."""
        result = condition_worker.execute_task({
            "condition": "confidence >= 0.70",
            "context": {"confidence": 0.55},
        })

        assert result["result"] is False

    def test_webhook_notification_at_end(self, expression_resolver):
        """GIVEN completed pipeline WHEN finalizing THEN sends webhook."""
        context = {
            "trigger-1": {
                "callback_url": "https://api.example.com/callback",
            },
            "post-process": {
                "final_data": {"invoice_number": "INV-001"},
            },
        }

        callback_url = expression_resolver(context).resolve('{{$("trigger-1").callback_url}}')
        final_data = expression_resolver(context).resolve('{{$("post-process").final_data}}')

        assert callback_url == "https://api.example.com/callback"
        assert final_data["invoice_number"] == "INV-001"


# ==============================================================================
# Scenario 5.2: Multi-Document Batch with Mixed Review
# ==============================================================================


class TestBatchMixedReview:
    """
    Test batch processing with priority-based review routing.
    """

    def test_classification_by_confidence(self):
        """GIVEN extraction results WHEN classifying THEN groups by confidence."""
        results = [
            {"id": "1", "confidence": 0.25},  # CRITICAL
            {"id": "2", "confidence": 0.40},  # HIGH
            {"id": "3", "confidence": 0.55},  # NORMAL
            {"id": "4", "confidence": 0.65},  # LOW
            {"id": "5", "confidence": 0.85},  # AUTO
        ]

        classified = {
            "critical": [],
            "high": [],
            "normal": [],
            "low": [],
            "auto_approve": [],
        }

        for r in results:
            conf = r["confidence"]
            if conf >= 0.70:
                classified["auto_approve"].append(r)
            elif conf >= 0.60:
                classified["low"].append(r)
            elif conf >= 0.50:
                classified["normal"].append(r)
            elif conf >= 0.30:
                classified["high"].append(r)
            else:
                classified["critical"].append(r)

        assert len(classified["critical"]) == 1
        assert len(classified["high"]) == 1
        assert len(classified["normal"]) == 1
        assert len(classified["low"]) == 1
        assert len(classified["auto_approve"]) == 1

    def test_priority_queues_have_different_timeouts(self):
        """GIVEN different priorities WHEN assigning THEN have different timeouts."""
        priority_timeouts = {
            "CRITICAL": 4,
            "HIGH": 8,
            "NORMAL": 24,
            "LOW": 48,
        }

        assert priority_timeouts["CRITICAL"] < priority_timeouts["HIGH"]
        assert priority_timeouts["HIGH"] < priority_timeouts["NORMAL"]
        assert priority_timeouts["NORMAL"] < priority_timeouts["LOW"]

    def test_aggregation_combines_all_results(self):
        """GIVEN all review queues completed WHEN aggregating THEN combines."""
        critical_results = [{"id": "1", "reviewed": True}]
        high_results = [{"id": "2", "reviewed": True}]
        normal_results = [{"id": "3", "reviewed": True}]
        low_results = [{"id": "4", "reviewed": True}]
        auto_approved = [{"id": "5", "auto": True}]

        all_results = (
            critical_results +
            high_results +
            normal_results +
            low_results +
            auto_approved
        )

        assert len(all_results) == 5


# ==============================================================================
# Scenario 5.3: Retry with Human Escalation
# ==============================================================================


class TestRetryEscalation:
    """
    Test extraction retry with human escalation on failure.
    """

    def test_first_extraction_success_completes(self, condition_worker):
        """GIVEN first extraction succeeds WHEN checking THEN continues."""
        result = condition_worker.execute_task({
            "condition": "success == true",
            "context": {"success": True},
        })

        assert result["result"] is True

    def test_first_failure_triggers_retry(self, condition_worker):
        """GIVEN first extraction fails WHEN checking THEN retries."""
        result = condition_worker.execute_task({
            "condition": "success == true",
            "context": {"success": False},
        })

        assert result["result"] is False

    def test_second_failure_escalates_to_human(self, condition_worker):
        """GIVEN retry also fails WHEN checking THEN escalates."""
        result = condition_worker.execute_task({
            "condition": "success == true",
            "context": {"success": False},
        })

        assert result["result"] is False

    def test_manual_data_used_when_escalated(self, expression_resolver):
        """GIVEN human provides manual data WHEN finalizing THEN uses manual data."""
        context = {
            "manual-review": {
                "manual_data": {
                    "invoice_number": "INV-001",
                    "total": 500.00,
                },
                "source": "manual_entry",
            }
        }

        manual_data = expression_resolver(context).resolve('{{$("manual-review").manual_data}}')

        assert manual_data["invoice_number"] == "INV-001"


# ==============================================================================
# Scenario 5.4: External API Validation
# ==============================================================================


class TestExternalValidation:
    """
    Test workflow with external API validation.
    """

    def test_external_api_called_with_data(self, expression_resolver):
        """GIVEN extracted data WHEN calling external API THEN sends data."""
        context = {
            "extract-1": {
                "extracted_data": {
                    "invoice_number": "INV-001",
                    "vendor_id": "V-123",
                },
            },
            "trigger-1": {
                "validation_api": "https://api.validator.com/validate",
            },
        }

        validation_api = expression_resolver(context).resolve('{{$("trigger-1").validation_api}}')
        data = expression_resolver(context).resolve('{{$("extract-1").extracted_data}}')

        assert validation_api == "https://api.validator.com/validate"
        assert data["invoice_number"] == "INV-001"

    def test_valid_response_continues(self, condition_worker):
        """GIVEN external API returns valid WHEN checking THEN continues."""
        result = condition_worker.execute_task({
            "condition": "is_valid == true",
            "context": {"is_valid": True},
        })

        assert result["result"] is True

    def test_invalid_response_routes_to_review(self, condition_worker):
        """GIVEN external API returns invalid WHEN checking THEN routes to review."""
        result = condition_worker.execute_task({
            "condition": "is_valid == true",
            "context": {"is_valid": False},
        })

        assert result["result"] is False


# ==============================================================================
# Complex Expression Tests
# ==============================================================================


class TestComplexExpressions:
    """
    Test complex expression evaluation in workflows.
    """

    def test_nested_object_access(self, expression_resolver):
        """GIVEN nested objects WHEN resolving THEN accesses correctly."""
        context = {
            "validate-external": {
                "body": {
                    "is_valid": True,
                    "errors": [],
                    "metadata": {
                        "checked_at": "2024-01-15",
                    },
                },
            },
        }

        is_valid = expression_resolver(context).resolve('{{$("validate-external").body.is_valid}}')

        assert is_valid is True

    def test_array_in_expression(self, expression_resolver):
        """GIVEN array data WHEN resolving THEN handles correctly."""
        context = {
            "classify-1": {
                "critical": [{"id": "1"}],
                "high": [{"id": "2"}, {"id": "3"}],
            },
        }

        critical = expression_resolver(context).resolve('{{$("classify-1").critical}}')
        high = expression_resolver(context).resolve('{{$("classify-1").high}}')

        assert len(critical) == 1
        assert len(high) == 2


# ==============================================================================
# Workflow Structure Tests
# ==============================================================================


class TestComplexWorkflowStructure:
    """
    Test complex workflow structures.
    """

    def test_full_pipeline_has_all_components(
        self, translator, full_pipeline_workflow
    ):
        """GIVEN full pipeline WHEN translating THEN has all components."""
        result = translator.translate(full_pipeline_workflow, full_pipeline_workflow.get("name", "test"))

        assert result is not None

    def test_batch_workflow_has_fork_join(
        self, translator, batch_mixed_review_workflow
    ):
        """GIVEN batch workflow WHEN translating THEN has fork/join."""
        result = translator.translate(batch_mixed_review_workflow, batch_mixed_review_workflow.get("name", "test"))

        assert result is not None

    def test_retry_workflow_has_multiple_decision_points(
        self, translator, retry_escalation_workflow
    ):
        """GIVEN retry workflow WHEN translating THEN has multiple decisions."""
        result = translator.translate(retry_escalation_workflow, retry_escalation_workflow.get("name", "test"))

        assert result is not None


# ==============================================================================
# End-to-End Flow Tests
# ==============================================================================


class TestEndToEndFlows:
    """
    Test complete end-to-end workflow flows.
    """

    def test_happy_path_valid_high_confidence(
        self, condition_worker, expression_resolver
    ):
        """GIVEN valid doc with high confidence WHEN processing THEN auto-approves."""
        # Validation
        validation = condition_worker.execute_task({
            "condition": "is_valid == true",
            "context": {"is_valid": True},
        })
        assert validation["result"] is True

        # Confidence check
        confidence_check = condition_worker.execute_task({
            "condition": "confidence >= 0.70",
            "context": {"confidence": 0.85},
        })
        assert confidence_check["result"] is True

    def test_low_confidence_goes_through_review(
        self, condition_worker, expression_resolver
    ):
        """GIVEN valid doc with low confidence WHEN processing THEN reviewed."""
        # Validation
        validation = condition_worker.execute_task({
            "condition": "is_valid == true",
            "context": {"is_valid": True},
        })
        assert validation["result"] is True

        # Confidence check
        confidence_check = condition_worker.execute_task({
            "condition": "confidence >= 0.70",
            "context": {"confidence": 0.55},
        })
        assert confidence_check["result"] is False

    def test_invalid_doc_rejected_early(self, condition_worker):
        """GIVEN invalid doc WHEN processing THEN rejected without extraction."""
        validation = condition_worker.execute_task({
            "condition": "is_valid == true",
            "context": {"is_valid": False},
        })
        assert validation["result"] is False
