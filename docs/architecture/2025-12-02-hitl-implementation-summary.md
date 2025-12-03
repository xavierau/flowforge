the# HITL Implementation Summary

**Quick Reference Guide for Human-in-the-Loop Service**
**Date:** 2025-12-02

---

## Executive Summary

This document provides a high-level overview of the HITL architecture design for the AI Document Processing platform. For complete technical details, see [2025-12-02-hitl-architecture.md](./2025-12-02-hitl-architecture.md).

---

## Key Components

### 1. Database Schema (2 New Tables)

**review_requests**
- Tracks human review requests for extraction jobs
- Links to ExtractionJob (one-to-one relationship)
- Contains: status, priority, SLA tracking, assignment info
- State machine: `pending → assigned → in_review → completed`

**review_corrections**
- Stores field-level human corrections
- Captures: field_path (JSONPath), original_value, corrected_value, correction_type
- Used for immediate correction + long-term AI improvement

### 2. Service Layer

**HITLService** (`app/services/hitl_service.py`)
- Core business logic for review lifecycle
- Key methods:
  - `should_request_review()` - Confidence threshold routing
  - `create_review_request()` - Create review request
  - `get_review_queue()` - Get pending reviews
  - `assign_review()` - Assign to reviewer
  - `submit_corrections()` - Process human feedback
  - `apply_corrections_to_result()` - Update extraction data
  - `check_sla_breaches()` - Monitor SLA violations

**Confidence Thresholds (Configurable)**

Thresholds are **configurable at multiple levels** (not hardcoded):
- **Global defaults** - System-wide fallback values
- **Per-tenant** - Tenant-specific overrides
- **Per-workflow** - Workflow node configuration
- **Per-schema** - Schema-specific requirements

**Default Values:**
```python
CRITICAL: < 0.30  (SLA: 1 hour)   # Configurable: tenant.hitl_critical_threshold
HIGH:     0.30-0.50 (SLA: 2 hours) # Configurable: tenant.hitl_high_threshold
NORMAL:   0.50-0.60 (SLA: 4 hours) # Configurable: tenant.hitl_normal_threshold
LOW:      0.60-0.70 (SLA: 8 hours) # Configurable: tenant.hitl_low_threshold
Auto-approve: > 0.70               # Configurable: tenant.hitl_auto_approve_threshold
```

**Configuration Priority:** Workflow Node Config > Schema Config > Tenant Settings > Global Defaults

### 3. Conductor Integration

**HUMAN Task Type**
- Leverage Netflix Conductor's built-in HUMAN task
- Workflow pauses until human review completes
- Worker: `HumanReviewWorker` polls for HUMAN tasks
- Completion: `ConductorHITLService.complete_conductor_task()`

**Workflow Example**
```json
{
  "tasks": [
    {"type": "SIMPLE", "name": "extract_document"},
    {"type": "SWITCH", "name": "check_confidence"},
    {"type": "HUMAN", "name": "human_review"},  // Pauses here
    {"type": "SIMPLE", "name": "finalize"}
  ]
}
```

### 4. API Endpoints

**Review Management**
```
POST   /api/v1/jobs/{job_id}/request-review    # Manual review request
GET    /api/v1/reviews/queue                   # Review queue (filtered)
GET    /api/v1/reviews/{review_id}             # Review details
POST   /api/v1/reviews/{review_id}/assign      # Assign to reviewer
POST   /api/v1/reviews/{review_id}/start       # Start review
POST   /api/v1/reviews/{review_id}/submit      # Submit corrections
GET    /api/v1/reviews/{review_id}/corrections # Get corrections
DELETE /api/v1/reviews/{review_id}             # Cancel review
GET    /api/v1/reviews/metrics                 # Accuracy metrics
```

### 5. VLLM Confidence Scoring

**Updated Provider Interface**
```python
# BEFORE
async def extract(...) -> Tuple[dict, int, int, int]:

# AFTER
async def extract(...) -> Tuple[dict, int, int, int, float]:
    # Returns: (data, input_tokens, output_tokens, time_ms, confidence_score)
```

**Confidence Calculation**
- Factor 1: Schema coverage (% of required fields present)
- Factor 2: Data completeness (% of non-null values)
- Factor 3: Model-specific signals (future: logprobs, safety ratings)
- Final score: Average of all factors (0.0-1.0)

---

## Data Flow

### Extraction with Auto-HITL Routing

```
1. User uploads document
2. Extraction job created
3. VLLM extracts data with confidence score
4. Check confidence score against threshold:
   - If > threshold (default: 0.70): Auto-approve (complete job)
   - If < threshold: Create ReviewRequest with priority
   - Threshold source: workflow config > tenant settings > default (0.70)
5. Reviewer assigned to review (based on priority)
6. Reviewer submits corrections
7. Corrections applied to ExtractionResult
8. Job marked as completed
```

### Conductor Workflow with HUMAN Task

```
1. Workflow starts with extraction
2. SWITCH task checks confidence
3. If low: HUMAN task created
4. HumanReviewWorker creates ReviewRequest
5. Workflow pauses (HUMAN task IN_PROGRESS)
6. Reviewer completes review
7. ConductorHITLService updates Conductor task (COMPLETED)
8. Workflow resumes with corrections
9. Finalization task applies corrections
```

---

## File Locations

### New Files
```
app/models/review_request.py              # ReviewRequest model
app/models/review_correction.py           # ReviewCorrection model
app/services/hitl_service.py              # Core HITL logic
app/services/conductor_hitl_service.py    # Conductor integration
app/api/reviews.py                        # API endpoints
app/schemas/review.py                     # Pydantic schemas
app/orchestration/workers/human_review_worker.py  # Conductor worker
alembic/versions/2025-12-02_add_hitl_tables.py   # Migration
```

### Modified Files
```
app/models/enums.py                       # Add ReviewRequestStatus, ReviewPriority, CorrectionType
app/models/extraction_job.py              # Add review_request relationship
app/models/tenant.py                      # Add review_requests relationship + threshold configs
app/models/extraction_schema.py           # Add hitl_threshold (nullable)
app/services/vllm_service.py              # Add confidence scoring
app/tasks/combined_extraction.py          # Add auto-review routing
```

---

## Implementation Checklist

### Phase 1: Foundation (Week 1)
- [ ] Create database migration
- [ ] Add enum definitions
- [ ] Update model relationships
- [ ] Run migration

### Phase 2: Confidence Scoring (Week 1)
- [ ] Update VLLMProvider interface
- [ ] Implement confidence calculation in GeminiVLLMProvider
- [ ] Implement confidence calculation in OpenAIVLLMProvider
- [ ] Update extraction tasks to populate confidence_score

### Phase 3: HITL Service (Week 2)
- [ ] Implement HITLService class
- [ ] Write unit tests
- [ ] Test with sample data

### Phase 4: API Layer (Week 2)
- [ ] Create Pydantic schemas
- [ ] Implement all API endpoints
- [ ] Write integration tests

### Phase 5: Conductor Integration (Week 3)
- [ ] Implement HumanReviewWorker
- [ ] Implement ConductorHITLService
- [ ] Test end-to-end workflow

### Phase 6: Auto-Routing (Week 3)
- [ ] Update extraction tasks with auto-review logic
- [ ] Add threshold columns to Tenant model
- [ ] Add hitl_threshold column to ExtractionSchema model
- [ ] Implement threshold resolution logic (workflow > schema > tenant > default)
- [ ] Test with various confidence scores and configurations

### Phase 7: SLA Monitoring (Week 4)
- [ ] Implement SLA breach detection
- [ ] Create Celery periodic task
- [ ] Implement escalation policy

### Phase 8: Frontend (Week 4)
- [ ] Review queue UI
- [ ] Review details/correction UI
- [ ] Metrics dashboard

---

## Testing Strategy

### Unit Tests
```python
# Test confidence routing
test_should_request_review_manual()
test_should_request_review_low_confidence()
test_should_request_review_high_confidence()

# Test review lifecycle
test_create_review_request()
test_assign_review()
test_start_review()
test_submit_corrections()
```

### Integration Tests
```python
# Test API endpoints
test_create_review_request_api()
test_get_review_queue_api()
test_assign_review_api()
test_submit_review_api()

# Test Conductor integration
test_human_task_creates_review()
test_completed_review_updates_conductor()
```

---

## Key Metrics to Monitor

```python
# Operational Metrics
review_requests_created_total          # Total reviews created
review_requests_completed_total        # Total reviews completed
review_time_seconds (histogram)        # Time to complete reviews
sla_breaches_total                     # SLA violations

# Quality Metrics
corrections_per_review (histogram)     # How many corrections per review
accuracy_rate_by_schema (gauge)        # Accuracy % by schema
most_corrected_fields                  # Which fields need most corrections

# Business Metrics
auto_approval_rate                     # % of extractions auto-approved
manual_review_rate                     # % requiring human review
avg_confidence_score                   # Average AI confidence
```

---

## Security & Permissions

### New Permissions
```
reviews:read    - View review queue and details
reviews:assign  - Assign reviews to users
reviews:update  - Start reviews and submit corrections
reviews:delete  - Cancel review requests
extraction:review - Request review for extraction jobs
```

### Tenant Isolation
- All review queries filter by `tenant_id`
- Reviewers only see their tenant's reviews
- Corrections inherit tenant isolation

---

## Performance Optimizations

### Database Indexes
```sql
-- Review queue queries (critical for performance)
CREATE INDEX idx_review_queue ON review_requests(
    tenant_id, status, priority, created_at
);

-- SLA monitoring
CREATE INDEX idx_review_requests_sla_deadline ON review_requests(sla_deadline);

-- Correction analysis
CREATE INDEX idx_review_corrections_field_path ON review_corrections(field_path);
```

### Query Best Practices
- Use composite index for queue queries
- Paginate results (50 per page, max 100)
- Cache metrics dashboard (5-minute refresh)

---

## Future Enhancements

### Phase 2 Features
1. **Active Learning**: Use corrections to fine-tune VLLM models
2. **Review Templates**: Pre-filled corrections for common errors
3. **Batch Review**: Review multiple similar documents at once
4. **Smart Assignment**: ML-based reviewer matching
5. **Review Sampling**: QA checks on high-confidence extractions

---

## Example Usage

### Manual Review Request
```bash
curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/request-review \
  -H "Authorization: Bearer $TOKEN"
```

### Get Review Queue
```bash
curl http://localhost:8000/api/v1/reviews/queue?status=pending&priority=high \
  -H "Authorization: Bearer $TOKEN"
```

### Submit Corrections
```bash
curl -X POST http://localhost:8000/api/v1/reviews/{review_id}/submit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "corrections": [
      {
        "extraction_result_id": "...",
        "field_path": "invoice.total",
        "original_value": "100.00",
        "corrected_value": "150.00",
        "correction_type": "value_change",
        "correction_notes": "Handwritten total was misread"
      }
    ]
  }'
```

---

## Questions & Troubleshooting

### Q: How do I adjust confidence thresholds?
A: Thresholds are configurable at multiple levels:

**Option 1: Per-Tenant (Recommended for most cases)**
```python
# Add columns to Tenant model:
# - hitl_auto_approve_threshold (default: 0.70)
# - hitl_critical_threshold (default: 0.30)
# - hitl_high_threshold (default: 0.50)
# - hitl_normal_threshold (default: 0.60)
# - hitl_low_threshold (default: 0.70)

tenant.hitl_auto_approve_threshold = 0.80  # More conservative
db.commit()
```

**Option 2: Per-Workflow (For specific use cases)**
```json
// In workflow HITL node configuration
{
  "nodeType": "HUMAN_REVIEW",
  "config": {
    "confidence_threshold": 0.65,
    "priority_thresholds": {
      "critical": 0.25,
      "high": 0.45,
      "normal": 0.55,
      "low": 0.65
    }
  }
}
```

**Option 3: Per-Schema (For document type-specific requirements)**
```python
# Add to ExtractionSchema model:
# - hitl_threshold (nullable, overrides tenant default)

schema.hitl_threshold = 0.85  # High-stakes documents (contracts, legal)
db.commit()
```

**Priority:** Workflow Config > Schema Config > Tenant Settings > Global Defaults (hardcoded fallback)

### Q: How do I test without Conductor?
A: Use manual review request API (`POST /jobs/{job_id}/request-review`). Conductor integration is optional.

### Q: What if a review times out?
A: The `check_sla_breaches()` method (run every 5 min) marks it as `escalated` and reassigns.

### Q: How does threshold resolution work with multiple configuration levels?
A: The system uses a **cascading configuration pattern**:

**Example Scenario:**
```python
# Global Default (hardcoded fallback)
DEFAULT_THRESHOLD = 0.70

# Tenant Setting (in database)
tenant.hitl_auto_approve_threshold = 0.75  # Tenant wants more conservative

# Schema Setting (in database, nullable)
schema.hitl_threshold = None  # Not set for this schema

# Workflow Node Config (in workflow definition)
workflow_node_config = {
  "confidence_threshold": 0.80  # Specific workflow requires higher confidence
}

# Resolution Logic:
actual_threshold = (
    workflow_node_config.get('confidence_threshold')  # 0.80 (wins!)
    or schema.hitl_threshold                          # None (not set)
    or tenant.hitl_auto_approve_threshold             # 0.75
    or DEFAULT_THRESHOLD                              # 0.70
)
# Result: 0.80 is used
```

**Use Cases:**
- **Financial documents**: Set schema.hitl_threshold = 0.90 (require high confidence)
- **Receipts**: Set schema.hitl_threshold = 0.60 (accept lower confidence)
- **Critical workflow**: Override in workflow node config = 0.95
- **Testing**: Set tenant threshold lower to force more reviews

### Q: Can I customize the confidence calculation?
A: Yes, override `_calculate_confidence_score()` in each VLLMProvider.

### Q: How do corrections improve future extractions?
A: Phase 2 will add active learning. For now, corrections are stored for analysis.

---

**For complete technical details, see:** [2025-12-02-hitl-architecture.md](./2025-12-02-hitl-architecture.md)
