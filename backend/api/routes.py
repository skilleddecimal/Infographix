"""
routes.py — API endpoints for InfographAI.

Endpoints:
- POST /api/analyze     — Prompt -> InfographBrief (Claude reasoning)
- POST /api/generate    — Brief -> PositionedLayout -> PPTX file
- POST /api/preview     — Brief -> PositionedLayout -> SVG preview
- GET  /api/download/{id} — Download generated file
- GET  /api/archetypes  — List available archetype types
- GET  /api/brands      — List available brand presets
"""

import os
import uuid
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from .config import get_settings
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    GenerateRequest,
    GenerateResponse,
    PreviewRequest,
    PreviewResponse,
    ArchetypesResponse,
    ArchetypeInfo,
    BrandPresetsResponse,
    BrandPresetInfo,
    BriefSchema,
    EntitySchema,
    LayerSchema,
    ConnectionSchema,
)

# Import engine components
from ..engine.llm_reasoning import (
    analyze_prompt_sync,
    InfographBrief,
    EntityBrief,
    LayerBrief,
    ConnectionBrief,
    validate_brief,
    enhance_brief,
)
from ..engine.brand_engine import (
    get_brand_preset,
    list_brand_presets,
    generate_palette_from_primary,
    BRAND_PRESETS,
)
from ..engine.layout_engine import (
    LayoutEngine,
    ArchetypeType,
    list_available_archetypes,
)
from ..engine.data_models import (
    ColorPalette,
    DiagramInput,
    BlockData,
    LayerData,
    ConnectorData,
)
from ..engine.positioned import ConnectorStyle
from ..engine.pptx_renderer import PPTXRenderer
from ..engine.svg_renderer import SVGRenderer, render_to_data_uri


router = APIRouter(prefix="/api", tags=["infograph"])

# In-memory file registry (in production, use Redis or database)
_file_registry: Dict[str, Dict] = {}


# =============================================================================
# ANALYZE ENDPOINT
# =============================================================================

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyze a natural language prompt and return a structured diagram brief.

    Uses Claude to parse the prompt and extract:
    - Title and subtitle
    - Diagram type (archetype)
    - Entities/components
    - Layers and groupings
    - Connections between entities
    """
    settings = get_settings()

    if not settings.has_anthropic_key:
        raise HTTPException(
            status_code=503,
            detail="Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable."
        )

    try:
        # Decode image if provided
        image_bytes = None
        if request.image_base64:
            try:
                image_bytes = base64.b64decode(request.image_base64)
            except Exception as e:
                return AnalyzeResponse(
                    success=False,
                    error=f"Invalid base64 image: {str(e)}"
                )

        # Call LLM to analyze prompt
        brief = analyze_prompt_sync(
            prompt=request.prompt,
            image=image_bytes,
            api_key=settings.anthropic_api_key,
        )

        # Validate and enhance the brief
        warnings = validate_brief(brief)
        brief = enhance_brief(brief)

        # Convert to response schema
        brief_schema = _brief_to_schema(brief)

        return AnalyzeResponse(
            success=True,
            brief=brief_schema,
            warnings=warnings,
        )

    except Exception as e:
        return AnalyzeResponse(
            success=False,
            error=str(e),
        )


# =============================================================================
# GENERATE ENDPOINT
# =============================================================================

@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
    """
    Generate a PPTX file from a diagram brief.

    Takes the analyzed brief and renders it to PowerPoint format.
    Returns a file ID that can be used with /download endpoint.
    """
    settings = get_settings()

    try:
        # Determine color palette
        palette = None
        if request.brand_preset:
            palette = get_brand_preset(request.brand_preset)
            if not palette:
                return GenerateResponse(
                    success=False,
                    error=f"Unknown brand preset: {request.brand_preset}",
                )
        elif request.palette:
            palette = ColorPalette(
                primary=request.palette.primary,
                secondary=request.palette.secondary,
                tertiary=request.palette.tertiary,
                quaternary=request.palette.quaternary,
                background=request.palette.background,
                text_dark=request.palette.text_dark,
                text_light=request.palette.text_light,
                border=request.palette.border,
                connector=request.palette.connector,
            )
        elif request.brief.color_hint:
            palette = generate_palette_from_primary(request.brief.color_hint)
        elif request.brief.brand_hint:
            palette = get_brand_preset(request.brief.brand_hint)

        if not palette:
            palette = ColorPalette()

        # Convert brief schema to InfographBrief
        brief = _schema_to_brief(request.brief)

        # Convert to DiagramInput
        diagram_input = brief.to_diagram_input(palette)

        # Determine archetype type
        archetype_type = None
        for at in ArchetypeType:
            if at.value == brief.diagram_type:
                archetype_type = at
                break

        # Generate layout
        engine = LayoutEngine(default_palette=palette)
        result = engine.generate_layout(diagram_input, archetype_type)

        if not result.success:
            return GenerateResponse(
                success=False,
                error=result.error_message,
                warnings=result.warnings,
            )

        # Render to PPTX
        renderer = PPTXRenderer()
        pptx_bytes = renderer.render(result.layout)

        # Save to file
        file_id = str(uuid.uuid4())
        output_dir = Path(settings.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{file_id}.pptx"
        filepath = output_dir / filename

        with open(filepath, "wb") as f:
            f.write(pptx_bytes)

        # Register file
        _file_registry[file_id] = {
            "filepath": str(filepath),
            "filename": f"{_sanitize_filename(brief.title)}.pptx",
            "created_at": datetime.now().isoformat(),
        }

        return GenerateResponse(
            success=True,
            file_id=file_id,
            download_url=f"/api/download/{file_id}",
            warnings=result.warnings,
        )

    except Exception as e:
        return GenerateResponse(
            success=False,
            error=str(e),
        )


# =============================================================================
# DOWNLOAD ENDPOINT
# =============================================================================

@router.get("/download/{file_id}")
async def download(file_id: str):
    """
    Download a generated PPTX file by its ID.
    """
    if file_id not in _file_registry:
        raise HTTPException(status_code=404, detail="File not found")

    file_info = _file_registry[file_id]
    filepath = file_info["filepath"]

    if not os.path.exists(filepath):
        del _file_registry[file_id]
        raise HTTPException(status_code=404, detail="File no longer available")

    return FileResponse(
        path=filepath,
        filename=file_info["filename"],
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


# =============================================================================
# PREVIEW ENDPOINT
# =============================================================================

@router.post("/preview", response_model=PreviewResponse)
async def preview(request: PreviewRequest) -> PreviewResponse:
    """
    Generate an SVG preview of a diagram from a brief.

    Returns the SVG as a string or data URI, suitable for
    real-time preview in the frontend before generating PPTX.
    """
    try:
        # Determine color palette
        palette = None
        if request.brand_preset:
            palette = get_brand_preset(request.brand_preset)
            if not palette:
                return PreviewResponse(
                    success=False,
                    error=f"Unknown brand preset: {request.brand_preset}",
                )
        elif request.palette:
            palette = ColorPalette(
                primary=request.palette.primary,
                secondary=request.palette.secondary,
                tertiary=request.palette.tertiary,
                quaternary=request.palette.quaternary,
                background=request.palette.background,
                text_dark=request.palette.text_dark,
                text_light=request.palette.text_light,
                border=request.palette.border,
                connector=request.palette.connector,
            )
        elif request.brief.color_hint:
            palette = generate_palette_from_primary(request.brief.color_hint)
        elif request.brief.brand_hint:
            palette = get_brand_preset(request.brief.brand_hint)

        if not palette:
            palette = ColorPalette()

        # Convert brief schema to InfographBrief
        brief = _schema_to_brief(request.brief)

        # Convert to DiagramInput
        diagram_input = brief.to_diagram_input(palette)

        # Determine archetype type
        archetype_type = None
        for at in ArchetypeType:
            if at.value == brief.diagram_type:
                archetype_type = at
                break

        # Generate layout
        engine = LayoutEngine(default_palette=palette)
        result = engine.generate_layout(diagram_input, archetype_type)

        if not result.success:
            return PreviewResponse(
                success=False,
                error=result.error_message,
                warnings=result.warnings,
            )

        # Render to SVG
        renderer = SVGRenderer(include_fonts=True)

        if request.format == "data_uri":
            svg_output = render_to_data_uri(result.layout)
        else:
            svg_output = renderer.render(result.layout)

        # Calculate dimensions in pixels (96 DPI)
        width_px = int(result.layout.slide_width_inches * 96)
        height_px = int(result.layout.slide_height_inches * 96)

        return PreviewResponse(
            success=True,
            svg=svg_output,
            format=request.format,
            width=width_px,
            height=height_px,
            warnings=result.warnings,
        )

    except Exception as e:
        return PreviewResponse(
            success=False,
            error=str(e),
        )


# =============================================================================
# ARCHETYPES ENDPOINT
# =============================================================================

@router.get("/archetypes", response_model=ArchetypesResponse)
async def get_archetypes() -> ArchetypesResponse:
    """
    List all available diagram archetypes.
    """
    archetypes = list_available_archetypes()

    return ArchetypesResponse(
        archetypes=[
            ArchetypeInfo(
                type=a["type"],
                name=a["name"],
                display_name=a["display_name"],
                description=a["description"],
                example_prompts=a.get("example_prompts", []),
            )
            for a in archetypes
        ]
    )


# =============================================================================
# BRAND PRESETS ENDPOINT
# =============================================================================

@router.get("/brands", response_model=BrandPresetsResponse)
async def get_brands() -> BrandPresetsResponse:
    """
    List all available brand color presets.
    """
    presets = []
    for name in list_brand_presets():
        palette = BRAND_PRESETS[name]
        presets.append(BrandPresetInfo(
            name=name,
            primary=palette.primary,
            secondary=palette.secondary,
        ))

    return BrandPresetsResponse(presets=presets)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _brief_to_schema(brief: InfographBrief) -> BriefSchema:
    """Convert InfographBrief to BriefSchema."""
    return BriefSchema(
        title=brief.title,
        subtitle=brief.subtitle,
        diagram_type=brief.diagram_type,
        entities=[
            EntitySchema(
                id=e.id,
                label=e.label,
                description=e.description,
                layer_id=e.layer_id,
                icon_hint=e.icon_hint,
            )
            for e in brief.entities
        ],
        layers=[
            LayerSchema(
                id=l.id,
                label=l.label,
                entity_ids=l.entity_ids,
                is_cross_cutting=l.is_cross_cutting,
            )
            for l in brief.layers
        ],
        connections=[
            ConnectionSchema(
                from_id=c.from_id,
                to_id=c.to_id,
                label=c.label,
                style=c.style,
            )
            for c in brief.connections
        ],
        brand_hint=brief.brand_hint,
        color_hint=brief.color_hint,
        style_notes=brief.style_notes,
        confidence=brief.confidence,
    )


def _schema_to_brief(schema: BriefSchema) -> InfographBrief:
    """Convert BriefSchema to InfographBrief."""
    return InfographBrief(
        title=schema.title,
        subtitle=schema.subtitle,
        diagram_type=schema.diagram_type,
        entities=[
            EntityBrief(
                id=e.id,
                label=e.label,
                description=e.description,
                layer_id=e.layer_id,
                icon_hint=e.icon_hint,
            )
            for e in schema.entities
        ],
        layers=[
            LayerBrief(
                id=l.id,
                label=l.label,
                entity_ids=l.entity_ids,
                is_cross_cutting=l.is_cross_cutting,
            )
            for l in schema.layers
        ],
        connections=[
            ConnectionBrief(
                from_id=c.from_id,
                to_id=c.to_id,
                label=c.label,
                style=c.style,
            )
            for c in schema.connections
        ],
        brand_hint=schema.brand_hint,
        color_hint=schema.color_hint,
        style_notes=schema.style_notes,
        confidence=schema.confidence,
    )


def _sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '')

    # Limit length
    if len(name) > 100:
        name = name[:100]

    # Default if empty
    if not name.strip():
        name = "diagram"

    return name.strip()
