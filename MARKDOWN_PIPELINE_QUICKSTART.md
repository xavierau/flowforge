# Markdown Pipeline - Quick Start Guide

## What is the Markdown Pipeline?

A two-stage extraction pipeline that processes documents more efficiently:

1. **Stage 1**: Image → Markdown (using vision models)
2. **Stage 2**: Markdown → JSON (using cheaper text models)

**Benefits**:
- 30-40% cheaper for complex documents
- Cached markdown can be reused for multiple schemas
- Better at handling tables and structured layouts
- Debuggable intermediate representation

---

## Prerequisites

1. **Database Migration** (run once):
   ```bash
   alembic upgrade head
   ```

2. **API Keys** (set in `.env`):
   ```bash
   # At least one required
   GOOGLE_API_KEY=your_google_api_key   # For gemini_vision converter
   OPENAI_API_KEY=your_openai_api_key   # For gpt4v converter
   ```

3. **Start Services**:
   ```bash
   # Terminal 1: API server
   uvicorn app.main:app --reload

   # Terminal 2: Celery worker
   celery -A app.tasks.celery_app worker --loglevel=info
   ```

---

## Basic Usage

### 1. Upload Document

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@invoice.pdf"
```

Response:
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "uploaded",
  "page_count": 4
}
```

### 2. Create Extraction Job (Markdown Mode)

```bash
curl -X POST http://localhost:8000/api/v1/documents/{document_id}/parse \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "extraction_schema": {
      "type": "object",
      "properties": {
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
      }
    },
    "model_provider_config": {
      "provider": "google",
      "model": "gemini-2.5-flash"
    },
    "processing_mode": "markdown",
    "markdown_converter": "gemini_vision",
    "markdown_format": "table_heavy"
  }'
```

Response:
```json
{
  "extraction_job_id": "660e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "estimated_time_seconds": 50
}
```

### 3. Check Job Status

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "job_id": "660e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "started_at": "2025-11-17T22:30:00Z",
  "completed_at": "2025-11-17T22:30:45Z"
}
```

### 4. Get Extraction Results

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}/result \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "extracted_data": {
    "invoice_number": "INV-2025-001",
    "total_amount": 1250.00,
    "line_items": [
      {
        "description": "Product A",
        "quantity": 5,
        "price": 200.00
      },
      {
        "description": "Product B",
        "quantity": 2,
        "price": 125.00
      }
    ]
  },
  "confidence_score": 1.0,
  "model_used": "google/gemini-2.0-flash-001"
}
```

### 5. View Markdown (for debugging)

```bash
curl http://localhost:8000/api/v1/documents/{document_id}/pages \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
[
  {
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "page_number": 1,
    "markdown_content": "<!-- PAGE 1 -->\n# Invoice INV-2025-001\n\n| Item | Qty | Price |\n|------|-----|-------|\n| Product A | 5 | $200.00 |\n| Product B | 2 | $125.00 |\n\n**Total**: $1,250.00",
    "markdown_provider": "gemini_vision",
    "markdown_generated_at": "2025-11-17T22:30:15Z"
  }
]
```

---

## Configuration Options

### Processing Modes

```python
"processing_mode": "markdown"   # Two-stage: Image→Markdown→JSON
"processing_mode": "batch"      # Direct: All pages vision→JSON (default)
"processing_mode": "per_page"   # Direct: Per-page vision→JSON
```

### Markdown Converters

```python
"markdown_converter": "gemini_vision"  # Google Gemini 2.5 Flash (recommended)
"markdown_converter": "gpt4v"          # OpenAI GPT-4 Vision
```

### Markdown Formats

```python
"markdown_format": "table_heavy"        # Emphasis on tables (recommended for invoices)
"markdown_format": "standard"           # Standard markdown formatting
"markdown_format": "layout_preserved"   # Preserve visual layout
```

---

## Caching Behavior

**First extraction**: Generates markdown and stores in database
```
1. Upload document
2. Parse with markdown mode → Generates markdown → Extracts JSON
   (Takes ~50 seconds for 4 pages)
```

**Second extraction** (same document, different schema): Reuses cached markdown
```
1. Parse with markdown mode → Skips generation → Extracts JSON
   (Takes ~10 seconds, saves 80% time)
```

**How to verify caching**:
```bash
# Check Celery logs
celery -A app.tasks.celery_app worker --loglevel=info

# Look for:
# "Markdown cache hit for document {id} (4 pages). Skipping generation."
```

---

## Troubleshooting

### Error: "Markdown converter not available"

**Cause**: API key not configured

**Solution**: Set API key in `.env`:
```bash
GOOGLE_API_KEY=your_key_here
```

Restart API server and Celery worker.

### Error: "Missing markdown for pages"

**Cause**: Markdown generation failed or was interrupted

**Solution**: Check Celery logs for errors. Re-run extraction to regenerate.

### Error: "Job stuck in processing"

**Cause**: Celery worker crashed or task timeout

**Solution**:
1. Check Celery worker is running
2. Check Celery logs for errors
3. Restart Celery worker if needed

### Markdown Quality Issues

**Problem**: Tables not formatted correctly

**Solution**: Use `"markdown_format": "table_heavy"` and ensure good quality source images.

**Problem**: Missing text content

**Solution**:
1. Check original image quality
2. Try different converter (`gemini_vision` vs `gpt4v`)
3. Review markdown via `/documents/{id}/pages` endpoint

---

## Performance Tips

1. **Use Batch Mode**: Markdown pipeline always uses batch mode internally (more efficient)

2. **Cache Advantage**: Extract multiple times with different schemas without regenerating markdown

3. **Format Selection**:
   - Invoices/receipts: `table_heavy`
   - Contracts/agreements: `standard`
   - Forms: `layout_preserved`

4. **Provider Selection**:
   - Gemini: Faster, cheaper, good table handling
   - GPT-4V: Higher quality, better layout preservation

---

## Code Examples

### Python SDK

```python
import requests

# Upload document
with open("invoice.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": f}
    )
document_id = response.json()["document_id"]

# Create extraction job (markdown mode)
response = requests.post(
    f"http://localhost:8000/api/v1/documents/{document_id}/parse",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    },
    json={
        "extraction_schema": {...},
        "model_provider_config": {
            "provider": "google",
            "model": "gemini-2.5-flash"
        },
        "processing_mode": "markdown",
        "markdown_converter": "gemini_vision",
        "markdown_format": "table_heavy"
    }
)
job_id = response.json()["extraction_job_id"]

# Poll for completion
import time
while True:
    response = requests.get(
        f"http://localhost:8000/api/v1/jobs/{job_id}/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    status = response.json()["status"]
    if status in ["completed", "failed"]:
        break
    time.sleep(5)

# Get results
response = requests.get(
    f"http://localhost:8000/api/v1/jobs/{job_id}/result",
    headers={"Authorization": f"Bearer {token}"}
)
extracted_data = response.json()["extracted_data"]
print(extracted_data)
```

### JavaScript SDK

```javascript
// Upload document
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const uploadResponse = await fetch('http://localhost:8000/api/v1/documents/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});
const { document_id } = await uploadResponse.json();

// Create extraction job (markdown mode)
const jobResponse = await fetch(`http://localhost:8000/api/v1/documents/${document_id}/parse`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    extraction_schema: {...},
    model_provider_config: {
      provider: 'google',
      model: 'gemini-2.5-flash'
    },
    processing_mode: 'markdown',
    markdown_converter: 'gemini_vision',
    markdown_format: 'table_heavy'
  })
});
const { extraction_job_id } = await jobResponse.json();

// Poll for completion
let status = 'queued';
while (status !== 'completed' && status !== 'failed') {
  await new Promise(resolve => setTimeout(resolve, 5000));
  const statusResponse = await fetch(`http://localhost:8000/api/v1/jobs/${extraction_job_id}/status`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  ({ status } = await statusResponse.json());
}

// Get results
const resultResponse = await fetch(`http://localhost:8000/api/v1/jobs/${extraction_job_id}/result`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
const { extracted_data } = await resultResponse.json();
console.log(extracted_data);
```

---

## Monitoring & Debugging

### Check Available Converters

```bash
curl http://localhost:8000/api/v1/converters/available \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "markdown_converters": ["gemini_vision", "gpt4v"],
  "json_extractors": ["gemini", "openai"]
}
```

### View Celery Task Logs

```bash
# In Celery worker terminal
# Look for logs like:
[2025-11-17 22:30:15] INFO Starting batch markdown conversion for 4 pages
[2025-11-17 22:30:30] INFO Batch converted 4 pages to markdown (tokens: 45000+8000)
[2025-11-17 22:30:35] INFO Extracting JSON from 4 pages of markdown (12500 chars)
[2025-11-17 22:30:45] INFO Extraction from markdown completed for job {id}
```

### Check Database State

```sql
-- Check markdown status
SELECT page_number, markdown_provider, markdown_generated_at
FROM document_pages
WHERE document_id = '{document_id}'
ORDER BY page_number;

-- Check job status
SELECT status, started_at, completed_at, error_message
FROM extraction_jobs
WHERE id = '{job_id}';
```

---

## Next Steps

1. **Test with your documents**: Try different document types and formats
2. **Experiment with formats**: Compare `table_heavy` vs `standard` vs `layout_preserved`
3. **Monitor costs**: Track token usage and compare with direct extraction
4. **Optimize schemas**: Refine extraction schemas based on markdown output
5. **Frontend integration**: Use `/documents/{id}/pages` endpoint to show markdown in UI

---

## Support & Resources

- **Implementation Details**: See `MARKDOWN_PIPELINE_IMPLEMENTATION.md`
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Architecture Docs**: See `docs/architecture/` directory
- **Troubleshooting**: See `docs/troubleshooting/` directory

---

## Common Use Cases

### Invoice Processing
```json
{
  "processing_mode": "markdown",
  "markdown_converter": "gemini_vision",
  "markdown_format": "table_heavy"  // Optimized for tables
}
```

### Contract Review
```json
{
  "processing_mode": "markdown",
  "markdown_converter": "gpt4v",      // Better text quality
  "markdown_format": "standard"
}
```

### Form Extraction
```json
{
  "processing_mode": "markdown",
  "markdown_converter": "gemini_vision",
  "markdown_format": "layout_preserved"  // Maintains field positions
}
```

---

**Happy Processing! 🚀**
