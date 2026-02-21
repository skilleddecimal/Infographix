"""API routes for Infographix."""

from fastapi import APIRouter

from backend.api.routes.generate import router as generate_router
from backend.api.routes.templates import router as templates_router
from backend.api.routes.downloads import router as downloads_router
from backend.api.routes.auth import router as auth_router
from backend.api.routes.billing import router as billing_router
from backend.api.routes.health import router as health_router
from backend.api.routes.organizations import router as organizations_router
from backend.api.routes.brand_guidelines import router as brand_guidelines_router
from backend.api.routes.audit import router as audit_router
from backend.api.routes.webhooks import router as webhooks_router

# Main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(billing_router, prefix="/billing", tags=["Billing"])
api_router.include_router(generate_router, prefix="/generate", tags=["Generation"])
api_router.include_router(templates_router, prefix="/templates", tags=["Templates"])
api_router.include_router(downloads_router, prefix="/downloads", tags=["Downloads"])

# Enterprise routes (organizations context)
api_router.include_router(organizations_router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(brand_guidelines_router, prefix="/organizations", tags=["Brand Guidelines"])
api_router.include_router(audit_router, prefix="/organizations", tags=["Audit Logs"])
api_router.include_router(webhooks_router, prefix="/organizations", tags=["Webhooks"])

__all__ = ["api_router"]
