"""
Extraction Worker

Executes document data extraction using VLLM providers.
Integrates with the existing VLLMService to extract structured data from documents.
"""

from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from .base_worker import BaseWorker
from app.database import SessionLocal
from app.services.vllm_service import VLLMService
from app.services.storage import StorageService
from app.models.document import Document
from app.config import settings


class ExtractionWorker(BaseWorker):
    """
    Worker that performs document data extraction.

    Input Parameters:
    - document_id (str): ID of the document to extract from
    - schema (dict): JSON schema defining extraction structure
    - provider (str): VLLM provider ("google", "openai", "deepseek")
    - model (str): Model name (optional, uses provider default)

    Output:
    - extracted_data: Extracted structured data
    - pages_processed: Number of pages processed
    - total_tokens: Total tokens used
    """

    def __init__(self):
        super().__init__(task_definition_name="document_extraction")
        self.storage_service = StorageService(backend=settings.storage_type)
        self.vllm_service = VLLMService()

    def validate_input(self, task_input: Dict[str, Any]) -> Optional[str]:
        """Validate extraction worker input."""
        if "document_id" not in task_input:
            return "Missing required parameter: 'document_id'"

        if "schema" not in task_input:
            return "Missing required parameter: 'schema'"

        if not isinstance(task_input["schema"], dict):
            return "Parameter 'schema' must be a dictionary"

        provider = task_input.get("provider", "google")
        if provider not in ["google", "openai", "deepseek"]:
            return f"Invalid provider: {provider}. Must be one of: google, openai, deepseek"

        return None

    def execute_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute document extraction.

        Args:
            task_input: Contains document_id, schema, provider, model

        Returns:
            Dictionary with extracted_data, pages_processed, total_tokens
        """
        document_id = task_input["document_id"]
        schema = task_input["schema"]
        provider = task_input.get("provider", "google")
        model = task_input.get("model")

        self.log_info(
            f"Starting extraction for document {document_id} "
            f"using provider {provider}"
        )

        db = SessionLocal()
        try:
            # Fetch document
            document = db.query(Document).filter(
                Document.id == document_id
            ).first()

            if not document:
                raise ValueError(f"Document not found: {document_id}")

            if document.status != "ready_for_extraction":
                raise ValueError(
                    f"Document not ready for extraction. "
                    f"Current status: {document.status}"
                )

            # Get document pages
            if not document.pages or len(document.pages) == 0:
                raise ValueError(f"Document has no pages: {document_id}")

            self.log_info(f"Processing {len(document.pages)} pages")

            # Extract from each page
            all_results = []
            total_input_tokens = 0
            total_output_tokens = 0

            for page in document.pages:
                # Get image data
                image_data = self.storage_service.get_file(page.image_path)

                # Perform extraction
                result, input_tokens, output_tokens = (
                    self.vllm_service.extract_from_image(
                        image_data=image_data,
                        schema=schema,
                        provider=provider,
                        model_name=model,
                    )
                )

                all_results.append(result)
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens

                self.log_debug(
                    f"Page {page.page_number} processed: "
                    f"{input_tokens} input tokens, {output_tokens} output tokens"
                )

            # Combine results
            extracted_data = self._combine_results(all_results)

            self.log_info(
                f"Extraction completed: {len(document.pages)} pages, "
                f"{total_input_tokens + total_output_tokens} total tokens"
            )

            return {
                "extracted_data": extracted_data,
                "pages_processed": len(document.pages),
                "total_tokens": total_input_tokens + total_output_tokens,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
            }

        finally:
            db.close()

    def _combine_results(self, results: list[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine results from multiple pages.

        If there's only one page, return that result directly.
        If multiple pages, combine them intelligently based on schema structure.

        Args:
            results: List of extraction results from each page

        Returns:
            Combined result
        """
        if len(results) == 1:
            return results[0]

        # For multi-page documents, combine array fields
        combined = {}

        for result in results:
            for key, value in result.items():
                if key not in combined:
                    combined[key] = value
                elif isinstance(value, list) and isinstance(combined[key], list):
                    # Combine arrays
                    combined[key].extend(value)
                # For non-array fields, keep first occurrence

        return combined
