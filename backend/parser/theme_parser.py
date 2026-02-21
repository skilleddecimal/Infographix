"""Extract theme colors from PowerPoint slide masters.

Parses <a:clrScheme> XML from the presentation's theme to extract
the full color palette including dark/light colors and accents.
"""

from typing import Any

from pptx import Presentation

from backend.dsl.schema import ThemeColors


# XML namespaces for Office Open XML
NAMESPACES = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}

# Theme color element names mapped to ThemeColors attributes
THEME_COLOR_MAP = {
    "dk1": "dark1",
    "lt1": "light1",
    "dk2": "dark2",
    "lt2": "light2",
    "accent1": "accent1",
    "accent2": "accent2",
    "accent3": "accent3",
    "accent4": "accent4",
    "accent5": "accent5",
    "accent6": "accent6",
    "hlink": "hyperlink",
    "folHlink": "followed_hyperlink",
}


class ThemeParser:
    """Extracts theme colors from PPTX slide masters."""

    def extract_theme(self, prs: Presentation) -> ThemeColors:
        """Extract theme colors from a presentation.

        Accesses the first slide master's theme to extract the color scheme.

        Args:
            prs: The python-pptx Presentation object.

        Returns:
            ThemeColors with the extracted color palette.

        XML structure example:
            <a:clrScheme name="Office">
                <a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>
                <a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>
                <a:dk2><a:srgbClr val="1F497D"/></a:dk2>
                <a:lt2><a:srgbClr val="EEECE1"/></a:lt2>
                <a:accent1><a:srgbClr val="0D9488"/></a:accent1>
                ...
            </a:clrScheme>
        """
        colors: dict[str, str] = {}

        try:
            # Access the first slide master
            if not prs.slide_masters:
                return ThemeColors()

            slide_master = prs.slide_masters[0]

            # Access the theme through the slide master
            # python-pptx doesn't directly expose theme colors, so we access XML
            theme_element = self._get_theme_element(slide_master)
            if theme_element is None:
                return ThemeColors()

            # Find the color scheme
            clr_scheme = theme_element.find(".//a:clrScheme", NAMESPACES)
            if clr_scheme is None:
                return ThemeColors()

            # Extract each color
            for xml_name, attr_name in THEME_COLOR_MAP.items():
                color_elem = clr_scheme.find(f"a:{xml_name}", NAMESPACES)
                if color_elem is not None:
                    hex_color = self._extract_color_value(color_elem)
                    if hex_color:
                        colors[attr_name] = hex_color

        except (AttributeError, TypeError, IndexError):
            # Fall back to defaults if theme extraction fails
            pass

        return ThemeColors(**colors)

    def _get_theme_element(self, slide_master: Any) -> Any | None:
        """Get the theme XML element from a slide master.

        Args:
            slide_master: The python-pptx SlideMaster object.

        Returns:
            The theme XML element or None.
        """
        try:
            # Access through slide master's theme part
            if hasattr(slide_master, "theme") and slide_master.theme:
                return slide_master.theme.element
        except (AttributeError, TypeError):
            pass

        # Alternative: try to access through _element
        try:
            if hasattr(slide_master, "_element"):
                # The theme might be referenced in the slide master
                return slide_master._element.find(".//a:theme", NAMESPACES)
        except (AttributeError, TypeError):
            pass

        return None

    def _extract_color_value(self, color_elem: Any) -> str | None:
        """Extract hex color value from a theme color element.

        Color elements can contain different child elements:
        - <a:srgbClr val="RRGGBB"/>  - Direct RGB value
        - <a:sysClr val="windowText" lastClr="RRGGBB"/>  - System color
        - <a:schemeClr val="accent1"/>  - Reference to another scheme color

        Args:
            color_elem: The color element (e.g., <a:dk1>).

        Returns:
            Hex color string (e.g., "#000000") or None.
        """
        # Try <a:srgbClr> first (direct RGB)
        srgb = color_elem.find("a:srgbClr", NAMESPACES)
        if srgb is not None:
            val = srgb.get("val")
            if val:
                return f"#{val.upper()}"

        # Try <a:sysClr> (system color with lastClr fallback)
        sys_clr = color_elem.find("a:sysClr", NAMESPACES)
        if sys_clr is not None:
            last_clr = sys_clr.get("lastClr")
            if last_clr:
                return f"#{last_clr.upper()}"

            # Map common system colors
            val = sys_clr.get("val")
            return self._system_color_to_hex(val)

        # Try <a:hslClr> (HSL color)
        hsl_clr = color_elem.find("a:hslClr", NAMESPACES)
        if hsl_clr is not None:
            return self._hsl_to_hex(hsl_clr)

        return None

    def _system_color_to_hex(self, sys_val: str | None) -> str | None:
        """Convert system color name to hex.

        Args:
            sys_val: System color name (e.g., 'windowText', 'window').

        Returns:
            Hex color string or None.
        """
        if sys_val is None:
            return None

        # Common system color mappings
        system_colors = {
            "windowText": "#000000",
            "window": "#FFFFFF",
            "highlight": "#0078D7",
            "highlightText": "#FFFFFF",
            "buttonFace": "#F0F0F0",
            "btnText": "#000000",
            "3dDkShadow": "#696969",
            "3dLight": "#E3E3E3",
            "infoText": "#000000",
            "infoBk": "#FFFFE1",
        }

        return system_colors.get(sys_val)

    def _hsl_to_hex(self, hsl_elem: Any) -> str | None:
        """Convert HSL color element to hex.

        Args:
            hsl_elem: The <a:hslClr> element.

        Returns:
            Hex color string or None.
        """
        try:
            # HSL values in OOXML are in special units
            # H: 0-21600000 (60,000 per degree, so 360 * 60000)
            # S: 0-100000 (percentage * 1000)
            # L: 0-100000 (percentage * 1000)
            h_raw = float(hsl_elem.get("hue", "0"))
            s_raw = float(hsl_elem.get("sat", "0"))
            l_raw = float(hsl_elem.get("lum", "0"))

            h = h_raw / 60000.0 / 360.0  # Normalize to 0-1
            s = s_raw / 100000.0
            l = l_raw / 100000.0

            # HSL to RGB conversion
            r, g, b = self._hsl_to_rgb(h, s, l)

            return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"

        except (TypeError, ValueError):
            return None

    def _hsl_to_rgb(self, h: float, s: float, l: float) -> tuple[float, float, float]:
        """Convert HSL to RGB.

        Args:
            h: Hue (0-1).
            s: Saturation (0-1).
            l: Lightness (0-1).

        Returns:
            Tuple of (r, g, b) in 0-1 range.
        """
        if s == 0:
            return (l, l, l)

        def hue_to_rgb(p: float, q: float, t: float) -> float:
            if t < 0:
                t += 1
            if t > 1:
                t -= 1
            if t < 1 / 6:
                return p + (q - p) * 6 * t
            if t < 1 / 2:
                return q
            if t < 2 / 3:
                return p + (q - p) * (2 / 3 - t) * 6
            return p

        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q

        r = hue_to_rgb(p, q, h + 1 / 3)
        g = hue_to_rgb(p, q, h)
        b = hue_to_rgb(p, q, h - 1 / 3)

        return (r, g, b)

    def get_theme_color_by_index(
        self,
        theme: ThemeColors,
        index: int,
    ) -> str:
        """Get a theme color by its index.

        PowerPoint uses indices for theme colors:
        0 = dk1, 1 = lt1, 2 = dk2, 3 = lt2,
        4-9 = accent1-6, 10 = hlink, 11 = folHlink

        Args:
            theme: The ThemeColors object.
            index: Color index (0-11).

        Returns:
            Hex color string.
        """
        index_map = [
            theme.dark1,
            theme.light1,
            theme.dark2,
            theme.light2,
            theme.accent1,
            theme.accent2,
            theme.accent3,
            theme.accent4,
            theme.accent5,
            theme.accent6,
            theme.hyperlink,
            theme.followed_hyperlink,
        ]

        if 0 <= index < len(index_map):
            return index_map[index]

        return theme.accent1  # Default fallback
