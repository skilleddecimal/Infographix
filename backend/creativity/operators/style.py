"""Style variation operators."""

import random
from typing import Any

from backend.creativity.operators.base import VariationOperator, VariationParams


class AccentStyleVariation(VariationOperator):
    """Swap accent styles (ring, arc, glow, none)."""

    name = "accent_style"
    description = "Change accent decorations on shapes"
    applicable_archetypes = []  # All archetypes

    # Available accent styles
    ACCENT_STYLES = ["ring", "arc", "glow", "gradient_overlay", "none"]

    def apply(self, dsl: dict[str, Any], params: VariationParams) -> dict[str, Any]:
        """Apply accent style variation.

        Args:
            dsl: Input DSL scene graph.
            params: Variation parameters.

        Returns:
            DSL with modified accent styles.
        """
        result = self._deep_copy(dsl)

        if params.seed is not None:
            random.seed(params.seed)

        target_style = params.extra.get("style")
        if not target_style:
            # Select random style based on intensity
            if params.intensity < 0.3:
                # Subtle: prefer none or subtle effects
                target_style = random.choice(["none", "glow"])
            elif params.intensity < 0.7:
                # Medium: any style
                target_style = random.choice(self.ACCENT_STYLES)
            else:
                # High: prefer bold effects
                target_style = random.choice(["ring", "arc", "gradient_overlay"])

        shapes = result.get("shapes", [])
        for shape in shapes:
            self._apply_accent_style(shape, target_style, params.intensity)

        return result

    def get_variation_range(self, dsl: dict[str, Any]) -> dict[str, Any]:
        """Get accent style variation range."""
        return {
            "styles": self.ACCENT_STYLES,
            "current_styles": self._detect_current_styles(dsl),
        }

    def _detect_current_styles(self, dsl: dict[str, Any]) -> list[str]:
        """Detect current accent styles in DSL."""
        styles = set()
        for shape in dsl.get("shapes", []):
            effects = shape.get("effects", {})
            if effects.get("ring"):
                styles.add("ring")
            if effects.get("arc"):
                styles.add("arc")
            if effects.get("glow"):
                styles.add("glow")
            if effects.get("gradient_overlay"):
                styles.add("gradient_overlay")
        return list(styles) if styles else ["none"]

    def _apply_accent_style(
        self,
        shape: dict,
        style: str,
        intensity: float,
    ) -> None:
        """Apply accent style to a shape."""
        if "effects" not in shape:
            shape["effects"] = {}

        effects = shape["effects"]

        # Clear existing accent effects
        for key in ["ring", "arc", "glow", "gradient_overlay"]:
            effects.pop(key, None)

        if style == "none":
            return

        if style == "ring":
            effects["ring"] = {
                "width": 2 + int(4 * intensity),
                "color": shape.get("fill", {}).get("color", "#0D9488"),
                "opacity": 0.3 + 0.4 * intensity,
            }
        elif style == "arc":
            effects["arc"] = {
                "position": "top",
                "thickness": 3 + int(3 * intensity),
                "color": shape.get("fill", {}).get("color", "#0D9488"),
            }
        elif style == "glow":
            effects["glow"] = {
                "radius": 4 + int(8 * intensity),
                "color": shape.get("fill", {}).get("color", "#0D9488"),
                "opacity": 0.2 + 0.3 * intensity,
            }
        elif style == "gradient_overlay":
            effects["gradient_overlay"] = {
                "type": "radial",
                "opacity": 0.2 + 0.3 * intensity,
            }


class DepthVariation(VariationOperator):
    """Adjust shadow/3D effect intensity."""

    name = "depth"
    description = "Adjust shadow and 3D depth effects"
    applicable_archetypes = []  # All archetypes

    # Depth presets
    DEPTH_PRESETS = {
        "flat": {"shadow": None, "bevel": None},
        "subtle": {
            "shadow": {"blur": 4, "offset_x": 2, "offset_y": 2, "opacity": 0.15},
            "bevel": None,
        },
        "soft": {
            "shadow": {"blur": 8, "offset_x": 4, "offset_y": 4, "opacity": 0.25},
            "bevel": None,
        },
        "elevated": {
            "shadow": {"blur": 16, "offset_x": 0, "offset_y": 8, "opacity": 0.3},
            "bevel": None,
        },
        "3d": {
            "shadow": {"blur": 4, "offset_x": 4, "offset_y": 4, "opacity": 0.4},
            "bevel": {"width": 2, "height": 2},
        },
    }

    def apply(self, dsl: dict[str, Any], params: VariationParams) -> dict[str, Any]:
        """Apply depth variation.

        Args:
            dsl: Input DSL scene graph.
            params: Variation parameters.

        Returns:
            DSL with modified depth effects.
        """
        result = self._deep_copy(dsl)

        if params.seed is not None:
            random.seed(params.seed)

        preset = params.extra.get("preset")
        if not preset:
            # Select preset based on intensity
            if params.intensity < 0.2:
                preset = "flat"
            elif params.intensity < 0.4:
                preset = "subtle"
            elif params.intensity < 0.6:
                preset = "soft"
            elif params.intensity < 0.8:
                preset = "elevated"
            else:
                preset = "3d"

        depth_config = self.DEPTH_PRESETS.get(preset, self.DEPTH_PRESETS["soft"])

        shapes = result.get("shapes", [])
        for shape in shapes:
            self._apply_depth(shape, depth_config)

        return result

    def get_variation_range(self, dsl: dict[str, Any]) -> dict[str, Any]:
        """Get depth variation range."""
        return {
            "presets": list(self.DEPTH_PRESETS.keys()),
            "current_preset": self._detect_current_depth(dsl),
        }

    def _detect_current_depth(self, dsl: dict[str, Any]) -> str:
        """Detect current depth preset."""
        shapes = dsl.get("shapes", [])
        if not shapes:
            return "flat"

        shape = shapes[0]
        effects = shape.get("effects", {})
        shadow = effects.get("shadow")

        if not shadow:
            return "flat"
        if shadow.get("blur", 0) <= 4:
            return "subtle"
        if shadow.get("blur", 0) <= 8:
            return "soft"
        if shadow.get("offset_y", 0) >= 8:
            return "elevated"
        return "3d"

    def _apply_depth(self, shape: dict, config: dict) -> None:
        """Apply depth configuration to shape."""
        if "effects" not in shape:
            shape["effects"] = {}

        effects = shape["effects"]

        # Apply shadow
        if config["shadow"]:
            effects["shadow"] = {
                "blur": config["shadow"]["blur"],
                "offset_x": config["shadow"]["offset_x"],
                "offset_y": config["shadow"]["offset_y"],
                "color": f"#000000{int(config['shadow']['opacity'] * 255):02X}",
            }
        else:
            effects.pop("shadow", None)

        # Apply bevel
        if config.get("bevel"):
            effects["bevel"] = config["bevel"]
        else:
            effects.pop("bevel", None)


class CornerRadiusVariation(VariationOperator):
    """Adjust corner radius styles."""

    name = "corner_radius"
    description = "Adjust corner roundness of shapes"
    applicable_archetypes = []  # All archetypes

    # Corner radius presets
    CORNER_PRESETS = {
        "sharp": 0,
        "subtle": 4,
        "rounded": 8,
        "pill": 50,  # Percentage for pill shape
    }

    def apply(self, dsl: dict[str, Any], params: VariationParams) -> dict[str, Any]:
        """Apply corner radius variation.

        Args:
            dsl: Input DSL scene graph.
            params: Variation parameters.

        Returns:
            DSL with modified corner radii.
        """
        result = self._deep_copy(dsl)

        if params.seed is not None:
            random.seed(params.seed)

        preset = params.extra.get("preset")
        if not preset:
            # Select preset based on intensity
            if params.intensity < 0.25:
                preset = "sharp"
            elif params.intensity < 0.5:
                preset = "subtle"
            elif params.intensity < 0.75:
                preset = "rounded"
            else:
                preset = "pill"

        radius = self.CORNER_PRESETS.get(preset, 8)
        is_percentage = preset == "pill"

        shapes = result.get("shapes", [])
        for shape in shapes:
            self._apply_corner_radius(shape, radius, is_percentage)

        return result

    def get_variation_range(self, dsl: dict[str, Any]) -> dict[str, Any]:
        """Get corner radius variation range."""
        return {
            "presets": list(self.CORNER_PRESETS.keys()),
            "current_preset": self._detect_current_radius(dsl),
        }

    def _detect_current_radius(self, dsl: dict[str, Any]) -> str:
        """Detect current corner radius preset."""
        shapes = dsl.get("shapes", [])
        if not shapes:
            return "rounded"

        shape = shapes[0]
        radius = shape.get("corner_radius", 0)

        if isinstance(radius, str) and "%" in radius:
            return "pill"
        if radius == 0:
            return "sharp"
        if radius <= 4:
            return "subtle"
        if radius <= 12:
            return "rounded"
        return "pill"

    def _apply_corner_radius(
        self,
        shape: dict,
        radius: int | float,
        is_percentage: bool,
    ) -> None:
        """Apply corner radius to shape."""
        if is_percentage:
            shape["corner_radius"] = f"{radius}%"
        else:
            shape["corner_radius"] = radius

        # Also update shape type if applicable
        shape_type = shape.get("auto_shape_type", "")
        if radius == 0 and shape_type == "roundRect":
            shape["auto_shape_type"] = "rect"
        elif radius > 0 and shape_type == "rect":
            shape["auto_shape_type"] = "roundRect"
