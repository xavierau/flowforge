"""Conductor workers for executing workflow nodes.

Worker Types:
- ExtractionWorker: VLLM-based document extraction
- PythonWorker: Python code execution in Docker sandbox
- HttpRequestWorker: HTTP requests with retry logic
- ConditionWorker: Conditional expression evaluation
- HumanReviewWorker: Human-in-the-loop review tasks (HITL)
- LoopWorker: Array iteration with n8n-style loop context
- LLMWorker: General-purpose LLM prompt/response

HITL Worker Pattern:
HumanReviewWorker implements a special pattern for human tasks:
1. Worker creates ReviewRequest, returns IN_PROGRESS
2. Workflow pauses until human submits review
3. ConductorHITLService completes task with corrected_data
4. Workflow resumes with review output

Loop Worker Context (n8n-style):
LoopWorker provides these context variables for each iteration:
- $loop.item: Current item being processed
- $loop.index: Current index (0-based)
- $loop.first: Boolean, true if first item
- $loop.last: Boolean, true if last item
- $loop.length: Total array length
"""

from .base_worker import BaseWorker
from .extraction_worker import ExtractionWorker
from .http_request_worker import HttpRequestWorker
from .condition_worker import ConditionWorker
from .human_review_worker import HumanReviewWorker
from .loop_worker import LoopWorker
from .llm_worker import LLMWorker

# PythonWorker requires docker - make import optional
try:
    from .python_worker import PythonWorker
    _PYTHON_WORKER_AVAILABLE = True
except ImportError:
    PythonWorker = None  # type: ignore
    _PYTHON_WORKER_AVAILABLE = False

__all__ = [
    "BaseWorker",
    "ExtractionWorker",
    "PythonWorker",
    "HttpRequestWorker",
    "ConditionWorker",
    "HumanReviewWorker",
    "LoopWorker",
    "LLMWorker",
]
