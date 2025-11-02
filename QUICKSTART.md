# Quick Start Guide - AI Document Processing

Get the MVP running in **5 minutes** using local development setup.

---

## Prerequisites

- Python 3.13+
- PostgreSQL 16+
- Redis 7+
- **OR** Docker + Docker Compose (easier)

---

## Option 1: Docker (Recommended for Quick Start)

### Step 1: Add API Keys

Edit `.env` file and add your VLLM API keys:

```bash
# At minimum, add ONE of these:
GOOGLE_API_KEY=your_actual_google_api_key_here
# OR
OPENAI_API_KEY=your_actual_openai_api_key_here
```

### Step 2: Start Everything

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f api

# Wait for "Application startup complete"
```

### Step 3: Run Migrations

```bash
# Apply the initial migration (already created)
docker-compose exec api alembic upgrade head
```

### Step 4: Test the API

Visit: http://localhost:8000/docs

Try the health check:
```bash
curl http://localhost:8000/health
```

**You're ready!** Skip to "Testing the Full Flow" section below.

---

## Option 2: Local Development

### Step 1: Install Dependencies

```bash
cd /Users/xavierau/Code/python/ai_document_processing

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install
pip install -e ".[dev]"
```

### Step 2: Start PostgreSQL and Redis

```bash
# Option A: Using Docker
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=doc_processing postgres:16
docker run -d -p 6379:6379 redis:7

# Option B: Using Homebrew (macOS)
brew install postgresql@16 redis
brew services start postgresql@16
brew services start redis

# Option C: Using system package manager (Linux)
# ...install and start services
```

### Step 3: Configure Environment

The `.env` file is already created. **Just add your API keys:**

```bash
# Edit .env
vim .env

# Add ONE of these:
GOOGLE_API_KEY=your_actual_google_api_key_here
# OR
OPENAI_API_KEY=your_actual_openai_api_key_here
```

### Step 4: Create Database

```bash
# Create database
createdb doc_processing

# OR if using docker postgres:
docker exec -it <postgres_container> psql -U postgres -c "CREATE DATABASE doc_processing;"
```

### Step 5: Run Migrations

```bash
# Apply the initial migration (already created)
alembic upgrade head
```

### Step 6: Start Services

```bash
# Terminal 1: Start API
uvicorn app.main:app --reload

# Terminal 2: Start Celery Worker
celery -A app.tasks.celery_app worker --loglevel=info

# Terminal 3: (Optional) Celery Flower for monitoring
celery -A app.tasks.celery_app flower
```

---

## Testing the Full Flow

### 1. Check Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "healthy",
  "service": "ai-document-processing",
  "version": "0.1.0"
}
```

### 2. Upload a Document

```bash
# Upload a PDF
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@/path/to/your/invoice.pdf"

# OR upload an image
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@/path/to/your/receipt.jpg"
```

Response:
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "invoice.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 245678,
  "status": "uploaded",
  "page_count": null,
  "created_at": "2025-11-02T10:30:00Z"
}
```

**Save the `document_id`** for next steps!

### 3. Parse the Document

```bash
curl -X POST http://localhost:8000/api/v1/documents/<DOCUMENT_ID>/parse \
  -H "Content-Type: application/json" \
  -d '{
    "extraction_schema": {
      "type": "object",
      "properties": {
        "vendor_name": {"type": "string"},
        "total_amount": {"type": "number"},
        "invoice_number": {"type": "string"}
      },
      "required": ["vendor_name", "total_amount"]
    },
    "custom_prompt": "Extract vendor name, total amount, and invoice number from this invoice.",
    "model_config": {
      "provider": "google",
      "model": "gemini-2.5-flash"
    }
  }'
```

Response:
```json
{
  "extraction_job_id": "660e8400-e29b-41d4-a716-446655440000",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "estimated_time_seconds": 15,
  "created_at": "2025-11-02T10:31:00Z"
}
```

**Save the `extraction_job_id`**!

### 4. Check Job Status

```bash
curl http://localhost:8000/api/v1/jobs/<JOB_ID>/status
```

Response (processing):
```json
{
  "job_id": "660e8400-e29b-41d4-a716-446655440000",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": {
    "total_pages": 1,
    "completed_pages": 0
  },
  "started_at": "2025-11-02T10:31:05Z",
  "updated_at": "2025-11-02T10:31:12Z",
  "error": null
}
```

### 5. Get Results

```bash
# Wait until status is "completed", then:
curl http://localhost:8000/api/v1/jobs/<JOB_ID>/result
```

Response:
```json
{
  "job_id": "660e8400-e29b-41d4-a716-446655440000",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "extracted_data": {
    "vendor_name": "ACME Corp",
    "total_amount": 1250.00,
    "invoice_number": "INV-2024-001"
  },
  "metadata": {
    "model_used": "google/gemini-2.5-flash",
    "tokens_used": 1250,
    "processing_time_ms": 8500,
    "confidence_score": 0.95
  },
  "completed_at": "2025-11-02T10:31:20Z"
}
```

### 6. List Documents

```bash
curl http://localhost:8000/api/v1/documents
```

---

## Interactive API Documentation

Visit **http://localhost:8000/docs** for interactive Swagger UI:

- Try all endpoints
- See request/response schemas
- Test with sample data

---

## Storage Location

Files are stored locally in `./storage/` directory:

```
storage/
├── documents/      # Uploaded PDFs and images
└── pages/          # Converted PDF pages (PNG)
```

---

## Troubleshooting

### API won't start

```bash
# Check if port 8000 is already in use
lsof -i :8000

# Check database connection
psql -h localhost -U postgres -d doc_processing -c "SELECT 1;"
```

### Celery worker not processing

```bash
# Check Redis connection
redis-cli ping

# Check Celery logs
docker-compose logs worker
# OR
# Check Terminal 2 logs
```

### "Provider not configured" error

Make sure you've added either `GOOGLE_API_KEY` or `OPENAI_API_KEY` to `.env`

### PDF conversion fails

Make sure `poppler-utils` is installed:
```bash
# macOS
brew install poppler

# Ubuntu
sudo apt-get install poppler-utils
```

---

## What's Next?

- Add more sophisticated JSON schemas
- Try multi-page PDFs
- Experiment with different VLLM models
- Add custom validation rules
- Integrate with your applications

---

## Development Tips

### Watch Logs

```bash
# Docker
docker-compose logs -f

# Local - API logs
tail -f logs/api.log

# Local - Celery logs
# Just watch Terminal 2
```

### Reset Everything

```bash
# Docker
docker-compose down -v
docker-compose up -d

# Local
dropdb doc_processing
createdb doc_processing
alembic upgrade head
```

### Run Tests

```bash
pytest
```

---

**🎉 Congratulations!** You now have a fully functional AI document processing API!
