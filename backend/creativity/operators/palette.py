"""Palette variation operator."""

import colorsys
import random
from typing import Any

from backend.creativity.operators.base import VariationOperator, VariationParams


class PaletteVariation(VariationOperator):
    """Change colors within theme tokens.

    Supports multiple variation modes:
    - hue_shift: Rotate hue while maintaining saturation/lightness
    - complementary: Generate complementary color scheme
    - analogous: Generate analogous color scheme
    - monochromatic: Vary saturation/lightness only
    - preset: Apply a predefined palette
    """

    name = "palette"
    description = "Change color palette while maintaining harmony"
    applicable_archetypes = []  # Applicable to all

    # Predefined palettes
    PRESETS = {
        "ocean": ["#0D9488", "#0891B2", "#0284C7", "#0EA5E9", "#38BDF8", "#67E8F9"],
        "sunset": ["#F97316", "#FB923C", "#FDBA74", "#FED7AA", "#FFEDD5", "#FFF7ED"],
        "forest": ["#166534", "#15803D", "#22C55E", "#4ADE80", "#86EFAC", "#BBF7D0"],
        "berry": ["#7C3AED", "#8B5CF6", "#A78BFA", "#C4B5FD", "#DDD6FE", "#EDE9FE"],
        "rose": ["#BE123C", "#E11D48", "#F43F5E", "#FB7185", "#FDA4AF", "#FECDD3"],
        "slate": ["#334155", "#475569", "#64748B", "#94A3B8", "#CBD5E1", "#E2E8F0"],
        "amber": ["#B45309", "#D97706", "#F59E0B", "#FBBF24", "#FCD34D", "#FDE68A"],
        "teal": ["#0F766E", "#0D9488", "#14B8A6", "#2DD4BF", "#5EEAD4", "#99F6E4"],
    }

    def apply(self, dsl: dict[str, Any], params: VariationParams) -> dict[str, Any]:
        """Apply palette variation.

        Args:
            dsl: Input DSL scene graph.
            params: Variation parameters with mode in extra.

        Returns:
            DSL with modified colors.
        """
        result = self._deep_copy(dsl)
        mode = params.extra.get("mode", "hue_shift")

        if params.seed is not None:
            random.seed(params.seed)

        if mode == "preset":
            preset_name = params.extra.get("preset", random.choice(list(self.PRESETS.keys())))
            new_palette = self.PRESETS.get(preset_name, self.PRESETS["teal"])
        elif mode == "hue_shift":
            shift = params.intensity * 180  # Max 180 degree shift
            new_palette = self._shift_hue(self._get_current_palette(dsl), shift)
        elif mode == "complementary":
            new_palette = self._generate_complementary(self._get_current_palette(dsl))
        elif mode == "analogous":
            new_palette = self._generate_analogous(self._get_current_palette(dsl))
        elif mode == "monochromatic":
            base_color = params.extra.get("base_color", "#0D9488")
            new_palette = self._generate_monochromatic(base_color)
        else:
            new_palette = self._get_current_palette(dsl)

        # Apply new palette to theme
        if "theme" not in result:
            result["theme"] = {}

        for i, color in enumerate(new_palette[:6]):
            result["theme"][f"accent{i + 1}"] = color

        # Update shapes with resolved colors
        self._update_shape_colors(result.get("shapes", []), new_palette)

        return result

    def get_variation_range(self, dsl: dict[str, Any]) -> dict[str, Any]:
        """Get palette variation range."""
        return {
            "modes": ["hue_shift", "complementary", "analogous", "monochromatic", "preset"],
            "presets": list(self.PRESETS.keys()),
            "hue_shift_range": [0, 360],
        }

    def _get_current_palette(self, dsl: dict[str, Any]) -> list[str]:
        """Extract current color palette from DSL."""
        theme = dsl.get("theme", {})
        palette = []
        for i in range(1, 7):
            color = theme.get(f"accent{i}", "#0D9488")
            palette.append(color)
        return palette if palette else ["#0D9488"] * 6

    def _hex_to_hsl(self, hex_color: str) -> tuple[float, float, float]:
        """Convert hex to HSL."""
        hex_color = hex_color.lstrip("#")
        r, g, b = tuple(int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        return h, s, l

    def _hsl_to_hex(self, h: float, s: float, l: float) -> str:
        """Convert HSL to hex."""
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"

    def _shift_hue(self, palette: list[str], shift_degrees: float) -> list[str]:
        """Shift hue of all colors in palette."""
        result = []
        for color in palette:
            h, s, l = self._hex_to_hsl(color)
            new_h = (h + shift_degrees / 360) % 1.0
            result.append(self._hsl_to_hex(new_h, s, l))
        return result

    def _generate_complementary(self, palette: list[str]) -> list[str]:
        """Generate complementary color scheme."""
        if not palette:
            return ["#0D9488"] * 6

        base_h, base_s, base_l = self._hex_to_hsl(palette[0])
        comp_h = (base_h + 0.5) % 1.0

        return [
            self._hsl_to_hex(base_h, base_s, base_l),
            self._hsl_to_hex(base_h, base_s * 0.8, min(base_l + 0.1, 0.9)),
            self._hsl_to_hex(base_h, base_s * 0.6, min(base_l + 0.2, 0.95)),
            self._hsl_to_hex(comp_h, base_s, base_l),
            self._hsl_to_hex(comp_h, base_s * 0.8, min(base_l + 0.1, 0.9)),
            self._hsl_to_hex(comp_h, base_s * 0.6, min(base_l + 0.2, 0.95)),
        ]

    def _generate_analogous(self, palette: list[str]) -> list[str]:
        """Generate analogous color scheme (adjacent hues)."""
        if not palette:
            return ["#0D9488"] * 6

        base_h, base_s, base_l = self._hex_to_hsl(palette[0])

        return [
            self._hsl_to_hex((base_h - 0.083) % 1.0, base_s, base_l),  # -30 degrees
            self._hsl_to_hex(base_h, base_s, base_l),  # base
            self._hsl_to_hex((base_h + 0.083) % 1.0, base_s, base_l),  # +30 degrees
            self._hsl_to_hex((base_h - 0.083) % 1.0, base_s * 0.7, min(base_l + 0.15, 0.9)),
            self._hsl_to_hex(base_h, base_s * 0.7, min(base_l + 0.15, 0.9)),
            self._hsl_to_hex((base_h + 0.083) % 1.0, base_s * 0.7, min(base_l + 0.15, 0.9)),
        ]

    def _generate_monochromatic(self, base_color: str) -> list[str]:
        """Generate monochromatic scheme from base color."""
        h, s, l = self._hex_to_hsl(base_color)

        return [
            self._hsl_to_hex(h, s, max(l - 0.2, 0.1)),
            self._hsl_to_hex(h, s, l),
            self._hsl_to_hex(h, s * 0.9, min(l + 0.1, 0.8)),
            self._hsl_to_hex(h, s * 0.8, min(l + 0.2, 0.85)),
            self._hsl_to_hex(h, s * 0.6, min(l + 0.3, 0.9)),
            self._hsl_to_hex(h, s * 0.4, min(l + 0.4, 0.95)),
        ]

    def _update_shape_colors(self, shapes: list[dict], palette: list[str]) -> None:
        """Update shape colors with new palette."""
        for shape in shapes:
            fill = shape.get("fill", {})
            if isinstance(fill, dict) and "color" in fill:
                color = fill["color"]
                if color.startswith("accent"):
                    try:
                        idx = int(color.replace("accent", "")) - 1
                        if 0 <= idx < len(palette):
                            fill["color"] = palette[idx]
                    except ValueError:
                        pass
