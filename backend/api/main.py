"""
main.py — FastAPI application entry point for InfographAI.

Run with:
    uvicorn backend.api.main:app --reload

Or programmatically:
    import uvicorn
    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=8000, reload=True)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routes import router
from .schemas import HealthResponse


# =============================================================================
# APP CONFIGURATION
# =============================================================================

app = FastAPI(
    title="InfographAI",
    description="AI-powered infographic and diagram generation API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# =============================================================================
# CORS MIDDLEWARE
# =============================================================================

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# ROUTES
# =============================================================================

app.include_router(router)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with basic info."""
    return {
        "name": "InfographAI",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health():
    """Health check endpoint."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        anthropic_configured=settings.has_anthropic_key,
    )


# =============================================================================
# STARTUP/SHUTDOWN EVENTS
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    settings = get_settings()

    # Create output directory
    import os
    os.makedirs(settings.output_dir, exist_ok=True)

    print(f"InfographAI API starting...")
    print(f"  Output directory: {settings.output_dir}")
    print(f"  Anthropic API configured: {settings.has_anthropic_key}")
    print(f"  CORS origins: {settings.cors_origins}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    print("InfographAI API shutting down...")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "backend.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
