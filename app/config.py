"""Application configuration using Pydantic Settings."""

from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
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

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-this-in-production"

    # File Upload Limits
    max_file_size_mb: int = 50
    allowed_image_types: set[str] = {"image/png", "image/jpeg", "image/jpg"}
    allowed_pdf_type: str = "application/pdf"

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def allowed_mime_types(self) -> set[str]:
        """Get all allowed MIME types."""
        return self.allowed_image_types | {self.allowed_pdf_type}


# Global settings instance
settings = Settings()
