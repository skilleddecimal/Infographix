"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.config import get_settings
from backend.api.routes import api_router
from backend.api.middleware import (
    RateLimitMiddleware,
    LoggingMiddleware,
    SecurityHeadersMiddleware,
)
from backend.api.middleware.rate_limit import RateLimitConfig

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.environment}")
    print(f"Debug mode: {settings.debug}")

    # Initialize database
    from backend.db.base import init_db
    init_db()

    yield

    # Shutdown
    print("Shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="AI-Powered PowerPoint Infographic Generator",
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Logging middleware
    app.add_middleware(
        LoggingMiddleware,
        exclude_paths=["/health", "/ready"],
    )

    # Rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        config=RateLimitConfig(
            requests_per_minute=60,
            exempt_paths=["/health", "/ready", "/docs", "/redoc", "/openapi.json"],
        ),
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
