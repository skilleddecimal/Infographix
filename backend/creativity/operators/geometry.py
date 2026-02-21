"""Geometry variation operators."""

import random
from typing import Any

from backend.creativity.operators.base import VariationOperator, VariationParams


class TaperVariation(VariationOperator):
    """Adjust funnel/pyramid taper ratio.

    Controls how much shapes narrow from top to bottom (funnel)
    or bottom to top (pyramid).
    """

    name = "taper"
    description = "Adjust taper ratio for funnel/pyramid shapes"
    applicable_archetypes = ["funnel", "pyramid"]

    def apply(self, dsl: dict[str, Any], params: VariationParams) -> dict[str, Any]:
        """Apply taper variation.

        Args:
            dsl: Input DSL scene graph.
            params: Variation parameters.

        Returns:
            DSL with modified taper.
        """
        result = self._deep_copy(dsl)

        if params.seed is not None:
            random.seed(params.seed)

        archetype = dsl.get("archetype", "funnel")
        shapes = result.get("shapes", [])

        if not shapes:
            return result

        # Calculate taper range based on intensity
        # 0.0 intensity = no taper change
        # 1.0 intensity = maximum taper (0.3 to 0.9)
        base_taper = params.extra.get("base_taper", 0.6)
        taper_range = 0.3 * params.intensity

        new_taper = base_taper + random.uniform(-taper_range, taper_range)
        new_taper = max(0.3, min(0.9, new_taper))

        # Apply taper to shapes
        self._apply_taper(shapes, new_taper, archetype)

        return result

    def get_variation_range(self, dsl: dict[str, Any]) -> dict[str, Any]:
        """Get taper variation range."""
        return {
            "min_taper": 0.3,
            "max_taper": 0.9,
            "current_taper": self._detect_current_taper(dsl),
        }

    def _detect_current_taper(self, dsl: dict[str, Any]) -> float:
        """Detect current taper ratio from shapes."""
        shapes = dsl.get("shapes", [])
        if len(shapes) < 2:
            return 0.6

        # Compare widths of first and last shapes
        widths = [s.get("bbox", {}).get("width", 100) for s in shapes]
        if widths[0] == 0:
            return 0.6
        return widths[-1] / widths[0]

    def _apply_taper(
        self,
        shapes: list[dict],
        taper: float,
        archetype: str,
    ) -> None:
        """Apply taper ratio to shapes."""
        if not shapes:
            return

        # Sort shapes by y position
        sorted_shapes = sorted(shapes, key=lambda s: s.get("bbox", {}).get("y", 0))

        # Get base width (top for funnel, bottom for pyramid)
        base_idx = 0 if archetype == "funnel" else -1
        base_width = sorted_shapes[base_idx].get("bbox", {}).get("width", 100)
        center_x = sorted_shapes[base_idx].get("bbox", {}).get("x", 0) + base_width / 2

        # Calculate width progression
        n = len(sorted_shapes)
        for i, shape in enumerate(sorted_shapes):
            if "bbox" not in shape:
                continue

            if archetype == "funnel":
                # Funnel: wider at top, narrower at bottom
                progress = i / (n - 1) if n > 1 else 0
                width_ratio = 1 - (1 - taper) * progress
            else:
                # Pyramid: narrower at top, wider at bottom
                progress = (n - 1 - i) / (n - 1) if n > 1 else 0
                width_ratio = 1 - (1 - taper) * progress

            new_width = base_width * width_ratio
            shape["bbox"]["width"] = new_width
            shape["bbox"]["x"] = center_x - new_width / 2


class ScaleVariation(VariationOperator):
    """Scale shapes uniformly or differentially."""

    name = "scale"
    description = "Scale shapes while maintaining proportions"
    applicable_archetypes = []  # All archetypes

    def apply(self, dsl: dict[str, Any], params: VariationParams) -> dict[str, Any]:
        """Apply scale variation.

        Args:
            dsl: Input DSL scene graph.
            params: Variation parameters.

        Returns:
            DSL with scaled shapes.
        """
        result = self._deep_copy(dsl)

        if params.seed is not None:
            random.seed(params.seed)

        mode = params.extra.get("mode", "uniform")
        shapes = result.get("shapes", [])

        if not shapes:
            return result

        # Calculate scale factor (0.7 to 1.3 range)
        scale_range = 0.3 * params.intensity
        if mode == "uniform":
            scale = 1.0 + random.uniform(-scale_range, scale_range)
            self._scale_uniform(shapes, scale)
        elif mode == "differential":
            self._scale_differential(shapes, params.intensity)

        return result

    def get_variation_range(self, dsl: dict[str, Any]) -> dict[str, Any]:
        """Get scale variation range."""
        return {
            "modes": ["uniform", "differential"],
            "min_scale": 0.7,
            "max_scale": 1.3,
        }

    def _scale_uniform(self, shapes: list[dict], scale: float) -> None:
        """Scale all shapes uniformly."""
        # Find center point
        all_x = [s.get("bbox", {}).get("x", 0) + s.get("bbox", {}).get("width", 0) / 2 for s in shapes]
        all_y = [s.get("bbox", {}).get("y", 0) + s.get("bbox", {}).get("height", 0) / 2 for s in shapes]

        if not all_x or not all_y:
            return

        center_x = sum(all_x) / len(all_x)
        center_y = sum(all_y) / len(all_y)

        for shape in shapes:
            bbox = shape.get("bbox", {})
            if not bbox:
                continue

            # Scale dimensions
            old_w, old_h = bbox.get("width", 0), bbox.get("height", 0)
            new_w, new_h = old_w * scale, old_h * scale

            # Scale position relative to center
            old_cx = bbox.get("x", 0) + old_w / 2
            old_cy = bbox.get("y", 0) + old_h / 2

            new_cx = center_x + (old_cx - center_x) * scale
            new_cy = center_y + (old_cy - center_y) * scale

            bbox["width"] = new_w
            bbox["height"] = new_h
            bbox["x"] = new_cx - new_w / 2
            bbox["y"] = new_cy - new_h / 2

    def _scale_differential(self, shapes: list[dict], intensity: float) -> None:
        """Scale shapes with slight random variation."""
        for shape in shapes:
            bbox = shape.get("bbox", {})
            if not bbox:
                continue

            # Small random scale per shape
            scale = 1.0 + random.uniform(-0.1, 0.1) * intensity
            bbox["width"] = bbox.get("width", 0) * scale
            bbox["height"] = bbox.get("height", 0) * scale


class SpacingVariation(VariationOperator):
    """Adjust spacing between elements."""

    name = "spacing"
    description = "Adjust spacing between diagram elements"
    applicable_archetypes = []  # All archetypes

    def apply(self, dsl: dict[str, Any], params: VariationParams) -> dict[str, Any]:
        """Apply spacing variation.

        Args:
            dsl: Input DSL scene graph.
            params: Variation parameters.

        Returns:
            DSL with modified spacing.
        """
        result = self._deep_copy(dsl)

        if params.seed is not None:
            random.seed(params.seed)

        mode = params.extra.get("mode", "uniform")
        shapes = result.get("shapes", [])

        if len(shapes) < 2:
            return result

        # Calculate spacing multiplier (0.5 to 1.5 range)
        spacing_range = 0.5 * params.intensity
        multiplier = 1.0 + random.uniform(-spacing_range, spacing_range)

        self._adjust_spacing(shapes, multiplier, mode)

        return result

    def get_variation_range(self, dsl: dict[str, Any]) -> dict[str, Any]:
        """Get spacing variation range."""
        return {
            "modes": ["uniform", "proportional"],
            "min_multiplier": 0.5,
            "max_multiplier": 1.5,
        }

    def _adjust_spacing(
        self,
        shapes: list[dict],
        multiplier: float,
        mode: str,
    ) -> None:
        """Adjust spacing between shapes."""
        # Determine primary axis (vertical or horizontal)
        y_positions = [s.get("bbox", {}).get("y", 0) for s in shapes]
        x_positions = [s.get("bbox", {}).get("x", 0) for s in shapes]

        y_range = max(y_positions) - min(y_positions) if y_positions else 0
        x_range = max(x_positions) - min(x_positions) if x_positions else 0

        if y_range >= x_range:
            # Vertical arrangement
            sorted_shapes = sorted(shapes, key=lambda s: s.get("bbox", {}).get("y", 0))
            self._adjust_vertical_spacing(sorted_shapes, multiplier)
        else:
            # Horizontal arrangement
            sorted_shapes = sorted(shapes, key=lambda s: s.get("bbox", {}).get("x", 0))
            self._adjust_horizontal_spacing(sorted_shapes, multiplier)

    def _adjust_vertical_spacing(self, shapes: list[dict], multiplier: float) -> None:
        """Adjust vertical spacing."""
        if len(shapes) < 2:
            return

        # Calculate center of first shape as anchor
        first_y = shapes[0].get("bbox", {}).get("y", 0)

        for i in range(1, len(shapes)):
            prev_bbox = shapes[i - 1].get("bbox", {})
            curr_bbox = shapes[i].get("bbox", {})

            if not prev_bbox or not curr_bbox:
                continue

            prev_bottom = prev_bbox.get("y", 0) + prev_bbox.get("height", 0)
            curr_top = curr_bbox.get("y", 0)
            gap = curr_top - prev_bottom

            # Adjust gap
            new_gap = gap * multiplier
            curr_bbox["y"] = prev_bottom + new_gap

    def _adjust_horizontal_spacing(self, shapes: list[dict], multiplier: float) -> None:
        """Adjust horizontal spacing."""
        if len(shapes) < 2:
            return

        for i in range(1, len(shapes)):
            prev_bbox = shapes[i - 1].get("bbox", {})
            curr_bbox = shapes[i].get("bbox", {})

            if not prev_bbox or not curr_bbox:
                continue

            prev_right = prev_bbox.get("x", 0) + prev_bbox.get("width", 0)
            curr_left = curr_bbox.get("x", 0)
            gap = curr_left - prev_right

            # Adjust gap
            new_gap = gap * multiplier
            curr_bbox["x"] = prev_right + new_gap
