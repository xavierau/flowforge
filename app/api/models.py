"""API endpoints for model configuration."""

from typing import Dict, List, Optional
import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_permission_flexible
from app.models.user import User
from app.domain.metrics.pricing_service import PricingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["models"])


class AvailableModel(BaseModel):
    """Model information for frontend dropdowns."""

    id: str = Field(..., description="Model pricing record ID")
    provider: str = Field(..., description="Provider name (google, openai, etc.)")
    model_name: str = Field(..., description="Model identifier")
    display_name: str = Field(..., description="Human-readable model name")
    supports_vision: bool = Field(..., description="Whether model supports image input")
    supports_markdown_conversion: bool = Field(
        ..., description="Whether model can convert to markdown"
    )
    supports_json_mode: bool = Field(..., description="Whether model supports JSON output mode")
    input_price_per_million: float = Field(..., description="Price per 1M input tokens (USD)")
    output_price_per_million: float = Field(..., description="Price per 1M output tokens (USD)")
    is_default_extraction: bool = Field(..., description="Default for extraction use case")
    is_default_markdown: bool = Field(..., description="Default for markdown conversion")
    is_default_llm: bool = Field(..., description="Default for general LLM tasks")


class DefaultModels(BaseModel):
    """Default models for each use case."""

    extraction: Optional[AvailableModel] = Field(None, description="Default extraction model")
    markdown: Optional[AvailableModel] = Field(None, description="Default markdown model")
    llm: Optional[AvailableModel] = Field(None, description="Default LLM model")


class AvailableModelsResponse(BaseModel):
    """Response containing available models and defaults."""

    models: List[AvailableModel] = Field(..., description="List of available models")
    defaults: DefaultModels = Field(..., description="Default models for each use case")
    providers: List[str] = Field(..., description="List of available providers")


class ProvidersResponse(BaseModel):
    """Response containing available providers."""

    providers: List[str] = Field(..., description="List of available providers")


@router.get("/available", response_model=AvailableModelsResponse)
async def get_available_models(
    use_case: Optional[str] = Query(
        None,
        description="Filter by use case: 'extraction', 'markdown', or 'llm'",
    ),
    provider: Optional[str] = Query(
        None,
        description="Filter by provider: 'google', 'openai', 'qwen', 'deepseek'",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_flexible("models:read")),
) -> AvailableModelsResponse:
    """
    Get available AI models for workflow configuration.

    Returns models that:
    1. Are marked as active in the database
    2. Have pricing configured

    Optionally filter by:
    - use_case: extraction (vision models), markdown (markdown conversion), llm (text completion)
    - provider: google, openai, qwen, deepseek

    Supports both JWT and API token authentication.

    Required Permission: models:read

    Args:
        use_case: Optional filter by use case
        provider: Optional filter by provider
        current_user: Authenticated user with models:read permission
        db: Database session

    Returns:
        Available models with defaults and provider list
    """
    pricing_service = PricingService(db)

    # Get models based on use case
    if use_case == "extraction":
        models_data = pricing_service.get_models_for_extraction()
    elif use_case == "markdown":
        models_data = pricing_service.get_models_for_markdown()
    elif use_case == "llm":
        models_data = pricing_service.get_models_for_llm()
    elif provider:
        models_data = pricing_service.get_models_by_provider(provider)
    else:
        # Return all active models (LLM is most inclusive - supports_text)
        models_data = pricing_service.get_models_for_llm()

    # Further filter by provider if specified with use_case
    if provider and use_case:
        models_data = [m for m in models_data if m["provider"] == provider.lower()]

    # Convert to response models
    models = [AvailableModel(**m) for m in models_data]

    # Get defaults
    extraction_default = pricing_service.get_default_model("extraction")
    markdown_default = pricing_service.get_default_model("markdown")
    llm_default = pricing_service.get_default_model("llm")

    defaults = DefaultModels(
        extraction=AvailableModel(**extraction_default) if extraction_default else None,
        markdown=AvailableModel(**markdown_default) if markdown_default else None,
        llm=AvailableModel(**llm_default) if llm_default else None,
    )

    # Get available providers
    providers = pricing_service.get_available_providers()

    return AvailableModelsResponse(
        models=models,
        defaults=defaults,
        providers=providers,
    )


@router.get("/providers", response_model=ProvidersResponse)
async def get_available_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission_flexible("models:read")),
) -> ProvidersResponse:
    """
    Get list of available model providers.

    Supports both JWT and API token authentication.

    Required Permission: models:read

    Args:
        current_user: Authenticated user with models:read permission
        db: Database session

    Returns:
        List of available provider names
    """
    pricing_service = PricingService(db)
    return ProvidersResponse(
        providers=pricing_service.get_available_providers(),
    )
