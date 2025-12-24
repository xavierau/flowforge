"""LlamaParse document-to-markdown converter implementation.

Uses LlamaCloud's LlamaParse service to convert documents (PDF, DOCX, etc.)
directly to markdown. This is a document-level converter that charges per page
rather than per token.

LlamaParse API documentation:
- https://developers.llamaindex.ai/python/cloud/llamaparse/getting_started/
- https://developers.llamaindex.ai/python/cloud/llamaparse/api-v2-guide
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.converters.base import (
    IDocumentToMarkdownConverter,
    DocumentConversionResult,
    PageMarkdown,
)

logger = logging.getLogger(__name__)


class LlamaParseConverter(IDocumentToMarkdownConverter):
    """LlamaParse document-to-markdown converter.

    Converts documents (PDF, DOCX, PPTX, etc.) to markdown using LlamaCloud's
    LlamaParse service. Charges per page processed.

    Key features:
    - Direct PDF/document upload (no image conversion needed)
    - Page-based billing (actual pages processed returned)
    - Async processing with polling
    - High-quality table and layout extraction

    Attributes:
        api_key: LlamaCloud API key
        num_workers: Number of parallel workers for batch processing
        language: Target language for extraction
        verbose: Whether to print progress
    """

    # Supported file extensions
    SUPPORTED_EXTENSIONS = {
        '.pdf', '.docx', '.doc', '.pptx', '.ppt',
        '.xlsx', '.xls', '.html', '.htm', '.txt',
        '.rtf', '.epub', '.md', '.csv'
    }

    def __init__(
        self,
        api_key: str,
        num_workers: int = 4,
        language: str = "en",
        verbose: bool = False,
        result_type: str = "markdown",
    ):
        """Initialize LlamaParse converter.

        Args:
            api_key: LlamaCloud API key (llx-...)
            num_workers: Number of workers for parallel processing
            language: Target language code (default: "en")
            verbose: Whether to print progress messages
            result_type: Output format - "markdown" or "text"
        """
        if not api_key:
            raise ValueError("LlamaParse API key is required")

        self._api_key = api_key
        self._num_workers = num_workers
        self._language = language
        self._verbose = verbose
        self._result_type = result_type
        self._parser = None  # Lazy initialization

    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "llamaparse"

    @property
    def model_name(self) -> str:
        """Get the model/parser name."""
        return "llamaparse-v2"

    def _get_parser(self):
        """Lazy initialization of LlamaParse client.

        Returns:
            LlamaParse instance

        Raises:
            ImportError: If llama-cloud-services is not installed
        """
        if self._parser is None:
            try:
                from llama_cloud_services import LlamaParse
            except ImportError:
                raise ImportError(
                    "llama-cloud-services package is required for LlamaParse. "
                    "Install with: pip install llama-cloud-services"
                )

            self._parser = LlamaParse(
                api_key=self._api_key,
                num_workers=self._num_workers,
                verbose=self._verbose,
                language=self._language,
                result_type=self._result_type,
            )

        return self._parser

    def supports_format(self, filename: str) -> bool:
        """Check if the converter supports the given file format.

        Args:
            filename: Filename to check

        Returns:
            True if format is supported
        """
        if '.' not in filename:
            return False
        ext = '.' + filename.lower().rsplit('.', 1)[-1]
        return ext in self.SUPPORTED_EXTENSIONS

    async def convert_document(
        self,
        document_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> DocumentConversionResult:
        """Convert a document file to markdown.

        Args:
            document_path: Path to the document file
            options: Optional conversion options:
                - language: Override language setting
                - result_type: "markdown" or "text"
                - split_by_page: Whether to split output by page (default: True)

        Returns:
            DocumentConversionResult with markdown and page count

        Raises:
            FileNotFoundError: If document does not exist
            ValueError: If format is not supported
            Exception: If conversion fails
        """
        path = Path(document_path)

        if not path.exists():
            raise FileNotFoundError(f"Document not found: {document_path}")

        if not self.supports_format(path.name):
            raise ValueError(
                f"Unsupported format: {path.suffix}. "
                f"Supported: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
            )

        options = options or {}
        start_time = time.time()

        try:
            parser = self._get_parser()

            # Parse the document using async method
            logger.info(f"Starting LlamaParse conversion for: {path.name}")

            # Use aparse for async processing
            result = await parser.aparse(str(document_path))

            # Extract page results
            page_results = self._extract_page_results(result, options)
            pages_processed = len(page_results)

            # Combine markdown from all pages
            markdown_content = self._combine_page_markdown(page_results)

            processing_time = time.time() - start_time

            logger.info(
                f"LlamaParse conversion complete: {pages_processed} pages, "
                f"{processing_time:.2f}s"
            )

            return DocumentConversionResult(
                markdown_content=markdown_content,
                pages_processed=pages_processed,
                provider=self.provider_name,
                model=self.model_name,
                page_results=page_results,
                processing_time_seconds=processing_time,
                raw_response=self._extract_raw_response(result),
                job_id=self._extract_job_id(result),
            )

        except ImportError:
            raise
        except Exception as e:
            logger.error(
                f"LlamaParse conversion failed: {type(e).__name__}: {e}",
                exc_info=True
            )
            raise Exception(f"LlamaParse conversion error: {type(e).__name__}: {e}")

    async def convert_document_bytes(
        self,
        document_bytes: bytes,
        filename: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> DocumentConversionResult:
        """Convert document bytes to markdown.

        Creates a temporary file and processes it. The temp file is deleted
        after processing.

        Args:
            document_bytes: Raw document bytes
            filename: Original filename (for format detection)
            options: Optional conversion options

        Returns:
            DocumentConversionResult with markdown and page count

        Raises:
            ValueError: If format is not supported
            Exception: If conversion fails
        """
        if not self.supports_format(filename):
            ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'unknown'
            raise ValueError(
                f"Unsupported format: .{ext}. "
                f"Supported: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
            )

        # Create temporary file
        import tempfile

        # Get extension from filename
        ext = '.' + filename.rsplit('.', 1)[-1] if '.' in filename else '.pdf'

        with tempfile.NamedTemporaryFile(
            suffix=ext,
            delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(document_bytes)

        try:
            # Process the temp file
            return await self.convert_document(tmp_path, options)
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _extract_page_results(
        self,
        result: Any,
        options: Dict[str, Any]
    ) -> List[PageMarkdown]:
        """Extract per-page markdown from LlamaParse result.

        Args:
            result: LlamaParse JobResult object
            options: Conversion options

        Returns:
            List of PageMarkdown objects
        """
        page_results = []

        # Check if result has pages attribute
        if hasattr(result, 'pages') and result.pages:
            for i, page in enumerate(result.pages, start=1):
                markdown = ""
                raw_text = None

                # Extract markdown content
                if hasattr(page, 'md'):
                    markdown = page.md or ""
                elif hasattr(page, 'markdown'):
                    markdown = page.markdown or ""
                elif hasattr(page, 'text'):
                    markdown = page.text or ""

                # Extract raw text if available
                if hasattr(page, 'text') and page.text != markdown:
                    raw_text = page.text

                page_results.append(PageMarkdown(
                    page_number=i,
                    markdown=markdown,
                    raw_text=raw_text,
                ))
        else:
            # Fallback: try to get markdown documents with page splitting
            try:
                docs = result.get_markdown_documents(split_by_page=True)
                for i, doc in enumerate(docs, start=1):
                    content = doc.text if hasattr(doc, 'text') else str(doc)
                    page_results.append(PageMarkdown(
                        page_number=i,
                        markdown=content,
                    ))
            except Exception:
                # Last resort: get combined content
                try:
                    docs = result.get_markdown_documents(split_by_page=False)
                    content = docs[0].text if docs and hasattr(docs[0], 'text') else ""
                    # Estimate 1 page if we can't determine actual count
                    page_results.append(PageMarkdown(
                        page_number=1,
                        markdown=content,
                    ))
                except Exception:
                    logger.warning("Could not extract page results from LlamaParse response")

        return page_results

    def _combine_page_markdown(self, page_results: List[PageMarkdown]) -> str:
        """Combine per-page markdown into single document.

        Adds page markers between pages for downstream processing.

        Args:
            page_results: List of PageMarkdown objects

        Returns:
            Combined markdown with page markers
        """
        if not page_results:
            return ""

        if len(page_results) == 1:
            return f"<!-- PAGE 1 -->\n{page_results[0].markdown}"

        parts = []
        for page in page_results:
            parts.append(f"<!-- PAGE {page.page_number} -->\n{page.markdown}")

        return "\n\n".join(parts)

    def _extract_raw_response(self, result: Any) -> Optional[Dict[str, Any]]:
        """Extract raw response data for debugging.

        Args:
            result: LlamaParse JobResult

        Returns:
            Dict with raw response info or None
        """
        try:
            raw = {}
            if hasattr(result, 'job_id'):
                raw['job_id'] = result.job_id
            if hasattr(result, 'status'):
                raw['status'] = result.status
            if hasattr(result, 'pages'):
                raw['page_count'] = len(result.pages)
            return raw if raw else None
        except Exception:
            return None

    def _extract_job_id(self, result: Any) -> Optional[str]:
        """Extract job ID from result.

        Args:
            result: LlamaParse JobResult

        Returns:
            Job ID string or None
        """
        try:
            if hasattr(result, 'job_id'):
                return str(result.job_id)
            return None
        except Exception:
            return None
