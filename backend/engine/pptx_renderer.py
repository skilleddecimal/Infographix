"""
pptx_renderer.py — PowerPoint file generation from PositionedLayout.

This renderer consumes PositionedLayout and produces .pptx files.
It NEVER computes positions — that's the layout engine's job.
It only converts inches to EMU and creates the actual shapes.

CRITICAL RULES:
1. NEVER set shape.text_frame.auto_size = MSO_AUTO_SIZE.SHAPE_TO_FIT_TEXT
2. ALWAYS use pre-computed font sizes from PositionedText
3. ALWAYS disable word wrap for single-line text
4. Use explicit paragraph formatting (no defaults)

VISUAL EFFECTS SUPPORT:
- Shadows (outer, inner, perspective)
- Gradients (linear, radial)
- Multiple shape types (rectangle, rounded rectangle, trapezoid, chevron, etc.)
- 3D effects (bevel, depth)
"""

from pathlib import Path
from typing import Optional, BinaryIO, Union, Dict, Any
from io import BytesIO
from dataclasses import dataclass
from enum import Enum

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.oxml import parse_xml
from lxml import etree

from .positioned import (
    PositionedLayout,
    PositionedElement,
    PositionedConnector,
    PositionedText,
    ElementType,
    ConnectorStyle,
    TextAlignment,
    MultiSlidePresentation,
)
from .units import (
    inches_to_emu,
    pt_to_emu,
    SLIDE_WIDTH_EMU,
    SLIDE_HEIGHT_EMU,
)

# Learned styles from template analysis
try:
    from .learned_styles import (
        generate_creative_pyramid_style,
        LearnedShadow,
        SHADOW_PYRAMIDA,
    )
    LEARNED_STYLES_AVAILABLE = True
except ImportError:
    LEARNED_STYLES_AVAILABLE = False

# Custom shape rendering system
try:
    from .shape_learning import (
        ShapeLibrary,
        ShapeGenerator,
        get_shape_library,
    )
    from .custom_shape_renderer import (
        CustomShapeRenderer,
        render_pyramid_to_slide,
        add_custom_shape_to_slide,
    )
    CUSTOM_SHAPES_AVAILABLE = True
except ImportError:
    CUSTOM_SHAPES_AVAILABLE = False


# =============================================================================
# VISUAL EFFECT TYPES
# =============================================================================

class ShapeType(Enum):
    """Available shape types for elements."""
    RECTANGLE = "rectangle"
    ROUNDED_RECTANGLE = "rounded_rectangle"
    TRAPEZOID = "trapezoid"
    CHEVRON = "chevron"
    HEXAGON = "hexagon"
    PARALLELOGRAM = "parallelogram"
    OVAL = "oval"
    DIAMOND = "diamond"
    PENTAGON = "pentagon"
    OCTAGON = "octagon"
    ARROW = "arrow"
    CALLOUT = "callout"


# Map ShapeType to MSO_SHAPE constants
SHAPE_TYPE_MAP = {
    ShapeType.RECTANGLE: MSO_SHAPE.RECTANGLE,
    ShapeType.ROUNDED_RECTANGLE: MSO_SHAPE.ROUNDED_RECTANGLE,
    ShapeType.TRAPEZOID: MSO_SHAPE.TRAPEZOID,
    ShapeType.CHEVRON: MSO_SHAPE.CHEVRON,
    ShapeType.HEXAGON: MSO_SHAPE.HEXAGON,
    ShapeType.PARALLELOGRAM: MSO_SHAPE.PARALLELOGRAM,
    ShapeType.OVAL: MSO_SHAPE.OVAL,
    ShapeType.DIAMOND: MSO_SHAPE.DIAMOND,
    ShapeType.PENTAGON: MSO_SHAPE.PENTAGON,
    ShapeType.OCTAGON: MSO_SHAPE.OCTAGON,
    ShapeType.ARROW: MSO_SHAPE.RIGHT_ARROW,
    ShapeType.CALLOUT: MSO_SHAPE.RECTANGULAR_CALLOUT,
}


@dataclass
class ShadowEffect:
    """Shadow effect configuration."""
    enabled: bool = True
    blur_radius_pt: float = 4.0  # Blur radius in points
    distance_pt: float = 3.0     # Distance from shape
    direction_deg: float = 45.0  # Angle in degrees (0=right, 90=down)
    color: str = "#000000"       # Shadow color
    opacity: float = 0.4         # 0-1, transparency
    shadow_type: str = "outer"   # outer, inner, perspective


@dataclass
class GradientEffect:
    """Gradient fill effect configuration."""
    enabled: bool = True
    gradient_type: str = "linear"  # linear, radial, rectangular, path
    angle_deg: float = 270.0       # For linear gradients (270=top to bottom)
    stops: list = None             # List of (position, color) tuples

    def __post_init__(self):
        if self.stops is None:
            # Default: darker at bottom for 3D effect
            self.stops = [
                (0.0, None),    # Will be filled with base color lightened
                (1.0, None),    # Will be filled with base color darkened
            ]


@dataclass
class VisualStyle:
    """Complete visual style for an element."""
    shape_type: ShapeType = ShapeType.ROUNDED_RECTANGLE
    shadow: Optional[ShadowEffect] = None
    gradient: Optional[GradientEffect] = None
    bevel_enabled: bool = False
    bevel_type: str = "circle"    # circle, relaxedInset, softRound, etc.
    bevel_width_pt: float = 3.0
    bevel_height_pt: float = 3.0
    reflection_enabled: bool = False
    glow_enabled: bool = False
    glow_color: str = "#FFFFFF"
    glow_radius_pt: float = 4.0


# =============================================================================
# COLOR HELPERS
# =============================================================================

def hex_to_rgb_color(hex_color: str) -> RGBColor:
    """Convert hex color string to pptx RGBColor."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return RGBColor(0x33, 0x33, 0x33)  # Default dark gray

    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return RGBColor(r, g, b)
    except ValueError:
        return RGBColor(0x33, 0x33, 0x33)


def hex_to_rgb_tuple(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple (0-255)."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return (51, 51, 51)
    try:
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16)
        )
    except ValueError:
        return (51, 51, 51)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to hex string."""
    return f"#{r:02X}{g:02X}{b:02X}"


def lighten_color(hex_color: str, factor: float = 0.2) -> str:
    """Lighten a color by a factor (0-1)."""
    r, g, b = hex_to_rgb_tuple(hex_color)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return rgb_to_hex(r, g, b)


def darken_color(hex_color: str, factor: float = 0.2) -> str:
    """Darken a color by a factor (0-1)."""
    r, g, b = hex_to_rgb_tuple(hex_color)
    r = max(0, int(r * (1 - factor)))
    g = max(0, int(g * (1 - factor)))
    b = max(0, int(b * (1 - factor)))
    return rgb_to_hex(r, g, b)


# =============================================================================
# PRESET VISUAL STYLES
# =============================================================================

# Professional shadow preset
SHADOW_SUBTLE = ShadowEffect(
    enabled=True,
    blur_radius_pt=6.0,
    distance_pt=3.0,
    direction_deg=135.0,
    color="#000000",
    opacity=0.25,
    shadow_type="outer"
)

SHADOW_MEDIUM = ShadowEffect(
    enabled=True,
    blur_radius_pt=8.0,
    distance_pt=4.0,
    direction_deg=135.0,
    color="#000000",
    opacity=0.35,
    shadow_type="outer"
)

SHADOW_STRONG = ShadowEffect(
    enabled=True,
    blur_radius_pt=12.0,
    distance_pt=6.0,
    direction_deg=135.0,
    color="#000000",
    opacity=0.45,
    shadow_type="outer"
)

# Learned shadow from Pyramida template (soft, diffuse shadow)
SHADOW_PYRAMIDA = ShadowEffect(
    enabled=True,
    blur_radius_pt=40.0,    # Large blur for soft edge
    distance_pt=4.0,        # Subtle offset
    direction_deg=135.0,    # Bottom-right direction
    color="#000000",
    opacity=0.60,           # 60% opacity as per template
    shadow_type="outer"
)

# Gradient presets
GRADIENT_SUBTLE_3D = GradientEffect(
    enabled=True,
    gradient_type="linear",
    angle_deg=270.0,  # Top to bottom
    stops=[(0.0, None), (1.0, None)]  # Auto-compute from base color
)

GRADIENT_GLASS = GradientEffect(
    enabled=True,
    gradient_type="linear",
    angle_deg=270.0,
    stops=[(0.0, None), (0.5, None), (1.0, None)]  # Three-stop glass effect
)

# Combined visual style presets
STYLE_FLAT = VisualStyle(
    shape_type=ShapeType.ROUNDED_RECTANGLE,
    shadow=None,
    gradient=None,
    bevel_enabled=False
)

STYLE_SUBTLE_3D = VisualStyle(
    shape_type=ShapeType.ROUNDED_RECTANGLE,
    shadow=SHADOW_SUBTLE,
    gradient=GRADIENT_SUBTLE_3D,
    bevel_enabled=False
)

STYLE_PROFESSIONAL = VisualStyle(
    shape_type=ShapeType.ROUNDED_RECTANGLE,
    shadow=SHADOW_MEDIUM,
    gradient=GRADIENT_SUBTLE_3D,
    bevel_enabled=True,
    bevel_type="softRound",
    bevel_width_pt=2.0,
    bevel_height_pt=2.0
)

STYLE_EXECUTIVE = VisualStyle(
    shape_type=ShapeType.RECTANGLE,
    shadow=SHADOW_STRONG,
    gradient=GRADIENT_GLASS,
    bevel_enabled=True,
    bevel_type="relaxedInset",
    bevel_width_pt=3.0,
    bevel_height_pt=3.0
)

# Pyramid-specific styles (learned from Pyramida template)
# Template uses: soft shadows (40pt blur), no strokes, no 3D bevels
STYLE_PYRAMID_LEVEL = VisualStyle(
    shape_type=ShapeType.TRAPEZOID,
    shadow=SHADOW_PYRAMIDA,       # Soft diffuse shadow from template
    gradient=GRADIENT_SUBTLE_3D,  # Subtle depth gradient
    bevel_enabled=False,          # Template doesn't use 3D bevels
    bevel_type=None,
    bevel_width_pt=0,
    bevel_height_pt=0
)


def get_alignment(text_align: TextAlignment) -> PP_ALIGN:
    """Convert TextAlignment to pptx PP_ALIGN."""
    mapping = {
        TextAlignment.LEFT: PP_ALIGN.LEFT,
        TextAlignment.CENTER: PP_ALIGN.CENTER,
        TextAlignment.RIGHT: PP_ALIGN.RIGHT,
    }
    return mapping.get(text_align, PP_ALIGN.CENTER)


# =============================================================================
# XML GENERATION FOR VISUAL EFFECTS
# =============================================================================

# XML namespace for DrawingML
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
A_NSMAP = {'a': A_NS}


def _create_shadow_xml(shadow: ShadowEffect) -> etree.Element:
    """
    Create DrawingML XML for shadow effect.

    Returns an <a:effectLst> element with the shadow definition.
    """
    # Convert values to EMU (1 point = 12700 EMU)
    blur_emu = int(shadow.blur_radius_pt * 12700)
    dist_emu = int(shadow.distance_pt * 12700)

    # Direction in PowerPoint: 0 = right, 5400000 = down (60000 units = 1 degree)
    direction = int(shadow.direction_deg * 60000)

    # Opacity: 0 = transparent, 100000 = opaque
    alpha = int(shadow.opacity * 100000)

    # Color without #
    color_hex = shadow.color.lstrip('#')

    if shadow.shadow_type == "outer":
        effect_xml = f'''
        <a:effectLst xmlns:a="{A_NS}">
            <a:outerShdw blurRad="{blur_emu}" dist="{dist_emu}" dir="{direction}" algn="ctr" rotWithShape="0">
                <a:srgbClr val="{color_hex}">
                    <a:alpha val="{alpha}"/>
                </a:srgbClr>
            </a:outerShdw>
        </a:effectLst>
        '''
    elif shadow.shadow_type == "inner":
        effect_xml = f'''
        <a:effectLst xmlns:a="{A_NS}">
            <a:innerShdw blurRad="{blur_emu}" dist="{dist_emu}" dir="{direction}">
                <a:srgbClr val="{color_hex}">
                    <a:alpha val="{alpha}"/>
                </a:srgbClr>
            </a:innerShdw>
        </a:effectLst>
        '''
    elif shadow.shadow_type == "perspective":
        # Perspective shadow with preset
        effect_xml = f'''
        <a:effectLst xmlns:a="{A_NS}">
            <a:outerShdw blurRad="{blur_emu}" dist="{dist_emu}" dir="{direction}"
                         sx="100000" sy="100000" kx="0" ky="0" algn="b" rotWithShape="0">
                <a:srgbClr val="{color_hex}">
                    <a:alpha val="{alpha}"/>
                </a:srgbClr>
            </a:outerShdw>
        </a:effectLst>
        '''
    else:
        effect_xml = f'<a:effectLst xmlns:a="{A_NS}"/>'

    return etree.fromstring(effect_xml)


def _create_gradient_fill_xml(gradient: GradientEffect, base_color: str) -> etree.Element:
    """
    Create DrawingML XML for gradient fill.

    Returns an <a:gradFill> element.
    """
    # Angle in DrawingML: 0 = horizontal (left to right), 16200000 = 270 degrees
    # angle_val = angle_deg * 60000
    angle_val = int(gradient.angle_deg * 60000)

    # Build gradient stops
    stops_xml = ""
    for i, (pos, color) in enumerate(gradient.stops):
        # Position as percentage * 1000 (0-100000)
        pos_val = int(pos * 100000)

        # If color is None, auto-compute from base color
        if color is None:
            if len(gradient.stops) == 2:
                # Two stops: lighter at top, base at bottom
                if i == 0:
                    color = lighten_color(base_color, 0.25)
                else:
                    color = darken_color(base_color, 0.15)
            elif len(gradient.stops) == 3:
                # Three stops: glass effect
                if i == 0:
                    color = lighten_color(base_color, 0.35)
                elif i == 1:
                    color = base_color
                else:
                    color = darken_color(base_color, 0.20)
            else:
                color = base_color

        color_hex = color.lstrip('#')
        stops_xml += f'''
            <a:gs pos="{pos_val}">
                <a:srgbClr val="{color_hex}"/>
            </a:gs>
        '''

    if gradient.gradient_type == "linear":
        fill_xml = f'''
        <a:gradFill xmlns:a="{A_NS}" rotWithShape="1">
            <a:gsLst>
                {stops_xml}
            </a:gsLst>
            <a:lin ang="{angle_val}" scaled="1"/>
        </a:gradFill>
        '''
    elif gradient.gradient_type == "radial":
        fill_xml = f'''
        <a:gradFill xmlns:a="{A_NS}" rotWithShape="1">
            <a:gsLst>
                {stops_xml}
            </a:gsLst>
            <a:path path="circle">
                <a:fillToRect l="50000" t="50000" r="50000" b="50000"/>
            </a:path>
        </a:gradFill>
        '''
    else:
        # Default to linear
        fill_xml = f'''
        <a:gradFill xmlns:a="{A_NS}" rotWithShape="1">
            <a:gsLst>
                {stops_xml}
            </a:gsLst>
            <a:lin ang="{angle_val}" scaled="1"/>
        </a:gradFill>
        '''

    return etree.fromstring(fill_xml)


def _create_bevel_xml(bevel_type: str, width_pt: float, height_pt: float) -> etree.Element:
    """
    Create DrawingML XML for 3D bevel effect.

    Returns an <a:sp3d> element.
    """
    # Convert points to EMU
    width_emu = int(width_pt * 12700)
    height_emu = int(height_pt * 12700)

    sp3d_xml = f'''
    <a:sp3d xmlns:a="{A_NS}">
        <a:bevelT w="{width_emu}" h="{height_emu}" prst="{bevel_type}"/>
    </a:sp3d>
    '''

    return etree.fromstring(sp3d_xml)


def apply_visual_effects_to_shape(shape, visual_style: VisualStyle, base_color: str) -> None:
    """
    Apply visual effects (shadow, gradient, bevel) to a PowerPoint shape.

    This manipulates the underlying XML of the shape to add effects
    that python-pptx doesn't directly support.
    """
    try:
        spPr = shape._element.spPr

        # Apply gradient fill
        if visual_style.gradient and visual_style.gradient.enabled:
            # Remove existing solidFill if present
            existing_fill = spPr.find(qn('a:solidFill'))
            if existing_fill is not None:
                spPr.remove(existing_fill)

            # Add gradient fill
            grad_fill = _create_gradient_fill_xml(visual_style.gradient, base_color)

            # Insert after prstGeom/custGeom (OOXML requires fill after geometry)
            # Order: xfrm -> prstGeom/custGeom -> fill -> ln -> effectLst -> sp3d
            prstGeom = spPr.find(qn('a:prstGeom'))
            custGeom = spPr.find(qn('a:custGeom'))
            geom = prstGeom if prstGeom is not None else custGeom

            if geom is not None:
                geom_index = list(spPr).index(geom)
                spPr.insert(geom_index + 1, grad_fill)
            else:
                # Fallback: insert after xfrm
                xfrm = spPr.find(qn('a:xfrm'))
                if xfrm is not None:
                    xfrm_index = list(spPr).index(xfrm)
                    spPr.insert(xfrm_index + 1, grad_fill)
                else:
                    spPr.insert(0, grad_fill)

        # Apply shadow effect
        if visual_style.shadow and visual_style.shadow.enabled:
            # Remove existing effectLst
            existing_effects = spPr.find(qn('a:effectLst'))
            if existing_effects is not None:
                spPr.remove(existing_effects)

            # Add shadow
            effect_lst = _create_shadow_xml(visual_style.shadow)
            spPr.append(effect_lst)

        # Apply 3D bevel
        if visual_style.bevel_enabled:
            # Remove existing sp3d
            existing_3d = spPr.find(qn('a:sp3d'))
            if existing_3d is not None:
                spPr.remove(existing_3d)

            # Add bevel
            sp3d = _create_bevel_xml(
                visual_style.bevel_type,
                visual_style.bevel_width_pt,
                visual_style.bevel_height_pt
            )
            spPr.append(sp3d)

    except Exception as e:
        # Silently fail - effects are optional enhancements
        pass


# =============================================================================
# PPTX RENDERER
# =============================================================================

def convert_design_style_to_visual_style(design_style) -> VisualStyle:
    """
    Convert a learned DesignStyle (from design_learner) to a VisualStyle.

    This extracts the visual effects (shadows, gradients, etc.) from a learned
    design style and creates a VisualStyle that can be used by the renderer.
    The colors from the learned style are NOT used - only the visual effects.
    """
    if design_style is None:
        return None

    shape_style = design_style.shape_style
    if shape_style is None:
        return STYLE_PROFESSIONAL

    # Convert shadow
    shadow = None
    if shape_style.shadow:
        shadow = ShadowEffect(
            enabled=shape_style.shadow.enabled,
            blur_radius_pt=shape_style.shadow.blur_radius_pt,
            distance_pt=shape_style.shadow.distance_pt,
            direction_deg=shape_style.shadow.angle_degrees,
            color=shape_style.shadow.color,
            opacity=shape_style.shadow.opacity,
            shadow_type="outer",
        )

    # Convert gradient (but colors will be replaced with user's colors)
    gradient = None
    if shape_style.gradient:
        gradient = GradientEffect(
            enabled=True,
            gradient_type=shape_style.gradient.type.value if hasattr(shape_style.gradient.type, 'value') else str(shape_style.gradient.type),
            angle_deg=shape_style.gradient.angle_degrees,
            stops=None,  # Will be filled with user's colors
        )

    # Determine shape type based on corner radius
    shape_type = ShapeType.ROUNDED_RECTANGLE
    if shape_style.corner_radius_ratio < 0.03:
        shape_type = ShapeType.RECTANGLE
    elif shape_style.corner_radius_ratio > 0.15:
        shape_type = ShapeType.ROUNDED_RECTANGLE

    return VisualStyle(
        shape_type=shape_type,
        shadow=shadow,
        gradient=gradient,
        bevel_enabled=False,  # Can be extended later
    )


class PPTXRenderer:
    """
    Renders PositionedLayout to PowerPoint files.

    The renderer is stateless — each render() call creates a new presentation.
    Supports visual styles for professional-grade output.
    """

    def __init__(self, default_style: Optional[VisualStyle] = None, visual_style=None):
        """
        Initialize renderer with optional default visual style.

        Args:
            default_style: Default visual style for blocks. If None, uses STYLE_PROFESSIONAL.
            visual_style: Optional learned DesignStyle to apply (takes precedence).
        """
        # If a learned visual_style is provided, convert it
        if visual_style is not None:
            converted = convert_design_style_to_visual_style(visual_style)
            self.default_style = converted if converted else STYLE_PROFESSIONAL
        else:
            self.default_style = default_style or STYLE_PROFESSIONAL
        self._element_styles: Dict[str, VisualStyle] = {}

    def set_element_style(self, element_id: str, style: VisualStyle) -> None:
        """Set a specific visual style for an element by ID."""
        self._element_styles[element_id] = style

    def set_archetype_style(self, archetype: str, style: VisualStyle) -> None:
        """
        Set visual style for all elements of a specific archetype.

        Args:
            archetype: Archetype name (e.g., "pyramid", "marketecture")
            style: Visual style to apply
        """
        # Store as special key
        self._element_styles[f"__archetype__{archetype}"] = style

    def get_style_for_element(
        self,
        element: PositionedElement,
        archetype: Optional[str] = None
    ) -> VisualStyle:
        """
        Get the appropriate visual style for an element.

        Priority:
        1. Element-specific style (by ID)
        2. Archetype-specific style
        3. Default renderer style
        """
        # Check element-specific style
        if element.id and element.id in self._element_styles:
            return self._element_styles[element.id]

        # Check archetype-specific style
        if archetype and f"__archetype__{archetype}" in self._element_styles:
            return self._element_styles[f"__archetype__{archetype}"]

        # Return default
        return self.default_style

    def render(
        self,
        layout: PositionedLayout,
        output: Optional[Union[str, Path, BinaryIO]] = None
    ) -> bytes:
        """
        Render a PositionedLayout to PPTX format.

        Args:
            layout: The positioned layout to render
            output: Optional output path or file-like object
                    If None, returns bytes

        Returns:
            PPTX file contents as bytes
        """
        # Create presentation with correct dimensions
        prs = Presentation()
        prs.slide_width = Emu(inches_to_emu(layout.slide_width_inches))
        prs.slide_height = Emu(inches_to_emu(layout.slide_height_inches))

        # Set archetype-specific style if layout specifies an archetype
        if layout.archetype:
            archetype_styles = {
                "pyramid": STYLE_PYRAMID_LEVEL,
                # Add more archetype-specific styles here as needed
            }
            if layout.archetype in archetype_styles:
                self.set_archetype_style(layout.archetype, archetype_styles[layout.archetype])

        # Add blank slide
        blank_layout = prs.slide_layouts[6]  # Blank layout
        slide = prs.slides.add_slide(blank_layout)

        # Set background color
        self._set_slide_background(slide, layout.background_color)

        # Render title and subtitle first (z-order highest)
        if layout.title:
            self._render_element(slide, layout.title)
        if layout.subtitle:
            self._render_element(slide, layout.subtitle)

        # Count pyramid levels if this is a pyramid archetype
        if layout.archetype == "pyramid":
            pyramid_levels = sum(
                1 for e in layout.elements
                if e.id and e.id.startswith("level_")
            )
            self._pyramid_level_count = max(2, pyramid_levels)

        # Render elements sorted by z-order (lowest first = behind)
        for element in layout.elements_sorted_by_z_order():
            self._render_element(slide, element, archetype=layout.archetype)

        # Render connectors
        for connector in layout.connectors:
            self._render_connector(slide, connector)

        # Save to output
        if output is None:
            buffer = BytesIO()
            prs.save(buffer)
            return buffer.getvalue()
        elif isinstance(output, (str, Path)):
            prs.save(str(output))
            with open(output, 'rb') as f:
                return f.read()
        else:
            prs.save(output)
            output.seek(0)
            return output.read()

    def render_to_file(self, layout: PositionedLayout, filepath: Union[str, Path]) -> None:
        """
        Render layout directly to a file.

        Args:
            layout: The positioned layout to render
            filepath: Output file path
        """
        self.render(layout, output=filepath)

    def render_presentation(
        self,
        presentation: MultiSlidePresentation,
        output: Optional[Union[str, Path, BinaryIO]] = None
    ) -> bytes:
        """
        Render a multi-slide presentation to PPTX format.

        Args:
            presentation: The MultiSlidePresentation to render
            output: Optional output path or file-like object
                    If None, returns bytes

        Returns:
            PPTX file contents as bytes
        """
        if not presentation.slides:
            raise ValueError("Presentation has no slides")

        # Create presentation with correct dimensions
        prs = Presentation()
        prs.slide_width = Emu(inches_to_emu(presentation.slide_width_inches))
        prs.slide_height = Emu(inches_to_emu(presentation.slide_height_inches))

        # Render each slide
        for slide_layout in presentation.slides:
            self._render_slide(prs, slide_layout)

        # Save to output
        if output is None:
            buffer = BytesIO()
            prs.save(buffer)
            return buffer.getvalue()
        elif isinstance(output, (str, Path)):
            prs.save(str(output))
            with open(output, 'rb') as f:
                return f.read()
        else:
            prs.save(output)
            output.seek(0)
            return output.read()

    def _render_slide(self, prs: Presentation, layout: PositionedLayout) -> None:
        """Render a single slide to an existing presentation."""
        # Add blank slide
        blank_layout = prs.slide_layouts[6]  # Blank layout
        slide = prs.slides.add_slide(blank_layout)

        # Set background color
        self._set_slide_background(slide, layout.background_color)

        # Render title and subtitle first (z-order highest)
        if layout.title:
            self._render_element(slide, layout.title)
        if layout.subtitle:
            self._render_element(slide, layout.subtitle)

        # Render elements sorted by z-order (lowest first = behind)
        for element in layout.elements_sorted_by_z_order():
            self._render_element(slide, element)

        # Render connectors
        for connector in layout.connectors:
            self._render_connector(slide, connector)

        # Add speaker notes if present
        if layout.speaker_notes:
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = layout.speaker_notes

    # =========================================================================
    # SLIDE BACKGROUND
    # =========================================================================

    def _set_slide_background(self, slide, color: str) -> None:
        """Set slide background color."""
        if color.lower() == "transparent" or color == "#FFFFFF":
            return  # White/transparent is default

        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = hex_to_rgb_color(color)

    # =========================================================================
    # ELEMENT RENDERING
    # =========================================================================

    def _render_element(self, slide, element: PositionedElement, archetype: Optional[str] = None) -> None:
        """Render a single positioned element."""
        # Skip transparent fill elements without text (spacers)
        if element.fill_color == "transparent" and element.text is None:
            return

        # Convert to EMU
        left = Emu(inches_to_emu(element.x_inches))
        top = Emu(inches_to_emu(element.y_inches))
        width = Emu(inches_to_emu(element.width_inches))
        height = Emu(inches_to_emu(element.height_inches))

        # Choose shape type based on element type
        if element.element_type == ElementType.TITLE:
            self._render_title(slide, element, left, top, width, height)
        elif element.element_type == ElementType.SUBTITLE:
            self._render_subtitle(slide, element, left, top, width, height)
        elif element.element_type == ElementType.BAND:
            self._render_band(slide, element, left, top, width, height)
        elif element.element_type == ElementType.LABEL:
            self._render_label(slide, element, left, top, width, height)
        else:
            self._render_block(slide, element, left, top, width, height, archetype=archetype)

    def _render_block(
        self,
        slide,
        element: PositionedElement,
        left,
        top,
        width,
        height,
        visual_style: Optional[VisualStyle] = None,
        archetype: Optional[str] = None
    ) -> None:
        """
        Render a standard block with visual effects.

        Args:
            slide: PowerPoint slide
            element: Element to render
            left, top, width, height: Position/size in EMU
            visual_style: Optional visual style override
            archetype: Optional archetype name for style selection
        """
        # Check if this is a pyramid element that should use custom geometry
        if archetype == "pyramid" and CUSTOM_SHAPES_AVAILABLE:
            # total_pyramid_levels is set in render() when counting pyramid elements
            total_levels = getattr(self, '_pyramid_level_count', 4)
            self._render_pyramid_block(slide, element, archetype, total_levels)
            return

        # Get visual style
        style = visual_style or self.get_style_for_element(element, archetype=archetype)

        # Get shape type from style or default
        shape_type = SHAPE_TYPE_MAP.get(style.shape_type, MSO_SHAPE.ROUNDED_RECTANGLE)

        # Create shape
        shape = slide.shapes.add_shape(
            shape_type,
            left, top, width, height
        )

        # Set corner radius for rounded rectangles
        if style.shape_type == ShapeType.ROUNDED_RECTANGLE:
            corner_pct = min(50000, int((element.corner_radius_inches / element.height_inches) * 100000))
            try:
                shape.adjustments[0] = corner_pct / 100000
            except (IndexError, TypeError):
                pass  # Some shapes don't have adjustments

        # Base fill color (used for gradient computation)
        base_color = element.fill_color if element.fill_color and element.fill_color != "transparent" else "#4A90A4"

        # Apply fill (solid or gradient)
        if style.gradient and style.gradient.enabled:
            # Gradient will be applied via XML
            # First set solid fill so shape has a base
            shape.fill.solid()
            shape.fill.fore_color.rgb = hex_to_rgb_color(base_color)
        elif element.fill_color and element.fill_color != "transparent":
            shape.fill.solid()
            shape.fill.fore_color.rgb = hex_to_rgb_color(element.fill_color)
        else:
            shape.fill.background()  # No fill

        # Border
        if element.stroke_color:
            shape.line.color.rgb = hex_to_rgb_color(element.stroke_color)
            shape.line.width = Pt(element.stroke_width_pt)
        else:
            shape.line.fill.background()  # No border

        # Apply visual effects via XML manipulation
        if style.gradient or style.shadow or style.bevel_enabled:
            apply_visual_effects_to_shape(shape, style, base_color)

        # Add text if present
        if element.text:
            self._apply_text(shape, element.text, element.height_inches)

    def _render_pyramid_block(
        self,
        slide,
        element: PositionedElement,
        archetype: str,
        total_pyramid_levels: int = 4,
    ) -> None:
        """
        Render a pyramid block using custom FREEFORM geometry.

        Creates proper triangular pyramid segments with pointed tops instead
        of basic trapezoid shapes. Extracts level information from element ID
        to generate appropriate geometry.

        Args:
            slide: PowerPoint slide
            element: The pyramid level element
            archetype: Archetype name (should be "pyramid")
            total_pyramid_levels: Total number of levels in the pyramid
        """
        # Parse level information from element ID (e.g., "level_0", "level_1")
        level_idx = 0
        total_levels = total_pyramid_levels

        if element.id and element.id.startswith("level_"):
            try:
                level_idx = int(element.id.split("_")[1])
            except (ValueError, IndexError):
                pass

        # Get shape from library
        library = get_shape_library()
        shapes = library.get_pyramid_shapes(total_levels)

        # Get the appropriate shape for this level
        if level_idx < len(shapes):
            pyramid_shape = shapes[level_idx]
        else:
            # Generate a fallback shape
            pyramid_shape = ShapeGenerator.create_pyramid_segment(
                level=level_idx,
                total_levels=total_levels,
                taper_ratio=0.12
            )

        # Fill color
        fill_color = element.fill_color if element.fill_color and element.fill_color != "transparent" else "#4472C4"

        # Determine if gradient and shadow should be used
        use_gradient = True
        use_shadow = True
        shadow_blur = 40.0  # Learned from Pyramida template

        # Check if stroke should be applied
        stroke_color = element.stroke_color if element.stroke_width_pt > 0 else None
        stroke_width = element.stroke_width_pt if stroke_color else 0

        # Render custom shape
        renderer = CustomShapeRenderer(slide)
        renderer.add_shape(
            shape=pyramid_shape,
            left=element.x_inches,
            top=element.y_inches,
            width=element.width_inches,
            height=element.height_inches,
            fill_color=fill_color,
            gradient=use_gradient,
            gradient_angle=270.0,  # Top to bottom
            shadow=use_shadow,
            shadow_blur_pt=shadow_blur,
            shadow_opacity=0.6,
            stroke_color=stroke_color,
            stroke_width_pt=stroke_width,
        )

        # Add text overlay if present
        if element.text:
            self._add_pyramid_text_overlay(slide, element, level_idx, total_levels)

    def _add_pyramid_text_overlay(
        self,
        slide,
        element: PositionedElement,
        level_idx: int = 0,
        total_levels: int = 4,
    ) -> None:
        """
        Add text overlay on top of a custom pyramid shape.

        For trapezoid/triangle shapes, the visual center is lower than the
        geometric center. We adjust the text position and width to fit
        within the visible shape area.

        Args:
            slide: PowerPoint slide
            element: The pyramid level element
            level_idx: Current level index (0=base, N-1=apex)
            total_levels: Total number of pyramid levels
        """
        if not element.text:
            return

        # For pyramid shapes, adjust text position based on shape geometry
        # The visible area of a trapezoid is wider at bottom than top
        # Text should be positioned in the center of the visible area

        # Calculate the average width of the shape (considering taper)
        # For trapezoids, the text area should be in the middle 60% of height
        # and horizontally centered based on average visible width

        is_apex = (level_idx == total_levels - 1)

        if is_apex:
            # Triangle apex - text goes in lower 2/3 where it's wider
            text_top = element.y_inches + element.height_inches * 0.35
            text_height = element.height_inches * 0.55
            # Width is narrower for apex - use 70% centered
            text_width = element.width_inches * 0.7
            text_left = element.x_inches + (element.width_inches - text_width) / 2
        else:
            # Trapezoid - text centered but slightly lower
            # The visible center is lower due to the taper
            text_top = element.y_inches + element.height_inches * 0.2
            text_height = element.height_inches * 0.6
            # Use 80% of width for text area (accounting for angled edges)
            text_width = element.width_inches * 0.8
            text_left = element.x_inches + (element.width_inches - text_width) / 2

        left = Emu(inches_to_emu(text_left))
        top = Emu(inches_to_emu(text_top))
        width = Emu(inches_to_emu(text_width))
        height = Emu(inches_to_emu(text_height))

        textbox = slide.shapes.add_textbox(left, top, width, height)
        self._apply_text(textbox, element.text, text_height)

    def _render_band(self, slide, element: PositionedElement, left, top, width, height) -> None:
        """Render a full-width band (rectangle)."""
        shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            left, top, width, height
        )

        # Fill with semi-transparency
        if element.fill_color and element.fill_color != "transparent":
            shape.fill.solid()
            shape.fill.fore_color.rgb = hex_to_rgb_color(element.fill_color)

            # Set transparency if specified
            if element.opacity < 1.0:
                # Transparency is inverted (0 = opaque, 100000 = transparent)
                transparency = int((1 - element.opacity) * 100000)
                shape.fill.fore_color.brightness = 0  # Reset brightness
                # Note: python-pptx doesn't directly support fill transparency
                # Would need to modify XML directly for true transparency
        else:
            shape.fill.background()

        # No border for bands
        shape.line.fill.background()

        # Add text
        if element.text:
            self._apply_text(shape, element.text, element.height_inches)

    def _render_title(self, slide, element: PositionedElement, left, top, width, height) -> None:
        """Render title text."""
        if not element.text:
            return

        # Use text box for title
        textbox = slide.shapes.add_textbox(left, top, width, height)
        self._apply_text(textbox, element.text, element.height_inches, is_title=True)

    def _render_subtitle(self, slide, element: PositionedElement, left, top, width, height) -> None:
        """Render subtitle text."""
        if not element.text:
            return

        textbox = slide.shapes.add_textbox(left, top, width, height)
        self._apply_text(textbox, element.text, element.height_inches)

    def _render_label(self, slide, element: PositionedElement, left, top, width, height) -> None:
        """Render a text label."""
        if not element.text:
            return

        textbox = slide.shapes.add_textbox(left, top, width, height)
        self._apply_text(textbox, element.text, element.height_inches)

    # =========================================================================
    # TEXT APPLICATION (CRITICAL - PREVENTS OVERFLOW)
    # =========================================================================

    def _apply_text(
        self,
        shape,
        text: PositionedText,
        container_height: float,
        is_title: bool = False
    ) -> None:
        """
        Apply pre-measured text to a shape.

        CRITICAL: Uses pre-computed font sizes and line breaks.
        Never lets PowerPoint auto-size or wrap text.
        """
        tf = shape.text_frame

        # CRITICAL: Disable auto-size — we computed the font size
        tf.auto_size = None  # Explicitly None to prevent any auto-sizing

        # Set margins (minimal)
        tf.margin_left = Emu(inches_to_emu(0.05))
        tf.margin_right = Emu(inches_to_emu(0.05))
        tf.margin_top = Emu(inches_to_emu(0.03))
        tf.margin_bottom = Emu(inches_to_emu(0.03))

        # Vertical centering
        tf.anchor = MSO_ANCHOR.MIDDLE

        # Word wrap — only if multiple lines
        tf.word_wrap = len(text.lines) > 1

        # Clear existing paragraphs and add new ones
        for i, line in enumerate(text.lines):
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()

            p.text = line
            p.alignment = get_alignment(text.alignment)

            # Apply font formatting to the run
            if p.runs:
                run = p.runs[0]
            else:
                run = p.add_run()
                run.text = line

            # CRITICAL: Use pre-computed font size
            run.font.size = Pt(text.font_size_pt)
            run.font.name = text.font_family
            run.font.bold = text.bold
            run.font.italic = text.italic

            if text.color and text.color != "transparent":
                run.font.color.rgb = hex_to_rgb_color(text.color)

            # Line spacing for multi-line text
            if len(text.lines) > 1:
                p.line_spacing = 1.15

    # =========================================================================
    # CONNECTOR RENDERING
    # =========================================================================

    def _render_connector(self, slide, connector: PositionedConnector) -> None:
        """Render a connector line using a freeform shape for precise positioning."""
        from pptx.oxml.ns import nsmap
        from pptx.oxml import parse_xml
        from lxml import etree

        start_x_emu = inches_to_emu(connector.start_x)
        start_y_emu = inches_to_emu(connector.start_y)
        end_x_emu = inches_to_emu(connector.end_x)
        end_y_emu = inches_to_emu(connector.end_y)

        # Calculate bounding box
        min_x = min(start_x_emu, end_x_emu)
        min_y = min(start_y_emu, end_y_emu)
        width = abs(end_x_emu - start_x_emu)
        height = abs(end_y_emu - start_y_emu)

        # Ensure minimum size
        if width < 1:
            width = 1
        if height < 1:
            height = 1

        # Calculate relative positions within bounding box (0-based)
        # These are relative to the top-left of the bounding box
        rel_start_x = start_x_emu - min_x
        rel_start_y = start_y_emu - min_y
        rel_end_x = end_x_emu - min_x
        rel_end_y = end_y_emu - min_y

        # Create a freeform/path shape via XML for precise line positioning
        # This gives us exact control over start and end points

        # Build the shape XML
        nsmap_a = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}

        sp_xml = f'''
        <p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
              xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
          <p:nvSpPr>
            <p:cNvPr id="0" name="Line"/>
            <p:cNvSpPr/>
            <p:nvPr/>
          </p:nvSpPr>
          <p:spPr>
            <a:xfrm>
              <a:off x="{min_x}" y="{min_y}"/>
              <a:ext cx="{width}" cy="{height}"/>
            </a:xfrm>
            <a:custGeom>
              <a:avLst/>
              <a:gdLst/>
              <a:ahLst/>
              <a:cxnLst/>
              <a:rect l="0" t="0" r="0" b="0"/>
              <a:pathLst>
                <a:path w="{width}" h="{height}">
                  <a:moveTo>
                    <a:pt x="{rel_start_x}" y="{rel_start_y}"/>
                  </a:moveTo>
                  <a:lnTo>
                    <a:pt x="{rel_end_x}" y="{rel_end_y}"/>
                  </a:lnTo>
                </a:path>
              </a:pathLst>
            </a:custGeom>
            <a:ln w="{int(connector.stroke_width_pt * 12700)}">
              <a:solidFill>
                <a:srgbClr val="{connector.color.lstrip('#')}"/>
              </a:solidFill>
            </a:ln>
          </p:spPr>
          <p:txBody>
            <a:bodyPr/>
            <a:lstStyle/>
            <a:p/>
          </p:txBody>
        </p:sp>
        '''

        # Parse and add to slide
        sp_element = etree.fromstring(sp_xml)
        slide.shapes._spTree.append(sp_element)

        # For arrow heads, we need to add them via XML as well
        if connector.style in [ConnectorStyle.ARROW, ConnectorStyle.DASHED, ConnectorStyle.BIDIRECTIONAL]:
            self._add_arrow_to_xml(sp_element, connector.style)

        # Add label if present
        if connector.label:
            self._add_connector_label(slide, connector)

    def _add_arrow_to_xml(self, sp_element, style: ConnectorStyle) -> None:
        """Add arrowhead(s) to a shape via XML."""
        try:
            nsmap_a = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
            ln = sp_element.find('.//a:ln', nsmap_a)
            if ln is not None:
                # Add end arrow
                tail_end = etree.SubElement(ln, '{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd')
                tail_end.set('type', 'triangle')
                tail_end.set('w', 'med')
                tail_end.set('len', 'med')

                # Add start arrow for bidirectional
                if style == ConnectorStyle.BIDIRECTIONAL:
                    head_end = etree.SubElement(ln, '{http://schemas.openxmlformats.org/drawingml/2006/main}headEnd')
                    head_end.set('type', 'triangle')
                    head_end.set('w', 'med')
                    head_end.set('len', 'med')

                # Add dash for dashed style
                if style == ConnectorStyle.DASHED:
                    prstDash = etree.SubElement(ln, '{http://schemas.openxmlformats.org/drawingml/2006/main}prstDash')
                    prstDash.set('val', 'dash')
        except Exception:
            pass

    def _add_end_arrow(self, shape) -> None:
        """Add arrowhead to end of connector."""
        # Access line element and add arrow
        try:
            line = shape.line
            # Set end arrow using underlying XML
            spPr = shape._element.spPr
            ln = spPr.find(qn('a:ln'))
            if ln is not None:
                tailEnd = parse_xml(
                    '<a:tailEnd xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                    'type="triangle" w="med" len="med"/>'
                )
                ln.append(tailEnd)
        except Exception:
            pass  # Arrow heads may fail in some cases

    def _add_start_arrow(self, shape) -> None:
        """Add arrowhead to start of connector."""
        try:
            spPr = shape._element.spPr
            ln = spPr.find(qn('a:ln'))
            if ln is not None:
                headEnd = parse_xml(
                    '<a:headEnd xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                    'type="triangle" w="med" len="med"/>'
                )
                ln.append(headEnd)
        except Exception:
            pass

    def _add_connector_label(self, slide, connector: PositionedConnector) -> None:
        """Add a text label at connector midpoint."""
        if not connector.label:
            return

        # Position label at midpoint
        mid_x = connector.midpoint_x
        mid_y = connector.midpoint_y

        # Small textbox for label
        label_width = 1.5
        label_height = 0.3

        left = Emu(inches_to_emu(mid_x - label_width / 2))
        top = Emu(inches_to_emu(mid_y - label_height / 2))
        width = Emu(inches_to_emu(label_width))
        height = Emu(inches_to_emu(label_height))

        textbox = slide.shapes.add_textbox(left, top, width, height)
        self._apply_text(textbox, connector.label, label_height)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def render_to_pptx(
    layout: PositionedLayout,
    output_path: Optional[str] = None,
    style: Optional[VisualStyle] = None
) -> bytes:
    """
    Convenience function to render a layout to PPTX.

    Args:
        layout: PositionedLayout to render
        output_path: Optional file path to save to
        style: Optional visual style (defaults to STYLE_PROFESSIONAL)

    Returns:
        PPTX file bytes
    """
    renderer = PPTXRenderer(default_style=style)
    if output_path:
        renderer.render_to_file(layout, output_path)
        with open(output_path, 'rb') as f:
            return f.read()
    else:
        return renderer.render(layout)


def render_to_bytes(
    layout: PositionedLayout,
    style: Optional[VisualStyle] = None
) -> bytes:
    """Render layout to PPTX bytes (for API responses)."""
    renderer = PPTXRenderer(default_style=style)
    return renderer.render(layout)


def render_styled(
    layout: PositionedLayout,
    style_name: str = "professional",
    output_path: Optional[str] = None
) -> bytes:
    """
    Render a layout with a named visual style preset.

    Args:
        layout: PositionedLayout to render
        style_name: Style preset name: "flat", "subtle_3d", "professional", "executive", "pyramid"
        output_path: Optional output file path

    Returns:
        PPTX file bytes
    """
    style_map = {
        "flat": STYLE_FLAT,
        "subtle_3d": STYLE_SUBTLE_3D,
        "professional": STYLE_PROFESSIONAL,
        "executive": STYLE_EXECUTIVE,
        "pyramid": STYLE_PYRAMID_LEVEL,
    }

    style = style_map.get(style_name.lower(), STYLE_PROFESSIONAL)
    return render_to_pptx(layout, output_path, style)


def render_presentation_to_pptx(
    presentation: MultiSlidePresentation,
    output_path: Optional[str] = None
) -> bytes:
    """
    Convenience function to render a multi-slide presentation to PPTX.

    Args:
        presentation: MultiSlidePresentation to render
        output_path: Optional file path to save to

    Returns:
        PPTX file bytes
    """
    renderer = PPTXRenderer()
    if output_path:
        return renderer.render_presentation(presentation, output_path)
    else:
        return renderer.render_presentation(presentation)


def render_presentation_to_bytes(presentation: MultiSlidePresentation) -> bytes:
    """Render multi-slide presentation to PPTX bytes (for API responses)."""
    renderer = PPTXRenderer()
    return renderer.render_presentation(presentation)


def create_presentation_from_layouts(
    layouts: list,
    title: str = "Presentation"
) -> MultiSlidePresentation:
    """
    Create a MultiSlidePresentation from a list of PositionedLayout objects.

    Args:
        layouts: List of PositionedLayout objects
        title: Presentation title

    Returns:
        MultiSlidePresentation containing all slides
    """
    from datetime import datetime

    presentation = MultiSlidePresentation(
        presentation_title=title,
        created_at=datetime.now().isoformat(),
    )

    for layout in layouts:
        presentation.add_slide(layout)

    return presentation
