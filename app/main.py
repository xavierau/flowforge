"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import documents, jobs, health
from app.config import settings

# Create FastAPI app
app = FastAPI(
    title="AI Document Processing API",
    description="VLLM-powered document processing with custom schema extraction",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
app.include_router(jobs.router, prefix="/api/v1", tags=["Jobs"])


@app.on_event("startup")
async def startup_event() -> None:
    """Run on application startup."""
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


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Run on application shutdown."""
    print("👋 AI Document Processing API shutting down...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
