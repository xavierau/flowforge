"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import documents, jobs, health, schemas, auth, users, metrics, logging, tokens, subscriptions, admin, credits, workflows, reviews, credentials, models, splits, inbound_emails, webhooks, platform, admin_platform
from app.core.redis import close_redis_pool
from app.dependencies.rate_limit import limiter
from app.config import settings
from app.middleware.tenant_context import TenantContextMiddleware
from app.middleware.admin_audit import AdminAuditMiddleware
from app.middleware.rate_limit_headers import RateLimitHeaderMiddleware
from app.logging_config import setup_logging

# Initialize logging
setup_logging(log_dir=settings.log_dir, log_level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    print("🚀 AI Document Processing API starting...")
    print(f"📊 Database: {settings.database_url.split('@')[-1]}")  # Hide credentials
    print(f"💾 Storage: {settings.storage_type}")
    print(f"🤖 VLLM Providers configured: ", end="")
    providers = []
    if settings.google_api_key:
        providers.append("Google Gemini")
    if settings.openai_api_key:
        providers.append("OpenAI GPT-4V")
    print(", ".join(providers) if providers else "None")

    yield  # Application runs here

    # Shutdown
    print("Closing Redis connection pool...")
    close_redis_pool()
    print("AI Document Processing API shutting down...")


# Create FastAPI app
app = FastAPI(
    title="AI Document Processing API",
    description="VLLM-powered document processing with custom schema extraction",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS - Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add tenant context middleware for multi-tenancy support
app.add_middleware(TenantContextMiddleware)

# Add admin audit logging middleware (must be after tenant context)
app.add_middleware(AdminAuditMiddleware)

# Add rate limit header middleware for platform API
app.add_middleware(RateLimitHeaderMiddleware)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1", tags=["Users"])
app.include_router(tokens.router, prefix="/api/v1", tags=["API Tokens"])
app.include_router(subscriptions.router, prefix="/api/v1", tags=["Subscriptions"])
app.include_router(credits.router, tags=["Credits"])
app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
app.include_router(jobs.router, prefix="/api/v1", tags=["Jobs"])
app.include_router(schemas.router, prefix="/api/v1", tags=["Schemas"])
app.include_router(metrics.router, prefix="/api/v1", tags=["Metrics"])
app.include_router(logging.router, prefix="/api/v1", tags=["Logging"])
app.include_router(admin.router, prefix="/api/v1", tags=["Admin"])
app.include_router(workflows.router, prefix="/api/v1", tags=["Workflows"])
app.include_router(reviews.router, prefix="/api/v1", tags=["Reviews"])
app.include_router(credentials.router, prefix="/api/v1", tags=["Credentials"])
app.include_router(models.router, prefix="/api/v1", tags=["Models"])
app.include_router(splits.router, prefix="/api/v1", tags=["Document Splitting"])
app.include_router(inbound_emails.router, prefix="/api/v1", tags=["Inbound Emails"])
app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])

# Platform API routers (for external application integration)
app.include_router(platform.router, tags=["Platform API"])
app.include_router(admin_platform.router, prefix="/api/v1", tags=["Admin - Platform"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
