# VLLM Integration Architecture

## Overview

The system integrates multiple Vision Language Model (VLLM) providers through a unified abstraction layer, enabling runtime provider selection, fallback strategies, and provider-agnostic error handling.

**Default Model:** `gemini-2.5-flash` (configured in `app/services/vllm_service.py:115, 194`)

## Provider Abstraction

### Interface Design

```python
# app/services/vllm_service.py

class VLLMProvider(ABC):
    """Abstract base class for all VLLM providers."""

    @abstractmethod
    async def extract_from_image(
        self,
        image_bytes: bytes,
        extraction_schema: Dict[str, Any],
        custom_prompt: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int, int]:
        """
        Extract structured data from image using VLLM.

        Args:
            image_bytes: Image data in bytes
            extraction_schema: JSON Schema defining expected output
            custom_prompt: Optional custom prompt for extraction

        Returns:
            Tuple of (extracted_data, tokens_used, processing_time_ms)
        """
        pass
```

### Concrete Implementations

#### 1. Google Gemini Provider

```python
class GeminiVLLMProvider(VLLMProvider):
    """Google Gemini Vision implementation."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        genai.configure(api_key=api_key)

    async def extract_from_image(
        self,
        image_bytes: bytes,
        extraction_schema: Dict[str, Any],
        custom_prompt: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int, int]:
        start_time = time.time()

        # Prepare image
        image = Image.open(io.BytesIO(image_bytes))

        # Build prompt with schema
        prompt = self._build_prompt(extraction_schema, custom_prompt)

        # Call Gemini API
        model = genai.GenerativeModel(self.model)
        response = model.generate_content([prompt, image])

        # Parse JSON response
        extracted_data = json.loads(response.text)

        # Calculate metrics
        tokens_used = response.usage_metadata.total_token_count
        processing_time = int((time.time() - start_time) * 1000)

        return extracted_data, tokens_used, processing_time

    def _build_prompt(
        self,
        schema: Dict[str, Any],
        custom_prompt: Optional[str]
    ) -> str:
        """Build prompt from schema and custom instructions."""
        schema_str = json.dumps(schema, indent=2)

        prompt = f"""
Extract structured data from this document image.

{custom_prompt or "Extract all relevant information accurately."}

Return ONLY valid JSON matching this schema:
{schema_str}

Ensure all required fields are present and types match the schema.
"""
        return prompt
```

**Location:** `app/services/vllm_service.py:70-140`

#### 2. OpenAI GPT-4 Vision Provider

```python
class OpenAIVLLMProvider(VLLMProvider):
    """OpenAI GPT-4 Vision implementation."""

    def __init__(self, api_key: str, model: str = "gpt-4-vision-preview"):
        self.api_key = api_key
        self.model = model
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def extract_from_image(
        self,
        image_bytes: bytes,
        extraction_schema: Dict[str, Any],
        custom_prompt: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int, int]:
        start_time = time.time()

        # Encode image to base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Build messages
        prompt = self._build_prompt(extraction_schema, custom_prompt)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]

        # Call OpenAI API
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"}
        )

        # Parse response
        extracted_data = json.loads(response.choices[0].message.content)

        # Calculate metrics
        tokens_used = response.usage.total_tokens
        processing_time = int((time.time() - start_time) * 1000)

        return extracted_data, tokens_used, processing_time
```

**Location:** `app/services/vllm_service.py:145-210`

#### 3. DeepSeek Vision Provider

```python
class DeepSeekVLLMProvider(VLLMProvider):
    """DeepSeek VL implementation."""

    def __init__(self, api_key: str, model: str = "deepseek-vl-7b-chat"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.deepseek.com/v1"

    async def extract_from_image(
        self,
        image_bytes: bytes,
        extraction_schema: Dict[str, Any],
        custom_prompt: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int, int]:
        # Similar implementation pattern
        # ... (details in source code)
```

**Location:** `app/services/vllm_service.py:215-280`

## VLLMService: Multi-Provider Orchestration

```python
class VLLMService:
    """High-level service managing multiple VLLM providers."""

    def __init__(self):
        self.providers: Dict[str, VLLMProvider] = {}
        self.validator = SchemaValidator()

        # Initialize available providers based on API keys
        if settings.google_api_key:
            self.providers["google"] = GeminiVLLMProvider(
                api_key=settings.google_api_key,
                model="gemini-2.5-flash"
            )

        if settings.openai_api_key:
            self.providers["openai"] = OpenAIVLLMProvider(
                api_key=settings.openai_api_key,
                model="gpt-4-vision-preview"
            )

        if settings.deepseek_api_key:
            self.providers["deepseek"] = DeepSeekVLLMProvider(
                api_key=settings.deepseek_api_key,
                model="deepseek-vl-7b-chat"
            )

    def get_provider(self, provider_name: str) -> VLLMProvider:
        """Get provider by name, raise error if not configured."""
        if provider_name not in self.providers:
            raise ValueError(
                f"Provider '{provider_name}' not configured. "
                f"Available: {list(self.providers.keys())}"
            )
        return self.providers[provider_name]

    async def extract_from_image(
        self,
        image_bytes: bytes,
        extraction_schema: Dict[str, Any],
        provider: str = "google",
        model: Optional[str] = None,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from image using specified provider.

        Returns dict with:
        - extracted_data: The extracted JSON
        - is_valid: Whether data matches schema
        - validation_errors: List of validation errors (if any)
        - tokens_used: Token count
        - processing_time_ms: Processing time
        - provider: Provider used
        - model: Model used
        """

        # Get provider
        vllm_provider = self.get_provider(provider)

        # Override model if specified
        if model:
            vllm_provider.model = model

        # Extract data
        extracted_data, tokens, time_ms = await vllm_provider.extract_from_image(
            image_bytes=image_bytes,
            extraction_schema=extraction_schema,
            custom_prompt=custom_prompt
        )

        # Validate against schema
        is_valid, errors = self.validator.validate(
            data=extracted_data,
            schema=extraction_schema
        )

        return {
            "extracted_data": extracted_data,
            "is_valid": is_valid,
            "validation_errors": errors,
            "tokens_used": tokens,
            "processing_time_ms": time_ms,
            "provider": provider,
            "model": vllm_provider.model
        }
```

**Location:** `app/services/vllm_service.py:285-380`

## Usage in Tasks

### Extraction Task Implementation

```python
# app/tasks/extraction_tasks.py

@celery_app.task(bind=True, max_retries=3)
def extract_page_task(
    self: Task,
    extraction_job_id: str,
    page_id: str
):
    """Extract data from single document page."""
    db = SessionLocal()
    try:
        # Get job and page from database
        job = db.query(ExtractionJob).filter(...).first()
        page = db.query(DocumentPage).filter(...).first()

        # Load image from storage
        storage = get_storage_service()
        image_bytes = await storage.get_file(page.image_path)

        # Get VLLM service
        vllm_service = get_vllm_service()

        # Extract data using configured provider
        result = await vllm_service.extract_from_image(
            image_bytes=image_bytes,
            extraction_schema=job.extraction_schema,
            provider=job.model_provider,
            model=job.model_name,
            custom_prompt=job.custom_prompt
        )

        # Store result
        extraction_result = ExtractionResult(
            extraction_job_id=job.id,
            document_page_id=page.id,
            extracted_data=result["extracted_data"],
            is_valid=result["is_valid"],
            validation_errors=result["validation_errors"],
            tokens_used=result["tokens_used"],
            processing_time_ms=result["processing_time_ms"]
        )
        db.add(extraction_result)
        db.commit()

    except ProviderError as e:
        # Retry on provider errors
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    finally:
        db.close()
```

**Location:** `app/tasks/extraction_tasks.py:120-185`

## Invoice Extraction Example

### Complete API Flow

```bash
# 1. Upload invoice PDF
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@invoice_1.pdf"

# Response:
{
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "invoice_1.pdf",
  "status": "uploaded"
}

# 2. Submit extraction job with invoice schema
curl -X POST http://localhost:8000/api/v1/documents/123e4567-e89b-12d3-a456-426614174000/parse \
  -H "Content-Type: application/json" \
  -d '{
    "extraction_schema": {
      "type": "object",
      "properties": {
        "invoice_number": {"type": "string"},
        "invoice_date": {"type": "string", "format": "date"},
        "vendor": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "address": {"type": "string"}
          }
        },
        "line_items": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "description": {"type": "string"},
              "quantity": {"type": "number"},
              "unit_price": {"type": "number"},
              "amount": {"type": "number"}
            }
          }
        },
        "total_amount": {"type": "number"},
        "currency": {"type": "string"}
      }
    },
    "custom_prompt": "Extract invoice details including all line items",
    "model_provider_config": {
      "provider": "google",
      "model": "gemini-2.5-flash"
    }
  }'

# Response:
{
  "extraction_job_id": "456e7890-e89b-12d3-a456-426614174111",
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "queued"
}

# 3. Poll job status
curl http://localhost:8000/api/v1/jobs/456e7890-e89b-12d3-a456-426614174111/status

# Response (processing):
{
  "job_id": "456e7890-e89b-12d3-a456-426614174111",
  "status": "processing",
  "progress": {
    "total_pages": 1,
    "completed_pages": 0
  }
}

# 4. Get results when completed
curl http://localhost:8000/api/v1/jobs/456e7890-e89b-12d3-a456-426614174111/result

# Response:
{
  "job_id": "456e7890-e89b-12d3-a456-426614174111",
  "status": "completed",
  "extracted_data": {
    "invoice_number": "INV-2024-001",
    "invoice_date": "2024-03-15",
    "vendor": {
      "name": "ACME Corporation",
      "address": "123 Business St, Tech City"
    },
    "line_items": [
      {
        "description": "Professional Services",
        "quantity": 40,
        "unit_price": 150.00,
        "amount": 6000.00
      }
    ],
    "total_amount": 9240.00,
    "currency": "USD"
  },
  "metadata": {
    "provider": "google",
    "model": "gemini-2.5-flash",
    "tokens_used": 2500,
    "processing_time_ms": 8500
  }
}
```

**Invoice Schema:** See `invoice_schema.json` for complete schema
**Test Documentation:** See `TEST_RESULTS.md` for expected responses

## Adding a New Provider

### Step 1: Implement Provider Class

```python
# app/services/vllm_service.py

class NewProviderVLLMProvider(VLLMProvider):
    """New VLLM provider implementation."""

    def __init__(self, api_key: str, model: str = "default-model"):
        self.api_key = api_key
        self.model = model
        # Initialize client/SDK

    async def extract_from_image(
        self,
        image_bytes: bytes,
        extraction_schema: Dict[str, Any],
        custom_prompt: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int, int]:
        # 1. Convert image to provider format
        # 2. Build prompt with schema
        # 3. Call provider API
        # 4. Parse response
        # 5. Return (data, tokens, time)
        pass
```

### Step 2: Add API Key to Settings

```python
# app/core/config.py

class Settings(BaseSettings):
    # ... existing settings ...

    # New provider API key
    newprovider_api_key: str = Field(
        default="",
        description="API key for NewProvider"
    )
```

### Step 3: Register in VLLMService

```python
# app/services/vllm_service.py

class VLLMService:
    def __init__(self):
        self.providers: Dict[str, VLLMProvider] = {}

        # ... existing providers ...

        # Register new provider
        if settings.newprovider_api_key:
            self.providers["newprovider"] = NewProviderVLLMProvider(
                api_key=settings.newprovider_api_key,
                model="default-model"
            )
```

### Step 4: Update API Validation

```python
# app/api/documents.py

@router.post("/documents/{document_id}/parse")
async def parse_document(...):
    # Add to valid providers
    valid_providers = ["google", "openai", "deepseek", "newprovider"]

    if request.model_provider_config.provider not in valid_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {valid_providers}"
        )
```

### Step 5: Add Tests

```python
# tests/unit/test_vllm_service.py

@pytest.mark.asyncio
async def test_newprovider_extraction():
    """Test new provider extraction."""
    provider = NewProviderVLLMProvider(api_key="test_key")

    schema = {"type": "object", "properties": {"name": {"type": "string"}}}
    image_bytes = load_test_image()

    data, tokens, time_ms = await provider.extract_from_image(
        image_bytes=image_bytes,
        extraction_schema=schema
    )

    assert isinstance(data, dict)
    assert "name" in data
    assert tokens > 0
    assert time_ms > 0
```

## Error Handling

### Provider-Specific Errors

```python
class ProviderError(Exception):
    """Base class for provider errors."""
    pass

class RateLimitError(ProviderError):
    """API rate limit exceeded."""
    pass

class AuthenticationError(ProviderError):
    """Invalid API key."""
    pass

class TimeoutError(ProviderError):
    """Request timeout."""
    pass
```

### Retry Strategy

```python
@celery_app.task(bind=True, max_retries=3)
def extract_page_task(self: Task, job_id: str, page_id: str):
    try:
        # Attempt extraction
        result = await vllm_service.extract(...)

    except RateLimitError as e:
        # Longer backoff for rate limits
        countdown = 300  # 5 minutes
        raise self.retry(exc=e, countdown=countdown)

    except TimeoutError as e:
        # Exponential backoff for timeouts
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=e, countdown=countdown)

    except AuthenticationError as e:
        # Don't retry authentication errors
        logger.error(f"Authentication failed: {e}")
        raise
```

### Fallback Strategy

```python
async def extract_with_fallback(
    image_bytes: bytes,
    schema: Dict[str, Any],
    providers: List[str] = ["google", "openai", "deepseek"]
) -> Dict[str, Any]:
    """Try multiple providers in order until success."""

    for provider in providers:
        try:
            result = await vllm_service.extract_from_image(
                image_bytes=image_bytes,
                extraction_schema=schema,
                provider=provider
            )
            return result

        except ProviderError as e:
            logger.warning(f"{provider} failed: {e}, trying next provider")
            continue

    raise Exception("All providers failed")
```

## Cost Tracking

### Token Usage Monitoring

```sql
-- Total tokens by provider
SELECT
    model_provider,
    SUM(tokens_used) as total_tokens,
    COUNT(*) as extractions,
    AVG(tokens_used) as avg_tokens
FROM extraction_results
GROUP BY model_provider;

-- Cost estimation (approximate)
SELECT
    model_provider,
    SUM(tokens_used) as total_tokens,
    CASE model_provider
        WHEN 'google' THEN SUM(tokens_used) * 0.00025 / 1000  -- Gemini pricing
        WHEN 'openai' THEN SUM(tokens_used) * 0.01 / 1000     -- GPT-4V pricing
        ELSE 0
    END as estimated_cost_usd
FROM extraction_results
GROUP BY model_provider;
```

## References

- Provider implementations: `app/services/vllm_service.py`
- Extraction tasks: `app/tasks/extraction_tasks.py`
- Invoice schema: `invoice_schema.json`
- Test results: `TEST_RESULTS.md`
- API documentation: `http://localhost:8000/docs`
