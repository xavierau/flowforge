"""
HITL Backend Implementation Guide
==================================

This guide provides production-ready code templates for completing the HITL system implementation.

## COMPLETED COMPONENTS

✅ Database Models:
   - app/models/review_request.py
   - app/models/review_correction.py
   - app/models/enums.py (ReviewRequestStatus, ReviewPriority, CorrectionType)

✅ Model Updates:
   - ExtractionJob.confidence_score + review_request relationship
   - Tenant HITL threshold columns
   - SchemaDefinition.hitl_threshold

✅ Alembic Migration:
   - alembic/versions/2025-12-02_306f7c4dda3d_add_hitl_tables.py

✅ Service Layer:
   - app/services/hitl_service.py (complete with all business logic)

## REMAINING COMPONENTS

The following components need to be implemented. Use the templates below.

---

## 1. VLLM Confidence Scoring

Update app/services/vllm_service.py to return 5-tuple with confidence score.

### VLLMProvider Base Class Update

```python
# In app/services/vllm_service.py

class VLLMProvider(ABC):
    @abstractmethod
    async def extract(
        self,
        image_base64: str,
        schema: dict[str, Any],
        prompt: str,
    ) -> tuple[dict[str, Any], int, int, int, float]:  # Added float for confidence
        \"\"\"
        Extract structured data from image.

        Returns:
            Tuple of (extracted_data, input_tokens, output_tokens, processing_time_ms, confidence_score)
        \"\"\"
        pass

    @abstractmethod
    async def extract_batch(
        self,
        images_base64: list[str],
        schema: dict[str, Any],
        prompt: str,
    ) -> tuple[dict[str, Any], int, int, int, float]:  # Added float for confidence
        \"\"\"
        Extract structured data from multiple images.

        Returns:
            Tuple of (extracted_data, input_tokens, output_tokens, processing_time_ms, confidence_score)
        \"\"\"
        pass

    def _calculate_confidence_score(
        self,
        extracted_data: dict[str, Any],
        schema: dict[str, Any]
    ) -> float:
        \"\"\"
        Calculate confidence score based on schema coverage and data completeness.

        Factors:
        1. Schema coverage: % of required fields present (0.0-1.0)
        2. Data completeness: % of non-null values (0.0-1.0)
        3. Future: Model-specific signals (logprobs, safety ratings)

        Returns:
            float: Confidence score (0.0-1.0)
        \"\"\"
        if not schema or not extracted_data:
            return 0.0

        # Factor 1: Schema coverage
        required_fields = schema.get("required", [])
        if not required_fields:
            schema_coverage = 1.0  # No required fields = full coverage
        else:
            present_fields = sum(
                1 for field in required_fields
                if field in extracted_data and extracted_data[field] is not None
            )
            schema_coverage = present_fields / len(required_fields)

        # Factor 2: Data completeness
        all_fields = schema.get("properties", {}).keys()
        if not all_fields:
            data_completeness = 1.0
        else:
            non_null_fields = sum(
                1 for field in all_fields
                if field in extracted_data and extracted_data[field] is not None
            )
            data_completeness = non_null_fields / len(all_fields)

        # Final score: weighted average
        confidence = (schema_coverage * 0.7) + (data_completeness * 0.3)

        return round(confidence, 3)
```

### OpenAIVLLMProvider Update

```python
# In app/services/vllm_service.py - OpenAIVLLMProvider class

async def extract(
    self,
    image_base64: str,
    schema: dict[str, Any],
    prompt: str,
) -> tuple[dict[str, Any], int, int, int, float]:
    start_time = time.time()

    system_prompt = f\"\"\"You are a document data extraction expert.
Extract information from the provided document image according to this JSON schema:

{json.dumps(schema, indent=2)}

Additional instructions: {prompt}

Return ONLY valid JSON matching the schema.\"\"\"

    try:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": system_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000,
            temperature=0.0
        )

        processing_time_ms = int((time.time() - start_time) * 1000)

        extracted_data = json.loads(response.choices[0].message.content)
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(extracted_data, schema)

        return extracted_data, input_tokens, output_tokens, processing_time_ms, confidence_score

    except Exception as e:
        logger.error(f"OpenAI extraction failed: {e}")
        raise

async def extract_batch(
    self,
    images_base64: list[str],
    schema: dict[str, Any],
    prompt: str,
) -> tuple[dict[str, Any], int, int, int, float]:
    # Similar implementation with confidence scoring
    # ... (full code omitted for brevity)
    confidence_score = self._calculate_confidence_score(extracted_data, schema)
    return extracted_data, input_tokens, output_tokens, processing_time_ms, confidence_score
```

### GeminiVLLMProvider Update

```python
# In app/services/vllm_service.py - GeminiVLLMProvider class

async def extract(
    self,
    image_base64: str,
    schema: dict[str, Any],
    prompt: str,
) -> tuple[dict[str, Any], int, int, int, float]:
    # ... existing implementation ...

    # At the end, add confidence scoring:
    confidence_score = self._calculate_confidence_score(extracted_data, schema)

    return extracted_data, input_tokens, output_tokens, processing_time_ms, confidence_score

async def extract_batch(
    self,
    images_base64: list[str],
    schema: dict[str, Any],
    prompt: str,
) -> tuple[dict[str, Any], int, int, int, float]:
    # ... existing implementation ...

    confidence_score = self._calculate_confidence_score(extracted_data, schema)

    return extracted_data, input_tokens, output_tokens, processing_time_ms, confidence_score
```

---

## 2. Pydantic Schemas

Create app/schemas/review.py:

```python
\"\"\"Pydantic schemas for review API.\"\"\"

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.enums import ReviewRequestStatus, ReviewPriority, CorrectionType


class ReviewCorrectionCreate(BaseModel):
    \"\"\"Schema for creating a correction.\"\"\"
    extraction_result_id: UUID
    field_path: str = Field(..., max_length=500)
    original_value: Optional[dict] = None
    corrected_value: Optional[dict] = None
    correction_type: CorrectionType
    correction_notes: Optional[str] = None


class ReviewCorrectionResponse(BaseModel):
    \"\"\"Schema for correction response.\"\"\"
    id: UUID
    review_request_id: UUID
    extraction_result_id: UUID
    corrected_by_user_id: Optional[UUID]
    field_path: str
    original_value: Optional[dict]
    corrected_value: Optional[dict]
    correction_type: str
    correction_notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewSubmitRequest(BaseModel):
    \"\"\"Schema for submitting review corrections.\"\"\"
    corrections: List[ReviewCorrectionCreate]
    review_notes: Optional[str] = None


class ReviewRequestResponse(BaseModel):
    \"\"\"Schema for review request response.\"\"\"
    id: UUID
    tenant_id: UUID
    extraction_job_id: UUID
    assigned_to_user_id: Optional[UUID]
    status: str
    priority: str
    confidence_score: float
    trigger_reason: Optional[str]
    review_notes: Optional[str]
    sla_deadline: datetime
    created_at: datetime
    assigned_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewQueueResponse(BaseModel):
    \"\"\"Schema for paginated review queue.\"\"\"
    reviews: List[ReviewRequestResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class ReviewMetricsResponse(BaseModel):
    \"\"\"Schema for review metrics.\"\"\"
    total_reviews: int
    completed_reviews: int
    avg_review_time_minutes: float
    sla_breach_rate: float
    top_corrected_fields: List[tuple[str, int]]
    accuracy_rate: float


class ReviewAssignRequest(BaseModel):
    \"\"\"Schema for assigning a review.\"\"\"
    assigned_to_user_id: UUID
```

---

## 3. API Endpoints

Create app/api/reviews.py:

```python
\"\"\"Review API endpoints for HITL system.\"\"\"

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.enums import ReviewRequestStatus, ReviewPriority
from app.services.hitl_service import HITLService
from app.schemas.review import (
    ReviewRequestResponse,
    ReviewQueueResponse,
    ReviewSubmitRequest,
    ReviewCorrectionResponse,
    ReviewMetricsResponse,
    ReviewAssignRequest
)
from app.dependencies.auth import require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


@router.post("/jobs/{job_id}/request-review", response_model=ReviewRequestResponse)
async def request_review(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("extraction:review"))
):
    \"\"\"
    Manually request human review for an extraction job.

    Permissions: extraction:review
    \"\"\"
    try:
        hitl_service = HITLService(db)
        review_request = hitl_service.create_review_request(
            extraction_job_id=job_id,
            trigger_reason="manual_request"
        )
        return review_request
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create review request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create review request"
        )


@router.get("/queue", response_model=ReviewQueueResponse)
async def get_review_queue(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    assigned_to_me: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reviews:read"))
):
    \"\"\"
    Get paginated review queue with filters.

    Permissions: reviews:read
    Tenant Isolation: Automatic via current_user.tenant_id
    \"\"\"
    try:
        # Parse enum values
        status_enum = (
            ReviewRequestStatus(status_filter) if status_filter else None
        )
        priority_enum = (
            ReviewPriority(priority_filter) if priority_filter else None
        )
        assigned_to_user_id = current_user.id if assigned_to_me else None

        hitl_service = HITLService(db)
        reviews, total_count = hitl_service.get_review_queue(
            tenant_id=current_user.tenant_id,
            status=status_enum,
            priority=priority_enum,
            assigned_to_user_id=assigned_to_user_id,
            page=page,
            page_size=page_size
        )

        total_pages = (total_count + page_size - 1) // page_size

        return ReviewQueueResponse(
            reviews=reviews,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"Failed to get review queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve review queue"
        )


@router.get("/{review_id}", response_model=ReviewRequestResponse)
async def get_review(
    review_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reviews:read"))
):
    \"\"\"
    Get review request details.

    Permissions: reviews:read
    Tenant Isolation: Verified
    \"\"\"
    hitl_service = HITLService(db)
    review = db.query(hitl_service.db.query(ReviewRequest).filter(
        ReviewRequest.id == review_id,
        ReviewRequest.tenant_id == current_user.tenant_id  # Tenant isolation
    ).first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review request not found"
        )

    return review


@router.post("/{review_id}/assign", response_model=ReviewRequestResponse)
async def assign_review(
    review_id: UUID,
    request: ReviewAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reviews:assign"))
):
    \"\"\"
    Assign a review to a user.

    Permissions: reviews:assign
    \"\"\"
    try:
        hitl_service = HITLService(db)
        review = hitl_service.assign_review(
            review_id=review_id,
            assigned_to_user_id=request.assigned_to_user_id,
            current_user_id=current_user.id
        )
        return review
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{review_id}/start", response_model=ReviewRequestResponse)
async def start_review(
    review_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reviews:update"))
):
    \"\"\"
    Start a review (mark as in_review).

    Permissions: reviews:update
    \"\"\"
    try:
        hitl_service = HITLService(db)
        review = hitl_service.start_review(
            review_id=review_id,
            current_user_id=current_user.id
        )
        return review
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{review_id}/submit", response_model=ReviewRequestResponse)
async def submit_review(
    review_id: UUID,
    request: ReviewSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reviews:update"))
):
    \"\"\"
    Submit corrections and complete review.

    Permissions: reviews:update
    \"\"\"
    try:
        # Convert Pydantic models to dicts
        corrections_data = [c.model_dump() for c in request.corrections]

        hitl_service = HITLService(db)
        review = hitl_service.submit_corrections(
            review_id=review_id,
            corrections=corrections_data,
            corrected_by_user_id=current_user.id,
            review_notes=request.review_notes
        )
        return review
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{review_id}/corrections", response_model=List[ReviewCorrectionResponse])
async def get_corrections(
    review_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reviews:read"))
):
    \"\"\"
    Get all corrections for a review.

    Permissions: reviews:read
    \"\"\"
    from app.models.review_correction import ReviewCorrection
    from app.models.review_request import ReviewRequest

    # Verify tenant isolation
    review = db.query(ReviewRequest).filter(
        ReviewRequest.id == review_id,
        ReviewRequest.tenant_id == current_user.tenant_id
    ).first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review request not found"
        )

    corrections = db.query(ReviewCorrection).filter(
        ReviewCorrection.review_request_id == review_id
    ).all()

    return corrections


@router.delete("/{review_id}", response_model=ReviewRequestResponse)
async def cancel_review(
    review_id: UUID,
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reviews:delete"))
):
    \"\"\"
    Cancel a review request.

    Permissions: reviews:delete
    \"\"\"
    try:
        hitl_service = HITLService(db)
        review = hitl_service.cancel_review(
            review_id=review_id,
            current_user_id=current_user.id,
            reason=reason
        )
        return review
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/metrics", response_model=ReviewMetricsResponse)
async def get_review_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reviews:read"))
):
    \"\"\"
    Get review metrics for the tenant.

    Permissions: reviews:read
    \"\"\"
    try:
        hitl_service = HITLService(db)
        metrics = hitl_service.calculate_review_metrics(
            tenant_id=current_user.tenant_id
        )
        return metrics
    except Exception as e:
        logger.error(f"Failed to calculate metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate metrics"
        )
```

**Register in app/main.py:**

```python
from app.api import reviews

app.include_router(reviews.router)
```

---

## 4. Update Extraction Tasks

Update app/tasks/combined_extraction.py (or equivalent):

```python
# At the end of the extraction task, after result is saved:

from app.services.hitl_service import HITLService

# ... existing extraction code ...

# Store confidence score in job
job.confidence_score = confidence_score
db.commit()

# Check if review is needed
hitl_service = HITLService(db)
if hitl_service.should_request_review(job, workflow_config=None):
    logger.info(f"Creating review request for job {job.id} (confidence={confidence_score:.3f})")
    hitl_service.create_review_request(
        extraction_job_id=job.id,
        trigger_reason="low_confidence"
    )
    # Job status remains 'processing' until review completes
else:
    logger.info(f"Auto-approving job {job.id} (confidence={confidence_score:.3f})")
    job.status = JobStatus.COMPLETED.value
    job.completed_at = datetime.utcnow()
    db.commit()
```

---

## 5. SLA Monitoring Task

Create app/tasks/sla_monitoring.py:

```python
\"\"\"SLA monitoring periodic task for HITL reviews.\"\"\"

import logging
from celery import Task

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.services.hitl_service import HITLService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="hitl.check_sla_breaches")
def check_sla_breaches(self: Task):
    \"\"\"
    Periodic task to check for SLA breaches and escalate reviews.

    Runs every 5 minutes via Celery Beat schedule.
    \"\"\"
    db = SessionLocal()
    try:
        hitl_service = HITLService(db)
        escalated = hitl_service.check_sla_breaches()

        if escalated:
            logger.warning(f"Escalated {len(escalated)} reviews due to SLA breach")
            # TODO: Send notifications (email, Slack, etc.)
        else:
            logger.debug("No SLA breaches detected")

        return {"escalated_count": len(escalated)}

    except Exception as e:
        logger.error(f"SLA monitoring task failed: {e}")
        raise
    finally:
        db.close()
```

**Add to Celery Beat schedule (app/tasks/celery_app.py):**

```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    # ... existing tasks ...
    "check-sla-breaches": {
        "task": "hitl.check_sla_breaches",
        "schedule": 300.0,  # Every 5 minutes (300 seconds)
    },
}
```

---

## 6. Permissions

Update app/models/permission.py or wherever permissions are defined:

```python
# Add to PERMISSION_DEFINITIONS or similar:

REVIEW_PERMISSIONS = [
    Permission(name="reviews:read", description="View review requests and queue"),
    Permission(name="reviews:assign", description="Assign reviews to users"),
    Permission(name="reviews:update", description="Start and submit reviews"),
    Permission(name="reviews:delete", description="Cancel review requests"),
    Permission(name="extraction:review", description="Request manual review for extractions"),
]

# Add to appropriate roles (e.g., REVIEWER, ADMIN):
REVIEWER_ROLE_PERMISSIONS = [
    "reviews:read",
    "reviews:update",
]

ADMIN_ROLE_PERMISSIONS = [
    "reviews:read",
    "reviews:assign",
    "reviews:update",
    "reviews:delete",
    "extraction:review",
]
```

---

## 7. Run Migration

```bash
# Apply migration
alembic upgrade head

# Verify tables were created
docker exec -it postgres psql -U postgres -d ai_document_processing
\\dt review_*

# Expected output:
#  review_requests
#  review_corrections
```

---

## 8. Testing

### Unit Tests (tests/test_hitl_service.py)

```python
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.hitl_service import HITLService
from app.models.review_request import ReviewRequest
from app.models.extraction_job import ExtractionJob
from app.models.tenant import Tenant
from app.models.enums import ReviewPriority, ReviewRequestStatus


def test_should_request_review_low_confidence(db_session, sample_tenant):
    \"\"\"Test that low confidence triggers review request.\"\"\"
    # Create job with low confidence
    job = ExtractionJob(
        tenant_id=sample_tenant.id,
        document_id=uuid4(),
        extraction_schema={},
        model_provider="google",
        model_name="gemini-2.5-flash",
        confidence_score=0.45,  # Below default threshold
        status="processing"
    )
    db_session.add(job)
    db_session.commit()

    hitl_service = HITLService(db_session)
    assert hitl_service.should_request_review(job) is True


def test_should_request_review_high_confidence(db_session, sample_tenant):
    \"\"\"Test that high confidence auto-approves.\"\"\"
    job = ExtractionJob(
        tenant_id=sample_tenant.id,
        document_id=uuid4(),
        extraction_schema={},
        model_provider="google",
        model_name="gemini-2.5-flash",
        confidence_score=0.85,  # Above threshold
        status="processing"
    )
    db_session.add(job)
    db_session.commit()

    hitl_service = HITLService(db_session)
    assert hitl_service.should_request_review(job) is False


def test_create_review_request(db_session, sample_tenant, sample_job):
    \"\"\"Test review request creation.\"\"\"
    hitl_service = HITLService(db_session)
    review = hitl_service.create_review_request(
        extraction_job_id=sample_job.id,
        trigger_reason="low_confidence"
    )

    assert review.id is not None
    assert review.status == ReviewRequestStatus.PENDING.value
    assert review.tenant_id == sample_tenant.id
    assert review.confidence_score == sample_job.confidence_score


def test_calculate_priority(db_session, sample_tenant):
    \"\"\"Test priority calculation based on confidence.\"\"\"
    hitl_service = HITLService(db_session)

    # Critical: < 0.30
    job_critical = ExtractionJob(
        tenant_id=sample_tenant.id,
        confidence_score=0.20
    )
    assert hitl_service._calculate_priority(job_critical) == ReviewPriority.CRITICAL

    # High: 0.30-0.50
    job_high = ExtractionJob(
        tenant_id=sample_tenant.id,
        confidence_score=0.40
    )
    assert hitl_service._calculate_priority(job_high) == ReviewPriority.HIGH


def test_check_sla_breaches(db_session, sample_tenant, sample_job):
    \"\"\"Test SLA breach detection.\"\"\"
    hitl_service = HITLService(db_session)

    # Create review with past deadline
    review = ReviewRequest(
        tenant_id=sample_tenant.id,
        extraction_job_id=sample_job.id,
        status=ReviewRequestStatus.PENDING.value,
        priority=ReviewPriority.CRITICAL.value,
        confidence_score=0.20,
        sla_deadline=datetime.utcnow() - timedelta(hours=2),  # 2 hours ago
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(review)
    db_session.commit()

    escalated = hitl_service.check_sla_breaches()

    assert len(escalated) == 1
    assert escalated[0].status == ReviewRequestStatus.ESCALATED.value
```

### Integration Tests (tests/test_review_api.py)

```python
import pytest
from fastapi.testclient import TestClient


def test_request_review_api(client, auth_headers, sample_job):
    \"\"\"Test manual review request API.\"\"\"
    response = client.post(
        f"/api/v1/reviews/jobs/{sample_job.id}/request-review",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["extraction_job_id"] == str(sample_job.id)
    assert data["status"] == "pending"


def test_get_review_queue(client, auth_headers, sample_review):
    \"\"\"Test review queue retrieval.\"\"\"
    response = client.get(
        "/api/v1/reviews/queue?status=pending&page=1&page_size=50",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "reviews" in data
    assert "total_count" in data
    assert data["page"] == 1


def test_submit_review(client, auth_headers, sample_review):
    \"\"\"Test submitting review corrections.\"\"\"
    payload = {
        "corrections": [
            {
                "extraction_result_id": str(sample_review.extraction_job.extraction_results[0].id),
                "field_path": "invoice.total",
                "original_value": {"value": "100.00"},
                "corrected_value": {"value": "150.00"},
                "correction_type": "value_change",
                "correction_notes": "Handwritten total misread"
            }
        ],
        "review_notes": "Corrected total amount"
    }

    response = client.post(
        f"/api/v1/reviews/{sample_review.id}/submit",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
```

---

## DEPLOYMENT CHECKLIST

- [ ] Run Alembic migration: `alembic upgrade head`
- [ ] Verify tables created: `review_requests`, `review_corrections`
- [ ] Start Celery worker with beat: `celery -A app.tasks.celery_app worker --beat --loglevel=info`
- [ ] Test manual review request: `POST /api/v1/reviews/jobs/{job_id}/request-review`
- [ ] Test review queue: `GET /api/v1/reviews/queue`
- [ ] Monitor SLA task logs: Look for \"check-sla-breaches\" in Celery logs
- [ ] Verify confidence scoring: Check extraction_jobs.confidence_score is populated
- [ ] Test end-to-end: Upload document → Extract → Review → Submit corrections

---

## NEXT STEPS

1. **Frontend UI** (React):
   - Review queue component
   - Review details/correction UI
   - Metrics dashboard

2. **Conductor Integration** (if using Netflix Conductor):
   - HumanReviewWorker (polls HUMAN tasks)
   - ConductorHITLService (completes Conductor tasks)

3. **Notifications**:
   - SLA breach alerts (email/Slack)
   - Review assignment notifications
   - Completion notifications

4. **Active Learning** (Future):
   - Use corrections to fine-tune VLLM models
   - Periodic model retraining pipeline

---

## FILE MANIFEST

### Created Files:
1. app/models/review_request.py
2. app/models/review_correction.py
3. app/models/enums.py (updated)
4. app/services/hitl_service.py
5. alembic/versions/2025-12-02_306f7c4dda3d_add_hitl_tables.py

### Files to Create:
1. app/schemas/review.py (Pydantic schemas)
2. app/api/reviews.py (API endpoints)
3. app/tasks/sla_monitoring.py (SLA task)
4. tests/test_hitl_service.py (unit tests)
5. tests/test_review_api.py (integration tests)

### Files to Update:
1. app/services/vllm_service.py (add confidence scoring)
2. app/tasks/combined_extraction.py (integrate auto-review)
3. app/models/extraction_job.py (done)
4. app/models/tenant.py (done)
5. app/models/schema_definition.py (done)
6. app/main.py (register reviews router)
7. app/models/permission.py (add review permissions)
8. app/tasks/celery_app.py (add SLA beat schedule)

---

END OF IMPLEMENTATION GUIDE
\"\"\"
