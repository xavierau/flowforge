"""Application configuration using Pydantic Settings."""

from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars not defined in the model
    )

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/doc_processing"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Storage
    storage_type: Literal["local", "s3"] = "local"
    local_storage_path: str = "./storage"
    s3_bucket: str = "doc-processing-files"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"

    # VLLM Providers
    google_api_key: str = ""
    openai_api_key: str = ""
    dashscope_api_key: str = ""
    llamaextract_api_key: str = ""  # LlamaCloud API key for LlamaExtract extraction

    # Document Converters
    llamaparse_api_key: str = ""  # LlamaCloud API key for LlamaParse (llx-...)

    # Default VLLM Configuration
    default_model_provider: str = "google"
    default_model_name: str = "gemini-2.5-flash"

    # Default Models per Provider (for markdown conversion - vision models)
    default_gemini_vision_model: str = "gemini-3-flash-preview"
    default_gpt4v_model: str = "gpt-4-vision-preview"
    default_qwen_vision_model: str = "qwen3-vl-32b-instruct"

    # Default Models for JSON Extraction (text models)
    default_gemini_json_model: str = "gemini-3-flash-preview"
    default_openai_json_model: str = "gpt-4o-mini"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-this-in-production"

    # JWT Authentication
    jwt_secret_key: str = "change-this-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # JWT Domain Restrictions (comma-separated list of allowed domains)
    # JWT tokens will only work from these domains
    # API tokens (sk_*) can be used from any domain
    # Example: "http://localhost:3002,https://yourdomain.com,https://app.yourdomain.com"
    jwt_allowed_origins: str = "http://localhost:3002,http://localhost:3000"

    # Email (SendGrid)
    sendgrid_api_key: str = ""
    email_from_address: str = "noreply@example.com"
    email_from_name: str = "AI Document Processing"

    # Inbound Email Processing
    inbound_email_domain: str = "parse.phbsolution.com"
    inbound_email_webhook_secret: str = ""
    max_email_attachment_size_mb: int = 25

    # Frontend URL (for email links)
    frontend_url: str = "http://localhost:3002"

    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""

    # File Upload Limits
    max_file_size_mb: int = 50
    allowed_image_types: set[str] = {"image/png", "image/jpeg", "image/jpg"}
    allowed_pdf_type: str = "application/pdf"

    # Logging
    log_level: str = "INFO"
    log_dir: str = "logs"

    # Netflix Conductor
    conductor_url: str = "http://localhost:8080"
    conductor_timeout: int = 30

    # Credential Encryption
    # Master key for encrypting workflow credentials (API keys, secrets)
    # Must be 32 bytes (256 bits), base64 encoded
    # Generate with: python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
    credential_encryption_key: str = ""

    # Markdown Pipeline Configuration
    default_markdown_converter: str = "gemini_vision"
    default_markdown_format: str = "table_heavy"
    enable_markdown_caching: bool = True
    markdown_pipeline_enabled: bool = True  # Feature flag

    # Document Split Configuration
    dashscope_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    split_max_image_size: int = 2048  # Max dimension for API calls
    split_default_dpi: int = 150  # DPI for PDF to image conversion

    # Rate Limiting
    # Set to False in tests to disable rate limiting
    rate_limit_enabled: bool = True

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def allowed_mime_types(self) -> set[str]:
        """Get all allowed MIME types."""
        return self.allowed_image_types | {self.allowed_pdf_type}

    @property
    def jwt_allowed_origins_list(self) -> set[str]:
        """Get JWT allowed origins as a set."""
        if not self.jwt_allowed_origins:
            return set()
        return {origin.strip() for origin in self.jwt_allowed_origins.split(",") if origin.strip()}


# Global settings instance
settings = Settings()
