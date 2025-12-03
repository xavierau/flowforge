"""Conductor workers for executing workflow nodes.

Worker Types:
- ExtractionWorker: VLLM-based document extraction
- PythonWorker: Python code execution in Docker sandbox
- HttpRequestWorker: HTTP requests with retry logic
- ConditionWorker: Conditional expression evaluation
- HumanReviewWorker: Human-in-the-loop review tasks (HITL)

HITL Worker Pattern:
HumanReviewWorker implements a special pattern for human tasks:
1. Worker creates ReviewRequest, returns IN_PROGRESS
2. Workflow pauses until human submits review
3. ConductorHITLService completes task with corrected_data
4. Workflow resumes with review output
"""

from .base_worker import BaseWorker
from .extraction_worker import ExtractionWorker
from .python_worker import PythonWorker
from .http_request_worker import HttpRequestWorker
from .condition_worker import ConditionWorker
from .human_review_worker import HumanReviewWorker

__all__ = [
    "BaseWorker",
    "ExtractionWorker",
    "PythonWorker",
    "HttpRequestWorker",
    "ConditionWorker",
    "HumanReviewWorker",
]
