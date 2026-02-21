"""Apply visual styles to PowerPoint shapes."""

from typing import Any

from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE, MSO_THEME_COLOR
from pptx.oxml.ns import qn
from pptx.slide import Slide
from pptx.util import Emu, Pt

from backend.dsl.schema import (
    Bevel,
    DashStyle,
    Effects,
    Fill,
    Glow,
    GradientFill,
    NoFill,
    Reflection,
    Shadow,
    SolidFill,
    Stroke,
    ThemeColors,
)


# Map DSL dash styles to MSO
DASH_STYLE_MAP: dict[DashStyle, MSO_LINE_DASH_STYLE] = {
    DashStyle.SOLID: MSO_LINE_DASH_STYLE.SOLID,
    DashStyle.DASH: MSO_LINE_DASH_STYLE.DASH,
    DashStyle.DOT: MSO_LINE_DASH_STYLE.ROUND_DOT,
    DashStyle.DASH_DOT: MSO_LINE_DASH_STYLE.DASH_DOT,
    DashStyle.LONG_DASH: MSO_LINE_DASH_STYLE.LONG_DASH,
}


class StyleRenderer:
    """Applies visual styles to PowerPoint shapes."""

    def apply_fill(
        self,
        pptx_shape: Any,
        fill: Fill,
        theme: ThemeColors,
    ) -> None:
        """Apply fill style to a shape.

        Args:
            pptx_shape: The python-pptx shape object.
            fill: The DSL fill specification.
            theme: Theme colors for resolving references.
        """
        if isinstance(fill, NoFill) or fill.type == "none":
            pptx_shape.fill.background()
        elif isinstance(fill, SolidFill) or fill.type == "solid":
            self._apply_solid_fill(pptx_shape, fill, theme)
        elif isinstance(fill, GradientFill) or fill.type == "gradient":
            self._apply_gradient_fill(pptx_shape, fill, theme)

    def _apply_solid_fill(
        self,
        pptx_shape: Any,
        fill: SolidFill,
        theme: ThemeColors,
    ) -> None:
        """Apply solid fill to a shape.

        Args:
            pptx_shape: The python-pptx shape object.
            fill: The solid fill specification.
            theme: Theme colors.
        """
        pptx_shape.fill.solid()
        color = self._resolve_color(fill.color, theme)
        pptx_shape.fill.fore_color.rgb = color

        # Apply transparency if not fully opaque
        if fill.alpha < 1.0:
            self._set_fill_transparency(pptx_shape, fill.alpha)

    def _apply_gradient_fill(
        self,
        pptx_shape: Any,
        fill: GradientFill,
        theme: ThemeColors,
    ) -> None:
        """Apply gradient fill to a shape.

        Args:
            pptx_shape: The python-pptx shape object.
            fill: The gradient fill specification.
            theme: Theme colors.
        """
        pptx_shape.fill.gradient()

        # Set gradient angle for linear gradients
        if fill.gradient_type.value == "linear":
            pptx_shape.fill.gradient_angle = fill.angle

        # Clear existing stops and add new ones
        gradient_stops = pptx_shape.fill.gradient_stops

        # Add gradient stops
        for i, stop in enumerate(fill.stops):
            if i < len(gradient_stops):
                gs = gradient_stops[i]
            else:
                # Can't easily add stops via python-pptx, use first/last
                continue

            gs.color.rgb = self._resolve_color(stop.color, theme)
            gs.position = stop.position

    def apply_stroke(
        self,
        pptx_shape: Any,
        stroke: Stroke,
        theme: ThemeColors,
    ) -> None:
        """Apply stroke/line style to a shape.

        Args:
            pptx_shape: The python-pptx shape object.
            stroke: The stroke specification.
            theme: Theme colors.
        """
        line = pptx_shape.line

        # Set line color
        line.color.rgb = self._resolve_color(stroke.color, theme)

        # Set line width
        line.width = Emu(stroke.width)

        # Set dash style
        dash_style = DASH_STYLE_MAP.get(stroke.dash_style, MSO_LINE_DASH_STYLE.SOLID)
        line.dash_style = dash_style

    def apply_effects(self, pptx_shape: Any, effects: Effects) -> None:
        """Apply visual effects to a shape.

        Args:
            pptx_shape: The python-pptx shape object.
            effects: The effects specification.
        """
        if effects.shadow:
            self._apply_shadow(pptx_shape, effects.shadow)

        if effects.glow:
            self._apply_glow(pptx_shape, effects.glow)

        if effects.reflection:
            self._apply_reflection(pptx_shape, effects.reflection)

        if effects.bevel:
            self._apply_bevel(pptx_shape, effects.bevel)

        if effects.soft_edges:
            self._apply_soft_edges(pptx_shape, effects.soft_edges)

    def _apply_shadow(self, pptx_shape: Any, shadow: Shadow) -> None:
        """Apply shadow effect to a shape.

        Args:
            pptx_shape: The python-pptx shape object.
            shadow: The shadow specification.
        """
        try:
            # Access shape's spPr (shape properties) element
            sp = pptx_shape._element
            spPr = sp.find(qn("p:spPr"))
            if spPr is None:
                return

            # Create effectLst if it doesn't exist
            effectLst = spPr.find(qn("a:effectLst"))
            if effectLst is None:
                from lxml import etree
                effectLst = etree.SubElement(spPr, qn("a:effectLst"))

            # Create outer shadow element
            from lxml import etree

            # Remove existing shadow
            for existing in effectLst.findall(qn("a:outerShdw")):
                effectLst.remove(existing)

            # Add new shadow
            outerShdw = etree.SubElement(effectLst, qn("a:outerShdw"))
            outerShdw.set("blurRad", str(shadow.blur_radius))
            outerShdw.set("dist", str(shadow.distance))
            outerShdw.set("dir", str(int(shadow.angle * 60000)))  # degrees to EMUs
            outerShdw.set("algn", "tl")
            outerShdw.set("rotWithShape", "0")

            # Set shadow color with alpha
            srgbClr = etree.SubElement(outerShdw, qn("a:srgbClr"))
            color_hex = shadow.color.lstrip("#")
            srgbClr.set("val", color_hex)

            # Add alpha
            alpha = etree.SubElement(srgbClr, qn("a:alpha"))
            alpha.set("val", str(int(shadow.alpha * 100000)))

        except Exception:
            # Shadow application failed, continue without it
            pass

    def _apply_glow(self, pptx_shape: Any, glow: Glow) -> None:
        """Apply glow effect to a shape.

        Args:
            pptx_shape: The python-pptx shape object.
            glow: The glow specification.
        """
        try:
            from lxml import etree

            sp = pptx_shape._element
            spPr = sp.find(qn("p:spPr"))
            if spPr is None:
                return

            # Create effectLst if it doesn't exist
            effectLst = spPr.find(qn("a:effectLst"))
            if effectLst is None:
                effectLst = etree.SubElement(spPr, qn("a:effectLst"))

            # Remove existing glow
            for existing in effectLst.findall(qn("a:glow")):
                effectLst.remove(existing)

            # Add new glow
            glow_elem = etree.SubElement(effectLst, qn("a:glow"))
            glow_elem.set("rad", str(glow.radius))

            # Set glow color with alpha
            srgbClr = etree.SubElement(glow_elem, qn("a:srgbClr"))
            color_hex = glow.color.lstrip("#")
            srgbClr.set("val", color_hex)

            # Add alpha
            alpha = etree.SubElement(srgbClr, qn("a:alpha"))
            alpha.set("val", str(int(glow.alpha * 100000)))

        except Exception:
            pass

    def _apply_reflection(self, pptx_shape: Any, reflection: Reflection) -> None:
        """Apply reflection effect to a shape.

        Args:
            pptx_shape: The python-pptx shape object.
            reflection: The reflection specification.
        """
        try:
            from lxml import etree

            sp = pptx_shape._element
            spPr = sp.find(qn("p:spPr"))
            if spPr is None:
                return

            # Create effectLst if it doesn't exist
            effectLst = spPr.find(qn("a:effectLst"))
            if effectLst is None:
                effectLst = etree.SubElement(spPr, qn("a:effectLst"))

            # Remove existing reflection
            for existing in effectLst.findall(qn("a:reflection")):
                effectLst.remove(existing)

            # Add new reflection
            refl = etree.SubElement(effectLst, qn("a:reflection"))
            refl.set("blurRad", str(reflection.blur_radius))
            refl.set("stA", str(int(reflection.start_alpha * 100000)))
            refl.set("endA", str(int(reflection.end_alpha * 100000)))
            refl.set("dist", str(reflection.distance))
            refl.set("dir", str(int(reflection.direction * 60000)))
            refl.set("sx", str(int(reflection.scale_x * 100000)))
            refl.set("sy", str(int(reflection.scale_y * 100000)))
            refl.set("algn", "bl")
            refl.set("rotWithShape", "0")

        except Exception:
            pass

    def _apply_bevel(self, pptx_shape: Any, bevel: Bevel) -> None:
        """Apply 3D bevel effect to a shape.

        Args:
            pptx_shape: The python-pptx shape object.
            bevel: The bevel specification.
        """
        try:
            from lxml import etree

            sp = pptx_shape._element
            spPr = sp.find(qn("p:spPr"))
            if spPr is None:
                return

            # Create sp3d if it doesn't exist
            sp3d = spPr.find(qn("a:sp3d"))
            if sp3d is None:
                sp3d = etree.SubElement(spPr, qn("a:sp3d"))

            # Remove existing bevel
            for existing in sp3d.findall(qn("a:bevelT")):
                sp3d.remove(existing)

            # Add new bevel
            bevelT = etree.SubElement(sp3d, qn("a:bevelT"))
            bevelT.set("w", str(bevel.width))
            bevelT.set("h", str(bevel.height))
            bevelT.set("prst", bevel.type)

        except Exception:
            pass

    def _apply_soft_edges(self, pptx_shape: Any, radius: int) -> None:
        """Apply soft edges effect to a shape.

        Args:
            pptx_shape: The python-pptx shape object.
            radius: Soft edge radius in EMUs.
        """
        try:
            from lxml import etree

            sp = pptx_shape._element
            spPr = sp.find(qn("p:spPr"))
            if spPr is None:
                return

            # Create effectLst if it doesn't exist
            effectLst = spPr.find(qn("a:effectLst"))
            if effectLst is None:
                effectLst = etree.SubElement(spPr, qn("a:effectLst"))

            # Remove existing soft edges
            for existing in effectLst.findall(qn("a:softEdge")):
                effectLst.remove(existing)

            # Add new soft edges
            softEdge = etree.SubElement(effectLst, qn("a:softEdge"))
            softEdge.set("rad", str(radius))

        except Exception:
            pass

    def apply_background(self, slide: Slide, fill: Fill) -> None:
        """Apply background fill to a slide.

        Args:
            slide: The PowerPoint slide.
            fill: The background fill specification.
        """
        background = slide.background

        if isinstance(fill, NoFill) or fill.type == "none":
            # Use default/inherited background
            pass
        elif isinstance(fill, SolidFill) or fill.type == "solid":
            background.fill.solid()
            background.fill.fore_color.rgb = self._parse_color(fill.color)
        elif isinstance(fill, GradientFill) or fill.type == "gradient":
            background.fill.gradient()
            if fill.gradient_type.value == "linear":
                background.fill.gradient_angle = fill.angle

    def _resolve_color(self, color: str, theme: ThemeColors) -> RGBColor:
        """Resolve a color string to RGBColor.

        Args:
            color: Color string (hex or theme reference).
            theme: Theme colors for resolving references.

        Returns:
            RGBColor object.
        """
        # Check for theme color references
        color_lower = color.lower()
        if color_lower.startswith("accent"):
            try:
                accent_num = int(color_lower.replace("accent", "").replace("_", ""))
                theme_colors = {
                    1: theme.accent1,
                    2: theme.accent2,
                    3: theme.accent3,
                    4: theme.accent4,
                    5: theme.accent5,
                    6: theme.accent6,
                }
                color = theme_colors.get(accent_num, theme.accent1)
            except ValueError:
                pass
        elif color_lower in ("dark1", "dk1"):
            color = theme.dark1
        elif color_lower in ("light1", "lt1"):
            color = theme.light1
        elif color_lower in ("dark2", "dk2"):
            color = theme.dark2
        elif color_lower in ("light2", "lt2"):
            color = theme.light2

        return self._parse_color(color)

    def _parse_color(self, color: str) -> RGBColor:
        """Parse a hex color string to RGBColor.

        Args:
            color: Hex color string (e.g., '#0D9488' or '0D9488').

        Returns:
            RGBColor object.
        """
        color = color.lstrip("#")
        if len(color) == 6:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            return RGBColor(r, g, b)
        return RGBColor(0, 0, 0)

    def _set_fill_transparency(self, pptx_shape: Any, alpha: float) -> None:
        """Set fill transparency via XML.

        Args:
            pptx_shape: The python-pptx shape object.
            alpha: Opacity value (0-1).
        """
        try:
            from lxml import etree

            sp = pptx_shape._element
            spPr = sp.find(qn("p:spPr"))
            if spPr is None:
                return

            solidFill = spPr.find(qn("a:solidFill"))
            if solidFill is None:
                return

            srgbClr = solidFill.find(qn("a:srgbClr"))
            if srgbClr is None:
                return

            # Remove existing alpha
            for existing in srgbClr.findall(qn("a:alpha")):
                srgbClr.remove(existing)

            # Add new alpha
            alpha_elem = etree.SubElement(srgbClr, qn("a:alpha"))
            alpha_elem.set("val", str(int(alpha * 100000)))

        except Exception:
            pass
