"""Document boundary detection service using DSPy.

This service analyzes document pages to detect boundaries between documents
in a multi-document PDF file. It uses:
- DSPy for optimizable LLM calls (boundary detection)
- Tesseract OSD for reliable rotation detection

IMPORTANT: The Pydantic output model has reasoning fields BEFORE classification
fields because LLM autoregression generates tokens sequentially. Having the model
explain its reasoning first leads to better classification decisions.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

import PIL.Image
from pydantic import BaseModel, Field

from app.config import settings
from app.utils.rotation_utils import (
    detect_rotation_tesseract,
    resize_image_for_api,
    image_to_base64,
)

logger = logging.getLogger(__name__)

# DSPy import with fallback
try:
    import dspy
    from dspy.adapters.image_utils import encode_image

    DSPY_AVAILABLE = True
except ImportError:
    dspy = None
    encode_image = None
    DSPY_AVAILABLE = False
    logger.warning("DSPy not available - document analyzer will use fallback mode")


# ==============================================================================
# DSPy Signatures and Modules for Document Analysis
# ==============================================================================
# CRITICAL: Reasoning fields BEFORE classification fields!
# LLMs generate tokens sequentially (autoregression). By having the model
# explain its reasoning first, it makes better classification decisions.
# ==============================================================================


class DocumentAnalysisOutput(BaseModel):
    """Structured output for document page analysis.

    IMPORTANT: Field order matters for LLM autoregression!
    Reasoning/analysis fields come FIRST, classification SECOND.
    """

    # Step 1: Analysis/Reasoning (generated FIRST by LLM)
    boundary_reason: str = Field(
        description="Brief explanation of why this is or is not a starting page"
    )
    detected_document_type: str = Field(
        description="Type of document (e.g., invoice, receipt, form, letter, report, unknown)"
    )

    # Step 2: Classification (generated AFTER reasoning)
    is_starting_page: bool = Field(
        description="True if this is the first page of a new document, False if it's a continuation"
    )
    boundary_confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence level of the assessment"
    )


if DSPY_AVAILABLE:

    class DocumentBoundaryDetection(dspy.Signature):
        """Analyze a document page image to determine if it's the first page of a new document.

        A starting page typically has:
        - Document header/title at the top
        - Company logo or letterhead
        - Document number, date, or reference at the top
        - "Page 1" or similar indicator
        - Invoice header, receipt header, or form title
        - Fresh document layout (not a continuation)

        A NON-starting page (continuation) typically has:
        - Page numbers > 1
        - "Continued from..." text
        - No document header/title
        - Content that appears to continue from a previous page
        """

        image: dspy.Image = dspy.InputField(desc="The document page image to analyze")
        analysis: DocumentAnalysisOutput = dspy.OutputField(
            desc="Analysis with boundary_reason and detected_document_type first, "
            "then is_starting_page and boundary_confidence"
        )

    class DocumentAnalyzerModule(dspy.Module):
        """DSPy Module for analyzing document pages.

        This module can be optimized using DSPy optimizers like:
        - dspy.BootstrapFewShot(metric=your_metric)
        - dspy.MIPROv2(metric=your_metric)
        """

        def __init__(self):
            super().__init__()
            self.predictor = dspy.ChainOfThought(DocumentBoundaryDetection)

        def forward(self, image: dspy.Image) -> DocumentAnalysisOutput:
            """Analyze a document page image.

            Args:
                image: DSPy Image object

            Returns:
                DocumentAnalysisOutput with analysis results
            """
            result = self.predictor(image=image)
            return result.analysis


@dataclass
class PageAnalysisResult:
    """Result of analyzing a single page."""

    page_number: int  # 1-indexed
    page_index: int  # 0-indexed

    # Boundary detection (reasoning FIRST, classification SECOND)
    boundary_reason: str
    detected_document_type: str
    is_starting_page: bool
    boundary_confidence: Literal["high", "medium", "low"]

    # Rotation detection
    rotation_needed: int  # 0, 90, 180, 270 clockwise
    rotation_confidence: Literal["high", "medium", "low"]
    rotation_method: str

    # Token tracking
    input_tokens: int
    output_tokens: int

    # Optional child document reference (filled after splitting)
    child_document_id: Optional[str] = None


class DocumentAnalyzerService:
    """Service for analyzing document pages for boundary and rotation detection.

    Uses DSPy for boundary detection (optimizable with labeled examples) and
    Tesseract OSD for reliable rotation detection.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_image_size: Optional[int] = None,
    ):
        """Initialize the document analyzer service.

        Args:
            model: Model name (default: from settings.default_qwen_vision_model)
            api_key: Dashscope API key (default: from settings)
            base_url: API base URL (default: from settings.dashscope_base_url)
            max_image_size: Maximum image dimension for API calls (default: from settings)
        """
        self.model = model or settings.default_qwen_vision_model
        self.api_key = api_key or settings.dashscope_api_key
        self.base_url = base_url or settings.dashscope_base_url
        self.max_image_size = max_image_size or settings.split_max_image_size

        self._lm: Optional["dspy.LM"] = None
        self._analyzer: Optional["DocumentAnalyzerModule"] = None
        self._initialized = False

    def _initialize_dspy(self) -> None:
        """Initialize DSPy with the configured model."""
        if not DSPY_AVAILABLE:
            raise RuntimeError("DSPy is not available. Install with: pip install dspy")

        if not self.api_key:
            raise ValueError(
                "Dashscope API key not configured. "
                "Set DASHSCOPE_API_KEY environment variable."
            )

        if self._initialized:
            return

        # Initialize DSPy LM with Qwen VL via Dashscope (OpenAI-compatible)
        self._lm = dspy.LM(
            model=f"openai/{self.model}",
            api_key=self.api_key,
            api_base=self.base_url,
            temperature=0.1,
        )
        dspy.configure(lm=self._lm)

        # Initialize the analyzer module
        self._analyzer = DocumentAnalyzerModule()
        self._initialized = True

        logger.info(f"DSPy DocumentAnalyzer initialized with model: {self.model}")

    def _get_token_usage(self) -> Tuple[int, int]:
        """Extract token usage from DSPy's LM history.

        Returns:
            Tuple of (input_tokens, output_tokens)
        """
        if not self._lm or not self._lm.history:
            return 0, 0

        try:
            last_call = self._lm.history[-1]
            if hasattr(last_call, "usage") and last_call.usage:
                input_tokens = getattr(last_call.usage, "prompt_tokens", 0) or 0
                output_tokens = getattr(last_call.usage, "completion_tokens", 0) or 0
                return input_tokens, output_tokens
        except Exception as e:
            logger.warning(f"Failed to extract token usage: {e}")

        return 0, 0

    def _map_rotation_confidence(self, osd_confidence: float) -> Literal["high", "medium", "low"]:
        """Map Tesseract OSD confidence to string level."""
        if osd_confidence > 5.0:
            return "high"
        elif osd_confidence > 1.0:
            return "medium"
        else:
            return "low"

    def analyze_page(
        self,
        image: PIL.Image.Image,
        page_number: int,
        use_tesseract_for_rotation: bool = True,
    ) -> PageAnalysisResult:
        """Analyze a single page for boundary and rotation detection.

        Args:
            image: PIL Image of the page
            page_number: 1-indexed page number
            use_tesseract_for_rotation: Use Tesseract OSD for rotation (recommended)

        Returns:
            PageAnalysisResult with analysis results
        """
        self._initialize_dspy()

        page_index = page_number - 1

        # ====================
        # ROTATION DETECTION (Tesseract - More Reliable)
        # ====================
        rotation_needed = 0
        rotation_confidence: Literal["high", "medium", "low"] = "low"
        rotation_method = "none"

        if use_tesseract_for_rotation:
            rotation_result = detect_rotation_tesseract(image)
            rotation_needed = rotation_result["rotation_needed"]
            # detect_rotation_tesseract already returns confidence as string
            rotation_confidence = rotation_result.get("confidence", "low")
            rotation_method = "tesseract_osd"

            if "error" in rotation_result:
                logger.warning(
                    f"Page {page_number}: Tesseract OSD error: {rotation_result['error']}"
                )

        # ====================
        # DOCUMENT BOUNDARY DETECTION (DSPy - Optimizable)
        # ====================
        resized = resize_image_for_api(image, self.max_image_size)

        # Convert PIL Image to DSPy Image using encode_image
        # Note: dspy.Image.from_PIL() has a bug, so we use encode_image directly
        data_uri = encode_image(resized)
        dspy_image = dspy.Image(url=data_uri)

        try:
            # Use DSPy module for prediction
            result = self._analyzer(image=dspy_image)
            input_tokens, output_tokens = self._get_token_usage()

            return PageAnalysisResult(
                page_number=page_number,
                page_index=page_index,
                # Boundary detection
                boundary_reason=result.boundary_reason,
                detected_document_type=result.detected_document_type,
                is_starting_page=result.is_starting_page,
                boundary_confidence=result.boundary_confidence,
                # Rotation detection
                rotation_needed=rotation_needed,
                rotation_confidence=rotation_confidence,
                rotation_method=rotation_method,
                # Token tracking
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        except Exception as e:
            logger.error(f"Page {page_number}: DSPy error: {e}")
            # Return safe defaults on error
            return PageAnalysisResult(
                page_number=page_number,
                page_index=page_index,
                boundary_reason=f"DSPy error: {str(e)}",
                detected_document_type="unknown",
                is_starting_page=True,  # Safe default: treat as new document
                boundary_confidence="low",
                rotation_needed=rotation_needed,
                rotation_confidence=rotation_confidence,
                rotation_method=rotation_method,
                input_tokens=0,
                output_tokens=0,
            )

    def analyze_all_pages(
        self,
        images: List[PIL.Image.Image],
        use_tesseract_for_rotation: bool = True,
    ) -> List[PageAnalysisResult]:
        """Analyze all pages in a document.

        Args:
            images: List of PIL Images (one per page)
            use_tesseract_for_rotation: Use Tesseract OSD for rotation

        Returns:
            List of PageAnalysisResult for each page
        """
        results = []

        for i, image in enumerate(images):
            page_number = i + 1
            result = self.analyze_page(image, page_number, use_tesseract_for_rotation)
            results.append(result)

            logger.info(
                f"Page {page_number}: "
                f"{'START' if result.is_starting_page else 'CONT'} "
                f"({result.boundary_confidence}) "
                f"type={result.detected_document_type} "
                f"rotation={result.rotation_needed}°"
            )

        return results

    @staticmethod
    def get_starting_indices(results: List[PageAnalysisResult]) -> List[int]:
        """Extract 0-indexed starting page indices.

        Args:
            results: List of page analysis results

        Returns:
            Sorted list of 0-indexed starting page indices
        """
        starting_indices = [
            result.page_index for result in results if result.is_starting_page
        ]

        # Always ensure page 0 is included as a starting page
        if 0 not in starting_indices:
            starting_indices.insert(0, 0)

        return sorted(starting_indices)

    @staticmethod
    def get_rotation_map(results: List[PageAnalysisResult]) -> Dict[int, int]:
        """Build rotation map from analysis results.

        Args:
            results: List of page analysis results

        Returns:
            Dict mapping page_index -> rotation degrees (0, 90, 180, 270)
        """
        return {
            result.page_index: result.rotation_needed
            for result in results
            if result.rotation_needed != 0
        }

    @staticmethod
    def get_token_totals(results: List[PageAnalysisResult]) -> Dict[str, int]:
        """Calculate total token usage.

        Args:
            results: List of page analysis results

        Returns:
            Dict with input_tokens, output_tokens, total_tokens
        """
        input_total = sum(r.input_tokens for r in results)
        output_total = sum(r.output_tokens for r in results)

        return {
            "input_tokens": input_total,
            "output_tokens": output_total,
            "total_tokens": input_total + output_total,
        }
