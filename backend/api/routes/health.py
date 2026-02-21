"""Health check routes."""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.base import get_db

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    database: str
    version: str


class ReadinessResponse(BaseModel):
    """Readiness check response."""
    ready: bool
    checks: dict[str, bool]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        database="unknown",
        version="1.0.0",
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(db: Session = Depends(get_db)):
    """Readiness check with dependency validation."""
    checks = {}

    # Check database
    try:
        db.execute("SELECT 1")
        checks["database"] = True
    except Exception:
        checks["database"] = False

    # All checks must pass
    ready = all(checks.values())

    return ReadinessResponse(
        ready=ready,
        checks=checks,
    )
