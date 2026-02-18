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


class BriefSchema(BaseModel):
    """Complete diagram brief specification."""
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
            }
        }


class PreviewRequest(BaseModel):
    """Request to generate an SVG preview from a brief."""
    brief: BriefSchema
    palette: Optional[ColorPaletteSchema] = None
    brand_preset: Optional[str] = Field(
        None, description="Name of brand preset (e.g., 'microsoft', 'opentext')"
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


class GenerateResponse(BaseModel):
    """Response from generate endpoint."""
    success: bool
    file_id: Optional[str] = None
    download_url: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = None


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
