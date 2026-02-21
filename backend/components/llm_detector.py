"""LLM-enhanced component detector with multi-pattern support."""

import json
import math
from dataclasses import dataclass, field
from typing import Any

from backend.api.config import get_settings
from backend.dsl.schema import Shape, SlideScene


@dataclass
class ShapeCluster:
    """A cluster of related shapes that may form a pattern."""

    shapes: list[Shape]
    bounds: dict[str, int]  # x, y, width, height
    centroid: tuple[int, int]

    @property
    def shape_ids(self) -> set[str]:
        return {s.id for s in self.shapes}


@dataclass
class PatternGroup:
    """A detected pattern within a region of the slide."""

    archetype: str
    confidence: float
    cluster: ShapeCluster
    components: list[dict[str, Any]]
    reasoning: str = ""


@dataclass
class MultiPatternResult:
    """Result of multi-pattern detection on a scene."""

    patterns: list[PatternGroup]
    unmatched_shapes: list[Shape]
    llm_analysis: str = ""

    @property
    def primary_archetype(self) -> str | None:
        """Get the highest-confidence archetype."""
        if not self.patterns:
            return None
        return max(self.patterns, key=lambda p: p.confidence).archetype

    @property
    def archetypes(self) -> list[str]:
        """Get all detected archetypes."""
        return [p.archetype for p in self.patterns]


class ShapeClusterer:
    """Groups shapes into spatial clusters using proximity analysis."""

    def __init__(self, distance_threshold_ratio: float = 0.15):
        """Initialize clusterer.

        Args:
            distance_threshold_ratio: Max distance between shapes as ratio of canvas diagonal.
        """
        self.distance_threshold_ratio = distance_threshold_ratio

    def cluster(
        self,
        shapes: list[Shape],
        canvas_width: int,
        canvas_height: int,
    ) -> list[ShapeCluster]:
        """Cluster shapes by spatial proximity.

        Args:
            shapes: List of shapes to cluster.
            canvas_width: Canvas width for threshold calculation.
            canvas_height: Canvas height for threshold calculation.

        Returns:
            List of shape clusters.
        """
        if not shapes:
            return []

        # Calculate distance threshold based on canvas size
        canvas_diagonal = math.sqrt(canvas_width**2 + canvas_height**2)
        threshold = canvas_diagonal * self.distance_threshold_ratio

        # Initialize each shape as its own cluster
        clusters: list[set[int]] = [{i} for i in range(len(shapes))]
        shape_to_cluster: dict[int, int] = {i: i for i in range(len(shapes))}

        # Merge clusters based on proximity
        for i, shape1 in enumerate(shapes):
            for j, shape2 in enumerate(shapes[i + 1 :], start=i + 1):
                if self._shapes_are_close(shape1, shape2, threshold):
                    # Merge clusters
                    cluster_i = shape_to_cluster[i]
                    cluster_j = shape_to_cluster[j]

                    if cluster_i != cluster_j:
                        # Merge j's cluster into i's cluster
                        clusters[cluster_i].update(clusters[cluster_j])
                        for idx in clusters[cluster_j]:
                            shape_to_cluster[idx] = cluster_i
                        clusters[cluster_j] = set()

        # Build final clusters
        result = []
        for cluster_indices in clusters:
            if not cluster_indices:
                continue

            cluster_shapes = [shapes[i] for i in cluster_indices]
            bounds = self._calculate_bounds(cluster_shapes)
            centroid = (
                bounds["x"] + bounds["width"] // 2,
                bounds["y"] + bounds["height"] // 2,
            )

            result.append(
                ShapeCluster(
                    shapes=cluster_shapes,
                    bounds=bounds,
                    centroid=centroid,
                )
            )

        # Sort clusters by position (top-left to bottom-right)
        result.sort(key=lambda c: (c.centroid[1], c.centroid[0]))

        return result

    def _shapes_are_close(self, shape1: Shape, shape2: Shape, threshold: float) -> bool:
        """Check if two shapes are within proximity threshold."""
        # Calculate center-to-center distance
        cx1 = shape1.bbox.center_x
        cy1 = shape1.bbox.center_y
        cx2 = shape2.bbox.center_x
        cy2 = shape2.bbox.center_y

        distance = math.sqrt((cx2 - cx1) ** 2 + (cy2 - cy1) ** 2)

        # Also check edge-to-edge distance (shapes might be large)
        edge_distance = self._edge_distance(shape1, shape2)

        return min(distance, edge_distance) < threshold

    def _edge_distance(self, shape1: Shape, shape2: Shape) -> float:
        """Calculate minimum edge-to-edge distance between shapes."""
        # Horizontal distance
        if shape1.bbox.x + shape1.bbox.width < shape2.bbox.x:
            dx = shape2.bbox.x - (shape1.bbox.x + shape1.bbox.width)
        elif shape2.bbox.x + shape2.bbox.width < shape1.bbox.x:
            dx = shape1.bbox.x - (shape2.bbox.x + shape2.bbox.width)
        else:
            dx = 0  # Overlapping horizontally

        # Vertical distance
        if shape1.bbox.y + shape1.bbox.height < shape2.bbox.y:
            dy = shape2.bbox.y - (shape1.bbox.y + shape1.bbox.height)
        elif shape2.bbox.y + shape2.bbox.height < shape1.bbox.y:
            dy = shape1.bbox.y - (shape2.bbox.y + shape2.bbox.height)
        else:
            dy = 0  # Overlapping vertically

        return math.sqrt(dx**2 + dy**2)

    def _calculate_bounds(self, shapes: list[Shape]) -> dict[str, int]:
        """Calculate bounding box for a group of shapes."""
        min_x = min(s.bbox.x for s in shapes)
        min_y = min(s.bbox.y for s in shapes)
        max_x = max(s.bbox.x + s.bbox.width for s in shapes)
        max_y = max(s.bbox.y + s.bbox.height for s in shapes)

        return {
            "x": min_x,
            "y": min_y,
            "width": max_x - min_x,
            "height": max_y - min_y,
        }


class LLMPatternDetector:
    """Uses LLM reasoning to detect infographic patterns."""

    SUPPORTED_ARCHETYPES = [
        "funnel",
        "pyramid",
        "timeline",
        "process",
        "cycle",
        "hub_spoke",
        "matrix",
        "comparison",
        "flowchart",
        "org_chart",
        "venn",
        "gauge",
        "bullet_list",
        "unknown",
    ]

    def __init__(self, use_llm: bool = True):
        """Initialize detector.

        Args:
            use_llm: Whether to use LLM for detection. Falls back to heuristics if False.
        """
        self.use_llm = use_llm
        self.clusterer = ShapeClusterer()
        self._client = None

    @property
    def client(self):
        """Lazy-load Anthropic client."""
        if self._client is None:
            try:
                import anthropic

                settings = get_settings()
                if settings.anthropic_api_key:
                    self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            except ImportError:
                pass
        return self._client

    def detect(self, scene: SlideScene) -> MultiPatternResult:
        """Detect all patterns in a scene.

        Args:
            scene: The SlideScene to analyze.

        Returns:
            MultiPatternResult with all detected patterns.
        """
        shapes = list(scene.shapes)

        if not shapes:
            return MultiPatternResult(patterns=[], unmatched_shapes=[])

        # Step 1: Cluster shapes by proximity
        clusters = self.clusterer.cluster(
            shapes=shapes,
            canvas_width=scene.canvas.width,
            canvas_height=scene.canvas.height,
        )

        # Step 2: Detect pattern for each cluster
        patterns = []
        llm_analysis = ""

        if self.use_llm and self.client:
            # Use LLM for all clusters at once
            patterns, llm_analysis = self._detect_with_llm(clusters, scene)
        else:
            # Fall back to heuristic detection per cluster
            for cluster in clusters:
                pattern = self._detect_with_heuristics(cluster)
                if pattern:
                    patterns.append(pattern)

        # Collect unmatched shapes
        matched_ids = set()
        for pattern in patterns:
            matched_ids.update(pattern.cluster.shape_ids)

        unmatched = [s for s in shapes if s.id not in matched_ids]

        return MultiPatternResult(
            patterns=patterns,
            unmatched_shapes=unmatched,
            llm_analysis=llm_analysis,
        )

    def _detect_with_llm(
        self,
        clusters: list[ShapeCluster],
        scene: SlideScene,
    ) -> tuple[list[PatternGroup], str]:
        """Use LLM to detect patterns in clusters.

        Args:
            clusters: Shape clusters to analyze.
            scene: Original scene for context.

        Returns:
            Tuple of (detected patterns, LLM analysis text).
        """
        # Build description of each cluster
        cluster_descriptions = []
        for i, cluster in enumerate(clusters):
            desc = self._describe_cluster(cluster, i)
            cluster_descriptions.append(desc)

        prompt = self._build_detection_prompt(cluster_descriptions, scene)

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            analysis = response.content[0].text
            patterns = self._parse_llm_response(analysis, clusters)

            return patterns, analysis

        except Exception as e:
            # Fall back to heuristics on LLM failure
            print(f"LLM detection failed: {e}, falling back to heuristics")
            patterns = []
            for cluster in clusters:
                pattern = self._detect_with_heuristics(cluster)
                if pattern:
                    patterns.append(pattern)
            return patterns, f"LLM error: {e}"

    def _describe_cluster(self, cluster: ShapeCluster, index: int) -> dict[str, Any]:
        """Create a description of a cluster for LLM analysis."""
        shapes_desc = []
        for shape in cluster.shapes:
            text = ""
            if shape.text and shape.text.runs:
                text = " ".join(run.text for run in shape.text.runs if run.text)

            shapes_desc.append(
                {
                    "type": shape.auto_shape_type or shape.type,
                    "x": shape.bbox.x,
                    "y": shape.bbox.y,
                    "width": shape.bbox.width,
                    "height": shape.bbox.height,
                    "text": text[:100] if text else None,  # Truncate long text
                }
            )

        # Sort by position for consistent ordering
        shapes_desc.sort(key=lambda s: (s["y"], s["x"]))

        return {
            "cluster_id": index,
            "bounds": cluster.bounds,
            "shape_count": len(cluster.shapes),
            "shapes": shapes_desc,
        }

    def _build_detection_prompt(
        self,
        cluster_descriptions: list[dict[str, Any]],
        scene: SlideScene,
    ) -> str:
        """Build the prompt for LLM pattern detection."""
        archetypes_list = ", ".join(self.SUPPORTED_ARCHETYPES)

        return f"""Analyze these shape clusters from a PowerPoint slide and identify the infographic pattern each represents.

Canvas size: {scene.canvas.width} x {scene.canvas.height} EMUs (914400 EMU = 1 inch)

Clusters:
{json.dumps(cluster_descriptions, indent=2)}

For each cluster, determine:
1. The archetype (one of: {archetypes_list})
2. Confidence score (0.0-1.0)
3. Brief reasoning

Consider:
- Shape arrangement (vertical stack, horizontal row, circular, grid)
- Width/height patterns (decreasing=funnel, increasing=pyramid)
- Text content (dates suggest timeline, numbers suggest process steps)
- Shape types (circles for timeline nodes, rectangles for process steps)

Respond in JSON format:
{{
  "clusters": [
    {{
      "cluster_id": 0,
      "archetype": "funnel",
      "confidence": 0.9,
      "reasoning": "4 vertically stacked shapes with decreasing widths"
    }}
  ]
}}

Only output the JSON, no other text."""

    def _parse_llm_response(
        self,
        response: str,
        clusters: list[ShapeCluster],
    ) -> list[PatternGroup]:
        """Parse LLM response into PatternGroup objects."""
        patterns = []

        try:
            # Extract JSON from response
            response = response.strip()
            if response.startswith("```"):
                # Remove markdown code blocks
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])

            data = json.loads(response)

            for cluster_result in data.get("clusters", []):
                cluster_id = cluster_result.get("cluster_id", 0)
                if cluster_id >= len(clusters):
                    continue

                cluster = clusters[cluster_id]
                archetype = cluster_result.get("archetype", "unknown")
                confidence = float(cluster_result.get("confidence", 0.5))
                reasoning = cluster_result.get("reasoning", "")

                # Skip low-confidence or unknown patterns
                if confidence < 0.4 or archetype == "unknown":
                    continue

                patterns.append(
                    PatternGroup(
                        archetype=archetype,
                        confidence=confidence,
                        cluster=cluster,
                        components=self._extract_components(cluster, archetype),
                        reasoning=reasoning,
                    )
                )

        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response: {e}")
            # Fall back to heuristics
            for cluster in clusters:
                pattern = self._detect_with_heuristics(cluster)
                if pattern:
                    patterns.append(pattern)

        return patterns

    def _extract_components(
        self,
        cluster: ShapeCluster,
        archetype: str,
    ) -> list[dict[str, Any]]:
        """Extract component definitions from a cluster."""
        components = []
        shapes = cluster.shapes

        # Sort shapes based on archetype
        if archetype in ["funnel", "pyramid"]:
            shapes = sorted(shapes, key=lambda s: s.bbox.y)
        elif archetype in ["timeline", "process"]:
            shapes = sorted(shapes, key=lambda s: s.bbox.x)
        elif archetype == "matrix":
            shapes = sorted(shapes, key=lambda s: (s.bbox.y, s.bbox.x))

        component_type = self._archetype_to_component(archetype)

        for i, shape in enumerate(shapes):
            text = ""
            if shape.text and shape.text.runs:
                text = " ".join(run.text for run in shape.text.runs if run.text)

            components.append(
                {
                    "component_type": component_type,
                    "index": i,
                    "total": len(shapes),
                    "shape_id": shape.id,
                    "text": text,
                    "bbox": {
                        "x": shape.bbox.x,
                        "y": shape.bbox.y,
                        "width": shape.bbox.width,
                        "height": shape.bbox.height,
                    },
                }
            )

        return components

    def _archetype_to_component(self, archetype: str) -> str:
        """Map archetype to component type name."""
        mapping = {
            "funnel": "funnel_layer",
            "pyramid": "pyramid_tier",
            "timeline": "timeline_node",
            "process": "process_step",
            "cycle": "cycle_node",
            "hub_spoke": "hub_spoke_node",
            "matrix": "matrix_cell",
            "comparison": "comparison_item",
            "flowchart": "flowchart_node",
            "org_chart": "org_node",
            "venn": "venn_region",
            "gauge": "gauge_segment",
            "bullet_list": "bullet_item",
        }
        return mapping.get(archetype, "generic_shape")

    def _detect_with_heuristics(self, cluster: ShapeCluster) -> PatternGroup | None:
        """Detect pattern using geometric heuristics (fallback).

        Args:
            cluster: Shape cluster to analyze.

        Returns:
            PatternGroup or None if no pattern detected.
        """
        shapes = cluster.shapes

        if len(shapes) < 2:
            return None

        # Check arrangement patterns
        sorted_by_y = sorted(shapes, key=lambda s: s.bbox.y)
        sorted_by_x = sorted(shapes, key=lambda s: s.bbox.x)

        # Check for vertical stacking
        if self._is_vertically_stacked(sorted_by_y):
            widths = [s.bbox.width for s in sorted_by_y]
            if self._widths_decreasing(widths):
                return PatternGroup(
                    archetype="funnel",
                    confidence=0.8,
                    cluster=cluster,
                    components=self._extract_components(cluster, "funnel"),
                    reasoning="Vertically stacked shapes with decreasing widths",
                )
            elif self._widths_increasing(widths):
                return PatternGroup(
                    archetype="pyramid",
                    confidence=0.8,
                    cluster=cluster,
                    components=self._extract_components(cluster, "pyramid"),
                    reasoning="Vertically stacked shapes with increasing widths",
                )

        # Check for horizontal arrangement
        if self._is_horizontally_arranged(sorted_by_x):
            # Check for timeline indicators
            has_circles = any(
                (s.auto_shape_type or "").lower() in ["ellipse", "circle"]
                for s in shapes
            )
            if has_circles:
                return PatternGroup(
                    archetype="timeline",
                    confidence=0.75,
                    cluster=cluster,
                    components=self._extract_components(cluster, "timeline"),
                    reasoning="Horizontally arranged circular shapes",
                )
            else:
                return PatternGroup(
                    archetype="process",
                    confidence=0.7,
                    cluster=cluster,
                    components=self._extract_components(cluster, "process"),
                    reasoning="Horizontally arranged shapes",
                )

        # Check for grid/matrix FIRST (before cycle, since 2x2 grids can look circular)
        if self._is_grid_arrangement(shapes):
            return PatternGroup(
                archetype="matrix",
                confidence=0.7,
                cluster=cluster,
                components=self._extract_components(cluster, "matrix"),
                reasoning="Shapes arranged in grid pattern",
            )

        # Check for hub-spoke pattern (before cycle, as it's more specific)
        if self._is_hub_spoke_pattern(shapes):
            return PatternGroup(
                archetype="hub_spoke",
                confidence=0.7,
                cluster=cluster,
                components=self._extract_components(cluster, "hub_spoke"),
                reasoning="Central shape with radiating elements",
            )

        # Check for circular arrangement
        if self._is_circular_arrangement(shapes):
            return PatternGroup(
                archetype="cycle",
                confidence=0.7,
                cluster=cluster,
                components=self._extract_components(cluster, "cycle"),
                reasoning="Shapes arranged in circular pattern",
            )

        return None

    # Heuristic helper methods (similar to original detector)

    def _is_vertically_stacked(self, shapes: list[Shape]) -> bool:
        if len(shapes) < 2:
            return False
        y_positions = [s.bbox.y for s in shapes]
        y_range = max(y_positions) - min(y_positions)
        avg_height = sum(s.bbox.height for s in shapes) / len(shapes)
        if y_range < avg_height * 0.5:
            return False
        return all(y_positions[i] < y_positions[i + 1] for i in range(len(y_positions) - 1))

    def _is_horizontally_arranged(self, shapes: list[Shape]) -> bool:
        if len(shapes) < 2:
            return False
        y_centers = [s.bbox.center_y for s in shapes]
        y_variance = max(y_centers) - min(y_centers)
        avg_height = sum(s.bbox.height for s in shapes) / len(shapes)
        return y_variance < avg_height * 0.5

    def _is_circular_arrangement(self, shapes: list[Shape]) -> bool:
        if len(shapes) < 3:
            return False
        center_x = sum(s.bbox.center_x for s in shapes) / len(shapes)
        center_y = sum(s.bbox.center_y for s in shapes) / len(shapes)
        distances = []
        for s in shapes:
            dx = s.bbox.center_x - center_x
            dy = s.bbox.center_y - center_y
            distances.append(math.sqrt(dx * dx + dy * dy))
        if distances:
            avg_dist = sum(distances) / len(distances)
            if avg_dist == 0:
                return False
            variance = sum((d - avg_dist) ** 2 for d in distances) / len(distances)
            std_dev = math.sqrt(variance)
            return std_dev / avg_dist < 0.3
        return False

    def _is_hub_spoke_pattern(self, shapes: list[Shape]) -> bool:
        if len(shapes) < 3:
            return False
        center_x = sum(s.bbox.center_x for s in shapes) / len(shapes)
        center_y = sum(s.bbox.center_y for s in shapes) / len(shapes)
        distances = []
        for s in shapes:
            dx = s.bbox.center_x - center_x
            dy = s.bbox.center_y - center_y
            distances.append(math.sqrt(dx * dx + dy * dy))
        min_dist = min(distances)
        other_distances = [d for d in distances if d > min_dist * 1.5]
        if len(other_distances) < 2:
            return False
        avg_spoke_dist = sum(other_distances) / len(other_distances)
        if avg_spoke_dist == 0:
            return False
        spoke_variance = sum((d - avg_spoke_dist) ** 2 for d in other_distances)
        return spoke_variance / (avg_spoke_dist**2) < 0.2

    def _is_grid_arrangement(self, shapes: list[Shape]) -> bool:
        if len(shapes) < 4:
            return False
        # Check for consistent row/column alignment
        x_positions = sorted(set(s.bbox.x for s in shapes))
        y_positions = sorted(set(s.bbox.y for s in shapes))
        # Grid should have multiple rows AND columns
        return len(x_positions) >= 2 and len(y_positions) >= 2

    def _widths_decreasing(self, widths: list[int]) -> bool:
        if len(widths) < 2:
            return False
        if max(widths) == min(widths):
            return False
        return all(widths[i] >= widths[i + 1] for i in range(len(widths) - 1))

    def _widths_increasing(self, widths: list[int]) -> bool:
        if len(widths) < 2:
            return False
        if max(widths) == min(widths):
            return False
        return all(widths[i] <= widths[i + 1] for i in range(len(widths) - 1))
