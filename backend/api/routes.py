"""API routes for Infographix."""

import io
import tempfile
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from backend.dsl.schema import GenerateRequest, GenerateResponse, SlideScene
from backend.renderer import PPTXWriter
from backend.constraints import ConstraintEngine, ArchetypeRules

router = APIRouter(tags=["generation"])

# Temporary storage for generated files (in production, use cloud storage)
_file_storage: dict[str, bytes] = {}


class RenderRequest(BaseModel):
    """Request to render a DSL scene to PPTX."""

    scenes: List[SlideScene]
    apply_constraints: bool = True
    apply_archetype_rules: bool = True


class RenderResponse(BaseModel):
    """Response from render endpoint."""

    file_id: str
    download_url: str
    validation_score: float
    violations_count: int


class ValidationRequest(BaseModel):
    """Request to validate a scene."""

    scene: SlideScene


class ValidationResponse(BaseModel):
    """Response from validation endpoint."""

    is_valid: bool
    score: float
    violations: list[dict]


@router.post("/generate", response_model=GenerateResponse)
async def generate_slide(request: GenerateRequest) -> GenerateResponse:
    """Generate an infographic slide from a prompt.

    Args:
        request: Generation request containing prompt and options.

    Returns:
        Generation response with slide data and download URL.
    """
    # TODO: Implement full generation pipeline
    # 1. Parse prompt with LLM
    # 2. Determine archetype
    # 3. Generate layout
    # 4. Render to PPTX

    return GenerateResponse(
        id="gen_placeholder",
        status="pending",
        message="Generation pipeline not yet implemented",
    )


@router.get("/generate/{generation_id}", response_model=GenerateResponse)
async def get_generation_status(generation_id: str) -> GenerateResponse:
    """Get the status of a generation request.

    Args:
        generation_id: The ID of the generation request.

    Returns:
        Current status of the generation.
    """
    # TODO: Implement status tracking
    raise HTTPException(status_code=404, detail="Generation not found")


@router.post("/parse", response_model=SlideScene)
async def parse_pptx(file: UploadFile = File(...)) -> SlideScene:
    """Parse a PPTX file and extract the DSL scene graph.

    Args:
        file: The PPTX file to parse.

    Returns:
        The extracted scene graph in DSL format.
    """
    if not file.filename or not file.filename.endswith(".pptx"):
        raise HTTPException(status_code=400, detail="File must be a .pptx file")

    # TODO: Implement PPTX parsing
    # 1. Save uploaded file
    # 2. Parse with python-pptx
    # 3. Extract shapes, styles, effects
    # 4. Return DSL

    raise HTTPException(status_code=501, detail="PPTX parsing not yet implemented")


@router.get("/templates")
async def list_templates() -> dict[str, list[dict[str, str]]]:
    """List available infographic templates.

    Returns:
        List of available templates with metadata.
    """
    # TODO: Implement template library
    return {
        "templates": [
            {"id": "funnel_basic", "name": "Basic Funnel", "category": "funnel"},
            {"id": "pyramid_3tier", "name": "3-Tier Pyramid", "category": "pyramid"},
            {"id": "timeline_horizontal", "name": "Horizontal Timeline", "category": "timeline"},
            {"id": "process_5step", "name": "5-Step Process", "category": "process"},
        ]
    }


@router.get("/downloads/{file_id}")
async def download_file(file_id: str) -> StreamingResponse:
    """Download a generated PPTX file.

    Args:
        file_id: The ID of the file to download.

    Returns:
        The PPTX file as a download.
    """
    if file_id not in _file_storage:
        raise HTTPException(status_code=404, detail="File not found")

    pptx_bytes = _file_storage[file_id]
    return StreamingResponse(
        io.BytesIO(pptx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="infographic_{file_id}.pptx"'},
    )


@router.post("/render", response_model=RenderResponse)
async def render_scenes(request: RenderRequest) -> RenderResponse:
    """Render DSL scenes to a PPTX file.

    Args:
        request: Render request containing scenes and options.

    Returns:
        Render response with file ID and download URL.
    """
    if not request.scenes:
        raise HTTPException(status_code=400, detail="At least one scene is required")

    engine = ConstraintEngine()
    total_score = 0.0
    total_violations = 0

    processed_scenes = []
    for scene in request.scenes:
        # Apply archetype rules if enabled
        if request.apply_archetype_rules:
            scene = ArchetypeRules.apply_rules(scene)

        # Apply constraint fixes if enabled
        if request.apply_constraints:
            scene = engine.fix(scene)

        # Validate and track score
        result = engine.validate(scene)
        total_score += result.score
        total_violations += len(result.violations)

        processed_scenes.append(scene)

    # Calculate average score
    avg_score = total_score / len(request.scenes)

    # Render to PPTX
    writer = PPTXWriter()
    pptx_bytes = writer.write(processed_scenes, None)

    if pptx_bytes is None:
        raise HTTPException(status_code=500, detail="Failed to generate PPTX")

    # Store the file
    file_id = str(uuid.uuid4())[:8]
    _file_storage[file_id] = pptx_bytes

    return RenderResponse(
        file_id=file_id,
        download_url=f"/api/downloads/{file_id}",
        validation_score=round(avg_score, 1),
        violations_count=total_violations,
    )


@router.post("/render/stream")
async def render_scenes_stream(request: RenderRequest) -> StreamingResponse:
    """Render DSL scenes and stream the PPTX directly.

    Args:
        request: Render request containing scenes and options.

    Returns:
        The PPTX file as a streaming response.
    """
    if not request.scenes:
        raise HTTPException(status_code=400, detail="At least one scene is required")

    engine = ConstraintEngine()
    processed_scenes = []

    for scene in request.scenes:
        if request.apply_archetype_rules:
            scene = ArchetypeRules.apply_rules(scene)
        if request.apply_constraints:
            scene = engine.fix(scene)
        processed_scenes.append(scene)

    writer = PPTXWriter()
    pptx_bytes = writer.write(processed_scenes, None)

    if pptx_bytes is None:
        raise HTTPException(status_code=500, detail="Failed to generate PPTX")

    return StreamingResponse(
        io.BytesIO(pptx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": 'attachment; filename="infographic.pptx"'},
    )


@router.post("/validate", response_model=ValidationResponse)
async def validate_scene(request: ValidationRequest) -> ValidationResponse:
    """Validate a DSL scene against layout constraints.

    Args:
        request: Validation request containing the scene.

    Returns:
        Validation response with score and violations.
    """
    engine = ConstraintEngine()
    result = engine.validate(request.scene)

    violations = [
        {
            "rule": v.rule,
            "message": v.message,
            "severity": v.severity,
            "shape_ids": v.shape_ids,
        }
        for v in result.violations
    ]

    return ValidationResponse(
        is_valid=result.is_valid,
        score=round(result.score, 1),
        violations=violations,
    )


@router.post("/fix", response_model=SlideScene)
async def fix_scene(scene: SlideScene) -> SlideScene:
    """Apply automatic fixes to a DSL scene.

    Args:
        scene: The scene to fix.

    Returns:
        The fixed scene.
    """
    engine = ConstraintEngine()

    # Apply archetype rules first
    if scene.metadata.archetype:
        scene = ArchetypeRules.apply_rules(scene)

    # Then apply constraint fixes
    fixed_scene = engine.fix(scene)

    return fixed_scene
