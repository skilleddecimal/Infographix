"""
schemas.py — Pydantic request/response models for the API.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# =============================================================================
# REQUEST MODELS
# =============================================================================

class AnalyzeRequest(BaseModel):
    """Request to analyze a prompt and generate an InfographBrief."""
    prompt: str = Field(..., description="Natural language diagram description")
    image_base64: Optional[str] = Field(
        None, description="Optional base64-encoded image for vision analysis"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Create a 3-tier web architecture with React frontend, Node.js API, and PostgreSQL database"
            }
        }


class EntitySchema(BaseModel):
    """Entity in a diagram."""
    id: str
    label: str
    description: Optional[str] = None
    layer_id: Optional[str] = None
    icon_hint: Optional[str] = None


class LayerSchema(BaseModel):
    """Layer grouping entities."""
    id: str
    label: str
    entity_ids: List[str] = Field(default_factory=list)
    is_cross_cutting: bool = False


class ConnectionSchema(BaseModel):
    """Connection between entities."""
    from_id: str
    to_id: str
    label: Optional[str] = None
    style: str = "arrow"


class ColorPaletteSchema(BaseModel):
    """Color palette for the diagram."""
    primary: str = "#0073E6"
    secondary: str = "#00A3E0"
    tertiary: str = "#6CC24A"
    quaternary: str = "#FFB81C"
    background: str = "#FFFFFF"
    text_dark: str = "#333333"
    text_light: str = "#FFFFFF"
    border: str = "#CCCCCC"
    connector: str = "#666666"


class SlideSchema(BaseModel):
    """A single slide within a multi-slide presentation."""
    slide_number: int = 1
    title: str = ""
    subtitle: Optional[str] = None
    diagram_type: str = "marketecture"
    entities: List[EntitySchema] = Field(default_factory=list)
    layers: List[LayerSchema] = Field(default_factory=list)
    connections: List[ConnectionSchema] = Field(default_factory=list)
    speaker_notes: Optional[str] = None
    transition: Optional[str] = None  # fade, slide, none


class BriefSchema(BaseModel):
    """Complete diagram brief specification.

    For single-slide diagrams, use entities/layers/connections directly.
    For multi-slide presentations, populate the `slides` list and set `is_multi_slide=True`.
    """
    title: str
    subtitle: Optional[str] = None
    diagram_type: str = "marketecture"
    entities: List[EntitySchema] = Field(default_factory=list)
    layers: List[LayerSchema] = Field(default_factory=list)
    connections: List[ConnectionSchema] = Field(default_factory=list)
    brand_hint: Optional[str] = None
    color_hint: Optional[str] = None
    style_notes: Optional[str] = None
    confidence: float = 1.0
    # Multi-slide support
    slides: List[SlideSchema] = Field(default_factory=list)
    is_multi_slide: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Web Application Architecture",
                "subtitle": "3-Tier Design",
                "diagram_type": "marketecture",
                "entities": [
                    {"id": "react", "label": "React", "layer_id": "frontend"},
                    {"id": "nodejs", "label": "Node.js API", "layer_id": "backend"},
                    {"id": "postgres", "label": "PostgreSQL", "layer_id": "database"},
                ],
                "layers": [
                    {"id": "frontend", "label": "Frontend", "entity_ids": ["react"]},
                    {"id": "backend", "label": "Backend", "entity_ids": ["nodejs"]},
                    {"id": "database", "label": "Database", "entity_ids": ["postgres"]},
                ],
                "connections": [
                    {"from_id": "react", "to_id": "nodejs", "style": "arrow"},
                    {"from_id": "nodejs", "to_id": "postgres", "style": "arrow"},
                ],
            }
        }


class GenerateRequest(BaseModel):
    """Request to generate a PPTX file from a brief."""
    brief: BriefSchema
    palette: Optional[ColorPaletteSchema] = None
    brand_preset: Optional[str] = Field(
        None, description="Name of brand preset (e.g., 'microsoft', 'opentext')"
    )
    visual_style_id: Optional[str] = Field(
        None, description="ID of learned visual style to apply (shadows, gradients, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "brief": {
                    "title": "My Architecture",
                    "diagram_type": "marketecture",
                    "entities": [
                        {"id": "a", "label": "Component A"},
                        {"id": "b", "label": "Component B"},
                    ],
                },
                "brand_preset": "opentext",
                "visual_style_id": "learned_abc123",
            }
        }


class PreviewRequest(BaseModel):
    """Request to generate an SVG preview from a brief."""
    brief: BriefSchema
    palette: Optional[ColorPaletteSchema] = None
    brand_preset: Optional[str] = Field(
        None, description="Name of brand preset (e.g., 'microsoft', 'opentext')"
    )
    visual_style_id: Optional[str] = Field(
        None, description="ID of learned visual style to apply (shadows, gradients, etc.)"
    )
    format: str = Field(
        "svg",
        description="Output format: 'svg' for raw SVG string, 'data_uri' for data URI"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "brief": {
                    "title": "My Architecture",
                    "diagram_type": "marketecture",
                    "entities": [
                        {"id": "a", "label": "Component A"},
                        {"id": "b", "label": "Component B"},
                    ],
                },
                "brand_preset": "opentext",
                "visual_style_id": "learned_abc123",
                "format": "svg",
            }
        }


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class AnalyzeResponse(BaseModel):
    """Response from analyze endpoint."""
    success: bool
    brief: Optional[BriefSchema] = None
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class ValidationIssueSchema(BaseModel):
    """A single validation issue found during visual review."""
    severity: str = Field(..., description="Severity level: error, warning, or info")
    category: str = Field(..., description="Issue category: text_alignment, color_contrast, etc.")
    message: str = Field(..., description="Description of the issue")
    suggestion: Optional[str] = Field(None, description="Suggested fix")
    location: Optional[str] = Field(None, description="Location in the presentation")


class ValidationResultSchema(BaseModel):
    """Visual validation result for a PPTX file."""
    is_valid: bool = Field(..., description="Whether the file passed validation")
    score: float = Field(..., description="Quality score from 0-100")
    summary: str = Field("", description="Human-readable summary")
    issues: List[ValidationIssueSchema] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    """Response from generate endpoint."""
    success: bool
    file_id: Optional[str] = None
    download_url: Optional[str] = None
    slide_count: int = 1
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    validation: Optional[ValidationResultSchema] = Field(
        None, description="Visual validation results (if enabled)"
    )


class PreviewResponse(BaseModel):
    """Response from preview endpoint."""
    success: bool
    svg: Optional[str] = Field(None, description="SVG content or data URI")
    format: str = "svg"
    width: Optional[int] = None
    height: Optional[int] = None
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class ArchetypeInfo(BaseModel):
    """Information about an available archetype."""
    type: str
    name: str
    display_name: str
    description: str
    example_prompts: List[str] = Field(default_factory=list)


class ArchetypesResponse(BaseModel):
    """Response listing available archetypes."""
    archetypes: List[ArchetypeInfo]


class BrandPresetInfo(BaseModel):
    """Information about a brand preset."""
    name: str
    primary: str
    secondary: str


class BrandPresetsResponse(BaseModel):
    """Response listing available brand presets."""
    presets: List[BrandPresetInfo]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    anthropic_configured: bool


# =============================================================================
# EDITOR EXPORT MODELS
# =============================================================================

class CanvasObjectSchema(BaseModel):
    """A single object from Fabric.js canvas."""
    type: str
    left: Optional[float] = None
    top: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    fill: Optional[str] = None
    stroke: Optional[str] = None
    strokeWidth: Optional[float] = None
    text: Optional[str] = None
    fontSize: Optional[float] = None
    fontFamily: Optional[str] = None
    fontWeight: Optional[str] = None
    angle: Optional[float] = 0
    scaleX: Optional[float] = 1
    scaleY: Optional[float] = 1
    # Allow additional properties from Fabric.js

    class Config:
        extra = "allow"


class CanvasJsonSchema(BaseModel):
    """Fabric.js canvas JSON export format."""
    version: Optional[str] = None
    objects: List[CanvasObjectSchema] = Field(default_factory=list)
    background: Optional[str] = None

    class Config:
        extra = "allow"


class ExportRequest(BaseModel):
    """Request to export edited canvas to PPTX."""
    canvas_json: CanvasJsonSchema = Field(..., description="Fabric.js canvas JSON")
    title: str = Field("Edited Diagram", description="Title for the exported file")

    class Config:
        json_schema_extra = {
            "example": {
                "canvas_json": {
                    "version": "5.3.0",
                    "objects": [
                        {"type": "rect", "left": 100, "top": 100, "width": 200, "height": 100, "fill": "#0073E6"}
                    ],
                    "background": "#ffffff"
                },
                "title": "My Edited Diagram"
            }
        }


class ExportResponse(BaseModel):
    """Response from export endpoint."""
    success: bool
    file_id: Optional[str] = None
    download_url: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# Template Library Schemas
# ============================================================================

class TemplateSchema(BaseModel):
    """Schema for a diagram template."""
    id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Template display name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Template category")
    thumbnail_url: Optional[str] = Field(None, description="Preview thumbnail URL")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    brief: BriefSchema = Field(..., description="Template diagram brief")
    popularity: int = Field(0, description="Usage popularity score")
    is_premium: bool = Field(False, description="Premium template flag")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "3tier-web-architecture",
                "name": "3-Tier Web Architecture",
                "description": "Classic web application architecture",
                "category": "architecture",
                "tags": ["web", "architecture", "3-tier"],
                "brief": {
                    "title": "3-Tier Architecture",
                    "diagram_type": "marketecture",
                    "entities": [
                        {"name": "Frontend", "layer": "presentation"},
                        {"name": "Backend", "layer": "application"},
                        {"name": "Database", "layer": "data"},
                    ],
                    "layers": [
                        {"name": "presentation"},
                        {"name": "application"},
                        {"name": "data"},
                    ],
                },
                "popularity": 100,
                "is_premium": False,
            }
        }


class TemplateCategorySchema(BaseModel):
    """Schema for a template category."""
    id: str = Field(..., description="Category identifier")
    name: str = Field(..., description="Category display name")
    count: int = Field(0, description="Number of templates in category")


class TemplateTagSchema(BaseModel):
    """Schema for a template tag."""
    tag: str = Field(..., description="Tag name")
    count: int = Field(0, description="Number of templates with this tag")


class TemplateListRequest(BaseModel):
    """Request to list templates with filters."""
    category: Optional[str] = Field(None, description="Filter by category")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    search: Optional[str] = Field(None, description="Search in name/description")


class TemplateListResponse(BaseModel):
    """Response containing list of templates."""
    success: bool = True
    templates: List[TemplateSchema] = Field(default_factory=list)
    total: int = Field(0, description="Total number of templates")
    error: Optional[str] = None


class TemplateCategoriesResponse(BaseModel):
    """Response containing template categories."""
    success: bool = True
    categories: List[TemplateCategorySchema] = Field(default_factory=list)


class TemplateTagsResponse(BaseModel):
    """Response containing popular tags."""
    success: bool = True
    tags: List[TemplateTagSchema] = Field(default_factory=list)


class TemplateDetailResponse(BaseModel):
    """Response containing a single template."""
    success: bool = True
    template: Optional[TemplateSchema] = None
    error: Optional[str] = None


class UseTemplateResponse(BaseModel):
    """Response when using a template."""
    success: bool = True
    brief: Optional[BriefSchema] = None
    error: Optional[str] = None


# =============================================================================
# STYLE TRAINING MODELS
# =============================================================================

class TrainFromPPTXRequest(BaseModel):
    """Request to train from a PowerPoint file."""
    file_base64: str = Field(..., description="Base64-encoded PPTX file")
    style_name: str = Field(..., description="Name for the learned style")
    description: str = Field("", description="Optional description")
    tags: str = Field("", description="Comma-separated tags for categorization")

    class Config:
        json_schema_extra = {
            "example": {
                "file_base64": "UEsDBBQA...",
                "style_name": "Corporate Blue",
                "description": "Modern corporate presentation style",
                "tags": "corporate,blue,professional"
            }
        }


class TrainFromImageRequest(BaseModel):
    """Request to train from an image using Claude Vision."""
    image_base64: str = Field(..., description="Base64-encoded image (PNG, JPG)")
    style_name: str = Field(..., description="Name for the learned style")
    description: str = Field("", description="Optional description")
    tags: str = Field("", description="Comma-separated tags for categorization")

    class Config:
        json_schema_extra = {
            "example": {
                "image_base64": "iVBORw0KGgo...",
                "style_name": "Gradient Modern",
                "description": "Colorful gradient style from design inspiration",
                "tags": "gradient,modern,colorful"
            }
        }


class TrainResponse(BaseModel):
    """Response from training endpoints."""
    success: bool
    style_id: Optional[str] = None
    style_name: Optional[str] = None
    extracted: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
