"""Component detector for recognizing patterns in DSL scenes."""

import math
from dataclasses import dataclass
from typing import Any

from backend.dsl.schema import Shape, SlideScene


@dataclass
class DetectedComponent:
    """A detected component pattern in a scene."""

    component_type: str
    confidence: float  # 0.0 - 1.0
    shapes: list[Shape]
    params: dict[str, Any]
    bbox: dict[str, int]  # x, y, width, height


@dataclass
class DetectionResult:
    """Result of component detection on a scene."""

    archetype: str | None
    components: list[DetectedComponent]
    unmatched_shapes: list[Shape]
    confidence: float


class ComponentDetector:
    """Detects component patterns in DSL scenes.

    Uses heuristics and pattern matching to identify reusable
    components within a slide scene.
    """

    # Minimum confidence threshold for detection
    MIN_CONFIDENCE = 0.6

    # Shape type patterns for each component
    FUNNEL_SHAPES = {"trapezoid", "rectangle", "roundRect", "pentagon"}
    TIMELINE_SHAPES = {"ellipse", "circle", "diamond", "rectangle", "roundRect"}
    PYRAMID_SHAPES = {"trapezoid", "triangle", "isosceles_triangle"}
    PROCESS_SHAPES = {"rectangle", "roundRect", "chevron", "pentagon", "hexagon"}
    CYCLE_SHAPES = {"ellipse", "circle", "roundRect", "hexagon"}

    def detect(self, scene: SlideScene) -> DetectionResult:
        """Detect components in a scene.

        Args:
            scene: The SlideScene to analyze.

        Returns:
            DetectionResult with detected components.
        """
        shapes = list(scene.shapes)

        # First, try to detect the overall archetype
        archetype = self._detect_archetype(shapes)

        # Then detect individual components based on archetype
        components: list[DetectedComponent] = []
        matched_shape_ids: set[str] = set()

        if archetype == "funnel":
            funnel_components = self._detect_funnel_layers(shapes)
            components.extend(funnel_components)
            for comp in funnel_components:
                matched_shape_ids.update(s.id for s in comp.shapes)

        elif archetype == "pyramid":
            pyramid_components = self._detect_pyramid_tiers(shapes)
            components.extend(pyramid_components)
            for comp in pyramid_components:
                matched_shape_ids.update(s.id for s in comp.shapes)

        elif archetype == "timeline":
            timeline_components = self._detect_timeline_nodes(shapes)
            components.extend(timeline_components)
            for comp in timeline_components:
                matched_shape_ids.update(s.id for s in comp.shapes)

        elif archetype == "process":
            process_components = self._detect_process_steps(shapes)
            components.extend(process_components)
            for comp in process_components:
                matched_shape_ids.update(s.id for s in comp.shapes)

        elif archetype == "cycle":
            cycle_components = self._detect_cycle_nodes(shapes)
            components.extend(cycle_components)
            for comp in cycle_components:
                matched_shape_ids.update(s.id for s in comp.shapes)

        elif archetype == "hub_spoke":
            hub_spoke_components = self._detect_hub_spoke(shapes)
            components.extend(hub_spoke_components)
            for comp in hub_spoke_components:
                matched_shape_ids.update(s.id for s in comp.shapes)

        # Collect unmatched shapes
        unmatched = [s for s in shapes if s.id not in matched_shape_ids]

        # Calculate overall confidence
        if shapes:
            matched_ratio = len(matched_shape_ids) / len(shapes)
            avg_confidence = (
                sum(c.confidence for c in components) / len(components)
                if components
                else 0.0
            )
            overall_confidence = matched_ratio * 0.5 + avg_confidence * 0.5
        else:
            overall_confidence = 0.0

        return DetectionResult(
            archetype=archetype,
            components=components,
            unmatched_shapes=unmatched,
            confidence=overall_confidence,
        )

    def _detect_archetype(self, shapes: list[Shape]) -> str | None:
        """Detect the overall archetype of the slide.

        Args:
            shapes: List of shapes to analyze.

        Returns:
            Archetype name or None.
        """
        if len(shapes) < 2:
            return None

        # Analyze shape arrangement patterns
        sorted_by_y = sorted(shapes, key=lambda s: s.bbox.y)
        sorted_by_x = sorted(shapes, key=lambda s: s.bbox.x)

        # Check for vertical stacking (funnel, pyramid)
        if self._is_vertically_stacked(sorted_by_y):
            widths = [s.bbox.width for s in sorted_by_y]
            if self._widths_decreasing(widths):
                return "funnel"
            elif self._widths_increasing(widths):
                return "pyramid"

        # Check for horizontal arrangement (timeline, process)
        if self._is_horizontally_arranged(sorted_by_x):
            shape_types = {s.auto_shape_type or "rect" for s in shapes}
            if shape_types & self.TIMELINE_SHAPES:
                return "timeline"
            elif shape_types & self.PROCESS_SHAPES:
                return "process"

        # Check for circular arrangement (cycle)
        if self._is_circular_arrangement(shapes):
            return "cycle"

        # Check for hub and spoke pattern
        if self._is_hub_spoke_pattern(shapes):
            return "hub_spoke"

        return None

    def _detect_funnel_layers(self, shapes: list[Shape]) -> list[DetectedComponent]:
        """Detect funnel layer components."""
        components = []
        sorted_shapes = sorted(shapes, key=lambda s: s.bbox.y)

        # Filter to shapes that look like funnel layers
        funnel_shapes = [
            s
            for s in sorted_shapes
            if (s.auto_shape_type or "").lower() in self.FUNNEL_SHAPES
            or s.type == "autoShape"
        ]

        if len(funnel_shapes) < 2:
            return components

        total_layers = len(funnel_shapes)

        for i, shape in enumerate(funnel_shapes):
            # Extract color from fill
            color = "#0D9488"
            if hasattr(shape.fill, "color"):
                color = shape.fill.color

            params = {
                "layer_index": i,
                "total_layers": total_layers,
                "color": {"color_token": "accent1", "color_override": color},
                "text": {"title": shape.text.runs[0].text if shape.text and shape.text.runs else ""},
            }

            bbox = {
                "x": shape.bbox.x,
                "y": shape.bbox.y,
                "width": shape.bbox.width,
                "height": shape.bbox.height,
            }

            components.append(
                DetectedComponent(
                    component_type="funnel_layer",
                    confidence=0.8,
                    shapes=[shape],
                    params=params,
                    bbox=bbox,
                )
            )

        return components

    def _detect_pyramid_tiers(self, shapes: list[Shape]) -> list[DetectedComponent]:
        """Detect pyramid tier components."""
        components = []
        sorted_shapes = sorted(shapes, key=lambda s: s.bbox.y)

        pyramid_shapes = [
            s
            for s in sorted_shapes
            if (s.auto_shape_type or "").lower() in self.PYRAMID_SHAPES
            or s.type == "autoShape"
        ]

        if len(pyramid_shapes) < 2:
            return components

        total_tiers = len(pyramid_shapes)

        for i, shape in enumerate(pyramid_shapes):
            color = "#0D9488"
            if hasattr(shape.fill, "color"):
                color = shape.fill.color

            params = {
                "tier_index": i,
                "total_tiers": total_tiers,
                "color": {"color_token": "accent1", "color_override": color},
                "text": {"title": shape.text.runs[0].text if shape.text and shape.text.runs else ""},
            }

            bbox = {
                "x": shape.bbox.x,
                "y": shape.bbox.y,
                "width": shape.bbox.width,
                "height": shape.bbox.height,
            }

            components.append(
                DetectedComponent(
                    component_type="pyramid_tier",
                    confidence=0.8,
                    shapes=[shape],
                    params=params,
                    bbox=bbox,
                )
            )

        return components

    def _detect_timeline_nodes(self, shapes: list[Shape]) -> list[DetectedComponent]:
        """Detect timeline node components."""
        components = []
        sorted_shapes = sorted(shapes, key=lambda s: s.bbox.x)

        timeline_shapes = [
            s
            for s in sorted_shapes
            if (s.auto_shape_type or "").lower() in self.TIMELINE_SHAPES
            or s.type == "autoShape"
        ]

        if len(timeline_shapes) < 2:
            return components

        total_nodes = len(timeline_shapes)

        for i, shape in enumerate(timeline_shapes):
            color = "#0D9488"
            if hasattr(shape.fill, "color"):
                color = shape.fill.color

            params = {
                "node_index": i,
                "total_nodes": total_nodes,
                "color": {"color_token": "accent1", "color_override": color},
                "text": {"title": shape.text.runs[0].text if shape.text and shape.text.runs else ""},
            }

            bbox = {
                "x": shape.bbox.x,
                "y": shape.bbox.y,
                "width": shape.bbox.width,
                "height": shape.bbox.height,
            }

            components.append(
                DetectedComponent(
                    component_type="timeline_node",
                    confidence=0.75,
                    shapes=[shape],
                    params=params,
                    bbox=bbox,
                )
            )

        return components

    def _detect_process_steps(self, shapes: list[Shape]) -> list[DetectedComponent]:
        """Detect process step components."""
        components = []
        sorted_shapes = sorted(shapes, key=lambda s: s.bbox.x)

        process_shapes = [
            s
            for s in sorted_shapes
            if (s.auto_shape_type or "").lower() in self.PROCESS_SHAPES
            or s.type == "autoShape"
        ]

        if len(process_shapes) < 2:
            return components

        total_steps = len(process_shapes)

        for i, shape in enumerate(process_shapes):
            color = "#0D9488"
            if hasattr(shape.fill, "color"):
                color = shape.fill.color

            params = {
                "step_index": i,
                "total_steps": total_steps,
                "step_number": i + 1,
                "color": {"color_token": "accent1", "color_override": color},
                "text": {"title": shape.text.runs[0].text if shape.text and shape.text.runs else ""},
            }

            bbox = {
                "x": shape.bbox.x,
                "y": shape.bbox.y,
                "width": shape.bbox.width,
                "height": shape.bbox.height,
            }

            components.append(
                DetectedComponent(
                    component_type="process_step",
                    confidence=0.75,
                    shapes=[shape],
                    params=params,
                    bbox=bbox,
                )
            )

        return components

    def _detect_cycle_nodes(self, shapes: list[Shape]) -> list[DetectedComponent]:
        """Detect cycle/wheel node components."""
        components = []

        cycle_shapes = [
            s
            for s in shapes
            if (s.auto_shape_type or "").lower() in self.CYCLE_SHAPES
            or s.type == "autoShape"
        ]

        if len(cycle_shapes) < 3:
            return components

        # Calculate center point
        center_x = sum(s.bbox.center_x for s in cycle_shapes) // len(cycle_shapes)
        center_y = sum(s.bbox.center_y for s in cycle_shapes) // len(cycle_shapes)

        # Sort by angle from center
        def angle_from_center(shape: Shape) -> float:
            dx = shape.bbox.center_x - center_x
            dy = shape.bbox.center_y - center_y
            return math.atan2(dy, dx)

        sorted_shapes = sorted(cycle_shapes, key=angle_from_center)
        total_nodes = len(sorted_shapes)

        for i, shape in enumerate(sorted_shapes):
            color = "#0D9488"
            if hasattr(shape.fill, "color"):
                color = shape.fill.color

            angle = math.degrees(angle_from_center(shape))

            params = {
                "node_index": i,
                "total_nodes": total_nodes,
                "angle": angle,
                "color": {"color_token": "accent1", "color_override": color},
                "text": {"title": shape.text.runs[0].text if shape.text and shape.text.runs else ""},
            }

            bbox = {
                "x": shape.bbox.x,
                "y": shape.bbox.y,
                "width": shape.bbox.width,
                "height": shape.bbox.height,
            }

            components.append(
                DetectedComponent(
                    component_type="cycle_node",
                    confidence=0.7,
                    shapes=[shape],
                    params=params,
                    bbox=bbox,
                )
            )

        return components

    def _detect_hub_spoke(self, shapes: list[Shape]) -> list[DetectedComponent]:
        """Detect hub and spoke components."""
        components = []

        if len(shapes) < 3:
            return components

        # Find the center shape (likely largest or most central)
        center_x = sum(s.bbox.center_x for s in shapes) // len(shapes)
        center_y = sum(s.bbox.center_y for s in shapes) // len(shapes)

        # Find shape closest to center
        def dist_to_center(shape: Shape) -> float:
            dx = shape.bbox.center_x - center_x
            dy = shape.bbox.center_y - center_y
            return math.sqrt(dx * dx + dy * dy)

        sorted_by_dist = sorted(shapes, key=dist_to_center)
        hub_shape = sorted_by_dist[0]
        spoke_shapes = sorted_by_dist[1:]

        # Add hub component
        hub_color = "#0D9488"
        if hasattr(hub_shape.fill, "color"):
            hub_color = hub_shape.fill.color

        components.append(
            DetectedComponent(
                component_type="hub_spoke_node",
                confidence=0.75,
                shapes=[hub_shape],
                params={
                    "is_hub": True,
                    "spoke_index": 0,
                    "total_spokes": len(spoke_shapes),
                    "color": {"color_token": "accent1", "color_override": hub_color},
                    "text": {"title": hub_shape.text.runs[0].text if hub_shape.text and hub_shape.text.runs else ""},
                },
                bbox={
                    "x": hub_shape.bbox.x,
                    "y": hub_shape.bbox.y,
                    "width": hub_shape.bbox.width,
                    "height": hub_shape.bbox.height,
                },
            )
        )

        # Add spoke components
        for i, shape in enumerate(spoke_shapes):
            color = "#0D9488"
            if hasattr(shape.fill, "color"):
                color = shape.fill.color

            dx = shape.bbox.center_x - hub_shape.bbox.center_x
            dy = shape.bbox.center_y - hub_shape.bbox.center_y
            angle = math.degrees(math.atan2(dy, dx))

            components.append(
                DetectedComponent(
                    component_type="hub_spoke_node",
                    confidence=0.7,
                    shapes=[shape],
                    params={
                        "is_hub": False,
                        "spoke_index": i + 1,
                        "total_spokes": len(spoke_shapes),
                        "angle": angle,
                        "color": {"color_token": "accent2", "color_override": color},
                        "text": {"title": shape.text.runs[0].text if shape.text and shape.text.runs else ""},
                    },
                    bbox={
                        "x": shape.bbox.x,
                        "y": shape.bbox.y,
                        "width": shape.bbox.width,
                        "height": shape.bbox.height,
                    },
                )
            )

        return components

    # ========================================================================
    # Helper methods for pattern detection
    # ========================================================================

    def _is_vertically_stacked(self, shapes: list[Shape]) -> bool:
        """Check if shapes are vertically stacked."""
        if len(shapes) < 2:
            return False

        # Check if y positions are strictly increasing (not just equal)
        y_positions = [s.bbox.y for s in shapes]

        # Need at least some actual vertical separation
        y_range = max(y_positions) - min(y_positions)
        avg_height = sum(s.bbox.height for s in shapes) / len(shapes)

        # Shapes must have meaningful vertical spread
        if y_range < avg_height * 0.5:
            return False

        return all(y_positions[i] < y_positions[i + 1] for i in range(len(y_positions) - 1))

    def _is_horizontally_arranged(self, shapes: list[Shape]) -> bool:
        """Check if shapes are horizontally arranged."""
        if len(shapes) < 2:
            return False

        # Check similar y positions
        y_centers = [s.bbox.center_y for s in shapes]
        y_variance = max(y_centers) - min(y_centers)
        avg_height = sum(s.bbox.height for s in shapes) / len(shapes)

        # Allow some tolerance for y variation
        return y_variance < avg_height * 0.5

    def _is_circular_arrangement(self, shapes: list[Shape]) -> bool:
        """Check if shapes are arranged in a circle."""
        if len(shapes) < 3:
            return False

        # Calculate center point
        center_x = sum(s.bbox.center_x for s in shapes) / len(shapes)
        center_y = sum(s.bbox.center_y for s in shapes) / len(shapes)

        # Calculate distances from center
        distances = []
        for s in shapes:
            dx = s.bbox.center_x - center_x
            dy = s.bbox.center_y - center_y
            distances.append(math.sqrt(dx * dx + dy * dy))

        # Check if distances are similar (circular pattern)
        if distances:
            avg_dist = sum(distances) / len(distances)
            variance = sum((d - avg_dist) ** 2 for d in distances) / len(distances)
            std_dev = math.sqrt(variance)

            # Low standard deviation relative to average = circular
            return std_dev / avg_dist < 0.3 if avg_dist > 0 else False

        return False

    def _is_hub_spoke_pattern(self, shapes: list[Shape]) -> bool:
        """Check if shapes follow a hub and spoke pattern."""
        if len(shapes) < 3:
            return False

        # Calculate center
        center_x = sum(s.bbox.center_x for s in shapes) / len(shapes)
        center_y = sum(s.bbox.center_y for s in shapes) / len(shapes)

        # Find shape closest to center
        distances = []
        for s in shapes:
            dx = s.bbox.center_x - center_x
            dy = s.bbox.center_y - center_y
            distances.append(math.sqrt(dx * dx + dy * dy))

        min_dist = min(distances)
        other_distances = [d for d in distances if d > min_dist * 1.5]

        # Hub should be significantly closer to center than spokes
        if len(other_distances) < 2:
            return False

        # Check if spokes are at similar distances
        avg_spoke_dist = sum(other_distances) / len(other_distances)
        spoke_variance = sum((d - avg_spoke_dist) ** 2 for d in other_distances)

        return spoke_variance / (avg_spoke_dist ** 2) < 0.2 if avg_spoke_dist > 0 else False

    def _widths_decreasing(self, widths: list[int]) -> bool:
        """Check if widths are strictly decreasing (funnel shape)."""
        if len(widths) < 2:
            return False
        # Must have actual width variation, not just equal widths
        if max(widths) == min(widths):
            return False
        return all(widths[i] >= widths[i + 1] for i in range(len(widths) - 1))

    def _widths_increasing(self, widths: list[int]) -> bool:
        """Check if widths are strictly increasing (pyramid shape)."""
        if len(widths) < 2:
            return False
        # Must have actual width variation, not just equal widths
        if max(widths) == min(widths):
            return False
        return all(widths[i] <= widths[i + 1] for i in range(len(widths) - 1))
