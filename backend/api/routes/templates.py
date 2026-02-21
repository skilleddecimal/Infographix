"""Template routes."""

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.base import get_db
from backend.db.models import Template, User
from backend.api.dependencies import get_current_user, require_pro

router = APIRouter()


class TemplateCreate(BaseModel):
    """Request to create a template."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    archetype: str | None = None
    category: str | None = None
    dsl_template: dict[str, Any]
    parameters: dict[str, Any] | None = None
    is_public: bool = False


class TemplateUpdate(BaseModel):
    """Request to update a template."""
    name: str | None = None
    description: str | None = None
    archetype: str | None = None
    category: str | None = None
    dsl_template: dict[str, Any] | None = None
    parameters: dict[str, Any] | None = None
    is_public: bool | None = None


class TemplateResponse(BaseModel):
    """Template response."""
    id: str
    name: str
    description: str | None
    archetype: str | None
    category: str | None
    dsl_template: dict[str, Any]
    parameters: dict[str, Any] | None
    thumbnail_url: str | None
    is_public: bool
    use_count: int
    created_at: str
    updated_at: str


class TemplateListResponse(BaseModel):
    """Template list response."""
    templates: list[TemplateResponse]
    total: int
    limit: int
    offset: int


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    category: str | None = None,
    archetype: str | None = None,
    include_public: bool = True,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List available templates."""
    query = db.query(Template)

    # Filter by ownership or public
    if include_public:
        query = query.filter(
            (Template.user_id == current_user.id) | (Template.is_public == True)
        )
    else:
        query = query.filter(Template.user_id == current_user.id)

    # Apply filters
    if category:
        query = query.filter(Template.category == category)
    if archetype:
        query = query.filter(Template.archetype == archetype)

    # Get total count
    total = query.count()

    # Get paginated results
    templates = query.order_by(Template.use_count.desc()).offset(offset).limit(limit).all()

    return TemplateListResponse(
        templates=[
            TemplateResponse(
                id=t.id,
                name=t.name,
                description=t.description,
                archetype=t.archetype,
                category=t.category,
                dsl_template=t.dsl_template,
                parameters=t.parameters,
                thumbnail_url=t.thumbnail_url,
                is_public=t.is_public,
                use_count=t.use_count,
                created_at=t.created_at.isoformat(),
                updated_at=t.updated_at.isoformat(),
            )
            for t in templates
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/categories")
async def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List available template categories."""
    categories = db.query(Template.category).filter(
        (Template.user_id == current_user.id) | (Template.is_public == True),
        Template.category.isnot(None),
    ).distinct().all()

    return {"categories": [c[0] for c in categories if c[0]]}


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific template."""
    template = db.query(Template).filter(
        Template.id == template_id,
        (Template.user_id == current_user.id) | (Template.is_public == True),
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        archetype=template.archetype,
        category=template.category,
        dsl_template=template.dsl_template,
        parameters=template.parameters,
        thumbnail_url=template.thumbnail_url,
        is_public=template.is_public,
        use_count=template.use_count,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
    )


@router.post("", response_model=TemplateResponse)
async def create_template(
    request: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _pro: None = Depends(require_pro),
):
    """Create a new template (Pro+ only)."""
    template = Template(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        archetype=request.archetype,
        category=request.category,
        dsl_template=request.dsl_template,
        parameters=request.parameters,
        is_public=request.is_public,
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        archetype=template.archetype,
        category=template.category,
        dsl_template=template.dsl_template,
        parameters=template.parameters,
        thumbnail_url=template.thumbnail_url,
        is_public=template.is_public,
        use_count=template.use_count,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
    )


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    request: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a template."""
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.user_id == current_user.id,
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Update fields
    if request.name is not None:
        template.name = request.name
    if request.description is not None:
        template.description = request.description
    if request.archetype is not None:
        template.archetype = request.archetype
    if request.category is not None:
        template.category = request.category
    if request.dsl_template is not None:
        template.dsl_template = request.dsl_template
    if request.parameters is not None:
        template.parameters = request.parameters
    if request.is_public is not None:
        template.is_public = request.is_public

    db.commit()
    db.refresh(template)

    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        archetype=template.archetype,
        category=template.category,
        dsl_template=template.dsl_template,
        parameters=template.parameters,
        thumbnail_url=template.thumbnail_url,
        is_public=template.is_public,
        use_count=template.use_count,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
    )


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a template."""
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.user_id == current_user.id,
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    db.delete(template)
    db.commit()

    return {"status": "deleted"}


@router.post("/import")
async def import_template(
    file: UploadFile = File(...),
    name: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _pro: None = Depends(require_pro),
):
    """Import a template from PPTX file (Pro+ only)."""
    if not file.filename.endswith(".pptx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a .pptx file",
        )

    # Read file content
    content = await file.read()

    # Import template
    try:
        from backend.templates.ingestion import TemplateIngestionPipeline

        pipeline = TemplateIngestionPipeline()
        result = pipeline.ingest_from_bytes(
            content,
            name=name or file.filename.replace(".pptx", ""),
        )

        # Create template record
        template = Template(
            user_id=current_user.id,
            name=result.name,
            description=result.description,
            archetype=result.archetype,
            category=category,
            dsl_template=result.dsl_template,
            parameters=result.parameters,
        )
        db.add(template)
        db.commit()
        db.refresh(template)

        return TemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            archetype=template.archetype,
            category=template.category,
            dsl_template=template.dsl_template,
            parameters=template.parameters,
            thumbnail_url=template.thumbnail_url,
            is_public=template.is_public,
            use_count=template.use_count,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to import template: {str(e)}",
        )


@router.post("/{template_id}/use")
async def use_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record template usage and increment counter."""
    template = db.query(Template).filter(
        Template.id == template_id,
        (Template.user_id == current_user.id) | (Template.is_public == True),
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    template.use_count += 1
    db.commit()

    return {"use_count": template.use_count}
