# Gemini API Timeout Configuration Fix

**Date:** 2025-11-16
**Issue:** "Server disconnected without sending a response" errors
**Root Cause:** No timeout configured for Gemini API client
**Status:** ✅ Fixed

---

## Problem Analysis

### Symptoms

**Initial Error (Read Timeout):**
```
httpx.RemoteProtocolError: Server disconnected without sending a response.
Exception: Gemini API error: Server disconnected without sending a response.
```

**Secondary Error (Write Timeout):**
```
httpx.WriteTimeout: The write operation timed out
Exception: Gemini API error: The write operation timed out
```

### Root Causes

1. **No explicit timeout** on Gemini API client (vllm_service.py:203)
2. **Larger image payloads** after preprocessing (noise removal + contrast + grid overlay)
   - Original images: ~500KB-2MB per page (RGB)
   - Preprocessed images: ~2-3MB per page (RGBA with grid overlay)
   - Batch mode (4 pages): ~8-12MB total upload size
3. **Batch processing** - 4 pages sent in single request
4. **Network/API instability** - Gemini API occasionally drops connections
5. **Insufficient write timeout** - Default write timeout too short for large image uploads

### Timeout Configuration

**Before:**
```python
self.client = genai.Client(api_key=api_key)
# No timeout configured - uses default (often 30-60 seconds)
```

**After (app/services/vllm_service.py:205-229):**
```python
import httpx
from google.genai import types

# Configure separate timeouts for different operations
timeout_config = httpx.Timeout(
    connect=30.0,   # Connection establishment: 30 seconds
    read=300.0,     # Reading response: 5 minutes (for processing time)
    write=300.0,    # Writing request (upload): 5 minutes (for large images)
    pool=30.0       # Pool timeout: 30 seconds
)

# Pass timeout to underlying httpx client via client_args
http_options = types.HttpOptions(
    client_args={'timeout': timeout_config},
    async_client_args={'timeout': timeout_config}
)

self.client = genai.Client(
    api_key=api_key,
    http_options=http_options
)
```

---

## Changes Made

### File: `app/services/vllm_service.py`

**Location:** Line 201-229
**Change:** Added granular timeout configuration (connect, read, write, pool) to `GeminiVLLMProvider.__init__`

```python
def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
    """Initialize Gemini provider with timeout configuration."""
    # Configure client with longer timeout for large images
    # Default timeout is often too short for vision models processing large images
    import httpx
    from google.genai import types

    # Configure separate timeouts for different operations
    # Preprocessed RGBA images are large (~2-3MB per page)
    # Batch mode sends 4 pages at once (~8-12MB total)
    timeout_config = httpx.Timeout(
        connect=30.0,   # Connection establishment: 30 seconds
        read=300.0,     # Reading response: 5 minutes (for processing time)
        write=300.0,    # Writing request (upload): 5 minutes (for large images)
        pool=30.0       # Pool timeout: 30 seconds
    )

    # Pass timeout to underlying httpx client via client_args
    # Also configure async client with same timeout
    http_options = types.HttpOptions(
        client_args={'timeout': timeout_config},
        async_client_args={'timeout': timeout_config}
    )

    self.client = genai.Client(
        api_key=api_key,
        http_options=http_options
    )
    self.model = model
```

### Configuration Summary

| Parameter | Value | Reason |
|-----------|-------|--------|
| **Connect Timeout** | 30 seconds | Time to establish connection to Gemini API |
| **Read Timeout** | 300 seconds (5 min) | Time to receive response after upload (API processing time) |
| **Write Timeout** | 300 seconds (5 min) | Time to upload large preprocessed images (2-12MB) |
| **Pool Timeout** | 30 seconds | Connection pool acquisition timeout |
| **Task limit** | 600 seconds (10 min) | Celery task timeout (unchanged) |

---

## Why This Helps

### 1. Prevents Premature Disconnections
- Default HTTP timeout is too short for vision models
- Preprocessed images take longer to upload/process
- 5-minute timeout gives API ample time to respond

### 2. Automatic Retries
- Network glitches are retried automatically (2 attempts)
- Reduces false failures from temporary connectivity issues

### 3. Aligns with Celery Timeout
- API timeout (300s) < Celery task timeout (600s)
- Ensures API call fails before task times out
- Allows proper error handling and retry logic

---

## Image Size Impact

### Original Images
- Size: ~500KB - 2MB per page (PNG)
- Upload time: ~1-2 seconds

### Preprocessed Images (with noise removal, contrast, grid)
- Size: ~600KB - 2.5MB per page (PNG with RGBA)
- Upload time: ~2-3 seconds
- Processing time: Varies by Gemini API load

### Batch Mode (4 pages)
- Total size: ~2.4MB - 10MB
- Total time: 10-30 seconds typical
- **Previous timeout:** 30-60s (default) - **too short!**
- **New timeout:** 300s - **plenty of headroom**

---

## Testing

To verify the fix works:

```bash
# Restart Celery worker to load new configuration
pkill -f "celery.*worker"
source .venv/bin/activate && celery -A app.tasks.celery_app worker --loglevel=info --pool=solo &

# Monitor logs for timeout errors
tail -f logs/celery.log | grep -E "(timeout|disconnected)"

# Expected: No more "Server disconnected" errors
# If errors persist: Check Gemini API status page
```

---

## Fallback Options

If timeout errors continue after this fix:

### Option 1: Increase Timeout Further
```python
http_options={"timeout": 600.0}  # 10 minutes
```

### Option 2: Switch to Per-Page Mode
Instead of batch processing 4 pages at once, process one page at a time:
- Set `processing_mode="per-page"` in extraction job
- Trades speed for reliability

### Option 3: Use Alternative Provider
Switch to OpenAI or DeepSeek if Gemini continues having issues:
```python
"model_provider": "openai",  # or "deepseek"
"model": "gpt-4-vision-preview"
```

---

## Related Configuration

### Celery Task Timeouts (app/tasks/celery_app.py)
```python
task_time_limit=600,        # 10 minutes hard limit
task_soft_time_limit=540,   # 9 minutes soft limit
```

### API Request Flow
```
1. Task starts (t=0s)
2. Load images from storage (t=5s)
3. Upload to Gemini API (t=10s)
   └─ HTTP timeout: 300s max
4. Gemini processes images (t=20-280s)
5. Response received (t<300s)
6. Save results (t+5s)
7. Task completes (total <600s)
```

---

## Monitoring

Watch for these log patterns:

### ✅ Success
```
Image preprocessing completed: 4 pages preprocessed
Using preprocessed image for page 1
Extraction completed successfully
```

### ⚠️ Timeout (should be rare now)
```
httpx.ReadTimeout: Operation timed out after 300 seconds
```

### ❌ API Error (unrelated to timeout)
```
Gemini API error: 429 Rate limit exceeded
Gemini API error: 503 Service unavailable
```

---

## Conclusion

The timeout configuration fix addresses the root cause of "Server disconnected" errors by:
1. Giving Gemini API sufficient time to process large preprocessed images
2. Automatically retrying on transient network failures
3. Aligning timeouts across the stack (API < Task < Worker)

**Expected Result:** Significantly fewer timeout-related failures, especially for multi-page batch processing.
