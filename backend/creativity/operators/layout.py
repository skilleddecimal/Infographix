"""Layout variation operators."""

import random
from typing import Any

from backend.creativity.operators.base import VariationOperator, VariationParams


class LabelPlacementVariation(VariationOperator):
    """Change label placement (inside vs callout)."""

    name = "label_placement"
    description = "Change label position relative to shapes"
    applicable_archetypes = ["funnel", "pyramid", "timeline", "process"]

    # Label placement options
    PLACEMENTS = ["inside", "callout_left", "callout_right", "above", "below"]

    def apply(self, dsl: dict[str, Any], params: VariationParams) -> dict[str, Any]:
        """Apply label placement variation.

        Args:
            dsl: Input DSL scene graph.
            params: Variation parameters.

        Returns:
            DSL with modified label positions.
        """
        result = self._deep_copy(dsl)

        if params.seed is not None:
            random.seed(params.seed)

        placement = params.extra.get("placement")
        if not placement:
            placement = random.choice(self.PLACEMENTS)

        shapes = result.get("shapes", [])
        self._apply_label_placement(shapes, placement)

        return result

    def get_variation_range(self, dsl: dict[str, Any]) -> dict[str, Any]:
        """Get label placement variation range."""
        return {
            "placements": self.PLACEMENTS,
            "current_placement": self._detect_current_placement(dsl),
        }

    def _detect_current_placement(self, dsl: dict[str, Any]) -> str:
        """Detect current label placement."""
        shapes = dsl.get("shapes", [])
        for shape in shapes:
            text = shape.get("text")
            if text:
                placement = text.get("placement", "inside")
                if placement in self.PLACEMENTS:
                    return placement
        return "inside"

    def _apply_label_placement(self, shapes: list[dict], placement: str) -> None:
        """Apply label placement to all shapes with text."""
        for shape in shapes:
            text = shape.get("text")
            if not text:
                continue

            text["placement"] = placement

            # Adjust text alignment based on placement
            if placement == "inside":
                text["horizontal_alignment"] = "center"
                text["vertical_alignment"] = "middle"
            elif placement == "callout_left":
                text["horizontal_alignment"] = "right"
                text["callout_offset"] = {"x": -20, "y": 0}
            elif placement == "callout_right":
                text["horizontal_alignment"] = "left"
                text["callout_offset"] = {"x": 20, "y": 0}
            elif placement == "above":
                text["vertical_alignment"] = "bottom"
                text["callout_offset"] = {"x": 0, "y": -15}
            elif placement == "below":
                text["vertical_alignment"] = "top"
                text["callout_offset"] = {"x": 0, "y": 15}


class OrientationVariation(VariationOperator):
    """Change diagram orientation (horizontal/vertical/radial)."""

    name = "orientation"
    description = "Change diagram orientation"
    applicable_archetypes = ["timeline", "process", "funnel", "pyramid"]

    # Orientation options
    ORIENTATIONS = ["horizontal", "vertical", "radial"]

    def apply(self, dsl: dict[str, Any], params: VariationParams) -> dict[str, Any]:
        """Apply orientation variation.

        Args:
            dsl: Input DSL scene graph.
            params: Variation parameters.

        Returns:
            DSL with changed orientation.
        """
        result = self._deep_copy(dsl)

        if params.seed is not None:
            random.seed(params.seed)

        target_orientation = params.extra.get("orientation")
        if not target_orientation:
            target_orientation = random.choice(self.ORIENTATIONS)

        current_orientation = self._detect_current_orientation(dsl)
        if current_orientation == target_orientation:
            return result

        shapes = result.get("shapes", [])
        self._transform_orientation(shapes, current_orientation, target_orientation)

        result["orientation"] = target_orientation

        return result

    def get_variation_range(self, dsl: dict[str, Any]) -> dict[str, Any]:
        """Get orientation variation range."""
        return {
            "orientations": self.ORIENTATIONS,
            "current_orientation": self._detect_current_orientation(dsl),
        }

    def _detect_current_orientation(self, dsl: dict[str, Any]) -> str:
        """Detect current orientation from shape positions."""
        if dsl.get("orientation"):
            return dsl["orientation"]

        shapes = dsl.get("shapes", [])
        if len(shapes) < 2:
            return "horizontal"

        # Analyze shape positions
        y_positions = [s.get("bbox", {}).get("y", 0) for s in shapes]
        x_positions = [s.get("bbox", {}).get("x", 0) for s in shapes]

        y_range = max(y_positions) - min(y_positions) if y_positions else 0
        x_range = max(x_positions) - min(x_positions) if x_positions else 0

        if y_range > x_range * 1.5:
            return "vertical"
        elif x_range > y_range * 1.5:
            return "horizontal"
        return "horizontal"

    def _transform_orientation(
        self,
        shapes: list[dict],
        from_orientation: str,
        to_orientation: str,
    ) -> None:
        """Transform shapes from one orientation to another."""
        if not shapes:
            return

        if to_orientation == "radial":
            self._arrange_radially(shapes)
        elif from_orientation == "horizontal" and to_orientation == "vertical":
            self._transpose_shapes(shapes)
        elif from_orientation == "vertical" and to_orientation == "horizontal":
            self._transpose_shapes(shapes)
        elif from_orientation == "radial":
            # Convert radial to linear
            if to_orientation == "horizontal":
                self._arrange_horizontally(shapes)
            else:
                self._arrange_vertically(shapes)

    def _transpose_shapes(self, shapes: list[dict]) -> None:
        """Swap x and y positions (transpose)."""
        for shape in shapes:
            bbox = shape.get("bbox", {})
            if bbox:
                old_x, old_y = bbox.get("x", 0), bbox.get("y", 0)
                old_w, old_h = bbox.get("width", 100), bbox.get("height", 50)

                bbox["x"] = old_y
                bbox["y"] = old_x
                bbox["width"] = old_h
                bbox["height"] = old_w

    def _arrange_radially(self, shapes: list[dict]) -> None:
        """Arrange shapes in a radial pattern."""
        import math

        n = len(shapes)
        if n == 0:
            return

        # Calculate bounding box of all shapes
        all_x = [s.get("bbox", {}).get("x", 0) for s in shapes]
        all_y = [s.get("bbox", {}).get("y", 0) for s in shapes]
        all_w = [s.get("bbox", {}).get("width", 100) for s in shapes]
        all_h = [s.get("bbox", {}).get("height", 50) for s in shapes]

        center_x = sum(all_x) / n + sum(all_w) / (2 * n)
        center_y = sum(all_y) / n + sum(all_h) / (2 * n)
        radius = max(max(all_w), max(all_h)) * 1.5

        for i, shape in enumerate(shapes):
            angle = (2 * math.pi * i / n) - math.pi / 2  # Start from top
            bbox = shape.get("bbox", {})
            w, h = bbox.get("width", 100), bbox.get("height", 50)

            bbox["x"] = center_x + radius * math.cos(angle) - w / 2
            bbox["y"] = center_y + radius * math.sin(angle) - h / 2

    def _arrange_horizontally(self, shapes: list[dict]) -> None:
        """Arrange shapes horizontally."""
        if not shapes:
            return

        sorted_shapes = sorted(
            shapes,
            key=lambda s: s.get("bbox", {}).get("x", 0)
        )

        x = 50  # Starting x
        gap = 20
        y = 200  # Fixed y

        for shape in sorted_shapes:
            bbox = shape.get("bbox", {})
            w = bbox.get("width", 100)
            h = bbox.get("height", 50)

            bbox["x"] = x
            bbox["y"] = y - h / 2
            x += w + gap

    def _arrange_vertically(self, shapes: list[dict]) -> None:
        """Arrange shapes vertically."""
        if not shapes:
            return

        sorted_shapes = sorted(
            shapes,
            key=lambda s: s.get("bbox", {}).get("y", 0)
        )

        y = 50  # Starting y
        gap = 15
        x = 200  # Fixed x

        for shape in sorted_shapes:
            bbox = shape.get("bbox", {})
            w = bbox.get("width", 100)
            h = bbox.get("height", 50)

            bbox["x"] = x - w / 2
            bbox["y"] = y
            y += h + gap


class AlignmentVariation(VariationOperator):
    """Adjust alignment of shapes (left/center/right/distributed)."""

    name = "alignment"
    description = "Change shape alignment within diagram"
    applicable_archetypes = []  # All archetypes

    # Alignment options
    ALIGNMENTS = ["left", "center", "right", "distributed"]

    def apply(self, dsl: dict[str, Any], params: VariationParams) -> dict[str, Any]:
        """Apply alignment variation.

        Args:
            dsl: Input DSL scene graph.
            params: Variation parameters.

        Returns:
            DSL with adjusted alignment.
        """
        result = self._deep_copy(dsl)

        if params.seed is not None:
            random.seed(params.seed)

        alignment = params.extra.get("alignment")
        if not alignment:
            alignment = random.choice(self.ALIGNMENTS)

        shapes = result.get("shapes", [])
        canvas = result.get("canvas", {"width": 960, "height": 540})

        self._apply_alignment(shapes, alignment, canvas)

        return result

    def get_variation_range(self, dsl: dict[str, Any]) -> dict[str, Any]:
        """Get alignment variation range."""
        return {
            "alignments": self.ALIGNMENTS,
            "current_alignment": self._detect_current_alignment(dsl),
        }

    def _detect_current_alignment(self, dsl: dict[str, Any]) -> str:
        """Detect current alignment from shapes."""
        shapes = dsl.get("shapes", [])
        if len(shapes) < 2:
            return "center"

        # Check horizontal center alignment
        x_centers = [
            s.get("bbox", {}).get("x", 0) + s.get("bbox", {}).get("width", 0) / 2
            for s in shapes
        ]
        x_variance = max(x_centers) - min(x_centers) if x_centers else 0

        if x_variance < 10:
            return "center"

        # Check left alignment
        x_lefts = [s.get("bbox", {}).get("x", 0) for s in shapes]
        left_variance = max(x_lefts) - min(x_lefts) if x_lefts else 0

        if left_variance < 10:
            return "left"

        # Check right alignment
        x_rights = [
            s.get("bbox", {}).get("x", 0) + s.get("bbox", {}).get("width", 0)
            for s in shapes
        ]
        right_variance = max(x_rights) - min(x_rights) if x_rights else 0

        if right_variance < 10:
            return "right"

        return "distributed"

    def _apply_alignment(
        self,
        shapes: list[dict],
        alignment: str,
        canvas: dict,
    ) -> None:
        """Apply alignment to shapes."""
        if not shapes:
            return

        canvas_width = canvas.get("width", 960)

        if alignment == "left":
            target_x = 50  # Left margin
            for shape in shapes:
                bbox = shape.get("bbox", {})
                bbox["x"] = target_x

        elif alignment == "center":
            center_x = canvas_width / 2
            for shape in shapes:
                bbox = shape.get("bbox", {})
                w = bbox.get("width", 100)
                bbox["x"] = center_x - w / 2

        elif alignment == "right":
            target_right = canvas_width - 50  # Right margin
            for shape in shapes:
                bbox = shape.get("bbox", {})
                w = bbox.get("width", 100)
                bbox["x"] = target_right - w

        elif alignment == "distributed":
            n = len(shapes)
            if n < 2:
                return

            # Calculate available width
            total_shape_width = sum(
                s.get("bbox", {}).get("width", 100) for s in shapes
            )
            available_width = canvas_width - 100  # Margins
            gap = (available_width - total_shape_width) / (n - 1) if n > 1 else 0

            x = 50
            for shape in shapes:
                bbox = shape.get("bbox", {})
                w = bbox.get("width", 100)
                bbox["x"] = x
                x += w + gap
