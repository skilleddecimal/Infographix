"""Extract visual styles from PowerPoint shapes."""

from typing import Any

from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE, MSO_THEME_COLOR
from pptx.slide import Slide

from backend.dsl.schema import (
    DashStyle,
    Effects,
    Fill,
    GradientFill,
    GradientStop,
    GradientType,
    NoFill,
    Shadow,
    SolidFill,
    Stroke,
)


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
        if hasattr(fill, "solid") and fill.type and "SOLID" in str(fill.type):
            return self._extract_solid_fill(fill)

        # Gradient fill
        if hasattr(fill, "gradient_stops") and fill.type and "GRADIENT" in str(fill.type):
            return self._extract_gradient_fill(fill)

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
            if fill.fore_color and fill.fore_color.rgb:
                color = self._rgb_to_hex(fill.fore_color.rgb)
            elif fill.fore_color and fill.fore_color.theme_color:
                color = self._theme_color_to_hex(fill.fore_color.theme_color)
        except Exception:
            pass

        return SolidFill(color=color, alpha=alpha)

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
                    if hasattr(stop, "color") and stop.color.rgb:
                        color = self._rgb_to_hex(stop.color.rgb)

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
            if line.color and line.color.rgb:
                color = self._rgb_to_hex(line.color.rgb)

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

        Args:
            shape: The python-pptx shape object.

        Returns:
            Effects object.
        """
        shadow = None

        # Try to extract shadow
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

        return Effects(shadow=shadow)

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
