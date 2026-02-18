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
from typing import Dict, Optional

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
    SlideSchema,
    ExportRequest,
    ExportResponse,
    TemplateSchema,
    TemplateCategorySchema,
    TemplateTagSchema,
    TemplateListRequest,
    TemplateListResponse,
    TemplateCategoriesResponse,
    TemplateTagsResponse,
    TemplateDetailResponse,
    UseTemplateResponse,
    TrainFromPPTXRequest,
    TrainFromImageRequest,
    TrainResponse,
    ValidationResultSchema,
    ValidationIssueSchema,
)

# Import engine components
from ..engine.llm_reasoning import (
    analyze_prompt_sync,
    InfographBrief,
    EntityBrief,
    LayerBrief,
    ConnectionBrief,
    SlideBrief,
    validate_brief,
    enhance_brief,
)
from ..engine.brand_engine import (
    get_brand_preset,
    list_brand_presets,
    generate_palette_from_primary,
    BRAND_PRESETS,
)
from ..engine.template_library import (
    get_template,
    list_templates,
    get_categories,
    get_popular_tags,
    create_brief_from_template,
    TemplateCategory,
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
from ..engine.positioned import ConnectorStyle, MultiSlidePresentation
from ..engine.pptx_renderer import (
    PPTXRenderer,
    create_presentation_from_layouts,
    STYLE_FLAT,
    STYLE_SUBTLE_3D,
    STYLE_PROFESSIONAL,
    STYLE_EXECUTIVE,
    STYLE_PYRAMID_LEVEL,
)
from ..engine.svg_renderer import SVGRenderer, render_to_data_uri
from ..engine.design_learner import (
    StyleDatabase,
    PPTAnalyzer,
    ImageAnalyzer,
    DesignStyle,
)
from ..engine.visual_validator import (
    VisualValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
)
from ..engine.validation_feedback import (
    get_feedback_processor,
    ValidationFeedbackProcessor,
)


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

    Supports both single-slide and multi-slide presentations.
    For multi-slide, set is_multi_slide=True and populate the slides array.
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
            # Try to get brand preset, or generate from semantic hint
            palette = get_brand_preset(request.brief.brand_hint)
            if not palette:
                # Generate palette from semantic brand hint (e.g., "health" -> green)
                palette = _palette_from_semantic_hint(request.brief.brand_hint)

        if not palette:
            palette = ColorPalette()

        # Look up visual style if specified
        visual_style = None
        if request.visual_style_id:
            visual_style = _style_db.get_style(request.visual_style_id)
            if not visual_style:
                return GenerateResponse(
                    success=False,
                    error=f"Visual style not found: {request.visual_style_id}",
                )

        # Convert brief schema to InfographBrief
        brief = _schema_to_brief(request.brief)

        # Handle multi-slide presentations
        if brief.is_multi_slide and brief.slides:
            return await _generate_multi_slide(brief, palette, settings, visual_style)

        # Single slide generation (original logic)
        # Convert to DiagramInput
        diagram_input = brief.to_diagram_input(palette)

        # Determine archetype type
        archetype_type = None
        for at in ArchetypeType:
            if at.value == brief.diagram_type:
                archetype_type = at
                break

        # Get feedback processor for learning and auto-correction
        feedback_processor = get_feedback_processor()

        # Get preventive adjustments based on past learning
        preventive_adjustments = feedback_processor.get_preventive_adjustments(
            brief.diagram_type
        )

        # Generation loop with validation feedback
        max_attempts = 2
        attempt = 0
        validation_result = None
        val_result = None
        corrections_applied = []
        all_warnings = []

        engine = LayoutEngine(default_palette=palette)

        while attempt < max_attempts:
            attempt += 1

            # Apply adjustments (preventive on first attempt, corrective on retry)
            layout_adjustments = preventive_adjustments if attempt == 1 else {}
            if attempt > 1 and corrections_applied:
                # Apply corrections from previous validation
                layout_adjustments = feedback_processor.correction_engine.generate_layout_adjustments(
                    [feedback_processor.correction_engine.CORRECTION_STRATEGIES.get(cat, [{}])[0]
                     for cat in set(i.category for i in val_result.issues
                                   if i.severity in [ValidationSeverity.ERROR, ValidationSeverity.WARNING])
                     if cat in feedback_processor.correction_engine.CORRECTION_STRATEGIES],
                    brief.diagram_type,
                )

            # Generate layout
            # Note: layout_adjustments are computed for future use when
            # the layout engine supports dynamic adjustment parameters
            result = engine.generate_layout(diagram_input, archetype_type)

            if not result.success:
                return GenerateResponse(
                    success=False,
                    error=result.error_message,
                    warnings=result.warnings,
                )

            all_warnings.extend(result.warnings)

            # Render to PPTX with visual style
            renderer = PPTXRenderer(visual_style=visual_style)
            pptx_bytes = renderer.render(result.layout)

            # Save to file
            file_id = str(uuid.uuid4())
            output_dir = Path(settings.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{file_id}.pptx"
            filepath = output_dir / filename

            with open(filepath, "wb") as f:
                f.write(pptx_bytes)

            # Visual validation (if Anthropic API is configured)
            if not settings.has_anthropic_key:
                break  # No validation available

            try:
                import anthropic
                client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                validator = VisualValidator(anthropic_client=client)
                val_result = validator.validate_pptx(
                    pptx_path=str(filepath),
                    context=request.brief.title,
                )

                # Process validation and decide if retry needed
                should_retry, adjustments, correction_names = feedback_processor.process_validation(
                    validation_result=val_result,
                    diagram_type=brief.diagram_type,
                    title=brief.title,
                    attempt=attempt,
                )

                if should_retry and attempt < max_attempts:
                    corrections_applied = correction_names
                    all_warnings.append(
                        f"Auto-correcting: applying {', '.join(correction_names)}"
                    )
                    # Delete the failed file before retry
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass
                    continue  # Retry with corrections

                # Convert to response schema
                validation_result = ValidationResultSchema(
                    is_valid=val_result.is_valid,
                    score=val_result.score,
                    summary=val_result.summary + (
                        f" (after {attempt} attempt(s))" if attempt > 1 else ""
                    ),
                    issues=[
                        ValidationIssueSchema(
                            severity=issue.severity.value,
                            category=issue.category,
                            message=issue.message,
                            suggestion=issue.suggestion,
                            location=issue.location,
                        )
                        for issue in val_result.issues
                    ],
                )
                break  # Validation complete

            except Exception as e:
                # Validation failed; log but don't fail generation
                import logging
                logging.getLogger(__name__).warning(f"Visual validation failed: {e}")
                break

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
            slide_count=1,
            warnings=all_warnings,
            validation=validation_result,
        )

    except Exception as e:
        return GenerateResponse(
            success=False,
            error=str(e),
        )


async def _generate_multi_slide(
    brief: InfographBrief,
    palette: ColorPalette,
    settings,
    visual_style=None
) -> GenerateResponse:
    """Generate a multi-slide PPTX presentation."""
    all_warnings = []
    layouts = []

    # Generate layout for each slide
    engine = LayoutEngine(default_palette=palette)

    for slide_brief in brief.slides:
        # Convert slide to single brief
        single_brief = slide_brief.to_brief()

        # Convert to DiagramInput
        diagram_input = single_brief.to_diagram_input(palette)

        # Determine archetype type
        archetype_type = None
        for at in ArchetypeType:
            if at.value == single_brief.diagram_type:
                archetype_type = at
                break

        # Generate layout
        result = engine.generate_layout(diagram_input, archetype_type)

        if not result.success:
            return GenerateResponse(
                success=False,
                error=f"Slide {slide_brief.slide_number}: {result.error_message}",
                warnings=all_warnings + result.warnings,
            )

        # Add speaker notes if present
        if slide_brief.speaker_notes:
            result.layout.speaker_notes = slide_brief.speaker_notes

        layouts.append(result.layout)
        all_warnings.extend([f"Slide {slide_brief.slide_number}: {w}" for w in result.warnings])

    # Create multi-slide presentation
    presentation = create_presentation_from_layouts(layouts, brief.title)

    # Render to PPTX with visual style
    renderer = PPTXRenderer(visual_style=visual_style)
    pptx_bytes = renderer.render_presentation(presentation)

    # Save to file
    file_id = str(uuid.uuid4())
    output_dir = Path(settings.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{file_id}.pptx"
    filepath = output_dir / filename

    with open(filepath, "wb") as f:
        f.write(pptx_bytes)

    # Visual validation (optional, runs if Anthropic API is configured)
    validation_result = None
    if settings.has_anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            validator = VisualValidator(anthropic_client=client)
            val_result = validator.validate_pptx(
                pptx_path=str(filepath),
                context=brief.title,
            )
            validation_result = ValidationResultSchema(
                is_valid=val_result.is_valid,
                score=val_result.score,
                summary=val_result.summary,
                issues=[
                    ValidationIssueSchema(
                        severity=issue.severity.value,
                        category=issue.category,
                        message=issue.message,
                        suggestion=issue.suggestion,
                        location=issue.location,
                    )
                    for issue in val_result.issues
                ],
            )
        except Exception as e:
            # Validation is optional; log but don't fail
            import logging
            logging.getLogger(__name__).warning(f"Visual validation failed: {e}")

    # Register file
    _file_registry[file_id] = {
        "filepath": str(filepath),
        "filename": f"{_sanitize_filename(brief.title)}.pptx",
        "created_at": datetime.now().isoformat(),
        "slide_count": len(layouts),
    }

    return GenerateResponse(
        success=True,
        file_id=file_id,
        download_url=f"/api/download/{file_id}",
        slide_count=len(layouts),
        warnings=all_warnings,
        validation=validation_result,
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
            # Try to get brand preset, or generate from semantic hint
            palette = get_brand_preset(request.brief.brand_hint)
            if not palette:
                # Generate palette from semantic brand hint (e.g., "health" -> green)
                palette = _palette_from_semantic_hint(request.brief.brand_hint)

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
    # Convert slides if present
    slides = []
    for s in brief.slides:
        slides.append(SlideSchema(
            slide_number=s.slide_number,
            title=s.title,
            subtitle=s.subtitle,
            diagram_type=s.diagram_type,
            entities=[
                EntitySchema(
                    id=e.id,
                    label=e.label,
                    description=e.description,
                    layer_id=e.layer_id,
                    icon_hint=e.icon_hint,
                )
                for e in s.entities
            ],
            layers=[
                LayerSchema(
                    id=l.id,
                    label=l.label,
                    entity_ids=l.entity_ids,
                    is_cross_cutting=l.is_cross_cutting,
                )
                for l in s.layers
            ],
            connections=[
                ConnectionSchema(
                    from_id=c.from_id,
                    to_id=c.to_id,
                    label=c.label,
                    style=c.style,
                )
                for c in s.connections
            ],
            speaker_notes=s.speaker_notes,
            transition=s.transition,
        ))

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
        slides=slides,
        is_multi_slide=brief.is_multi_slide,
    )


def _schema_to_brief(schema: BriefSchema) -> InfographBrief:
    """Convert BriefSchema to InfographBrief."""
    # Convert slides if present
    slides = []
    for s in schema.slides:
        slides.append(SlideBrief(
            slide_number=s.slide_number,
            title=s.title,
            subtitle=s.subtitle,
            diagram_type=s.diagram_type,
            entities=[
                EntityBrief(
                    id=e.id,
                    label=e.label,
                    description=e.description,
                    layer_id=e.layer_id,
                    icon_hint=e.icon_hint,
                )
                for e in s.entities
            ],
            layers=[
                LayerBrief(
                    id=l.id,
                    label=l.label,
                    entity_ids=l.entity_ids,
                    is_cross_cutting=l.is_cross_cutting,
                )
                for l in s.layers
            ],
            connections=[
                ConnectionBrief(
                    from_id=c.from_id,
                    to_id=c.to_id,
                    label=c.label,
                    style=c.style,
                )
                for c in s.connections
            ],
            speaker_notes=s.speaker_notes,
            transition=s.transition,
        ))

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
        slides=slides,
        is_multi_slide=schema.is_multi_slide,
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


def _palette_from_semantic_hint(hint: str) -> Optional[ColorPalette]:
    """
    Generate a color palette from a semantic brand hint.

    Maps common semantic hints to appropriate color schemes.
    E.g., "health" -> green, "finance" -> blue, "energy" -> orange
    """
    hint_lower = hint.lower().strip()

    # Semantic color mappings
    semantic_colors = {
        # Health & wellness
        "health": "#4CAF50",      # Green
        "wellness": "#66BB6A",
        "medical": "#26A69A",
        "healthcare": "#00897B",
        "nutrition": "#8BC34A",
        "fitness": "#7CB342",
        "organic": "#689F38",
        "eco": "#558B2F",
        "nature": "#43A047",

        # Finance & business
        "finance": "#1976D2",     # Blue
        "business": "#0D47A1",
        "corporate": "#1565C0",
        "banking": "#0277BD",
        "investment": "#01579B",
        "professional": "#455A64",

        # Technology
        "tech": "#7C4DFF",        # Purple
        "technology": "#651FFF",
        "digital": "#536DFE",
        "software": "#304FFE",
        "ai": "#6200EA",
        "data": "#3D5AFE",

        # Energy & power
        "energy": "#FF9800",      # Orange
        "power": "#F57C00",
        "electric": "#FFB300",
        "solar": "#FFC107",

        # Safety & warning
        "safety": "#F44336",      # Red
        "warning": "#E53935",
        "alert": "#D32F2F",
        "emergency": "#C62828",

        # Education
        "education": "#3F51B5",   # Indigo
        "learning": "#5C6BC0",
        "academic": "#303F9F",
        "school": "#3949AB",

        # Creative
        "creative": "#E91E63",    # Pink
        "design": "#AD1457",
        "art": "#C2185B",
        "media": "#D81B60",
    }

    # Check for exact match
    if hint_lower in semantic_colors:
        return generate_palette_from_primary(semantic_colors[hint_lower])

    # Check for partial match
    for key, color in semantic_colors.items():
        if key in hint_lower or hint_lower in key:
            return generate_palette_from_primary(color)

    # No match found
    return None


# =============================================================================
# EXPORT ENDPOINT (Canvas to PPTX)
# =============================================================================

@router.post("/export", response_model=ExportResponse)
async def export_canvas(request: ExportRequest) -> ExportResponse:
    """
    Export an edited Fabric.js canvas to PPTX.

    Takes the canvas JSON and converts it back to a PowerPoint file.
    This allows users to edit diagrams in the browser and then export
    their changes to PPTX.
    """
    settings = get_settings()

    try:
        from ..engine.canvas_renderer import render_canvas_to_pptx

        # Render canvas to PPTX
        pptx_bytes = render_canvas_to_pptx(
            canvas_json=request.canvas_json.model_dump(),
            title=request.title
        )

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
            "filename": f"{_sanitize_filename(request.title)}.pptx",
            "created_at": datetime.now().isoformat(),
        }

        return ExportResponse(
            success=True,
            file_id=file_id,
            download_url=f"/api/download/{file_id}",
        )

    except Exception as e:
        return ExportResponse(
            success=False,
            error=str(e),
        )


# =============================================================================
# TEMPLATE LIBRARY ENDPOINTS
# =============================================================================

@router.get("/templates", response_model=TemplateListResponse)
async def templates_list(
    category: str = None,
    tags: str = None,
    search: str = None,
) -> TemplateListResponse:
    """
    List available diagram templates.

    Optional filters:
    - category: Filter by template category
    - tags: Comma-separated list of tags to filter by
    - search: Search in template name and description
    """
    try:
        # Parse category
        cat_enum = None
        if category:
            try:
                cat_enum = TemplateCategory(category)
            except ValueError:
                return TemplateListResponse(
                    success=False,
                    error=f"Invalid category: {category}",
                )

        # Parse tags
        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        # Get templates
        templates = list_templates(
            category=cat_enum,
            tags=tag_list,
            search=search,
        )

        # Convert to schema
        template_schemas = [
            TemplateSchema(
                id=t.id,
                name=t.name,
                description=t.description,
                category=t.category.value,
                thumbnail_url=t.thumbnail_url,
                tags=t.tags,
                brief=_brief_to_schema(t.brief),
                popularity=t.popularity,
                is_premium=t.is_premium,
            )
            for t in templates
        ]

        return TemplateListResponse(
            success=True,
            templates=template_schemas,
            total=len(template_schemas),
        )

    except Exception as e:
        return TemplateListResponse(
            success=False,
            error=str(e),
        )


@router.get("/templates/categories", response_model=TemplateCategoriesResponse)
async def templates_categories() -> TemplateCategoriesResponse:
    """Get all template categories with counts."""
    try:
        categories = get_categories()

        return TemplateCategoriesResponse(
            success=True,
            categories=[
                TemplateCategorySchema(**cat)
                for cat in categories
            ],
        )

    except Exception as e:
        return TemplateCategoriesResponse(
            success=False,
            categories=[],
        )


@router.get("/templates/tags", response_model=TemplateTagsResponse)
async def templates_tags(limit: int = 20) -> TemplateTagsResponse:
    """Get popular template tags."""
    try:
        tags = get_popular_tags(limit=limit)

        return TemplateTagsResponse(
            success=True,
            tags=[
                TemplateTagSchema(**tag)
                for tag in tags
            ],
        )

    except Exception as e:
        return TemplateTagsResponse(
            success=False,
            tags=[],
        )


@router.get("/templates/{template_id}", response_model=TemplateDetailResponse)
async def template_detail(template_id: str) -> TemplateDetailResponse:
    """Get a specific template by ID."""
    try:
        template = get_template(template_id)

        if not template:
            return TemplateDetailResponse(
                success=False,
                error=f"Template not found: {template_id}",
            )

        return TemplateDetailResponse(
            success=True,
            template=TemplateSchema(
                id=template.id,
                name=template.name,
                description=template.description,
                category=template.category.value,
                thumbnail_url=template.thumbnail_url,
                tags=template.tags,
                brief=_brief_to_schema(template.brief),
                popularity=template.popularity,
                is_premium=template.is_premium,
            ),
        )

    except Exception as e:
        return TemplateDetailResponse(
            success=False,
            error=str(e),
        )


@router.post("/templates/{template_id}/use", response_model=UseTemplateResponse)
async def use_template(template_id: str) -> UseTemplateResponse:
    """
    Create a new brief from a template.

    Returns a copy of the template's brief that can be customized
    and then sent to /api/generate.
    """
    try:
        brief = create_brief_from_template(template_id)

        if not brief:
            return UseTemplateResponse(
                success=False,
                error=f"Template not found: {template_id}",
            )

        return UseTemplateResponse(
            success=True,
            brief=_brief_to_schema(brief),
        )

    except Exception as e:
        return UseTemplateResponse(
            success=False,
            error=str(e),
        )


# =============================================================================
# DESIGN LEARNING / TRAINING ENDPOINTS
# =============================================================================

# Initialize style database (in production, use persistent storage path)
_style_db = StyleDatabase()
_ppt_analyzer = PPTAnalyzer()
_image_analyzer = ImageAnalyzer()


@router.post("/train/pptx", response_model=TrainResponse)
async def train_from_pptx(request: TrainFromPPTXRequest) -> TrainResponse:
    """
    Learn design patterns from a PowerPoint file.

    Analyzes the PPTX to extract:
    - Color palettes
    - Font styles and typography
    - Shape styles (shadows, gradients, borders)
    - Layout patterns

    The learned style is stored and can be applied to future generations.
    """
    settings = get_settings()

    try:
        # Decode file
        try:
            file_bytes = base64.b64decode(request.file_base64)
        except Exception as e:
            return TrainResponse(
                success=False,
                error=f"Invalid base64 file: {str(e)}"
            )

        # Save temp file for analysis
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            # Analyze the PPTX
            style = _ppt_analyzer.analyze_pptx(tmp_path)

            # Update style metadata
            style.name = request.style_name
            style.description = request.description
            style.tags = [t.strip() for t in request.tags.split(",") if t.strip()]

            # Store in database
            _style_db.add_style(style)

            # Get font info
            fonts = []
            if style.typography:
                if style.typography.title_font:
                    fonts.append(style.typography.title_font)
                if style.typography.body_font and style.typography.body_font not in fonts:
                    fonts.append(style.typography.body_font)

            return TrainResponse(
                success=True,
                style_id=style.id,
                style_name=style.name,
                extracted={
                    "colors": len(style.palette.accent_colors) if style.palette and style.palette.accent_colors else 0,
                    "fonts": fonts,
                    "shadow_detected": style.shape_style.shadow is not None if style.shape_style else False,
                    "gradient_detected": style.shape_style.gradient is not None if style.shape_style else False,
                }
            )
        finally:
            # Clean up temp file
            import os
            os.unlink(tmp_path)

    except Exception as e:
        return TrainResponse(
            success=False,
            error=str(e)
        )


@router.post("/train/image", response_model=TrainResponse)
async def train_from_image(request: TrainFromImageRequest) -> TrainResponse:
    """
    Learn design patterns from an image using Claude Vision.

    Analyzes the image to extract:
    - Color schemes
    - Visual style characteristics
    - Layout patterns
    - Typography suggestions
    """
    settings = get_settings()

    if not settings.has_anthropic_key:
        return TrainResponse(
            success=False,
            error="Anthropic API key not configured for image analysis"
        )

    try:
        # Decode image
        try:
            image_bytes = base64.b64decode(request.image_base64)
        except Exception as e:
            return TrainResponse(
                success=False,
                error=f"Invalid base64 image: {str(e)}"
            )

        # Save temp file for analysis
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        try:
            # Initialize analyzer with API key
            analyzer = ImageAnalyzer(api_key=settings.anthropic_api_key)

            # Analyze the image
            import asyncio
            style = asyncio.run(analyzer.analyze_image(tmp_path))

            # Update style metadata
            style.name = request.style_name
            style.description = request.description
            style.tags = [t.strip() for t in request.tags.split(",") if t.strip()]

            # Store in database
            _style_db.add_style(style)

            return TrainResponse(
                success=True,
                style_id=style.id,
                style_name=style.name,
                extracted={
                    "colors": len(style.palette.accent_colors) if style.palette and style.palette.accent_colors else 0,
                    "shadow_detected": style.shape_style.shadow is not None if style.shape_style else False,
                    "gradient_detected": style.shape_style.gradient is not None if style.shape_style else False,
                }
            )
        finally:
            # Clean up temp file
            import os
            os.unlink(tmp_path)

    except Exception as e:
        return TrainResponse(
            success=False,
            error=str(e)
        )


@router.get("/styles/presets")
async def list_style_presets():
    """
    List available visual style presets.

    These are built-in styles that can be applied to diagrams.
    """
    return {
        "success": True,
        "presets": [
            {
                "id": "flat",
                "name": "Flat",
                "description": "Clean, minimal design without shadows or gradients",
                "has_shadow": False,
                "has_gradient": False,
            },
            {
                "id": "subtle_3d",
                "name": "Subtle 3D",
                "description": "Subtle shadows and gradients for depth",
                "has_shadow": True,
                "has_gradient": True,
            },
            {
                "id": "professional",
                "name": "Professional",
                "description": "Balanced design with moderate effects and bevels",
                "has_shadow": True,
                "has_gradient": True,
            },
            {
                "id": "executive",
                "name": "Executive",
                "description": "Bold, high-impact design with strong effects",
                "has_shadow": True,
                "has_gradient": True,
            },
            {
                "id": "pyramid",
                "name": "Pyramid",
                "description": "Optimized for pyramid/hierarchy diagrams with trapezoid shapes",
                "has_shadow": True,
                "has_gradient": True,
            },
        ]
    }


@router.get("/styles")
async def list_styles(tags: str = None):
    """
    List all learned design styles.

    Args:
        tags: Optional comma-separated tags to filter by
    """
    try:
        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        styles = _style_db.list_styles(tags=tag_list)

        return {
            "success": True,
            "styles": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "tags": s.tags,
                    "source": s.source,
                    "created_at": s.created_at,
                    "has_shadow": s.shape_style.shadow is not None if s.shape_style else False,
                    "has_gradient": s.shape_style.gradient is not None if s.shape_style else False,
                    "color_count": len(s.palette.accent_colors) if s.palette and s.palette.accent_colors else 0,
                }
                for s in styles
            ],
            "total": len(styles),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/styles/{style_id}")
async def get_style(style_id: str):
    """Get a specific learned style by ID."""
    try:
        style = _style_db.get_style(style_id)

        if not style:
            return {
                "success": False,
                "error": f"Style not found: {style_id}"
            }

        shadow = style.shape_style.shadow if style.shape_style else None
        gradient = style.shape_style.gradient if style.shape_style else None

        return {
            "success": True,
            "style": {
                "id": style.id,
                "name": style.name,
                "description": style.description,
                "tags": style.tags,
                "source": style.source,
                "created_at": style.created_at,
                "palette": {
                    "colors": style.palette.accent_colors if style.palette and style.palette.accent_colors else [],
                    "primary": style.palette.primary if style.palette else None,
                    "secondary": style.palette.secondary if style.palette else None,
                },
                "shadow": {
                    "enabled": shadow.enabled if shadow else False,
                    "blur": shadow.blur_radius_pt if shadow else 0,
                    "opacity": shadow.opacity if shadow else 0,
                } if shadow else None,
                "gradient": {
                    "type": gradient.type.value if gradient else None,
                    "angle": gradient.angle_degrees if gradient else None,
                } if gradient else None,
                "typography": style.typography.to_dict() if style.typography else {},
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.delete("/styles/{style_id}")
async def delete_style(style_id: str):
    """Delete a learned style."""
    try:
        # Check if it's a built-in style
        if style_id.startswith("builtin_"):
            return {
                "success": False,
                "error": "Cannot delete built-in styles"
            }

        style = _style_db.get_style(style_id)
        if not style:
            return {
                "success": False,
                "error": f"Style not found: {style_id}"
            }

        _style_db.delete_style(style_id)

        return {
            "success": True,
            "message": f"Style '{style.name}' deleted"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# =============================================================================
# VALIDATION LEARNING ENDPOINTS
# =============================================================================

@router.get("/validation/stats")
async def get_validation_stats():
    """
    Get statistics about what the validation system has learned.

    Returns:
    - Total validations performed
    - Common issues by diagram type
    - Effective corrections and their success rates
    """
    try:
        processor = get_feedback_processor()
        stats = processor.get_learning_stats()

        return {
            "success": True,
            "stats": {
                "total_validations": stats["total_validations"],
                "issue_patterns": stats["issue_patterns"],
                "effective_corrections": [
                    {"correction": c[0], "avg_improvement": round(c[1], 2)}
                    for c in stats["effective_corrections"]
                ],
                "validations_by_type": stats["entries_by_type"],
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/validation/issues/{diagram_type}")
async def get_common_issues(diagram_type: str, top_n: int = 5):
    """
    Get the most common validation issues for a specific diagram type.

    This helps understand what issues are most frequently detected
    and can inform improvements to the generation system.
    """
    try:
        processor = get_feedback_processor()
        common_issues = processor.learning_db.get_common_issues(diagram_type, top_n)

        return {
            "success": True,
            "diagram_type": diagram_type,
            "common_issues": [
                {"category": issue[0], "count": issue[1]}
                for issue in common_issues
            ],
            "preventive_adjustments": processor.get_preventive_adjustments(diagram_type),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
