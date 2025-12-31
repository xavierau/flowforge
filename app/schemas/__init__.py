"""Pydantic schemas for API request/response models."""

from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentUploadResponse,
)
from app.schemas.extraction import (
    ParseRequest,
    ParseResponse,
    ModelConfig,
)
from app.schemas.job import (
    JobStatusResponse,
    JobResultResponse,
    JobProgress,
)
from app.schemas.document_split import (
    SplitJobCreateRequest,
    SplitJobCreateResponse,
    SplitJobProgress,
    SplitJobStatusResponse,
    SplitJobResultsResponse,
    PageAnalysisResult,
    ChildDocumentResponse,
    ChildDocumentsListResponse,
)

__all__ = [
    "DocumentResponse",
    "DocumentListResponse",
    "DocumentUploadResponse",
    "ParseRequest",
    "ParseResponse",
    "ModelConfig",
    "JobStatusResponse",
    "JobResultResponse",
    "JobProgress",
    # Document Split schemas
    "SplitJobCreateRequest",
    "SplitJobCreateResponse",
    "SplitJobProgress",
    "SplitJobStatusResponse",
    "SplitJobResultsResponse",
    "PageAnalysisResult",
    "ChildDocumentResponse",
    "ChildDocumentsListResponse",
]
