"""LlamaExtract VLLM provider for document data extraction.

LlamaExtract is an async job-based extraction API from LlamaCloud.
It uses agents to define extraction schemas and processes documents
to extract structured data.

API Flow:
1. Create extraction agent (with schema) - cached by schema hash
2. Upload file to LlamaCloud
3. Create extraction job (agent_id + file_id)
4. Poll job status until complete
5. Get extraction result

API Documentation:
- https://developers.llamaindex.ai/python/cloud/llamaextract/getting_started/
"""

import asyncio
import base64
import hashlib
import io
import json
import logging
import time
from typing import Any, Optional

import httpx

from app.config import settings
from app.models.enums import LlamaExtractMode, LlamaExtractTarget
from app.services.vllm_service import VLLMProvider

logger = logging.getLogger(__name__)

# LlamaCloud API base URL
LLAMACLOUD_API_BASE = "https://api.cloud.llamaindex.ai/api/v1"

# Default polling configuration
DEFAULT_POLL_INTERVAL_SECONDS = 2.0
DEFAULT_MAX_POLL_ATTEMPTS = 300  # 10 minutes at 2s interval
DEFAULT_TIMEOUT_SECONDS = 60.0

# Cache TTL (48 hours in seconds)
CACHE_TTL_SECONDS = 48 * 60 * 60


class LlamaExtractError(Exception):
    """Base exception for LlamaExtract errors."""

    pass


class LlamaExtractAgentError(LlamaExtractError):
    """Error creating or managing extraction agents."""

    pass


class LlamaExtractJobError(LlamaExtractError):
    """Error with extraction job execution."""

    pass


class LlamaExtractTimeoutError(LlamaExtractError):
    """Job polling timeout exceeded."""

    pass


def _compute_schema_hash(schema: dict[str, Any]) -> str:
    """Compute deterministic hash for a JSON schema.

    Args:
        schema: JSON schema dictionary

    Returns:
        SHA256 hash of the canonicalized schema
    """
    canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _map_mode_to_extraction_mode(mode: LlamaExtractMode) -> str:
    """Map our simplified mode to LlamaExtract API extraction mode.

    Args:
        mode: Our LlamaExtractMode enum

    Returns:
        LlamaExtract API extraction mode string
    """
    if mode == LlamaExtractMode.PREMIUM:
        return "PREMIUM"
    return "BALANCED"


def _map_target_to_extraction_target(target: LlamaExtractTarget) -> str:
    """Map our target enum to LlamaExtract API target.

    Args:
        target: Our LlamaExtractTarget enum

    Returns:
        LlamaExtract API extraction target string
    """
    if target == LlamaExtractTarget.PER_PAGE:
        return "PER_PAGE"
    return "PER_DOC"


def _convert_schema_for_llamaextract(schema: dict[str, Any]) -> dict[str, Any]:
    """Convert JSON Schema to LlamaExtract-compatible format.

    LlamaExtract expects a specific schema format. This function
    ensures compatibility by:
    - Removing unsupported $-prefixed metadata fields
    - Ensuring required fields are properly formatted

    Args:
        schema: Standard JSON Schema

    Returns:
        LlamaExtract-compatible schema
    """
    if not isinstance(schema, dict):
        return schema

    cleaned = {}
    for key, value in schema.items():
        # Skip $-prefixed metadata (e.g., $schema, $id)
        if key.startswith("$"):
            continue
        if isinstance(value, dict):
            cleaned[key] = _convert_schema_for_llamaextract(value)
        elif isinstance(value, list):
            cleaned[key] = [
                _convert_schema_for_llamaextract(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            cleaned[key] = value

    return cleaned


class LlamaExtractVLLMProvider(VLLMProvider):
    """LlamaExtract provider for document data extraction.

    Uses LlamaCloud's LlamaExtract API for high-quality document
    extraction with schema-based structured output.

    Features:
    - Agent caching by schema hash (48-hour cache)
    - Two extraction modes: STANDARD (BALANCED) and PREMIUM
    - Per-document or per-page extraction targets
    - Async job processing with polling

    Attributes:
        api_key: LlamaCloud API key
        mode: Extraction quality mode (STANDARD or PREMIUM)
        target: Extraction scope (PER_DOC or PER_PAGE)
        poll_interval: Seconds between status polls
        max_poll_attempts: Maximum polling attempts
    """

    def __init__(
        self,
        api_key: str,
        mode: LlamaExtractMode = LlamaExtractMode.STANDARD,
        target: LlamaExtractTarget = LlamaExtractTarget.PER_DOC,
        poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
        max_poll_attempts: int = DEFAULT_MAX_POLL_ATTEMPTS,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        """Initialize LlamaExtract provider.

        Args:
            api_key: LlamaCloud API key for authentication
            mode: Extraction quality mode
            target: Extraction target scope
            poll_interval: Seconds between job status polls
            max_poll_attempts: Max polls before timeout
            timeout: HTTP request timeout in seconds
        """
        if not api_key:
            raise ValueError("LlamaCloud API key is required")

        self._api_key = api_key
        self._mode = mode
        self._target = target
        self._poll_interval = poll_interval
        self._max_poll_attempts = max_poll_attempts
        self._timeout = timeout

        # Agent cache: schema_hash -> agent_id
        self._agent_cache: dict[str, str] = {}

    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "llamaextract"

    @property
    def model_name(self) -> str:
        """Get the model/mode name."""
        return f"llamaextract-{self._mode.value}"

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests.

        Returns:
            Headers dictionary with authorization
        """
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _create_agent(
        self,
        schema: dict[str, Any],
        schema_hash: str,
        client: httpx.AsyncClient,
    ) -> str:
        """Create an extraction agent for the given schema.

        Args:
            schema: JSON schema for extraction
            schema_hash: Hash of the schema for naming
            client: HTTP client instance

        Returns:
            Agent ID

        Raises:
            LlamaExtractAgentError: If agent creation fails
        """
        converted_schema = _convert_schema_for_llamaextract(schema)
        agent_name = f"agent_{schema_hash}"

        payload = {
            "name": agent_name,
            "data_schema": converted_schema,
            "extraction_mode": _map_mode_to_extraction_mode(self._mode),
            "extraction_target": _map_target_to_extraction_target(self._target),
        }

        logger.info(f"Creating LlamaExtract agent: {agent_name}")
        logger.debug(f"Agent payload: {json.dumps(payload, indent=2)}")

        try:
            response = await client.post(
                f"{LLAMACLOUD_API_BASE}/extraction/extraction-agents",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            agent_id = data.get("id")

            if not agent_id:
                raise LlamaExtractAgentError(
                    f"No agent ID in response: {data}"
                )

            logger.info(f"Created agent {agent_id} for schema {schema_hash}")
            return agent_id

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            logger.error(f"Agent creation failed: {error_detail}")
            raise LlamaExtractAgentError(
                f"Failed to create agent: {e.response.status_code} - {error_detail}"
            )
        except httpx.HTTPError as e:
            logger.error(f"HTTP error creating agent: {e}")
            raise LlamaExtractAgentError(f"HTTP error: {e}")

    async def _get_or_create_agent(
        self,
        schema: dict[str, Any],
        client: httpx.AsyncClient,
    ) -> str:
        """Get cached agent or create new one.

        Agents are cached by schema hash to avoid recreating
        for the same schema structure.

        Args:
            schema: JSON schema for extraction
            client: HTTP client instance

        Returns:
            Agent ID
        """
        schema_hash = _compute_schema_hash(schema)

        if schema_hash in self._agent_cache:
            logger.debug(f"Using cached agent for schema {schema_hash}")
            return self._agent_cache[schema_hash]

        agent_id = await self._create_agent(schema, schema_hash, client)
        self._agent_cache[schema_hash] = agent_id
        return agent_id

    async def _upload_file(
        self,
        file_content: bytes,
        filename: str,
        client: httpx.AsyncClient,
    ) -> str:
        """Upload file to LlamaCloud.

        Args:
            file_content: Raw file bytes
            filename: Name for the uploaded file
            client: HTTP client instance

        Returns:
            File ID

        Raises:
            LlamaExtractError: If upload fails
        """
        logger.info(f"Uploading file: {filename} ({len(file_content)} bytes)")

        try:
            # Use multipart form for file upload
            files = {"file": (filename, file_content, "application/octet-stream")}
            headers = {"Authorization": f"Bearer {self._api_key}"}

            response = await client.post(
                f"{LLAMACLOUD_API_BASE}/files",
                headers=headers,
                files=files,
            )
            response.raise_for_status()
            data = response.json()
            file_id = data.get("id")

            if not file_id:
                raise LlamaExtractError(f"No file ID in response: {data}")

            logger.info(f"Uploaded file {file_id}")
            return file_id

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            logger.error(f"File upload failed: {error_detail}")
            raise LlamaExtractError(
                f"Failed to upload file: {e.response.status_code} - {error_detail}"
            )
        except httpx.HTTPError as e:
            logger.error(f"HTTP error uploading file: {e}")
            raise LlamaExtractError(f"HTTP error: {e}")

    async def _create_job(
        self,
        agent_id: str,
        file_id: str,
        client: httpx.AsyncClient,
        use_cache: bool = True,
    ) -> str:
        """Create an extraction job.

        Args:
            agent_id: Extraction agent ID
            file_id: Uploaded file ID
            client: HTTP client instance
            use_cache: Whether to use 48-hour cache

        Returns:
            Job ID

        Raises:
            LlamaExtractJobError: If job creation fails
        """
        payload = {
            "extraction_agent_id": agent_id,
            "file_id": file_id,
            "invalidate_cache": not use_cache,
        }

        logger.info(f"Creating extraction job: agent={agent_id}, file={file_id}")

        try:
            response = await client.post(
                f"{LLAMACLOUD_API_BASE}/extraction/jobs",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            job_id = data.get("id")

            if not job_id:
                raise LlamaExtractJobError(f"No job ID in response: {data}")

            logger.info(f"Created job {job_id}")
            return job_id

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            logger.error(f"Job creation failed: {error_detail}")
            raise LlamaExtractJobError(
                f"Failed to create job: {e.response.status_code} - {error_detail}"
            )
        except httpx.HTTPError as e:
            logger.error(f"HTTP error creating job: {e}")
            raise LlamaExtractJobError(f"HTTP error: {e}")

    async def _poll_job_status(
        self,
        job_id: str,
        client: httpx.AsyncClient,
    ) -> dict[str, Any]:
        """Poll job status until completion or failure.

        Args:
            job_id: Extraction job ID
            client: HTTP client instance

        Returns:
            Final job status data

        Raises:
            LlamaExtractJobError: If job fails
            LlamaExtractTimeoutError: If polling exceeds max attempts
        """
        attempt = 0

        while attempt < self._max_poll_attempts:
            try:
                response = await client.get(
                    f"{LLAMACLOUD_API_BASE}/extraction/jobs/{job_id}",
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                data = response.json()

                status = data.get("status", "").upper()
                logger.debug(f"Job {job_id} status: {status} (attempt {attempt + 1})")

                if status == "COMPLETED":
                    logger.info(f"Job {job_id} completed")
                    return data

                if status == "FAILED":
                    error = data.get("error", "Unknown error")
                    logger.error(f"Job {job_id} failed: {error}")
                    raise LlamaExtractJobError(f"Extraction job failed: {error}")

                if status in ("CANCELLED", "CANCELED"):
                    raise LlamaExtractJobError("Extraction job was cancelled")

                # Still processing, wait before next poll
                await asyncio.sleep(self._poll_interval)
                attempt += 1

            except httpx.HTTPStatusError as e:
                error_detail = e.response.text if e.response else str(e)
                logger.error(f"Status poll failed: {error_detail}")
                raise LlamaExtractJobError(f"Failed to get job status: {error_detail}")
            except httpx.HTTPError as e:
                logger.error(f"HTTP error polling status: {e}")
                raise LlamaExtractJobError(f"HTTP error: {e}")

        raise LlamaExtractTimeoutError(
            f"Job {job_id} did not complete within {self._max_poll_attempts} attempts"
        )

    async def _get_job_result(
        self,
        job_id: str,
        client: httpx.AsyncClient,
    ) -> dict[str, Any]:
        """Get extraction result for completed job.

        Args:
            job_id: Extraction job ID
            client: HTTP client instance

        Returns:
            Extracted data from the job

        Raises:
            LlamaExtractJobError: If result retrieval fails
        """
        logger.info(f"Getting result for job {job_id}")

        try:
            response = await client.get(
                f"{LLAMACLOUD_API_BASE}/extraction/jobs/{job_id}/result",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()

            logger.debug(f"Job result: {json.dumps(data, indent=2)[:500]}...")
            return data

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            logger.error(f"Failed to get job result: {error_detail}")
            raise LlamaExtractJobError(
                f"Failed to get result: {e.response.status_code} - {error_detail}"
            )
        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting result: {e}")
            raise LlamaExtractJobError(f"HTTP error: {e}")

    def _parse_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Parse LlamaExtract result into extracted data.

        The result format varies based on extraction target:
        - PER_DOC: Single object in 'data' field
        - PER_PAGE: Array of objects in 'data' field

        Args:
            result: Raw result from LlamaExtract API

        Returns:
            Extracted data dictionary
        """
        # Handle various result structures
        if "data" in result:
            data = result["data"]
            # If it's a list for PER_DOC mode, take first element
            if isinstance(data, list) and self._target == LlamaExtractTarget.PER_DOC:
                return data[0] if data else {}
            return data

        # Fallback: return result as-is
        return result

    async def _extract_from_file_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        schema: dict[str, Any],
    ) -> tuple[dict[str, Any], int, int, int]:
        """Extract data from file bytes.

        Args:
            file_bytes: Raw file content
            filename: File name for upload
            schema: JSON schema for extraction

        Returns:
            Tuple of (extracted_data, input_tokens, output_tokens, processing_time_ms)
        """
        start_time = time.time()

        timeout = httpx.Timeout(
            connect=30.0,
            read=self._timeout,
            write=self._timeout,
            pool=30.0,
        )

        async with httpx.AsyncClient(timeout=timeout) as client:
            # Step 1: Get or create agent for this schema
            agent_id = await self._get_or_create_agent(schema, client)

            # Step 2: Upload file
            file_id = await self._upload_file(file_bytes, filename, client)

            # Step 3: Create extraction job
            job_id = await self._create_job(agent_id, file_id, client)

            # Step 4: Poll until complete
            await self._poll_job_status(job_id, client)

            # Step 5: Get result
            raw_result = await self._get_job_result(job_id, client)

        # Parse result into extracted data
        extracted_data = self._parse_result(raw_result)

        processing_time_ms = int((time.time() - start_time) * 1000)

        # LlamaExtract is page-based, not token-based
        # Return 0 for tokens as billing is per-page
        return extracted_data, 0, 0, processing_time_ms

    async def extract(
        self,
        image_base64: str,
        schema: dict[str, Any],
        prompt: str,
    ) -> tuple[dict[str, Any], int, int, int]:
        """Extract structured data from a single image.

        Note: LlamaExtract works best with document files (PDF, etc.).
        For single images, the image is uploaded as a file.

        Args:
            image_base64: Base64 encoded image
            schema: JSON schema for extraction
            prompt: Custom extraction prompt (not used by LlamaExtract)

        Returns:
            Tuple of (extracted_data, input_tokens, output_tokens, processing_time_ms)
        """
        logger.info("Starting LlamaExtract single image extraction")

        # Decode base64 image
        image_bytes = base64.b64decode(image_base64)

        # Determine image type from magic bytes
        filename = "document.png"
        if image_bytes[:2] == b"\xff\xd8":
            filename = "document.jpg"
        elif image_bytes[:4] == b"%PDF":
            filename = "document.pdf"

        return await self._extract_from_file_bytes(image_bytes, filename, schema)

    async def extract_batch(
        self,
        images_base64: list[str],
        schema: dict[str, Any],
        prompt: str,
    ) -> tuple[dict[str, Any], int, int, int]:
        """Extract structured data from multiple images.

        For batch extraction, images are combined into a single PDF
        before uploading to LlamaExtract.

        Args:
            images_base64: List of base64 encoded images
            schema: JSON schema for extraction
            prompt: Custom extraction prompt (not used by LlamaExtract)

        Returns:
            Tuple of (extracted_data, input_tokens, output_tokens, processing_time_ms)
        """
        logger.info(f"Starting LlamaExtract batch extraction: {len(images_base64)} images")

        if len(images_base64) == 1:
            return await self.extract(images_base64[0], schema, prompt)

        # Combine images into PDF for multi-page extraction
        pdf_bytes = await self._create_pdf_from_images(images_base64)

        return await self._extract_from_file_bytes(pdf_bytes, "document.pdf", schema)

    async def _create_pdf_from_images(self, images_base64: list[str]) -> bytes:
        """Create a PDF from multiple base64-encoded images.

        Args:
            images_base64: List of base64 encoded images

        Returns:
            PDF file bytes
        """
        from PIL import Image

        images = []
        for img_b64 in images_base64:
            img_bytes = base64.b64decode(img_b64)
            img = Image.open(io.BytesIO(img_bytes))
            # Convert to RGB if necessary (PDF doesn't support RGBA)
            if img.mode == "RGBA":
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")
            images.append(img)

        if not images:
            raise ValueError("No valid images to create PDF")

        # Create PDF in memory
        pdf_buffer = io.BytesIO()
        images[0].save(
            pdf_buffer,
            format="PDF",
            save_all=True,
            append_images=images[1:] if len(images) > 1 else [],
        )

        pdf_buffer.seek(0)
        return pdf_buffer.read()

    async def extract_from_pdf(
        self,
        pdf_bytes: bytes,
        schema: dict[str, Any],
        prompt: str = "",
    ) -> tuple[dict[str, Any], int, int, int]:
        """Extract structured data directly from PDF bytes.

        This is the preferred method for document extraction as
        LlamaExtract is optimized for document files.

        Args:
            pdf_bytes: Raw PDF file bytes
            schema: JSON schema for extraction
            prompt: Custom extraction prompt (not used)

        Returns:
            Tuple of (extracted_data, input_tokens, output_tokens, processing_time_ms)
        """
        logger.info(f"Starting LlamaExtract PDF extraction ({len(pdf_bytes)} bytes)")
        return await self._extract_from_file_bytes(pdf_bytes, "document.pdf", schema)

    def clear_agent_cache(self) -> None:
        """Clear the agent cache.

        Use this if you need to force recreation of agents,
        for example after schema changes.
        """
        logger.info(f"Clearing agent cache ({len(self._agent_cache)} entries)")
        self._agent_cache.clear()


def get_llamaextract_provider(
    mode: LlamaExtractMode = LlamaExtractMode.STANDARD,
    target: LlamaExtractTarget = LlamaExtractTarget.PER_DOC,
) -> Optional[LlamaExtractVLLMProvider]:
    """Factory function to get LlamaExtract provider.

    Args:
        mode: Extraction quality mode
        target: Extraction target scope

    Returns:
        LlamaExtractVLLMProvider instance or None if not configured
    """
    if not settings.llamaextract_api_key:
        logger.warning("LlamaExtract API key not configured")
        return None

    return LlamaExtractVLLMProvider(
        api_key=settings.llamaextract_api_key,
        mode=mode,
        target=target,
    )
