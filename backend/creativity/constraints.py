"""Brand constraint checker for creativity engine."""

import colorsys
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BrandGuidelines:
    """Brand guidelines for constraint checking."""

    # Required colors (must be used)
    primary_colors: list[str] = field(default_factory=list)

    # Allowed colors (can be used)
    allowed_colors: list[str] = field(default_factory=list)

    # Forbidden colors (must not be used)
    forbidden_colors: list[str] = field(default_factory=list)

    # Font restrictions
    allowed_fonts: list[str] = field(default_factory=list)

    # Corner radius restrictions
    min_corner_radius: float = 0
    max_corner_radius: float = 50

    # Shadow restrictions
    allow_shadows: bool = True
    max_shadow_blur: float = 20

    # Effect restrictions
    allow_glow: bool = True
    allow_gradients: bool = True

    # Color tolerance for matching (0-1)
    color_tolerance: float = 0.1


@dataclass
class ConstraintViolation:
    """A constraint violation."""

    severity: str  # "error", "warning"
    category: str  # "color", "font", "style", "layout"
    message: str
    shape_id: str | None = None
    suggested_fix: dict[str, Any] | None = None


@dataclass
class ConstraintResult:
    """Result of constraint checking."""

    is_valid: bool
    violations: list[ConstraintViolation] = field(default_factory=list)
    score: float = 1.0  # 0.0 = many violations, 1.0 = perfect compliance

    @property
    def error_count(self) -> int:
        """Count error-severity violations."""
        return sum(1 for v in self.violations if v.severity == "error")

    @property
    def warning_count(self) -> int:
        """Count warning-severity violations."""
        return sum(1 for v in self.violations if v.severity == "warning")


class BrandConstraintChecker:
    """Check DSL against brand guidelines.

    Ensures generated variations comply with brand requirements
    for colors, fonts, styles, and layout.
    """

    def __init__(self, guidelines: BrandGuidelines | None = None):
        """Initialize constraint checker.

        Args:
            guidelines: Brand guidelines to enforce.
        """
        self.guidelines = guidelines or BrandGuidelines()

    def check(self, dsl: dict[str, Any]) -> ConstraintResult:
        """Check DSL against brand constraints.

        Args:
            dsl: DSL scene graph to check.

        Returns:
            ConstraintResult with violations if any.
        """
        violations = []

        # Check colors
        violations.extend(self._check_colors(dsl))

        # Check fonts
        violations.extend(self._check_fonts(dsl))

        # Check styles
        violations.extend(self._check_styles(dsl))

        # Check layout
        violations.extend(self._check_layout(dsl))

        # Calculate compliance score
        error_weight = 1.0
        warning_weight = 0.3
        total_weight = sum(
            error_weight if v.severity == "error" else warning_weight
            for v in violations
        )
        score = max(0.0, 1.0 - total_weight * 0.1)

        return ConstraintResult(
            is_valid=all(v.severity != "error" for v in violations),
            violations=violations,
            score=score,
        )

    def enforce(self, dsl: dict[str, Any]) -> tuple[dict[str, Any], ConstraintResult]:
        """Enforce brand constraints by fixing violations.

        Args:
            dsl: DSL scene graph.

        Returns:
            Tuple of (fixed DSL, result with remaining violations).
        """
        import copy
        fixed_dsl = copy.deepcopy(dsl)

        # Fix color violations
        self._fix_colors(fixed_dsl)

        # Fix font violations
        self._fix_fonts(fixed_dsl)

        # Fix style violations
        self._fix_styles(fixed_dsl)

        # Re-check
        result = self.check(fixed_dsl)

        return fixed_dsl, result

    def _check_colors(self, dsl: dict[str, Any]) -> list[ConstraintViolation]:
        """Check color constraints."""
        violations = []

        # Collect all colors used
        used_colors = self._collect_colors(dsl)

        # Check for forbidden colors
        for color in used_colors:
            for forbidden in self.guidelines.forbidden_colors:
                if self._colors_match(color, forbidden):
                    violations.append(ConstraintViolation(
                        severity="error",
                        category="color",
                        message=f"Forbidden color {color} used",
                        suggested_fix={"replace_color": self._get_nearest_allowed(color)},
                    ))
                    break

        # Check if primary colors are used (if required)
        if self.guidelines.primary_colors:
            for primary in self.guidelines.primary_colors:
                found = any(
                    self._colors_match(used, primary)
                    for used in used_colors
                )
                if not found:
                    violations.append(ConstraintViolation(
                        severity="warning",
                        category="color",
                        message=f"Primary brand color {primary} not used",
                    ))

        # Check if colors are in allowed list (if allowed list specified)
        if self.guidelines.allowed_colors:
            for color in used_colors:
                in_allowed = any(
                    self._colors_match(color, allowed)
                    for allowed in self.guidelines.allowed_colors
                )
                in_primary = any(
                    self._colors_match(color, primary)
                    for primary in self.guidelines.primary_colors
                )
                if not in_allowed and not in_primary:
                    violations.append(ConstraintViolation(
                        severity="warning",
                        category="color",
                        message=f"Color {color} not in brand palette",
                        suggested_fix={"replace_color": self._get_nearest_allowed(color)},
                    ))

        return violations

    def _check_fonts(self, dsl: dict[str, Any]) -> list[ConstraintViolation]:
        """Check font constraints."""
        violations = []

        if not self.guidelines.allowed_fonts:
            return violations

        # Check main font
        font = dsl.get("font_family")
        if font and font not in self.guidelines.allowed_fonts:
            violations.append(ConstraintViolation(
                severity="error",
                category="font",
                message=f"Font '{font}' not in allowed fonts",
                suggested_fix={"font_family": self.guidelines.allowed_fonts[0]},
            ))

        # Check shape-level fonts
        for shape in dsl.get("shapes", []):
            text = shape.get("text", {})
            shape_font = text.get("font_family")
            if shape_font and shape_font not in self.guidelines.allowed_fonts:
                violations.append(ConstraintViolation(
                    severity="error",
                    category="font",
                    message=f"Font '{shape_font}' not allowed",
                    shape_id=shape.get("id"),
                    suggested_fix={"font_family": self.guidelines.allowed_fonts[0]},
                ))

        return violations

    def _check_styles(self, dsl: dict[str, Any]) -> list[ConstraintViolation]:
        """Check style constraints."""
        violations = []

        for shape in dsl.get("shapes", []):
            shape_id = shape.get("id")
            effects = shape.get("effects", {})

            # Check corner radius
            radius = shape.get("corner_radius", 0)
            if isinstance(radius, str):
                radius = 50  # Treat percentage as max
            if radius < self.guidelines.min_corner_radius:
                violations.append(ConstraintViolation(
                    severity="warning",
                    category="style",
                    message=f"Corner radius {radius} below minimum {self.guidelines.min_corner_radius}",
                    shape_id=shape_id,
                ))
            if radius > self.guidelines.max_corner_radius:
                violations.append(ConstraintViolation(
                    severity="warning",
                    category="style",
                    message=f"Corner radius {radius} above maximum {self.guidelines.max_corner_radius}",
                    shape_id=shape_id,
                ))

            # Check shadow
            shadow = effects.get("shadow")
            if shadow and not self.guidelines.allow_shadows:
                violations.append(ConstraintViolation(
                    severity="error",
                    category="style",
                    message="Shadows not allowed",
                    shape_id=shape_id,
                ))
            elif shadow and shadow.get("blur", 0) > self.guidelines.max_shadow_blur:
                violations.append(ConstraintViolation(
                    severity="warning",
                    category="style",
                    message=f"Shadow blur exceeds maximum {self.guidelines.max_shadow_blur}",
                    shape_id=shape_id,
                ))

            # Check glow
            if effects.get("glow") and not self.guidelines.allow_glow:
                violations.append(ConstraintViolation(
                    severity="error",
                    category="style",
                    message="Glow effects not allowed",
                    shape_id=shape_id,
                ))

            # Check gradients
            fill = shape.get("fill", {})
            if isinstance(fill, dict) and fill.get("type") == "gradient":
                if not self.guidelines.allow_gradients:
                    violations.append(ConstraintViolation(
                        severity="error",
                        category="style",
                        message="Gradient fills not allowed",
                        shape_id=shape_id,
                    ))

        return violations

    def _check_layout(self, dsl: dict[str, Any]) -> list[ConstraintViolation]:
        """Check layout constraints."""
        violations = []

        shapes = dsl.get("shapes", [])
        canvas = dsl.get("canvas", {"width": 960, "height": 540})
        canvas_w = canvas.get("width", 960)
        canvas_h = canvas.get("height", 540)

        for shape in shapes:
            shape_id = shape.get("id")
            bbox = shape.get("bbox", {})
            x = bbox.get("x", 0)
            y = bbox.get("y", 0)
            w = bbox.get("width", 0)
            h = bbox.get("height", 0)

            # Check if shape is outside canvas
            if x < 0 or y < 0:
                violations.append(ConstraintViolation(
                    severity="warning",
                    category="layout",
                    message=f"Shape extends outside canvas (negative position)",
                    shape_id=shape_id,
                ))
            if x + w > canvas_w or y + h > canvas_h:
                violations.append(ConstraintViolation(
                    severity="warning",
                    category="layout",
                    message=f"Shape extends outside canvas",
                    shape_id=shape_id,
                ))

        return violations

    def _collect_colors(self, dsl: dict[str, Any]) -> set[str]:
        """Collect all colors used in DSL."""
        colors = set()

        # Theme colors
        theme = dsl.get("theme", {})
        for key, value in theme.items():
            if isinstance(value, str) and self._is_hex_color(value):
                colors.add(value.upper())

        # Shape colors
        for shape in dsl.get("shapes", []):
            fill = shape.get("fill", {})
            if isinstance(fill, dict):
                color = fill.get("color")
                if color and self._is_hex_color(color):
                    colors.add(color.upper())

            stroke = shape.get("stroke", {})
            if isinstance(stroke, dict):
                color = stroke.get("color")
                if color and self._is_hex_color(color):
                    colors.add(color.upper())

        return colors

    def _is_hex_color(self, value: str) -> bool:
        """Check if value is a hex color."""
        return bool(re.match(r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$", value))

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        """Convert hex to RGB."""
        hex_color = hex_color.lstrip("#")[:6]
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _colors_match(self, color1: str, color2: str) -> bool:
        """Check if two colors match within tolerance."""
        try:
            rgb1 = self._hex_to_rgb(color1)
            rgb2 = self._hex_to_rgb(color2)

            # Calculate color distance
            distance = sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)) ** 0.5
            max_distance = (255 ** 2 * 3) ** 0.5

            return distance / max_distance <= self.guidelines.color_tolerance
        except (ValueError, IndexError):
            return color1.upper() == color2.upper()

    def _get_nearest_allowed(self, color: str) -> str | None:
        """Get nearest allowed color."""
        allowed = self.guidelines.allowed_colors + self.guidelines.primary_colors
        if not allowed:
            return None

        try:
            rgb = self._hex_to_rgb(color)

            min_distance = float("inf")
            nearest = allowed[0]

            for allowed_color in allowed:
                allowed_rgb = self._hex_to_rgb(allowed_color)
                distance = sum((a - b) ** 2 for a, b in zip(rgb, allowed_rgb)) ** 0.5
                if distance < min_distance:
                    min_distance = distance
                    nearest = allowed_color

            return nearest
        except (ValueError, IndexError):
            return allowed[0] if allowed else None

    def _fix_colors(self, dsl: dict[str, Any]) -> None:
        """Fix color violations in place."""
        # Fix shape colors
        for shape in dsl.get("shapes", []):
            fill = shape.get("fill", {})
            if isinstance(fill, dict) and "color" in fill:
                color = fill["color"]
                if self._is_hex_color(color):
                    # Check if forbidden
                    for forbidden in self.guidelines.forbidden_colors:
                        if self._colors_match(color, forbidden):
                            nearest = self._get_nearest_allowed(color)
                            if nearest:
                                fill["color"] = nearest
                            break

    def _fix_fonts(self, dsl: dict[str, Any]) -> None:
        """Fix font violations in place."""
        if not self.guidelines.allowed_fonts:
            return

        default_font = self.guidelines.allowed_fonts[0]

        # Fix main font
        if dsl.get("font_family") not in self.guidelines.allowed_fonts:
            dsl["font_family"] = default_font

        # Fix shape fonts
        for shape in dsl.get("shapes", []):
            text = shape.get("text", {})
            if text.get("font_family") not in self.guidelines.allowed_fonts:
                text["font_family"] = default_font

    def _fix_styles(self, dsl: dict[str, Any]) -> None:
        """Fix style violations in place."""
        for shape in dsl.get("shapes", []):
            effects = shape.get("effects", {})

            # Remove forbidden shadows
            if not self.guidelines.allow_shadows and "shadow" in effects:
                del effects["shadow"]

            # Clamp shadow blur
            shadow = effects.get("shadow")
            if shadow and shadow.get("blur", 0) > self.guidelines.max_shadow_blur:
                shadow["blur"] = self.guidelines.max_shadow_blur

            # Remove forbidden glow
            if not self.guidelines.allow_glow and "glow" in effects:
                del effects["glow"]

            # Remove forbidden gradients
            fill = shape.get("fill", {})
            if isinstance(fill, dict) and fill.get("type") == "gradient":
                if not self.guidelines.allow_gradients:
                    # Convert to solid color
                    stops = fill.get("stops", [])
                    if stops:
                        shape["fill"] = {"type": "solid", "color": stops[0].get("color", "#0D9488")}
