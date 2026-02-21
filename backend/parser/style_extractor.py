"""Extract visual styles from PowerPoint shapes.

Includes fill, stroke, and effects (shadow, glow, reflection, bevel, soft edges).
"""

from typing import Any

from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE, MSO_THEME_COLOR, MSO_FILL_TYPE
from pptx.slide import Slide

from backend.dsl.schema import (
    Bevel,
    DashStyle,
    Effects,
    Fill,
    Glow,
    GradientFill,
    GradientStop,
    GradientType,
    NoFill,
    Reflection,
    Shadow,
    SolidFill,
    Stroke,
)


# XML namespaces for Office Open XML
NAMESPACES = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


class StyleExtractor:
    """Extracts visual styles from PPTX elements."""

    # Map MSO dash styles to our enum
    DASH_STYLE_MAP = {
        MSO_LINE_DASH_STYLE.SOLID: DashStyle.SOLID,
        MSO_LINE_DASH_STYLE.DASH: DashStyle.DASH,
        MSO_LINE_DASH_STYLE.ROUND_DOT: DashStyle.DOT,
        MSO_LINE_DASH_STYLE.SQUARE_DOT: DashStyle.DOT,
        MSO_LINE_DASH_STYLE.DASH_DOT: DashStyle.DASH_DOT,
        MSO_LINE_DASH_STYLE.LONG_DASH: DashStyle.LONG_DASH,
    }

    def extract_fill(self, fill: Any) -> Fill:
        """Extract fill style from a shape.

        Args:
            fill: The python-pptx FillFormat object.

        Returns:
            Fill object (SolidFill, GradientFill, or NoFill).
        """
        if fill is None:
            return NoFill()

        try:
            fill_type = fill.type
        except Exception:
            return NoFill()

        if fill_type is None:
            return NoFill()

        # Solid fill
        if fill_type == MSO_FILL_TYPE.SOLID:
            return self._extract_solid_fill(fill)

        # Gradient fill
        if fill_type == MSO_FILL_TYPE.GRADIENT:
            return self._extract_gradient_fill(fill)

        # Patterned or other fills - treat as solid with default
        if fill_type == MSO_FILL_TYPE.PATTERNED:
            return self._extract_solid_fill(fill)

        return NoFill()

    def _extract_solid_fill(self, fill: Any) -> SolidFill:
        """Extract solid fill properties.

        Args:
            fill: The python-pptx FillFormat object.

        Returns:
            SolidFill object.
        """
        color = "#0D9488"  # Default to teal
        alpha = 1.0

        try:
            if fill.fore_color:
                color = self._extract_color(fill.fore_color)
        except Exception:
            pass

        return SolidFill(color=color, alpha=alpha)

    def _extract_color(self, color_obj: Any) -> str:
        """Extract color from any python-pptx color object.

        Handles RGBColor, SchemeColor, PrstColor, NoneColor, etc.

        Args:
            color_obj: The color object from python-pptx.

        Returns:
            Hex color string.
        """
        if color_obj is None:
            return "#0D9488"

        # Try to get RGB directly
        try:
            rgb = color_obj.rgb
            if rgb is not None:
                return self._rgb_to_hex(rgb)
        except (AttributeError, TypeError):
            pass

        # Try theme color
        try:
            theme_color = color_obj.theme_color
            if theme_color is not None:
                return self._theme_color_to_hex(theme_color)
        except (AttributeError, TypeError):
            pass

        # Try brightness-adjusted theme color
        try:
            if hasattr(color_obj, "type") and "SCHEME" in str(color_obj.type):
                # It's a scheme color, return a default based on context
                return "#0D9488"
        except (AttributeError, TypeError):
            pass

        # Default fallback
        return "#0D9488"

    def _extract_gradient_fill(self, fill: Any) -> GradientFill:
        """Extract gradient fill properties.

        Args:
            fill: The python-pptx FillFormat object.

        Returns:
            GradientFill object.
        """
        stops: list[GradientStop] = []
        angle = 0.0

        try:
            if hasattr(fill, "gradient_angle"):
                angle = float(fill.gradient_angle or 0)

            if hasattr(fill, "gradient_stops"):
                for stop in fill.gradient_stops:
                    position = stop.position if hasattr(stop, "position") else 0.0
                    color = "#0D9488"
                    if hasattr(stop, "color"):
                        color = self._extract_color(stop.color)

                    stops.append(GradientStop(position=position, color=color))
        except Exception:
            # Default gradient
            stops = [
                GradientStop(position=0.0, color="#0D9488"),
                GradientStop(position=1.0, color="#14B8A6"),
            ]

        if len(stops) < 2:
            stops = [
                GradientStop(position=0.0, color="#0D9488"),
                GradientStop(position=1.0, color="#14B8A6"),
            ]

        return GradientFill(
            gradient_type=GradientType.LINEAR,
            angle=angle,
            stops=stops,
        )

    def extract_stroke(self, line: Any) -> Stroke | None:
        """Extract stroke/line properties.

        Args:
            line: The python-pptx LineFormat object.

        Returns:
            Stroke object or None if no line.
        """
        if line is None:
            return None

        try:
            # Check if line is visible
            if hasattr(line, "fill") and line.fill.type is None:
                return None

            color = "#000000"
            if line.color:
                color = self._extract_color(line.color)

            width = 12700  # 1pt default
            if line.width:
                width = int(line.width)

            dash_style = DashStyle.SOLID
            if line.dash_style and line.dash_style in self.DASH_STYLE_MAP:
                dash_style = self.DASH_STYLE_MAP[line.dash_style]

            return Stroke(
                color=color,
                width=width,
                dash_style=dash_style,
            )
        except Exception:
            return None

    def extract_effects(self, shape: Any) -> Effects:
        """Extract visual effects from a shape.

        Extracts shadow, glow, reflection, bevel, and soft edges from
        the shape's effect list XML.

        Args:
            shape: The python-pptx shape object.

        Returns:
            Effects object with all detected effects.
        """
        shadow = None
        glow = None
        reflection = None
        bevel = None
        soft_edges = None

        # Try to extract shadow from python-pptx API
        try:
            if hasattr(shape, "shadow") and shape.shadow:
                shadow_obj = shape.shadow
                if shadow_obj.inherit is False or shadow_obj.visible:
                    shadow = Shadow(
                        type="outer",
                        color="#000000",
                        alpha=0.5,
                        blur_radius=50800,
                        distance=38100,
                        angle=45.0,
                    )
        except Exception:
            pass

        # Extract additional effects from XML
        try:
            element = shape._element

            # Find effect list in shape properties
            sp_pr = element.find(".//p:spPr", NAMESPACES)
            if sp_pr is None:
                sp_pr = element.find(".//a:spPr", NAMESPACES)

            if sp_pr is not None:
                # Extract effect list <a:effectLst>
                effect_lst = sp_pr.find("a:effectLst", NAMESPACES)
                if effect_lst is not None:
                    glow = self._extract_glow(effect_lst)
                    reflection = self._extract_reflection(effect_lst)
                    soft_edges = self._extract_soft_edges(effect_lst)

                    # Shadow from XML if not already extracted
                    if shadow is None:
                        shadow = self._extract_shadow_from_xml(effect_lst)

                # Extract 3D effects for bevel
                sp3d = sp_pr.find("a:sp3d", NAMESPACES)
                if sp3d is not None:
                    bevel = self._extract_bevel(sp3d)

        except (AttributeError, TypeError):
            pass

        return Effects(
            shadow=shadow,
            glow=glow,
            reflection=reflection,
            bevel=bevel,
            soft_edges=soft_edges,
        )

    def _extract_glow(self, effect_lst: Any) -> Glow | None:
        """Extract glow effect from effect list.

        XML structure:
            <a:glow rad="63500">
                <a:srgbClr val="FF0000">
                    <a:alpha val="60000"/>
                </a:srgbClr>
            </a:glow>

        Args:
            effect_lst: The <a:effectLst> XML element.

        Returns:
            Glow object or None.
        """
        glow_elem = effect_lst.find("a:glow", NAMESPACES)
        if glow_elem is None:
            return None

        # Extract radius (in EMUs)
        radius = int(glow_elem.get("rad", "63500"))

        # Extract color
        color = "#FFFF00"  # Default glow color (yellow)
        alpha = 0.6

        srgb = glow_elem.find("a:srgbClr", NAMESPACES)
        if srgb is not None:
            color = f"#{srgb.get('val', 'FFFF00')}"

            # Check for alpha modifier
            alpha_elem = srgb.find("a:alpha", NAMESPACES)
            if alpha_elem is not None:
                alpha_val = alpha_elem.get("val", "60000")
                alpha = float(alpha_val) / 100000.0

        return Glow(color=color, alpha=alpha, radius=radius)

    def _extract_reflection(self, effect_lst: Any) -> Reflection | None:
        """Extract reflection effect from effect list.

        XML structure:
            <a:reflection blurRad="6350" stA="52000" endA="300"
                          dist="0" dir="5400000" sy="-100000"
                          algn="bl" rotWithShape="0"/>

        Args:
            effect_lst: The <a:effectLst> XML element.

        Returns:
            Reflection object or None.
        """
        refl_elem = effect_lst.find("a:reflection", NAMESPACES)
        if refl_elem is None:
            return None

        # Extract blur radius
        blur_radius = int(refl_elem.get("blurRad", "0"))

        # Extract start and end alpha (in 100,000ths)
        start_alpha_raw = float(refl_elem.get("stA", "50000"))
        end_alpha_raw = float(refl_elem.get("endA", "0"))
        start_alpha = start_alpha_raw / 100000.0
        end_alpha = end_alpha_raw / 100000.0

        # Extract distance
        distance = int(refl_elem.get("dist", "0"))

        # Extract direction (in 60,000ths of a degree)
        dir_raw = float(refl_elem.get("dir", "5400000"))
        direction = dir_raw / 60000.0

        # Extract scale (in 100,000ths, negative for reflection)
        sy_raw = float(refl_elem.get("sy", "-100000"))
        scale_y = sy_raw / 100000.0

        sx_raw = float(refl_elem.get("sx", "100000"))
        scale_x = sx_raw / 100000.0

        return Reflection(
            blur_radius=blur_radius,
            start_alpha=start_alpha,
            end_alpha=end_alpha,
            distance=distance,
            direction=direction,
            scale_x=scale_x,
            scale_y=scale_y,
        )

    def _extract_soft_edges(self, effect_lst: Any) -> int | None:
        """Extract soft edge effect from effect list.

        XML structure:
            <a:softEdge rad="63500"/>

        Args:
            effect_lst: The <a:effectLst> XML element.

        Returns:
            Soft edge radius in EMUs or None.
        """
        soft_elem = effect_lst.find("a:softEdge", NAMESPACES)
        if soft_elem is None:
            return None

        return int(soft_elem.get("rad", "0"))

    def _extract_shadow_from_xml(self, effect_lst: Any) -> Shadow | None:
        """Extract shadow effect from effect list XML.

        XML structure:
            <a:outerShdw blurRad="50800" dist="38100" dir="2700000"
                         algn="tl" rotWithShape="0">
                <a:srgbClr val="000000">
                    <a:alpha val="50000"/>
                </a:srgbClr>
            </a:outerShdw>

        Args:
            effect_lst: The <a:effectLst> XML element.

        Returns:
            Shadow object or None.
        """
        # Try outer shadow first
        shadow_elem = effect_lst.find("a:outerShdw", NAMESPACES)
        shadow_type = "outer"

        if shadow_elem is None:
            shadow_elem = effect_lst.find("a:innerShdw", NAMESPACES)
            shadow_type = "inner"

        if shadow_elem is None:
            return None

        # Extract properties
        blur_radius = int(shadow_elem.get("blurRad", "50800"))
        distance = int(shadow_elem.get("dist", "38100"))

        # Direction in 60,000ths of a degree
        dir_raw = float(shadow_elem.get("dir", "2700000"))
        angle = dir_raw / 60000.0

        # Extract color
        color = "#000000"
        alpha = 0.5

        srgb = shadow_elem.find("a:srgbClr", NAMESPACES)
        if srgb is not None:
            color = f"#{srgb.get('val', '000000')}"

            alpha_elem = srgb.find("a:alpha", NAMESPACES)
            if alpha_elem is not None:
                alpha_val = alpha_elem.get("val", "50000")
                alpha = float(alpha_val) / 100000.0

        return Shadow(
            type=shadow_type,
            color=color,
            alpha=alpha,
            blur_radius=blur_radius,
            distance=distance,
            angle=angle,
        )

    def _extract_bevel(self, sp3d: Any) -> Bevel | None:
        """Extract bevel effect from 3D shape properties.

        XML structure:
            <a:sp3d>
                <a:bevelT w="76200" h="76200" prst="relaxedInset"/>
            </a:sp3d>

        Args:
            sp3d: The <a:sp3d> XML element.

        Returns:
            Bevel object or None.
        """
        bevel_t = sp3d.find("a:bevelT", NAMESPACES)
        if bevel_t is None:
            return None

        # Extract dimensions
        width = int(bevel_t.get("w", "76200"))
        height = int(bevel_t.get("h", "76200"))

        # Extract preset type
        preset = bevel_t.get("prst", "relaxedInset")

        # Map preset to our supported types
        preset_map = {
            "relaxedInset": "relaxedInset",
            "circle": "circle",
            "slope": "slope",
            "cross": "cross",
            "angle": "angle",
            "softRound": "softRound",
            # Map other presets to closest match
            "coolSlant": "slope",
            "convex": "circle",
            "divot": "angle",
            "riblet": "cross",
            "hardEdge": "angle",
            "artDeco": "slope",
        }

        bevel_type = preset_map.get(preset, "relaxedInset")

        return Bevel(type=bevel_type, width=width, height=height)

    def extract_background(self, slide: Slide) -> Fill:
        """Extract slide background fill.

        Args:
            slide: The python-pptx Slide object.

        Returns:
            Fill object for the background.
        """
        try:
            if slide.background and slide.background.fill:
                return self.extract_fill(slide.background.fill)
        except Exception:
            pass

        return SolidFill(color="#FFFFFF")

    def _rgb_to_hex(self, rgb: RGBColor | None) -> str:
        """Convert RGBColor to hex string.

        Args:
            rgb: RGBColor object.

        Returns:
            Hex color string.
        """
        if rgb is None:
            return "#000000"
        return f"#{rgb}"

    def _theme_color_to_hex(self, theme_color: MSO_THEME_COLOR) -> str:
        """Convert theme color to hex (using defaults).

        Args:
            theme_color: MSO_THEME_COLOR enum.

        Returns:
            Hex color string.
        """
        # Default theme color mappings
        theme_map = {
            MSO_THEME_COLOR.DARK_1: "#000000",
            MSO_THEME_COLOR.LIGHT_1: "#FFFFFF",
            MSO_THEME_COLOR.DARK_2: "#1F497D",
            MSO_THEME_COLOR.LIGHT_2: "#EEECE1",
            MSO_THEME_COLOR.ACCENT_1: "#0D9488",
            MSO_THEME_COLOR.ACCENT_2: "#14B8A6",
            MSO_THEME_COLOR.ACCENT_3: "#2DD4BF",
            MSO_THEME_COLOR.ACCENT_4: "#5EEAD4",
            MSO_THEME_COLOR.ACCENT_5: "#99F6E4",
            MSO_THEME_COLOR.ACCENT_6: "#CCFBF1",
        }
        return theme_map.get(theme_color, "#000000")
