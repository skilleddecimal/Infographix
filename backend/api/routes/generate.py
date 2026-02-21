"""Generation routes."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.base import get_db
from backend.db.models import Generation, GenerationStatus, User, UsageRecord
from backend.api.dependencies import get_current_user, check_credits

router = APIRouter()


class GenerateRequest(BaseModel):
    """Request to generate an infographic."""
    prompt: str = Field(..., min_length=1, max_length=2000)
    content: list[dict[str, str]] | None = None
    brand_colors: list[str] | None = None
    brand_fonts: list[str] | None = None
    formality: str = "professional"
    num_variations: int = Field(default=1, ge=1, le=10)


class GenerateResponse(BaseModel):
    """Response from generation."""
    id: str
    status: str
    archetype: str | None = None
    confidence: float | None = None


class GenerationResult(BaseModel):
    """Full generation result."""
    id: str
    status: str
    archetype: str | None = None
    archetype_confidence: float | None = None
    dsl: dict[str, Any] | None = None
    style: dict[str, Any] | None = None
    variations: list[dict[str, Any]] | None = None
    processing_time_ms: int | None = None
    created_at: str
    completed_at: str | None = None
    error_message: str | None = None


class VariationsRequest(BaseModel):
    """Request for additional variations."""
    generation_id: str
    count: int = Field(default=3, ge=1, le=10)
    strategy: str = "diverse"


@router.post("", response_model=GenerateResponse)
async def create_generation(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _credits: None = Depends(check_credits),
):
    """Create a new generation job.

    This queues the generation for background processing.
    Poll the status endpoint to check progress.
    """
    # Create generation record
    generation = Generation(
        user_id=current_user.id,
        prompt=request.prompt,
        content=request.content,
        brand_colors=request.brand_colors,
        brand_fonts=request.brand_fonts,
        status=GenerationStatus.PENDING,
    )
    db.add(generation)

    # Record usage
    usage = UsageRecord(
        user_id=current_user.id,
        action="generate",
        credits_used=1,
        generation_id=generation.id,
    )
    db.add(usage)

    # Deduct credits
    current_user.credits_remaining -= 1

    db.commit()
    db.refresh(generation)

    # Queue background processing
    background_tasks.add_task(
        process_generation,
        generation_id=generation.id,
        prompt=request.prompt,
        content=request.content,
        brand_colors=request.brand_colors,
        brand_fonts=request.brand_fonts,
        formality=request.formality,
        num_variations=request.num_variations,
    )

    return GenerateResponse(
        id=generation.id,
        status=generation.status.value,
    )


@router.get("/{generation_id}", response_model=GenerationResult)
async def get_generation(
    generation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get generation status and result."""
    generation = db.query(Generation).filter(
        Generation.id == generation_id,
        Generation.user_id == current_user.id,
    ).first()

    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found",
        )

    return GenerationResult(
        id=generation.id,
        status=generation.status.value,
        archetype=generation.archetype,
        archetype_confidence=generation.archetype_confidence,
        dsl=generation.dsl,
        style=generation.style,
        variations=generation.variations,
        processing_time_ms=generation.processing_time_ms,
        created_at=generation.created_at.isoformat(),
        completed_at=generation.completed_at.isoformat() if generation.completed_at else None,
        error_message=generation.error_message,
    )


@router.get("", response_model=list[GenerationResult])
async def list_generations(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's generations."""
    generations = db.query(Generation).filter(
        Generation.user_id == current_user.id,
    ).order_by(
        Generation.created_at.desc()
    ).offset(offset).limit(limit).all()

    return [
        GenerationResult(
            id=g.id,
            status=g.status.value,
            archetype=g.archetype,
            archetype_confidence=g.archetype_confidence,
            dsl=g.dsl,
            style=g.style,
            variations=g.variations,
            processing_time_ms=g.processing_time_ms,
            created_at=g.created_at.isoformat(),
            completed_at=g.completed_at.isoformat() if g.completed_at else None,
            error_message=g.error_message,
        )
        for g in generations
    ]


@router.post("/variations", response_model=GenerateResponse)
async def create_variations(
    request: VariationsRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _credits: None = Depends(check_credits),
):
    """Generate additional variations for an existing generation."""
    # Get original generation
    original = db.query(Generation).filter(
        Generation.id == request.generation_id,
        Generation.user_id == current_user.id,
    ).first()

    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original generation not found",
        )

    if original.status != GenerationStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Original generation not completed",
        )

    # Create new generation for variations
    generation = Generation(
        user_id=current_user.id,
        prompt=original.prompt,
        content=original.content,
        brand_colors=original.brand_colors,
        brand_fonts=original.brand_fonts,
        archetype=original.archetype,
        status=GenerationStatus.PENDING,
    )
    db.add(generation)

    # Record usage
    usage = UsageRecord(
        user_id=current_user.id,
        action="variations",
        credits_used=1,
        generation_id=generation.id,
    )
    db.add(usage)

    current_user.credits_remaining -= 1

    db.commit()
    db.refresh(generation)

    # Queue processing
    background_tasks.add_task(
        process_variations,
        generation_id=generation.id,
        original_dsl=original.dsl,
        archetype=original.archetype,
        count=request.count,
        strategy=request.strategy,
    )

    return GenerateResponse(
        id=generation.id,
        status=generation.status.value,
        archetype=original.archetype,
    )


@router.delete("/{generation_id}")
async def delete_generation(
    generation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a generation."""
    generation = db.query(Generation).filter(
        Generation.id == generation_id,
        Generation.user_id == current_user.id,
    ).first()

    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found",
        )

    db.delete(generation)
    db.commit()

    return {"status": "deleted"}


# Background task functions
async def process_generation(
    generation_id: str,
    prompt: str,
    content: list[dict] | None,
    brand_colors: list[str] | None,
    brand_fonts: list[str] | None,
    formality: str,
    num_variations: int,
):
    """Process generation in background."""
    from backend.db.base import SessionLocal
    from ml.inference import InferenceEngine

    db = SessionLocal()
    try:
        generation = db.query(Generation).filter(Generation.id == generation_id).first()
        if not generation:
            return

        start_time = datetime.utcnow()
        generation.status = GenerationStatus.PROCESSING
        db.commit()

        try:
            # Run inference
            engine = InferenceEngine(use_ml=False)  # Use fallbacks for now

            result = engine.generate(
                prompt=prompt,
                content=content,
                brand_colors=brand_colors,
                brand_fonts=brand_fonts,
                formality=formality,
            )

            # Generate variations if requested
            variations = None
            if num_variations > 1:
                variation_results = engine.generate_variations(
                    prompt=prompt,
                    count=num_variations,
                    content=content,
                    brand_colors=brand_colors,
                    brand_fonts=brand_fonts,
                    formality=formality,
                )
                variations = [v.dsl for v in variation_results]

            # Update generation record
            end_time = datetime.utcnow()
            generation.archetype = result.archetype
            generation.archetype_confidence = result.classification_confidence
            generation.dsl = result.dsl
            generation.style = {
                "color_palette": result.style.color_palette,
                "font_family": result.style.font_family,
                "corner_radius": result.style.corner_radius,
                "shadow": result.style.shadow,
                "glow": result.style.glow,
            }
            generation.variations = variations
            generation.status = GenerationStatus.COMPLETED
            generation.completed_at = end_time
            generation.processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

        except Exception as e:
            generation.status = GenerationStatus.FAILED
            generation.error_message = str(e)

        db.commit()

    finally:
        db.close()


async def process_variations(
    generation_id: str,
    original_dsl: dict,
    archetype: str,
    count: int,
    strategy: str,
):
    """Process variation generation in background."""
    from backend.db.base import SessionLocal
    from backend.creativity import VariationEngine

    db = SessionLocal()
    try:
        generation = db.query(Generation).filter(Generation.id == generation_id).first()
        if not generation:
            return

        start_time = datetime.utcnow()
        generation.status = GenerationStatus.PROCESSING
        db.commit()

        try:
            # Generate variations
            engine = VariationEngine()
            original_dsl["archetype"] = archetype

            results = engine.generate_variations(
                dsl=original_dsl,
                count=count,
                strategy=strategy,
            )

            # Update generation
            end_time = datetime.utcnow()
            generation.dsl = original_dsl
            generation.variations = [r.dsl for r in results]
            generation.status = GenerationStatus.COMPLETED
            generation.completed_at = end_time
            generation.processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

        except Exception as e:
            generation.status = GenerationStatus.FAILED
            generation.error_message = str(e)

        db.commit()

    finally:
        db.close()
