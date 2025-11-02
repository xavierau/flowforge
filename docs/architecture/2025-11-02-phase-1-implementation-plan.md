# Phase 1 Implementation Plan
# AI Document Processing SaaS - MVP

**Document Version:** 1.0
**Date:** 2025-11-02
**Status:** Implementation Ready
**Sprint Duration:** 4-6 weeks

---

## 1. Phase 1 Overview

### 1.1 Scope
Build a **stateless, API-first document processing system** with:
- File upload endpoint (images, PDFs)
- Document parsing endpoint with custom schema and prompts
- Two-stage job processing: PDF→Image, Image→Structured JSON
- Database state management
- Result storage and retrieval

### 1.2 Architecture Principles
- **Stateless jobs:** All job state stored in database
- **Job-based processing:** Celery workers for async processing
- **API-first:** RESTful endpoints for all operations
- **Schema-driven:** User-provided JSON schemas for extraction
- **VLLM-powered:** Use Gemini/GPT-4V for image understanding

---

## 2. API Endpoints

### 2.1 Document Upload Endpoint

```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data

Parameters:
- file: File (required) - Image (PNG, JPG) or PDF
- metadata: JSON (optional) - Custom metadata

Response (201 Created):
{
  "document_id": "doc_abc123",
  "filename": "invoice.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 245678,
  "status": "uploaded",
  "page_count": 3,  // for PDFs
  "created_at": "2025-11-02T10:30:00Z"
}
```

**Implementation:**
1. Validate file type and size (max 50MB)
2. Upload to S3 (or local storage for dev)
3. Create `Document` record in database
4. If PDF: Queue `pdf_to_images` job
5. If image: Set status to `ready_for_extraction`
6. Return document metadata

---

### 2.2 Document Parsing Endpoint

```http
POST /api/v1/documents/{document_id}/parse
Content-Type: application/json

Body:
{
  "extraction_schema": {
    "type": "object",
    "properties": {
      "vendor_name": {"type": "string"},
      "invoice_number": {"type": "string"},
      "total_amount": {"type": "number"},
      "line_items": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "description": {"type": "string"},
            "quantity": {"type": "number"},
            "price": {"type": "number"}
          }
        }
      }
    },
    "required": ["vendor_name", "total_amount"]
  },
  "custom_prompt": "Extract invoice details. Pay special attention to line items table.",
  "model_config": {
    "provider": "google",  // or "openai"
    "model": "gemini-pro-vision"  // or "gpt-4-vision-preview"
  }
}

Response (202 Accepted):
{
  "extraction_job_id": "job_xyz789",
  "document_id": "doc_abc123",
  "status": "queued",
  "estimated_time_seconds": 15,
  "created_at": "2025-11-02T10:31:00Z"
}
```

**Implementation:**
1. Validate document exists and is ready
2. Validate JSON schema format
3. Create `ExtractionJob` record
4. Queue `image_to_json` job(s) for each page
5. Return job ID

---

### 2.3 Job Status Endpoint

```http
GET /api/v1/jobs/{job_id}/status

Response (200 OK):
{
  "job_id": "job_xyz789",
  "document_id": "doc_abc123",
  "status": "processing",  // queued, processing, completed, failed
  "progress": {
    "total_pages": 3,
    "completed_pages": 1
  },
  "started_at": "2025-11-02T10:31:05Z",
  "updated_at": "2025-11-02T10:31:12Z",
  "error": null
}
```

---

### 2.4 Extraction Results Endpoint

```http
GET /api/v1/jobs/{job_id}/result

Response (200 OK):
{
  "job_id": "job_xyz789",
  "document_id": "doc_abc123",
  "status": "completed",
  "extracted_data": {
    "vendor_name": "ACME Corp",
    "invoice_number": "INV-2024-001",
    "total_amount": 1250.00,
    "line_items": [
      {
        "description": "Widget A",
        "quantity": 10,
        "price": 100.00
      },
      {
        "description": "Widget B",
        "quantity": 5,
        "price": 50.00
      }
    ]
  },
  "metadata": {
    "model_used": "gemini-pro-vision",
    "tokens_used": 1250,
    "processing_time_ms": 8500,
    "confidence_score": 0.95
  },
  "completed_at": "2025-11-02T10:31:20Z"
}
```

---

### 2.5 Document List Endpoint

```http
GET /api/v1/documents?status=uploaded&limit=20&offset=0

Response (200 OK):
{
  "documents": [
    {
      "document_id": "doc_abc123",
      "filename": "invoice.pdf",
      "status": "ready_for_extraction",
      "created_at": "2025-11-02T10:30:00Z"
    }
  ],
  "total": 45,
  "limit": 20,
  "offset": 0
}
```

---

## 3. Database Schema

### 3.1 Documents Table

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    size_bytes INTEGER NOT NULL,
    file_path TEXT NOT NULL,  -- S3 key or local path
    status VARCHAR(50) NOT NULL,  -- uploaded, processing, ready_for_extraction, completed
    page_count INTEGER,  -- for PDFs
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
```

**Status Flow:**
- `uploaded` → `processing` (PDF conversion) → `ready_for_extraction` → `completed`
- For images: `uploaded` → `ready_for_extraction` → `completed`

---

### 3.2 Document Pages Table

```sql
CREATE TABLE document_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    image_path TEXT NOT NULL,  -- S3 key or local path to converted image
    status VARCHAR(50) NOT NULL,  -- pending, ready, processed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(document_id, page_number)
);

CREATE INDEX idx_document_pages_document_id ON document_pages(document_id);
```

---

### 3.3 Extraction Jobs Table

```sql
CREATE TABLE extraction_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    extraction_schema JSONB NOT NULL,
    custom_prompt TEXT,
    model_provider VARCHAR(50) NOT NULL,  -- google, openai
    model_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,  -- queued, processing, completed, failed
    celery_task_id VARCHAR(255),  -- Celery task ID for tracking
    error TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_extraction_jobs_document_id ON extraction_jobs(document_id);
CREATE INDEX idx_extraction_jobs_status ON extraction_jobs(status);
CREATE INDEX idx_extraction_jobs_celery_task_id ON extraction_jobs(celery_task_id);
```

---

### 3.4 Extraction Results Table

```sql
CREATE TABLE extraction_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_job_id UUID NOT NULL REFERENCES extraction_jobs(id) ON DELETE CASCADE,
    document_page_id UUID REFERENCES document_pages(id) ON DELETE CASCADE,
    extracted_data JSONB NOT NULL,
    confidence_score FLOAT,
    model_used VARCHAR(100) NOT NULL,
    tokens_used INTEGER,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(extraction_job_id, document_page_id)
);

CREATE INDEX idx_extraction_results_job_id ON extraction_results(extraction_job_id);
CREATE INDEX idx_extraction_results_extracted_data ON extraction_results USING GIN(extracted_data);
```

---

### 3.5 Model Provider Keys Table

```sql
CREATE TABLE model_provider_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(50) NOT NULL,  -- google, openai
    api_key_encrypted TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(provider)
);
```

---

## 4. Celery Job Architecture

### 4.1 Job 1: PDF to Images

**Task:** `tasks.pdf_to_images`

**Input:**
```python
{
    "document_id": "doc_abc123",
    "file_path": "s3://bucket/documents/doc_abc123.pdf"
}
```

**Process:**
1. Download PDF from storage
2. Convert each page to PNG using `pdf2image` or `PyMuPDF`
3. Upload each image to storage
4. Create `document_pages` records
5. Update `documents.status` to `ready_for_extraction`

**Output:**
```python
{
    "document_id": "doc_abc123",
    "page_count": 3,
    "page_ids": ["page_1", "page_2", "page_3"]
}
```

**Error Handling:**
- Retry 3 times with exponential backoff
- On failure: Update `documents.status` to `failed`
- Log error details

---

### 4.2 Job 2: Image to Structured JSON

**Task:** `tasks.image_to_json`

**Input:**
```python
{
    "extraction_job_id": "job_xyz789",
    "document_page_id": "page_1",
    "image_path": "s3://bucket/images/page_1.png",
    "extraction_schema": {...},
    "custom_prompt": "...",
    "model_config": {
        "provider": "google",
        "model": "gemini-pro-vision"
    }
}
```

**Process:**
1. Download image from storage
2. Convert to base64
3. Build VLLM prompt with schema and custom instructions
4. Call VLLM API (Gemini or GPT-4V)
5. Parse JSON response
6. Validate against schema
7. Store in `extraction_results`
8. Update job progress

**DSPy Implementation:**
```python
import dspy
from pydantic import BaseModel, create_model

class DocumentExtractionSignature(dspy.Signature):
    """Extract structured data from document image."""
    image_base64: str = dspy.InputField()
    schema_description: str = dspy.InputField()
    custom_instructions: str = dspy.InputField()
    extracted_json: dict = dspy.OutputField()

class DocumentExtractor(dspy.Module):
    def __init__(self):
        super().__init__()
        self.extract = dspy.ChainOfThought(DocumentExtractionSignature)

    def forward(self, image_base64, schema, custom_prompt):
        # Configure VLLM (Gemini or GPT-4V)
        result = self.extract(
            image_base64=image_base64,
            schema_description=json.dumps(schema),
            custom_instructions=custom_prompt or "Extract data accurately"
        )
        return result.extracted_json
```

**Output:**
```python
{
    "extraction_job_id": "job_xyz789",
    "result_id": "res_123",
    "extracted_data": {...},
    "confidence_score": 0.95,
    "tokens_used": 1250,
    "processing_time_ms": 8500
}
```

**Error Handling:**
- Retry 3 times with exponential backoff
- Fallback to alternate model if primary fails
- On validation error: Store partial results + error details
- Update job status accordingly

---

## 5. Technology Stack

### 5.1 Backend
```python
# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
celery[redis]==5.3.4
redis==5.0.1
pydantic==2.5.0
python-multipart==0.0.6
pdf2image==1.16.3  # or PyMuPDF
Pillow==10.1.0
boto3==1.29.7  # for S3
dspy-ai==2.0.0
openai==1.3.0
google-generativeai==0.3.1
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

### 5.2 Infrastructure
- **Database:** PostgreSQL 16
- **Task Queue:** Redis 7
- **Object Storage:** AWS S3 (or MinIO for local dev)
- **API Framework:** FastAPI
- **Worker:** Celery with Redis broker

---

## 6. Project Structure

```
ai_document_processing/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Settings (Pydantic Settings)
│   ├── database.py             # SQLAlchemy setup
│   ├── models/
│   │   ├── __init__.py
│   │   ├── document.py         # Document ORM model
│   │   ├── extraction_job.py   # ExtractionJob ORM model
│   │   └── extraction_result.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── document.py         # Pydantic schemas for API
│   │   ├── extraction.py
│   │   └── job.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── documents.py        # Document endpoints
│   │   ├── jobs.py             # Job endpoints
│   │   └── health.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── storage.py          # S3/local storage service
│   │   ├── vllm_service.py     # VLLM provider abstraction
│   │   └── schema_validator.py
│   └── tasks/
│       ├── __init__.py
│       ├── celery_app.py       # Celery configuration
│       ├── pdf_processor.py    # PDF → Images job
│       └── extractor.py        # Image → JSON job
├── alembic/
│   ├── versions/
│   └── env.py
├── tests/
│   ├── test_api/
│   ├── test_tasks/
│   └── test_services/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## 7. Implementation Phases

### Week 1-2: Foundation
**Sprint 1: Infrastructure & Database**
- [ ] Set up FastAPI project structure
- [ ] Configure PostgreSQL with SQLAlchemy
- [ ] Create database migrations (Alembic)
- [ ] Set up Celery with Redis
- [ ] Configure S3/MinIO storage
- [ ] Basic health check endpoint

**Deliverable:** API skeleton with database and storage working

---

### Week 2-3: Core Features
**Sprint 2: Document Upload & Processing**
- [ ] Implement document upload endpoint
- [ ] PDF to images conversion job
- [ ] Image storage and page management
- [ ] Document status tracking
- [ ] Basic error handling

**Deliverable:** Documents can be uploaded and PDFs converted to images

---

### Week 3-4: VLLM Integration
**Sprint 3: Extraction Pipeline**
- [ ] VLLM provider service (Gemini + OpenAI)
- [ ] DSPy integration for extraction
- [ ] JSON schema validation
- [ ] Image to JSON extraction job
- [ ] Result storage
- [ ] Parse endpoint implementation

**Deliverable:** End-to-end extraction working

---

### Week 4-5: Polish & Testing
**Sprint 4: Refinement**
- [ ] Job status endpoint
- [ ] Results retrieval endpoint
- [ ] Document listing endpoint
- [ ] Comprehensive error handling
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Unit tests (>80% coverage)
- [ ] Integration tests

**Deliverable:** Production-ready API

---

### Week 5-6: Deployment
**Sprint 5: Production Deployment**
- [ ] Docker containerization
- [ ] Docker Compose for local dev
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Environment configuration
- [ ] Monitoring setup (basic logging)
- [ ] API key management
- [ ] Production deployment

**Deliverable:** Deployed and operational API

---

## 8. Configuration

### 8.1 Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/doc_processing

# Redis
REDIS_URL=redis://localhost:6379/0

# Storage
STORAGE_TYPE=s3  # or 'local'
S3_BUCKET=doc-processing-files
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# VLLM Providers
GOOGLE_API_KEY=...
OPENAI_API_KEY=...

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

---

## 9. API Usage Example

### Complete Flow

```bash
# 1. Upload document
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@invoice.pdf"

# Response: {"document_id": "doc_abc123", ...}

# 2. Start extraction
curl -X POST http://localhost:8000/api/v1/documents/doc_abc123/parse \
  -H "Content-Type: application/json" \
  -d '{
    "extraction_schema": {
      "type": "object",
      "properties": {
        "vendor_name": {"type": "string"},
        "total_amount": {"type": "number"}
      },
      "required": ["vendor_name", "total_amount"]
    },
    "custom_prompt": "Extract invoice data",
    "model_config": {
      "provider": "google",
      "model": "gemini-pro-vision"
    }
  }'

# Response: {"extraction_job_id": "job_xyz789", ...}

# 3. Check status
curl http://localhost:8000/api/v1/jobs/job_xyz789/status

# 4. Get results
curl http://localhost:8000/api/v1/jobs/job_xyz789/result
```

---

## 10. Success Criteria

### MVP Acceptance Criteria
- ✅ Upload PDF and images via API
- ✅ Convert PDF to images automatically
- ✅ Extract structured JSON using VLLM
- ✅ Support custom JSON schemas
- ✅ Support custom extraction prompts
- ✅ Store all states in database
- ✅ Stateless Celery jobs
- ✅ Handle multi-page PDFs
- ✅ Basic error handling and retries
- ✅ API documentation (Swagger)

### Performance Targets
- Document upload: < 3 seconds (10MB PDF)
- PDF conversion: < 2 seconds per page
- VLLM extraction: < 20 seconds per page
- API response time: < 200ms (non-job endpoints)
- Job processing: 3-5 concurrent jobs

---

## 11. Testing Strategy

### 11.1 Unit Tests
- Services (storage, VLLM, validation)
- Database models and queries
- API request/response schemas
- Schema validation logic

### 11.2 Integration Tests
- End-to-end upload → extraction → results
- PDF conversion pipeline
- VLLM API integration
- Database transactions

### 11.3 Manual Testing Checklist
- [ ] Upload single-page PDF
- [ ] Upload multi-page PDF
- [ ] Upload image (PNG, JPG)
- [ ] Invalid file type rejection
- [ ] File size limit enforcement
- [ ] Invalid JSON schema handling
- [ ] VLLM API failure handling
- [ ] Concurrent job processing
- [ ] Job status polling
- [ ] Results retrieval

---

## 12. Next Steps After Phase 1

**Phase 2: Frontend Workflow Builder**
- React + TypeScript frontend
- react-flow workflow canvas
- Visual JSON schema builder
- Workflow templates

**Phase 3: Advanced Features**
- Multi-model comparison
- Cost optimization
- Batch processing
- Webhooks
- User authentication

---

## 13. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| VLLM API reliability | High | Retry logic, multiple provider support |
| PDF conversion failures | Medium | Robust error handling, format validation |
| Large file processing | Medium | File size limits, streaming uploads |
| Database performance | Medium | Proper indexing, connection pooling |
| Cost overruns (VLLM) | Medium | Usage tracking, cost estimation |

---

**Document Status:** Implementation Ready
**Start Date:** TBD
**Target Completion:** 6 weeks from start
