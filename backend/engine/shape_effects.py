"""
shape_effects.py — Professional visual effects for shapes.

This module provides:
1. Enhanced visual effect data models (3D bevels, shadows, gradients)
2. Professional effect presets learned from templates
3. Effect extraction from template shapes
4. Effect synthesis for generating new combinations

These effects are UNIVERSAL - they apply to ALL shape types (funnels, pyramids,
process flows, etc.) and enable the system to:
- Replicate professional template quality
- Generate new shapes with learned visual principles
- Create variations with consistent professional polish
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import math
import colorsys


# =============================================================================
# VISUAL EFFECT DATA MODELS
# =============================================================================

class BevelType(Enum):
    """3D bevel presets matching PowerPoint options."""
    NONE = "none"
    SOFT_ROUND = "softRound"        # Soft, rounded bevel (most common)
    ROUND = "round"                  # Standard rounded bevel
    RELAXED_INSET = "relaxedInset"  # Subtle inset
    CROSS = "cross"                  # Cross pattern
    ANGLE = "angle"                  # Angular bevel
    SLOPE = "slope"                  # Sloped edge
    CONVEX = "convex"               # Convex surface
    COOL_SLANT = "coolSlant"        # Modern slanted
    DIVOT = "divot"                 # Indented center
    RIBLET = "riblet"               # Ribbed texture
    HARD_EDGE = "hardEdge"          # Sharp 3D edge
    ART_DECO = "artDeco"            # Art deco style


class ShadowDirection(Enum):
    """Shadow direction presets."""
    BOTTOM_RIGHT = 135      # Classic diagonal (default for many tools)
    BOTTOM = 90            # Directly below (more natural light source)
    BOTTOM_LEFT = 45       # Diagonal left
    RIGHT = 180            # Right side shadow
    TOP_RIGHT = 315        # Light from below
    CUSTOM = 0             # Use exact angle


class GradientType(Enum):
    """Gradient fill types."""
    LINEAR = "linear"
    RADIAL = "radial"
    PATH = "path"          # Follows shape path


@dataclass
class GradientStop:
    """A single stop in a gradient."""
    position: float        # 0.0 to 1.0
    color: str             # Hex color
    transparency: float = 0.0  # 0.0 = opaque, 1.0 = fully transparent

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": self.position,
            "color": self.color,
            "transparency": self.transparency,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GradientStop":
        return cls(
            position=data.get("position", 0.0),
            color=data.get("color", "#FFFFFF"),
            transparency=data.get("transparency", 0.0),
        )


@dataclass
class GradientConfig:
    """Complete gradient configuration."""
    type: GradientType = GradientType.LINEAR
    angle: float = 270.0    # Degrees (270 = top to bottom)
    stops: List[GradientStop] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "angle": self.angle,
            "stops": [s.to_dict() for s in self.stops],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GradientConfig":
        return cls(
            type=GradientType(data.get("type", "linear")),
            angle=data.get("angle", 270.0),
            stops=[GradientStop.from_dict(s) for s in data.get("stops", [])],
        )


@dataclass
class ShadowConfig:
    """Shadow effect configuration."""
    enabled: bool = True
    blur_radius_pt: float = 12.0    # Blur radius in points (8-15 is professional)
    distance_inches: float = 0.06   # Distance from shape
    direction_degrees: float = 90.0  # Direction (90 = straight down)
    color: str = "#000000"          # Shadow color
    transparency: float = 0.6       # 0.0 = solid, 1.0 = invisible

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "blur_radius_pt": self.blur_radius_pt,
            "distance_inches": self.distance_inches,
            "direction_degrees": self.direction_degrees,
            "color": self.color,
            "transparency": self.transparency,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShadowConfig":
        return cls(
            enabled=data.get("enabled", True),
            blur_radius_pt=data.get("blur_radius_pt", 12.0),
            distance_inches=data.get("distance_inches", 0.06),
            direction_degrees=data.get("direction_degrees", 90.0),
            color=data.get("color", "#000000"),
            transparency=data.get("transparency", 0.6),
        )


@dataclass
class BevelConfig:
    """3D bevel effect configuration."""
    enabled: bool = True
    type: BevelType = BevelType.SOFT_ROUND
    width_inches: float = 0.028     # Bevel width
    height_inches: float = 0.028    # Bevel height (depth)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "type": self.type.value,
            "width_inches": self.width_inches,
            "height_inches": self.height_inches,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BevelConfig":
        return cls(
            enabled=data.get("enabled", True),
            type=BevelType(data.get("type", "softRound")),
            width_inches=data.get("width_inches", 0.028),
            height_inches=data.get("height_inches", 0.028),
        )


@dataclass
class StrokeConfig:
    """Shape outline/stroke configuration."""
    enabled: bool = True
    color: str = "#CCCCCC"
    width_pt: float = 1.0
    transparency: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "color": self.color,
            "width_pt": self.width_pt,
            "transparency": self.transparency,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrokeConfig":
        return cls(
            enabled=data.get("enabled", True),
            color=data.get("color", "#CCCCCC"),
            width_pt=data.get("width_pt", 1.0),
            transparency=data.get("transparency", 0.0),
        )


# =============================================================================
# NEW VISUAL EFFECTS (Phase 3)
# =============================================================================

@dataclass
class GlowConfig:
    """
    Outer glow effect configuration.

    Creates a soft colored glow around the shape edge.
    Used for emphasis, highlighting, or creating a "selected" appearance.
    """
    enabled: bool = True
    radius_pt: float = 50.0             # Glow spread radius in points (EMU = pt * 12700)
    color: str = "#FFFFFF"              # Glow color
    transparency: float = 0.4           # 0.0 = opaque glow, 1.0 = invisible

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "radius_pt": self.radius_pt,
            "color": self.color,
            "transparency": self.transparency,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GlowConfig":
        return cls(
            enabled=data.get("enabled", True),
            radius_pt=data.get("radius_pt", 50.0),
            color=data.get("color", "#FFFFFF"),
            transparency=data.get("transparency", 0.4),
        )

    def to_emu_radius(self) -> int:
        """Convert radius from points to EMU."""
        return int(self.radius_pt * 12700)

    def to_alpha_percent(self) -> int:
        """Convert transparency to alpha percentage (0-100000)."""
        return int((1.0 - self.transparency) * 100000)


@dataclass
class ReflectionConfig:
    """
    Reflection effect configuration.

    Creates a mirror reflection below the shape, typically fading out.
    Common in glossy/glass UI designs.
    """
    enabled: bool = True
    blur_radius_pt: float = 0.5         # Blur radius for reflection edge
    start_opacity: float = 0.5          # Opacity at top of reflection (0-1)
    end_opacity: float = 0.0            # Opacity at bottom of reflection (0-1)
    distance_pt: float = 0.0            # Gap between shape and reflection
    direction_degrees: float = 90.0     # Direction (90 = straight down)
    scale_y: float = 0.5                # Vertical scale of reflection (0.5 = half height)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "blur_radius_pt": self.blur_radius_pt,
            "start_opacity": self.start_opacity,
            "end_opacity": self.end_opacity,
            "distance_pt": self.distance_pt,
            "direction_degrees": self.direction_degrees,
            "scale_y": self.scale_y,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReflectionConfig":
        return cls(
            enabled=data.get("enabled", True),
            blur_radius_pt=data.get("blur_radius_pt", 0.5),
            start_opacity=data.get("start_opacity", 0.5),
            end_opacity=data.get("end_opacity", 0.0),
            distance_pt=data.get("distance_pt", 0.0),
            direction_degrees=data.get("direction_degrees", 90.0),
            scale_y=data.get("scale_y", 0.5),
        )

    def to_blur_emu(self) -> int:
        """Convert blur radius to EMU."""
        return int(self.blur_radius_pt * 12700)

    def to_start_alpha(self) -> int:
        """Convert start opacity to DrawingML alpha (0-100000)."""
        return int(self.start_opacity * 100000)

    def to_end_alpha(self) -> int:
        """Convert end opacity to DrawingML alpha (0-100000)."""
        return int(self.end_opacity * 100000)

    def to_direction_emu(self) -> int:
        """Convert direction to EMU degrees (60000ths of a degree)."""
        return int(self.direction_degrees * 60000)

    def to_scale_percent(self) -> int:
        """Convert scale to DrawingML percentage (100000 = 100%)."""
        return int(self.scale_y * 100000)


@dataclass
class SoftEdgeConfig:
    """
    Soft edge effect configuration.

    Blurs the edges of the shape to create a soft, feathered appearance.
    Useful for backgrounds or decorative elements.
    """
    enabled: bool = True
    radius_pt: float = 2.0              # Soft edge radius in points

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "radius_pt": self.radius_pt,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SoftEdgeConfig":
        return cls(
            enabled=data.get("enabled", True),
            radius_pt=data.get("radius_pt", 2.0),
        )

    def to_emu_radius(self) -> int:
        """Convert radius from points to EMU."""
        return int(self.radius_pt * 12700)


@dataclass
class VisualEffects:
    """
    Complete visual effects configuration for a shape.

    This encapsulates ALL visual properties that make shapes look professional:
    - Gradient fills with precise stop positioning
    - Shadows with proper blur and direction
    - 3D bevel effects
    - Stroke/outline styling
    - Glow effects for emphasis (Phase 3)
    - Reflection for glossy appearance (Phase 3)
    - Soft edges for feathered look (Phase 3)
    """
    gradient: Optional[GradientConfig] = None
    shadow: Optional[ShadowConfig] = None
    bevel: Optional[BevelConfig] = None
    stroke: Optional[StrokeConfig] = None

    # Phase 3: Additional visual effects
    glow: Optional[GlowConfig] = None           # Outer glow effect
    reflection: Optional[ReflectionConfig] = None  # Mirror reflection below shape
    soft_edge: Optional[SoftEdgeConfig] = None  # Soft/feathered edges

    # Quality metrics (learned from templates)
    path_complexity: int = 0           # Number of bezier curves
    uses_elliptical_edges: bool = False  # Has curved top/bottom edges
    professional_score: float = 0.0    # 0-100 quality score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gradient": self.gradient.to_dict() if self.gradient else None,
            "shadow": self.shadow.to_dict() if self.shadow else None,
            "bevel": self.bevel.to_dict() if self.bevel else None,
            "stroke": self.stroke.to_dict() if self.stroke else None,
            "glow": self.glow.to_dict() if self.glow else None,
            "reflection": self.reflection.to_dict() if self.reflection else None,
            "soft_edge": self.soft_edge.to_dict() if self.soft_edge else None,
            "path_complexity": self.path_complexity,
            "uses_elliptical_edges": self.uses_elliptical_edges,
            "professional_score": self.professional_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisualEffects":
        return cls(
            gradient=GradientConfig.from_dict(data["gradient"]) if data.get("gradient") else None,
            shadow=ShadowConfig.from_dict(data["shadow"]) if data.get("shadow") else None,
            bevel=BevelConfig.from_dict(data["bevel"]) if data.get("bevel") else None,
            stroke=StrokeConfig.from_dict(data["stroke"]) if data.get("stroke") else None,
            glow=GlowConfig.from_dict(data["glow"]) if data.get("glow") else None,
            reflection=ReflectionConfig.from_dict(data["reflection"]) if data.get("reflection") else None,
            soft_edge=SoftEdgeConfig.from_dict(data["soft_edge"]) if data.get("soft_edge") else None,
            path_complexity=data.get("path_complexity", 0),
            uses_elliptical_edges=data.get("uses_elliptical_edges", False),
            professional_score=data.get("professional_score", 0.0),
        )

    @property
    def has_glow(self) -> bool:
        """Check if glow effect is enabled."""
        return self.glow is not None and self.glow.enabled

    @property
    def has_reflection(self) -> bool:
        """Check if reflection effect is enabled."""
        return self.reflection is not None and self.reflection.enabled

    @property
    def has_soft_edge(self) -> bool:
        """Check if soft edge effect is enabled."""
        return self.soft_edge is not None and self.soft_edge.enabled


# =============================================================================
# PROFESSIONAL EFFECT PRESETS
# =============================================================================

class EffectPresets:
    """
    Professional visual effect presets learned from analyzing templates.

    These presets capture the visual principles that make professional
    infographics look polished. They can be applied to ANY shape type.
    """

    # -------------------------------------------------------------------------
    # SHADOW PRESETS
    # -------------------------------------------------------------------------

    @staticmethod
    def shadow_subtle() -> ShadowConfig:
        """Subtle, professional shadow - minimal but adds depth."""
        return ShadowConfig(
            enabled=True,
            blur_radius_pt=8.0,
            distance_inches=0.04,
            direction_degrees=90.0,  # Straight down
            color="#000000",
            transparency=0.7,
        )

    @staticmethod
    def shadow_soft() -> ShadowConfig:
        """Soft shadow - balanced visibility and subtlety."""
        return ShadowConfig(
            enabled=True,
            blur_radius_pt=12.0,
            distance_inches=0.06,
            direction_degrees=90.0,
            color="#000000",
            transparency=0.6,
        )

    @staticmethod
    def shadow_elevated() -> ShadowConfig:
        """Elevated shadow - shape appears to float above background."""
        return ShadowConfig(
            enabled=True,
            blur_radius_pt=15.0,
            distance_inches=0.10,
            direction_degrees=90.0,
            color="#000000",
            transparency=0.5,
        )

    @staticmethod
    def shadow_dramatic() -> ShadowConfig:
        """Dramatic shadow - strong visual emphasis."""
        return ShadowConfig(
            enabled=True,
            blur_radius_pt=20.0,
            distance_inches=0.14,
            direction_degrees=120.0,  # Slightly diagonal
            color="#000000",
            transparency=0.4,
        )

    # -------------------------------------------------------------------------
    # BEVEL PRESETS
    # -------------------------------------------------------------------------

    @staticmethod
    def bevel_soft_3d() -> BevelConfig:
        """Soft 3D bevel - the most common professional look."""
        return BevelConfig(
            enabled=True,
            type=BevelType.SOFT_ROUND,
            width_inches=0.028,
            height_inches=0.028,
        )

    @staticmethod
    def bevel_subtle() -> BevelConfig:
        """Very subtle bevel - minimal 3D effect."""
        return BevelConfig(
            enabled=True,
            type=BevelType.SOFT_ROUND,
            width_inches=0.015,
            height_inches=0.015,
        )

    @staticmethod
    def bevel_prominent() -> BevelConfig:
        """Prominent bevel - strong 3D appearance."""
        return BevelConfig(
            enabled=True,
            type=BevelType.ROUND,
            width_inches=0.045,
            height_inches=0.045,
        )

    @staticmethod
    def bevel_modern() -> BevelConfig:
        """Modern bevel - clean, contemporary look."""
        return BevelConfig(
            enabled=True,
            type=BevelType.COOL_SLANT,
            width_inches=0.035,
            height_inches=0.025,
        )

    # -------------------------------------------------------------------------
    # GLOW PRESETS (Phase 3)
    # -------------------------------------------------------------------------

    @staticmethod
    def glow_subtle(color: str = "#FFFFFF") -> GlowConfig:
        """Subtle glow - minimal but adds emphasis."""
        return GlowConfig(
            enabled=True,
            radius_pt=30.0,
            color=color,
            transparency=0.6,
        )

    @staticmethod
    def glow_soft(color: str = "#FFFFFF") -> GlowConfig:
        """Soft glow - balanced visibility for highlighting."""
        return GlowConfig(
            enabled=True,
            radius_pt=50.0,
            color=color,
            transparency=0.4,
        )

    @staticmethod
    def glow_prominent(color: str = "#FFFFFF") -> GlowConfig:
        """Prominent glow - strong visual emphasis."""
        return GlowConfig(
            enabled=True,
            radius_pt=80.0,
            color=color,
            transparency=0.3,
        )

    @staticmethod
    def glow_neon(color: str = "#00FFFF") -> GlowConfig:
        """Neon glow - vibrant, saturated effect."""
        return GlowConfig(
            enabled=True,
            radius_pt=100.0,
            color=color,
            transparency=0.2,
        )

    # -------------------------------------------------------------------------
    # REFLECTION PRESETS (Phase 3)
    # -------------------------------------------------------------------------

    @staticmethod
    def reflection_subtle() -> ReflectionConfig:
        """Subtle reflection - minimal mirror effect."""
        return ReflectionConfig(
            enabled=True,
            blur_radius_pt=0.5,
            start_opacity=0.3,
            end_opacity=0.0,
            distance_pt=0.0,
            direction_degrees=90.0,
            scale_y=0.35,
        )

    @staticmethod
    def reflection_glass() -> ReflectionConfig:
        """Glass reflection - glossy UI appearance."""
        return ReflectionConfig(
            enabled=True,
            blur_radius_pt=0.5,
            start_opacity=0.5,
            end_opacity=0.0,
            distance_pt=0.0,
            direction_degrees=90.0,
            scale_y=0.5,
        )

    @staticmethod
    def reflection_floor() -> ReflectionConfig:
        """Floor reflection - as if on reflective surface."""
        return ReflectionConfig(
            enabled=True,
            blur_radius_pt=2.0,
            start_opacity=0.4,
            end_opacity=0.0,
            distance_pt=2.0,  # Small gap
            direction_degrees=90.0,
            scale_y=0.6,
        )

    # -------------------------------------------------------------------------
    # SOFT EDGE PRESETS (Phase 3)
    # -------------------------------------------------------------------------

    @staticmethod
    def soft_edge_subtle() -> SoftEdgeConfig:
        """Subtle soft edge - minimal blur."""
        return SoftEdgeConfig(
            enabled=True,
            radius_pt=1.5,
        )

    @staticmethod
    def soft_edge_medium() -> SoftEdgeConfig:
        """Medium soft edge - noticeable feathering."""
        return SoftEdgeConfig(
            enabled=True,
            radius_pt=3.0,
        )

    @staticmethod
    def soft_edge_strong() -> SoftEdgeConfig:
        """Strong soft edge - significant blur for backgrounds."""
        return SoftEdgeConfig(
            enabled=True,
            radius_pt=6.0,
        )

    # -------------------------------------------------------------------------
    # GRADIENT PRESETS
    # -------------------------------------------------------------------------

    @staticmethod
    def gradient_highlight(base_color: str) -> GradientConfig:
        """
        Gradient with highlight effect - bright spot at top.

        This is the KEY difference from amateur gradients:
        - Stop at 15% creates a "shine" effect
        - Makes shapes look 3D and glossy
        """
        lighter = EffectPresets._lighten_color(base_color, 0.3)
        darker = EffectPresets._darken_color(base_color, 0.3)

        return GradientConfig(
            type=GradientType.LINEAR,
            angle=270.0,  # Top to bottom
            stops=[
                GradientStop(position=0.0, color=lighter),
                GradientStop(position=0.15, color=base_color),  # KEY: 15% stop
                GradientStop(position=1.0, color=darker),
            ],
        )

    @staticmethod
    def gradient_glass(base_color: str) -> GradientConfig:
        """Glass/glossy gradient - reflective surface appearance."""
        lighter = EffectPresets._lighten_color(base_color, 0.4)
        mid_light = EffectPresets._lighten_color(base_color, 0.15)
        darker = EffectPresets._darken_color(base_color, 0.25)

        return GradientConfig(
            type=GradientType.LINEAR,
            angle=270.0,
            stops=[
                GradientStop(position=0.0, color=lighter),
                GradientStop(position=0.10, color=mid_light),  # Quick transition
                GradientStop(position=0.50, color=base_color),
                GradientStop(position=1.0, color=darker),
            ],
        )

    @staticmethod
    def gradient_depth(base_color: str) -> GradientConfig:
        """Depth gradient - creates sense of dimension."""
        lighter = EffectPresets._lighten_color(base_color, 0.2)
        darker = EffectPresets._darken_color(base_color, 0.35)

        return GradientConfig(
            type=GradientType.LINEAR,
            angle=270.0,
            stops=[
                GradientStop(position=0.0, color=lighter),
                GradientStop(position=0.5, color=base_color),
                GradientStop(position=1.0, color=darker),
            ],
        )

    @staticmethod
    def gradient_flat_modern(base_color: str) -> GradientConfig:
        """Modern flat gradient - subtle but adds polish."""
        slightly_lighter = EffectPresets._lighten_color(base_color, 0.08)
        slightly_darker = EffectPresets._darken_color(base_color, 0.08)

        return GradientConfig(
            type=GradientType.LINEAR,
            angle=270.0,
            stops=[
                GradientStop(position=0.0, color=slightly_lighter),
                GradientStop(position=1.0, color=slightly_darker),
            ],
        )

    # -------------------------------------------------------------------------
    # COMPLETE EFFECT COMBINATIONS
    # -------------------------------------------------------------------------

    @staticmethod
    def professional_3d(base_color: str) -> VisualEffects:
        """
        Complete professional 3D effect - the gold standard.

        Combines all elements that make professional templates look polished:
        - Highlight gradient (15% stop)
        - Soft shadow (12pt blur, 90 degree)
        - Soft round bevel
        """
        return VisualEffects(
            gradient=EffectPresets.gradient_highlight(base_color),
            shadow=EffectPresets.shadow_soft(),
            bevel=EffectPresets.bevel_soft_3d(),
            stroke=StrokeConfig(enabled=True, color="#CCCCCC", width_pt=1.0),
            professional_score=95.0,
        )

    @staticmethod
    def modern_minimal(base_color: str) -> VisualEffects:
        """Modern minimal style - clean with subtle depth."""
        return VisualEffects(
            gradient=EffectPresets.gradient_flat_modern(base_color),
            shadow=EffectPresets.shadow_subtle(),
            bevel=None,  # No bevel for minimal look
            stroke=StrokeConfig(enabled=False),
            professional_score=85.0,
        )

    @staticmethod
    def glossy_premium(base_color: str) -> VisualEffects:
        """Glossy premium style - high-end corporate look."""
        return VisualEffects(
            gradient=EffectPresets.gradient_glass(base_color),
            shadow=EffectPresets.shadow_elevated(),
            bevel=EffectPresets.bevel_prominent(),
            stroke=StrokeConfig(enabled=True, color="#FFFFFF", width_pt=0.5, transparency=0.5),
            professional_score=90.0,
        )

    @staticmethod
    def flat_material(base_color: str) -> VisualEffects:
        """Material design inspired - flat with subtle shadow."""
        return VisualEffects(
            gradient=None,  # Solid color
            shadow=EffectPresets.shadow_soft(),
            bevel=None,
            stroke=StrokeConfig(enabled=False),
            professional_score=80.0,
        )

    # -------------------------------------------------------------------------
    # COLOR UTILITIES
    # -------------------------------------------------------------------------

    @staticmethod
    def _lighten_color(hex_color: str, factor: float) -> str:
        """Lighten a hex color by a factor (0-1)."""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0

        # Convert to HLS
        h, l, s = colorsys.rgb_to_hls(r, g, b)

        # Increase lightness
        l = min(1.0, l + (1.0 - l) * factor)

        # Convert back
        r, g, b = colorsys.hls_to_rgb(h, l, s)

        return f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"

    @staticmethod
    def _darken_color(hex_color: str, factor: float) -> str:
        """Darken a hex color by a factor (0-1)."""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0

        # Convert to HLS
        h, l, s = colorsys.rgb_to_hls(r, g, b)

        # Decrease lightness
        l = max(0.0, l * (1.0 - factor))

        # Convert back
        r, g, b = colorsys.hls_to_rgb(h, l, s)

        return f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"


# =============================================================================
# EFFECT EXTRACTOR - Learn effects from templates
# =============================================================================

class EffectExtractor:
    """
    Extracts visual effects from template shapes.

    Analyzes the DrawingML XML to extract:
    - Gradient configurations (stops, angles)
    - Shadow parameters (blur, distance, direction)
    - 3D bevel effects
    - Stroke styling
    - Path complexity metrics
    """

    def __init__(self):
        self.ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}

    def extract_effects(self, shape) -> VisualEffects:
        """Extract all visual effects from a shape."""
        effects = VisualEffects()

        try:
            spPr = shape._element.spPr
            if spPr is None:
                return effects

            # Extract gradient
            effects.gradient = self._extract_gradient(spPr)

            # Extract shadow
            effects.shadow = self._extract_shadow(spPr)

            # Extract bevel
            effects.bevel = self._extract_bevel(spPr)

            # Extract stroke
            effects.stroke = self._extract_stroke(shape)

            # Calculate path complexity
            effects.path_complexity = self._calculate_path_complexity(spPr)
            effects.uses_elliptical_edges = self._has_elliptical_edges(spPr)

            # Calculate professional score
            effects.professional_score = self._calculate_professional_score(effects)

        except Exception as e:
            pass  # Return default effects on error

        return effects

    def _extract_gradient(self, spPr) -> Optional[GradientConfig]:
        """Extract gradient configuration from spPr element."""
        gradFill = spPr.find('.//a:gradFill', self.ns)
        if gradFill is None:
            return None

        config = GradientConfig()

        # Get gradient type
        path = gradFill.find('.//a:path', self.ns)
        if path is not None:
            config.type = GradientType.PATH
        else:
            lin = gradFill.find('.//a:lin', self.ns)
            if lin is not None:
                config.type = GradientType.LINEAR
                ang = lin.get('ang')
                if ang:
                    config.angle = int(ang) / 60000

        # Get gradient stops
        gsLst = gradFill.find('.//a:gsLst', self.ns)
        if gsLst is not None:
            for gs in gsLst.findall('.//a:gs', self.ns):
                pos = gs.get('pos')
                position = int(pos) / 100000 if pos else 0.0

                # Get color
                color = "#FFFFFF"
                srgbClr = gs.find('.//a:srgbClr', self.ns)
                if srgbClr is not None:
                    color = f"#{srgbClr.get('val', 'FFFFFF')}"

                # Get transparency
                transparency = 0.0
                alpha = gs.find('.//a:alpha', self.ns)
                if alpha is not None:
                    val = alpha.get('val')
                    if val:
                        transparency = 1.0 - (int(val) / 100000)

                config.stops.append(GradientStop(
                    position=position,
                    color=color,
                    transparency=transparency,
                ))

        return config if config.stops else None

    def _extract_shadow(self, spPr) -> Optional[ShadowConfig]:
        """Extract shadow configuration from spPr element."""
        effectLst = spPr.find('.//a:effectLst', self.ns)
        if effectLst is None:
            return None

        outerShdw = effectLst.find('.//a:outerShdw', self.ns)
        if outerShdw is None:
            return None

        config = ShadowConfig()

        # Blur radius (in EMU)
        blurRad = outerShdw.get('blurRad')
        if blurRad:
            config.blur_radius_pt = int(blurRad) / 12700  # EMU to points

        # Distance (in EMU)
        dist = outerShdw.get('dist')
        if dist:
            config.distance_inches = int(dist) / 914400  # EMU to inches

        # Direction (in 60000ths of a degree)
        dir_val = outerShdw.get('dir')
        if dir_val:
            config.direction_degrees = int(dir_val) / 60000

        # Color
        srgbClr = outerShdw.find('.//a:srgbClr', self.ns)
        if srgbClr is not None:
            config.color = f"#{srgbClr.get('val', '000000')}"

        # Transparency
        alpha = outerShdw.find('.//a:alpha', self.ns)
        if alpha is not None:
            val = alpha.get('val')
            if val:
                config.transparency = 1.0 - (int(val) / 100000)

        return config

    def _extract_bevel(self, spPr) -> Optional[BevelConfig]:
        """Extract 3D bevel configuration from spPr element."""
        sp3d = spPr.find('.//a:sp3d', self.ns)
        if sp3d is None:
            return None

        bevelT = sp3d.find('.//a:bevelT', self.ns)
        if bevelT is None:
            return None

        config = BevelConfig()

        # Bevel type
        prst = bevelT.get('prst')
        if prst:
            try:
                config.type = BevelType(prst)
            except ValueError:
                config.type = BevelType.SOFT_ROUND

        # Bevel width
        w = bevelT.get('w')
        if w:
            config.width_inches = int(w) / 914400

        # Bevel height
        h = bevelT.get('h')
        if h:
            config.height_inches = int(h) / 914400

        return config

    def _extract_stroke(self, shape) -> Optional[StrokeConfig]:
        """Extract stroke configuration from shape."""
        try:
            line = shape.line
            if line.fill.type is None:
                return StrokeConfig(enabled=False)

            config = StrokeConfig(enabled=True)

            try:
                config.width_pt = line.width.pt
            except:
                pass

            try:
                rgb = line.color.rgb
                config.color = f"#{rgb}"
            except:
                pass

            return config
        except:
            return None

    def _calculate_path_complexity(self, spPr) -> int:
        """Count the number of bezier curves in the path."""
        custGeom = spPr.find('.//a:custGeom', self.ns)
        if custGeom is None:
            return 0

        pathLst = custGeom.find('.//a:pathLst', self.ns)
        if pathLst is None:
            return 0

        curve_count = 0
        for path in pathLst.findall('.//a:path', self.ns):
            curve_count += len(path.findall('.//a:cubicBezTo', self.ns))
            curve_count += len(path.findall('.//a:quadBezTo', self.ns))

        return curve_count

    def _has_elliptical_edges(self, spPr) -> bool:
        """Check if the shape uses elliptical/curved top/bottom edges."""
        custGeom = spPr.find('.//a:custGeom', self.ns)
        if custGeom is None:
            return False

        pathLst = custGeom.find('.//a:pathLst', self.ns)
        if pathLst is None:
            return False

        for path in pathLst.findall('.//a:path', self.ns):
            # Check ratio of curves to lines
            curves = len(path.findall('.//a:cubicBezTo', self.ns))
            lines = len(path.findall('.//a:lnTo', self.ns))

            # If curves > lines, likely has elliptical edges
            if curves > lines and curves >= 4:
                return True

        return False

    def _calculate_professional_score(self, effects: VisualEffects) -> float:
        """Calculate a professional quality score (0-100)."""
        score = 50.0  # Base score

        # Gradient with multiple stops
        if effects.gradient and len(effects.gradient.stops) >= 3:
            score += 15.0
            # Bonus for highlight gradient (stop near 15%)
            for stop in effects.gradient.stops:
                if 0.10 <= stop.position <= 0.20:
                    score += 5.0
                    break

        # Shadow with professional parameters
        if effects.shadow:
            if 8.0 <= effects.shadow.blur_radius_pt <= 15.0:
                score += 10.0  # Good blur radius
            if 60 <= effects.shadow.direction_degrees <= 120:
                score += 5.0   # Good direction

        # 3D bevel
        if effects.bevel:
            score += 10.0

        # Path complexity
        if effects.path_complexity >= 6:
            score += 5.0

        # Elliptical edges
        if effects.uses_elliptical_edges:
            score += 10.0

        return min(100.0, score)


# =============================================================================
# EFFECT SYNTHESIZER - Generate new effect combinations
# =============================================================================

class EffectSynthesizer:
    """
    Synthesizes new visual effect combinations based on learned principles.

    Can generate effects for:
    - New shape types based on similar learned shapes
    - Variations of existing effects
    - Custom combinations following design principles
    """

    def __init__(self):
        self.learned_effects: Dict[str, VisualEffects] = {}
        self.style_principles: Dict[str, Any] = {}

    def learn_from_effects(self, category: str, effects: VisualEffects):
        """Learn effect patterns from extracted effects."""
        if category not in self.learned_effects:
            self.learned_effects[category] = effects
        else:
            # Merge with existing - keep the better one
            existing = self.learned_effects[category]
            if effects.professional_score > existing.professional_score:
                self.learned_effects[category] = effects

    def synthesize_for_shape(
        self,
        shape_type: str,
        base_color: str,
        style: str = "professional",
    ) -> VisualEffects:
        """
        Synthesize appropriate effects for a shape type.

        Args:
            shape_type: Type of shape (funnel, pyramid, arrow, etc.)
            base_color: Base color for the shape
            style: Visual style (professional, modern, minimal, dramatic)

        Returns:
            VisualEffects configured for the shape
        """
        # Check if we have learned effects for this type
        if shape_type in self.learned_effects:
            # Use learned effects as template, adjust colors
            learned = self.learned_effects[shape_type]
            return self._adapt_effects(learned, base_color)

        # Otherwise, generate based on style
        if style == "professional":
            return EffectPresets.professional_3d(base_color)
        elif style == "modern":
            return EffectPresets.modern_minimal(base_color)
        elif style == "glossy":
            return EffectPresets.glossy_premium(base_color)
        elif style == "flat":
            return EffectPresets.flat_material(base_color)
        else:
            return EffectPresets.professional_3d(base_color)

    def _adapt_effects(self, template: VisualEffects, new_color: str) -> VisualEffects:
        """Adapt learned effects to a new color."""
        effects = VisualEffects(
            shadow=template.shadow,
            bevel=template.bevel,
            stroke=template.stroke,
            path_complexity=template.path_complexity,
            uses_elliptical_edges=template.uses_elliptical_edges,
            professional_score=template.professional_score,
        )

        # Regenerate gradient with new color
        if template.gradient:
            effects.gradient = EffectPresets.gradient_highlight(new_color)
            effects.gradient.angle = template.gradient.angle

        return effects

    def create_variation(
        self,
        base_effects: VisualEffects,
        variation: str = "subtle",
    ) -> VisualEffects:
        """
        Create a variation of existing effects.

        Variations:
        - subtle: Minor adjustments to parameters
        - dramatic: Increase shadow and bevel
        - minimal: Reduce effects
        - inverted: Swap light/dark in gradients
        """
        effects = VisualEffects(
            gradient=base_effects.gradient,
            shadow=base_effects.shadow,
            bevel=base_effects.bevel,
            stroke=base_effects.stroke,
            path_complexity=base_effects.path_complexity,
            uses_elliptical_edges=base_effects.uses_elliptical_edges,
        )

        if variation == "dramatic":
            if effects.shadow:
                effects.shadow.blur_radius_pt *= 1.5
                effects.shadow.distance_inches *= 1.5
            if effects.bevel:
                effects.bevel.width_inches *= 1.5
                effects.bevel.height_inches *= 1.5

        elif variation == "minimal":
            effects.bevel = None
            if effects.shadow:
                effects.shadow.blur_radius_pt *= 0.6
                effects.shadow.transparency = 0.8

        return effects
