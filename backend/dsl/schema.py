"""Pydantic v2 models for the DSL scene graph schema.

This module defines the core data structures for representing PowerPoint slides
as a structured scene graph. All measurements are in EMUs (English Metric Units)
unless otherwise specified. 1 inch = 914400 EMUs.
"""

from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


# Constants
EMU_PER_INCH = 914400
EMU_PER_POINT = 12700


class ShapeType(str, Enum):
    """Supported shape types."""

    AUTO_SHAPE = "autoShape"
    FREEFORM = "freeform"
    TEXT = "text"
    IMAGE = "image"
    GROUP = "group"
    CONNECTOR = "connector"


class PathCommandType(str, Enum):
    """Path command types for freeform shapes."""

    MOVE_TO = "moveTo"
    LINE_TO = "lineTo"
    CURVE_TO = "curveTo"  # Cubic Bezier
    QUAD_TO = "quadTo"  # Quadratic Bezier
    ARC_TO = "arcTo"
    CLOSE = "close"


class GradientType(str, Enum):
    """Gradient fill types."""

    LINEAR = "linear"
    RADIAL = "radial"
    PATH = "path"


class DashStyle(str, Enum):
    """Line dash styles."""

    SOLID = "solid"
    DASH = "dash"
    DOT = "dot"
    DASH_DOT = "dashDot"
    LONG_DASH = "longDash"


# ============================================================================
# Geometry Models
# ============================================================================


class BoundingBox(BaseModel):
    """Bounding box in EMUs."""

    model_config = ConfigDict(frozen=True)

    x: int = Field(description="Left position in EMUs")
    y: int = Field(description="Top position in EMUs")
    width: int = Field(ge=0, description="Width in EMUs")
    height: int = Field(ge=0, description="Height in EMUs")

    @property
    def right(self) -> int:
        """Right edge position."""
        return self.x + self.width

    @property
    def bottom(self) -> int:
        """Bottom edge position."""
        return self.y + self.height

    @property
    def center_x(self) -> int:
        """Horizontal center."""
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        """Vertical center."""
        return self.y + self.height // 2

    def to_inches(self) -> dict[str, float]:
        """Convert to inches."""
        return {
            "x": self.x / EMU_PER_INCH,
            "y": self.y / EMU_PER_INCH,
            "width": self.width / EMU_PER_INCH,
            "height": self.height / EMU_PER_INCH,
        }


class Transform(BaseModel):
    """Shape transformation properties."""

    model_config = ConfigDict(frozen=True)

    rotation: float = Field(default=0.0, ge=-360.0, le=360.0, description="Rotation in degrees")
    flip_h: bool = Field(default=False, description="Horizontal flip")
    flip_v: bool = Field(default=False, description="Vertical flip")
    scale_x: float = Field(default=1.0, gt=0, description="Horizontal scale factor")
    scale_y: float = Field(default=1.0, gt=0, description="Vertical scale factor")


class PathCommand(BaseModel):
    """A single path command for freeform shapes."""

    model_config = ConfigDict(frozen=True)

    type: PathCommandType
    x: Optional[int] = Field(default=None, description="X coordinate in EMUs")
    y: Optional[int] = Field(default=None, description="Y coordinate in EMUs")
    # Control points for curves
    x1: Optional[int] = Field(default=None, description="First control point X")
    y1: Optional[int] = Field(default=None, description="First control point Y")
    x2: Optional[int] = Field(default=None, description="Second control point X (cubic)")
    y2: Optional[int] = Field(default=None, description="Second control point Y (cubic)")
    # Arc parameters
    width_radius: Optional[int] = Field(default=None, description="Arc width radius")
    height_radius: Optional[int] = Field(default=None, description="Arc height radius")
    start_angle: Optional[float] = Field(default=None, description="Arc start angle")
    swing_angle: Optional[float] = Field(default=None, description="Arc swing angle")


# ============================================================================
# Fill & Stroke Models
# ============================================================================


class SolidFill(BaseModel):
    """Solid color fill."""

    model_config = ConfigDict(frozen=True)

    type: Literal["solid"] = "solid"
    color: str = Field(description="RGB hex color (e.g., '#0D9488')")
    alpha: float = Field(default=1.0, ge=0.0, le=1.0, description="Opacity")


class GradientStop(BaseModel):
    """A gradient color stop."""

    model_config = ConfigDict(frozen=True)

    position: float = Field(ge=0.0, le=1.0, description="Position along gradient (0-1)")
    color: str = Field(description="RGB hex color")
    alpha: float = Field(default=1.0, ge=0.0, le=1.0, description="Opacity")


class GradientFill(BaseModel):
    """Gradient fill."""

    model_config = ConfigDict(frozen=True)

    type: Literal["gradient"] = "gradient"
    gradient_type: GradientType = GradientType.LINEAR
    angle: float = Field(default=0.0, description="Gradient angle in degrees (for linear)")
    stops: list[GradientStop] = Field(min_length=2, description="Color stops")


class PatternFill(BaseModel):
    """Pattern fill."""

    model_config = ConfigDict(frozen=True)

    type: Literal["pattern"] = "pattern"
    pattern: str = Field(description="Pattern name")
    fg_color: str = Field(description="Foreground color")
    bg_color: str = Field(description="Background color")


class NoFill(BaseModel):
    """No fill (transparent)."""

    model_config = ConfigDict(frozen=True)

    type: Literal["none"] = "none"


Fill = Annotated[
    Union[SolidFill, GradientFill, PatternFill, NoFill],
    Field(discriminator="type"),
]


class Stroke(BaseModel):
    """Line/border stroke properties."""

    model_config = ConfigDict(frozen=True)

    color: str = Field(default="#000000", description="RGB hex color")
    width: int = Field(default=12700, ge=0, description="Line width in EMUs (1pt = 12700 EMUs)")
    alpha: float = Field(default=1.0, ge=0.0, le=1.0, description="Opacity")
    dash_style: DashStyle = Field(default=DashStyle.SOLID, description="Dash pattern")
    cap: Literal["flat", "round", "square"] = Field(default="flat", description="Line cap style")
    join: Literal["miter", "round", "bevel"] = Field(default="miter", description="Line join style")


# ============================================================================
# Effects Models
# ============================================================================


class Shadow(BaseModel):
    """Shadow effect."""

    model_config = ConfigDict(frozen=True)

    type: Literal["outer", "inner"] = "outer"
    color: str = Field(default="#000000", description="Shadow color")
    alpha: float = Field(default=0.5, ge=0.0, le=1.0, description="Shadow opacity")
    blur_radius: int = Field(default=50800, ge=0, description="Blur radius in EMUs")
    distance: int = Field(default=38100, ge=0, description="Shadow distance in EMUs")
    angle: float = Field(default=45.0, description="Shadow direction in degrees")


class Glow(BaseModel):
    """Glow effect."""

    model_config = ConfigDict(frozen=True)

    color: str = Field(description="Glow color")
    alpha: float = Field(default=0.6, ge=0.0, le=1.0, description="Glow opacity")
    radius: int = Field(default=63500, ge=0, description="Glow radius in EMUs")


class Reflection(BaseModel):
    """Reflection effect."""

    model_config = ConfigDict(frozen=True)

    blur_radius: int = Field(default=0, ge=0, description="Blur radius in EMUs")
    start_alpha: float = Field(default=0.5, ge=0.0, le=1.0, description="Start opacity")
    end_alpha: float = Field(default=0.0, ge=0.0, le=1.0, description="End opacity")
    distance: int = Field(default=0, ge=0, description="Distance from shape in EMUs")
    direction: float = Field(default=90.0, description="Direction in degrees")
    fade_direction: float = Field(default=90.0, description="Fade direction")
    scale_x: float = Field(default=1.0, description="Horizontal scale")
    scale_y: float = Field(default=-1.0, description="Vertical scale (negative for reflection)")


class Bevel(BaseModel):
    """3D bevel effect."""

    model_config = ConfigDict(frozen=True)

    type: Literal["relaxedInset", "circle", "slope", "cross", "angle", "softRound"] = "relaxedInset"
    width: int = Field(default=76200, ge=0, description="Bevel width in EMUs")
    height: int = Field(default=76200, ge=0, description="Bevel height in EMUs")


class Effects(BaseModel):
    """Combined visual effects for a shape."""

    model_config = ConfigDict(frozen=True)

    shadow: Optional[Shadow] = None
    glow: Optional[Glow] = None
    reflection: Optional[Reflection] = None
    bevel: Optional[Bevel] = None
    soft_edges: Optional[int] = Field(default=None, ge=0, description="Soft edge radius in EMUs")


# ============================================================================
# Text Models
# ============================================================================


class TextRun(BaseModel):
    """A run of text with consistent formatting."""

    model_config = ConfigDict(frozen=True)

    text: str = Field(description="The text content")
    font_family: str = Field(default="Calibri", description="Font family name")
    font_size: int = Field(default=1400, description="Font size in hundredths of a point")
    bold: bool = Field(default=False)
    italic: bool = Field(default=False)
    underline: bool = Field(default=False)
    color: str = Field(default="#000000", description="Text color")


class TextContent(BaseModel):
    """Text content with formatting."""

    model_config = ConfigDict(frozen=True)

    runs: list[TextRun] = Field(default_factory=list, description="Formatted text runs")
    alignment: Literal["left", "center", "right", "justify"] = Field(default="left")
    vertical_alignment: Literal["top", "middle", "bottom"] = Field(default="middle")
    margin_left: int = Field(default=91440, description="Left margin in EMUs")
    margin_right: int = Field(default=91440, description="Right margin in EMUs")
    margin_top: int = Field(default=45720, description="Top margin in EMUs")
    margin_bottom: int = Field(default=45720, description="Bottom margin in EMUs")
    word_wrap: bool = Field(default=True)
    auto_fit: Literal["none", "shrink", "shape"] = Field(default="none")


# ============================================================================
# Shape Model
# ============================================================================


class Shape(BaseModel):
    """A single shape in the scene graph."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique shape identifier")
    type: ShapeType = Field(description="Shape type")
    name: Optional[str] = Field(default=None, description="Human-readable shape name")
    group_path: list[str] = Field(
        default_factory=lambda: ["root"],
        description="Path from root to this shape's parent group",
    )
    z_index: int = Field(default=0, description="Z-order (higher = on top)")

    # Geometry
    bbox: BoundingBox = Field(description="Bounding box")
    transform: Transform = Field(default_factory=Transform, description="Transformations")

    # For autoShapes
    auto_shape_type: Optional[str] = Field(
        default=None,
        description="PowerPoint auto shape type (e.g., 'rect', 'roundRect', 'trapezoid')",
    )

    # For freeform shapes
    path: Optional[list[PathCommand]] = Field(default=None, description="Path commands for freeform")

    # For images
    image_path: Optional[str] = Field(default=None, description="Path to image file")

    # For groups
    children: Optional[list["Shape"]] = Field(default=None, description="Child shapes for groups")

    # Visual properties
    fill: Fill = Field(default_factory=lambda: NoFill(), description="Fill style")
    stroke: Optional[Stroke] = Field(default=None, description="Stroke/border style")
    effects: Effects = Field(default_factory=Effects, description="Visual effects")

    # Text
    text: Optional[TextContent] = Field(default=None, description="Text content if applicable")

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ============================================================================
# Canvas & Scene Models
# ============================================================================


class Canvas(BaseModel):
    """Slide canvas properties."""

    model_config = ConfigDict(frozen=True)

    width: int = Field(default=12192000, description="Canvas width in EMUs (default 16:9)")
    height: int = Field(default=6858000, description="Canvas height in EMUs (default 16:9)")
    background: Fill = Field(
        default_factory=lambda: SolidFill(color="#FFFFFF"),
        description="Background fill",
    )

    @property
    def aspect_ratio(self) -> float:
        """Canvas aspect ratio."""
        return self.width / self.height if self.height > 0 else 0

    def to_inches(self) -> dict[str, float]:
        """Convert dimensions to inches."""
        return {
            "width": self.width / EMU_PER_INCH,
            "height": self.height / EMU_PER_INCH,
        }


class ThemeColors(BaseModel):
    """PowerPoint theme color palette."""

    model_config = ConfigDict(frozen=True)

    # Core colors
    dark1: str = Field(default="#000000", description="Dark 1 (typically black)")
    light1: str = Field(default="#FFFFFF", description="Light 1 (typically white)")
    dark2: str = Field(default="#1F497D", description="Dark 2")
    light2: str = Field(default="#EEECE1", description="Light 2")

    # Accent colors
    accent1: str = Field(default="#0D9488", description="Accent 1 (primary teal)")
    accent2: str = Field(default="#14B8A6", description="Accent 2")
    accent3: str = Field(default="#2DD4BF", description="Accent 3")
    accent4: str = Field(default="#5EEAD4", description="Accent 4")
    accent5: str = Field(default="#99F6E4", description="Accent 5")
    accent6: str = Field(default="#CCFBF1", description="Accent 6")

    # Hyperlinks
    hyperlink: str = Field(default="#0563C1", description="Hyperlink color")
    followed_hyperlink: str = Field(default="#954F72", description="Followed hyperlink color")


class SlideMetadata(BaseModel):
    """Metadata about the slide."""

    model_config = ConfigDict(frozen=True)

    title: Optional[str] = Field(default=None, description="Slide title")
    slide_number: int = Field(default=1, ge=1, description="Slide number")
    layout_name: Optional[str] = Field(default=None, description="Layout template name")
    notes: Optional[str] = Field(default=None, description="Speaker notes")
    archetype: Optional[str] = Field(
        default=None,
        description="Detected archetype (funnel, pyramid, timeline, etc.)",
    )
    tags: list[str] = Field(default_factory=list, description="Classification tags")


class SlideScene(BaseModel):
    """Complete scene graph for a single slide."""

    model_config = ConfigDict(frozen=True)

    canvas: Canvas = Field(default_factory=Canvas, description="Canvas properties")
    shapes: list[Shape] = Field(default_factory=list, description="All shapes on the slide")
    theme: ThemeColors = Field(default_factory=ThemeColors, description="Theme color palette")
    metadata: SlideMetadata = Field(default_factory=SlideMetadata, description="Slide metadata")

    def get_shape_by_id(self, shape_id: str) -> Optional[Shape]:
        """Find a shape by its ID."""
        for shape in self.shapes:
            if shape.id == shape_id:
                return shape
            if shape.children:
                for child in shape.children:
                    if child.id == shape_id:
                        return child
        return None


# ============================================================================
# API Request/Response Models
# ============================================================================


class GenerateRequest(BaseModel):
    """Request to generate an infographic slide."""

    prompt: str = Field(min_length=1, max_length=2000, description="User prompt describing the slide")
    archetype: Optional[str] = Field(
        default=None,
        description="Explicit archetype override (funnel, pyramid, timeline, etc.)",
    )
    template_id: Optional[str] = Field(default=None, description="Template to use as base")
    style: Optional[str] = Field(
        default=None,
        description="Style preset (professional, modern, minimal, bold)",
    )
    color_scheme: Optional[list[str]] = Field(
        default=None,
        max_length=6,
        description="Custom color palette (up to 6 hex colors)",
    )
    variations: int = Field(default=1, ge=1, le=10, description="Number of variations to generate")


class GenerateResponse(BaseModel):
    """Response from generation request."""

    id: str = Field(description="Generation request ID")
    status: Literal["pending", "processing", "completed", "failed"] = Field(description="Current status")
    message: Optional[str] = Field(default=None, description="Status message or error")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Progress (0-1)")
    scene: Optional[SlideScene] = Field(default=None, description="Generated scene (when completed)")
    download_url: Optional[str] = Field(default=None, description="PPTX download URL (when completed)")
    variations: list["GenerateResponse"] = Field(
        default_factory=list,
        description="Variation results (if requested)",
    )
