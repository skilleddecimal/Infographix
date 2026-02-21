"""Brand guidelines routes for Enterprise."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.base import get_db
from backend.db.models import (
    User,
    Organization,
    OrganizationMember,
    BrandGuideline,
    MemberRole,
)
from backend.api.dependencies import CurrentUser
from backend.api.routes.organizations import require_org_role

router = APIRouter()


# Request/Response Models
class ColorDefinition(BaseModel):
    """Color definition."""
    name: str
    hex: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    usage: str | None = None  # "primary", "accent", "background", etc.


class CreateBrandGuidelineRequest(BaseModel):
    """Create brand guideline request."""
    name: str = Field(..., min_length=1, max_length=100)
    primary_colors: list[ColorDefinition] = []
    secondary_colors: list[ColorDefinition] = []
    forbidden_colors: list[str] = []  # List of hex colors
    allowed_fonts: list[str] = []
    heading_font: str | None = None
    body_font: str | None = None
    logo_url: str | None = None
    logo_placement: str | None = None
    min_corner_radius: float = 0
    max_corner_radius: float = 50
    allow_shadows: bool = True
    allow_gradients: bool = True
    allow_glow: bool = True
    is_default: bool = False


class UpdateBrandGuidelineRequest(BaseModel):
    """Update brand guideline request."""
    name: str | None = None
    primary_colors: list[ColorDefinition] | None = None
    secondary_colors: list[ColorDefinition] | None = None
    forbidden_colors: list[str] | None = None
    allowed_fonts: list[str] | None = None
    heading_font: str | None = None
    body_font: str | None = None
    logo_url: str | None = None
    logo_placement: str | None = None
    min_corner_radius: float | None = None
    max_corner_radius: float | None = None
    allow_shadows: bool | None = None
    allow_gradients: bool | None = None
    allow_glow: bool | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class BrandGuidelineResponse(BaseModel):
    """Brand guideline response."""
    id: str
    organization_id: str
    name: str
    primary_colors: list[dict]
    secondary_colors: list[dict]
    forbidden_colors: list[str]
    allowed_fonts: list[str]
    heading_font: str | None
    body_font: str | None
    logo_url: str | None
    logo_placement: str | None
    min_corner_radius: float
    max_corner_radius: float
    allow_shadows: bool
    allow_gradients: bool
    allow_glow: bool
    is_default: bool
    is_active: bool
    created_at: str
    updated_at: str


class ComplianceCheckRequest(BaseModel):
    """Check brand compliance request."""
    colors: list[str] = []  # Hex colors to check
    fonts: list[str] = []  # Font names to check
    corner_radius: float | None = None
    has_shadows: bool = False
    has_gradients: bool = False
    has_glow: bool = False


class ComplianceCheckResponse(BaseModel):
    """Compliance check response."""
    compliant: bool
    violations: list[dict]
    warnings: list[dict]


def guideline_to_response(guideline: BrandGuideline) -> BrandGuidelineResponse:
    """Convert BrandGuideline model to response."""
    return BrandGuidelineResponse(
        id=guideline.id,
        organization_id=guideline.organization_id,
        name=guideline.name,
        primary_colors=guideline.primary_colors or [],
        secondary_colors=guideline.secondary_colors or [],
        forbidden_colors=guideline.forbidden_colors or [],
        allowed_fonts=guideline.allowed_fonts or [],
        heading_font=guideline.heading_font,
        body_font=guideline.body_font,
        logo_url=guideline.logo_url,
        logo_placement=guideline.logo_placement,
        min_corner_radius=guideline.min_corner_radius,
        max_corner_radius=guideline.max_corner_radius,
        allow_shadows=guideline.allow_shadows,
        allow_gradients=guideline.allow_gradients,
        allow_glow=guideline.allow_glow,
        is_default=guideline.is_default,
        is_active=guideline.is_active,
        created_at=guideline.created_at.isoformat(),
        updated_at=guideline.updated_at.isoformat(),
    )


@router.get("/{org_id}/brand-guidelines", response_model=list[BrandGuidelineResponse])
async def list_brand_guidelines(
    org_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    active_only: bool = True,
):
    """List brand guidelines for an organization."""
    require_org_role(db, current_user, org_id, list(MemberRole))

    query = db.query(BrandGuideline).filter(
        BrandGuideline.organization_id == org_id
    )

    if active_only:
        query = query.filter(BrandGuideline.is_active == True)

    guidelines = query.order_by(
        BrandGuideline.is_default.desc(),
        BrandGuideline.name,
    ).all()

    return [guideline_to_response(g) for g in guidelines]


@router.get("/{org_id}/brand-guidelines/{guideline_id}", response_model=BrandGuidelineResponse)
async def get_brand_guideline(
    org_id: str,
    guideline_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Get a specific brand guideline."""
    require_org_role(db, current_user, org_id, list(MemberRole))

    guideline = db.query(BrandGuideline).filter(
        BrandGuideline.id == guideline_id,
        BrandGuideline.organization_id == org_id,
    ).first()

    if not guideline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand guideline not found",
        )

    return guideline_to_response(guideline)


@router.post("/{org_id}/brand-guidelines", response_model=BrandGuidelineResponse)
async def create_brand_guideline(
    org_id: str,
    request: CreateBrandGuidelineRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Create a new brand guideline."""
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    # If this is set as default, unset any existing default
    if request.is_default:
        db.query(BrandGuideline).filter(
            BrandGuideline.organization_id == org_id,
            BrandGuideline.is_default == True,
        ).update({"is_default": False})

    guideline = BrandGuideline(
        organization_id=org_id,
        name=request.name,
        primary_colors=[c.model_dump() for c in request.primary_colors],
        secondary_colors=[c.model_dump() for c in request.secondary_colors],
        forbidden_colors=request.forbidden_colors,
        allowed_fonts=request.allowed_fonts,
        heading_font=request.heading_font,
        body_font=request.body_font,
        logo_url=request.logo_url,
        logo_placement=request.logo_placement,
        min_corner_radius=request.min_corner_radius,
        max_corner_radius=request.max_corner_radius,
        allow_shadows=request.allow_shadows,
        allow_gradients=request.allow_gradients,
        allow_glow=request.allow_glow,
        is_default=request.is_default,
    )

    db.add(guideline)
    db.commit()
    db.refresh(guideline)

    return guideline_to_response(guideline)


@router.patch("/{org_id}/brand-guidelines/{guideline_id}", response_model=BrandGuidelineResponse)
async def update_brand_guideline(
    org_id: str,
    guideline_id: str,
    request: UpdateBrandGuidelineRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Update a brand guideline."""
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    guideline = db.query(BrandGuideline).filter(
        BrandGuideline.id == guideline_id,
        BrandGuideline.organization_id == org_id,
    ).first()

    if not guideline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand guideline not found",
        )

    # If setting as default, unset any existing default
    if request.is_default:
        db.query(BrandGuideline).filter(
            BrandGuideline.organization_id == org_id,
            BrandGuideline.is_default == True,
            BrandGuideline.id != guideline_id,
        ).update({"is_default": False})

    # Update fields
    if request.name is not None:
        guideline.name = request.name
    if request.primary_colors is not None:
        guideline.primary_colors = [c.model_dump() for c in request.primary_colors]
    if request.secondary_colors is not None:
        guideline.secondary_colors = [c.model_dump() for c in request.secondary_colors]
    if request.forbidden_colors is not None:
        guideline.forbidden_colors = request.forbidden_colors
    if request.allowed_fonts is not None:
        guideline.allowed_fonts = request.allowed_fonts
    if request.heading_font is not None:
        guideline.heading_font = request.heading_font
    if request.body_font is not None:
        guideline.body_font = request.body_font
    if request.logo_url is not None:
        guideline.logo_url = request.logo_url
    if request.logo_placement is not None:
        guideline.logo_placement = request.logo_placement
    if request.min_corner_radius is not None:
        guideline.min_corner_radius = request.min_corner_radius
    if request.max_corner_radius is not None:
        guideline.max_corner_radius = request.max_corner_radius
    if request.allow_shadows is not None:
        guideline.allow_shadows = request.allow_shadows
    if request.allow_gradients is not None:
        guideline.allow_gradients = request.allow_gradients
    if request.allow_glow is not None:
        guideline.allow_glow = request.allow_glow
    if request.is_default is not None:
        guideline.is_default = request.is_default
    if request.is_active is not None:
        guideline.is_active = request.is_active

    db.commit()
    db.refresh(guideline)

    return guideline_to_response(guideline)


@router.delete("/{org_id}/brand-guidelines/{guideline_id}")
async def delete_brand_guideline(
    org_id: str,
    guideline_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Delete a brand guideline."""
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    guideline = db.query(BrandGuideline).filter(
        BrandGuideline.id == guideline_id,
        BrandGuideline.organization_id == org_id,
    ).first()

    if not guideline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand guideline not found",
        )

    db.delete(guideline)
    db.commit()

    return {"status": "brand_guideline_deleted"}


@router.post("/{org_id}/brand-guidelines/{guideline_id}/check-compliance", response_model=ComplianceCheckResponse)
async def check_compliance(
    org_id: str,
    guideline_id: str,
    request: ComplianceCheckRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Check if content complies with brand guidelines."""
    require_org_role(db, current_user, org_id, list(MemberRole))

    guideline = db.query(BrandGuideline).filter(
        BrandGuideline.id == guideline_id,
        BrandGuideline.organization_id == org_id,
    ).first()

    if not guideline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand guideline not found",
        )

    violations = []
    warnings = []

    # Check colors
    forbidden_colors = [c.lower() for c in (guideline.forbidden_colors or [])]
    allowed_colors = set()

    for color in (guideline.primary_colors or []):
        if isinstance(color, dict) and "hex" in color:
            allowed_colors.add(color["hex"].lower())

    for color in (guideline.secondary_colors or []):
        if isinstance(color, dict) and "hex" in color:
            allowed_colors.add(color["hex"].lower())

    for color in request.colors:
        color_lower = color.lower()
        if color_lower in forbidden_colors:
            violations.append({
                "type": "forbidden_color",
                "message": f"Color {color} is forbidden",
                "value": color,
            })
        elif allowed_colors and color_lower not in allowed_colors:
            warnings.append({
                "type": "unapproved_color",
                "message": f"Color {color} is not in the approved palette",
                "value": color,
            })

    # Check fonts
    allowed_fonts = [f.lower() for f in (guideline.allowed_fonts or [])]
    if guideline.heading_font:
        allowed_fonts.append(guideline.heading_font.lower())
    if guideline.body_font:
        allowed_fonts.append(guideline.body_font.lower())

    for font in request.fonts:
        if allowed_fonts and font.lower() not in allowed_fonts:
            warnings.append({
                "type": "unapproved_font",
                "message": f"Font '{font}' is not in the approved list",
                "value": font,
            })

    # Check corner radius
    if request.corner_radius is not None:
        if request.corner_radius < guideline.min_corner_radius:
            violations.append({
                "type": "corner_radius_too_small",
                "message": f"Corner radius {request.corner_radius} is below minimum {guideline.min_corner_radius}",
                "value": request.corner_radius,
            })
        if request.corner_radius > guideline.max_corner_radius:
            violations.append({
                "type": "corner_radius_too_large",
                "message": f"Corner radius {request.corner_radius} exceeds maximum {guideline.max_corner_radius}",
                "value": request.corner_radius,
            })

    # Check effects
    if request.has_shadows and not guideline.allow_shadows:
        violations.append({
            "type": "shadows_not_allowed",
            "message": "Shadows are not allowed by brand guidelines",
        })

    if request.has_gradients and not guideline.allow_gradients:
        violations.append({
            "type": "gradients_not_allowed",
            "message": "Gradients are not allowed by brand guidelines",
        })

    if request.has_glow and not guideline.allow_glow:
        violations.append({
            "type": "glow_not_allowed",
            "message": "Glow effects are not allowed by brand guidelines",
        })

    return ComplianceCheckResponse(
        compliant=len(violations) == 0,
        violations=violations,
        warnings=warnings,
    )


@router.get("/{org_id}/brand-guidelines/default", response_model=BrandGuidelineResponse | None)
async def get_default_brand_guideline(
    org_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Get the default brand guideline for an organization."""
    require_org_role(db, current_user, org_id, list(MemberRole))

    guideline = db.query(BrandGuideline).filter(
        BrandGuideline.organization_id == org_id,
        BrandGuideline.is_default == True,
        BrandGuideline.is_active == True,
    ).first()

    if not guideline:
        return None

    return guideline_to_response(guideline)
