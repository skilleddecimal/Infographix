"""
freeform_strategy.py — Arbitrary positioning layout strategy.

Used for: Canvas, Custom layouts, LLM-positioned diagrams
Pattern: Elements positioned at specific coordinates (from metadata or learning).
"""

from typing import List, Dict, Any, Optional

from .base_strategy import (
    BaseLayoutStrategy,
    StrategyResult,
    ElementPosition,
    ConnectorPosition,
    ContentBounds,
)
from ..archetype_rules import ArchetypeRules, ConnectorPattern
from ..data_models import DiagramInput, BlockData, ConnectorData, ColorPalette


class FreeformStrategy(BaseLayoutStrategy):
    """
    Freeform layout strategy for arbitrary positioning.

    Key features:
    - Elements positioned by explicit coordinates in metadata
    - Fallback to intelligent auto-placement if no coordinates
    - Support for any shape type
    - Full connector flexibility
    """

    def compute(
        self,
        input_data: DiagramInput,
        rules: ArchetypeRules,
        bounds: ContentBounds,
        palette: ColorPalette,
    ) -> StrategyResult:
        """Compute positions for freeform layout."""
        blocks = input_data.blocks
        if not blocks:
            return StrategyResult(warnings=["No blocks to layout"])

        template = rules.element_template

        # Check if blocks have explicit positions
        has_explicit_positions = all(
            'x' in block.metadata and 'y' in block.metadata
            for block in blocks
        )

        if has_explicit_positions:
            elements = self._compute_explicit_positions(
                blocks=blocks,
                bounds=bounds,
                template=template,
                palette=palette,
            )
        else:
            # Fallback: use smart auto-placement
            elements = self._compute_auto_positions(
                blocks=blocks,
                bounds=bounds,
                template=template,
                palette=palette,
            )

        # Generate connectors from explicit connector data
        connectors = self._compute_connectors(
            input_data.connectors,
            elements,
            palette,
        )

        result = StrategyResult(
            elements=elements,
            connectors=connectors,
            used_bounds=bounds,
        )

        # Apply constraints
        if rules.constraints:
            result = self.apply_constraints(result, rules.constraints, bounds)

        return result

    def _compute_explicit_positions(
        self,
        blocks: List[BlockData],
        bounds: ContentBounds,
        template,
        palette: ColorPalette,
    ) -> List[ElementPosition]:
        """Use explicit positions from block metadata."""
        elements = []
        num_elements = len(blocks)

        for i, block in enumerate(blocks):
            meta = block.metadata

            # Get explicit position and size
            x = float(meta.get('x', bounds.left))
            y = float(meta.get('y', bounds.top))
            width = float(meta.get('width', 2.0))
            height = float(meta.get('height', 1.0))

            # Optional: positions might be relative (0-1 range)
            if meta.get('relative_position', False):
                x = bounds.left + x * bounds.width
                y = bounds.top + y * bounds.height
                width = width * bounds.width
                height = height * bounds.height

            # Get optional styling overrides
            shape_type = meta.get('shape', template.element_type.value)
            corner_radius = float(meta.get('corner_radius', template.corner_radius))
            z_order = int(meta.get('z_order', 10))

            # Custom path for complex shapes
            custom_path = meta.get('custom_path')
            arrow_direction = meta.get('arrow_direction')

            fill_color = block.color or self.compute_element_color(
                block, template, i, num_elements, palette
            )
            stroke_color = meta.get('stroke_color', template.stroke_color)

            elements.append(ElementPosition(
                element_id=block.id,
                block_data=block,
                x=x,
                y=y,
                width=width,
                height=height,
                fill_color=fill_color,
                stroke_color=stroke_color,
                shape_type=shape_type,
                corner_radius=corner_radius,
                z_order=z_order,
                custom_path=custom_path,
                arrow_direction=arrow_direction,
            ))

        return elements

    def _compute_auto_positions(
        self,
        blocks: List[BlockData],
        bounds: ContentBounds,
        template,
        palette: ColorPalette,
    ) -> List[ElementPosition]:
        """
        Automatically position elements when no explicit coordinates given.

        Uses a force-directed-like placement that:
        1. Spaces elements evenly
        2. Groups by layer if layers are defined
        3. Avoids overlaps
        """
        elements = []
        num_elements = len(blocks)

        if num_elements == 0:
            return elements

        # Simple grid-based auto-placement
        import math
        cols = math.ceil(math.sqrt(num_elements))
        rows = math.ceil(num_elements / cols)

        gutter_h = 0.4
        gutter_v = 0.3

        total_gutter_h = gutter_h * (cols - 1)
        total_gutter_v = gutter_v * (rows - 1)

        available_width = bounds.width - total_gutter_h
        available_height = bounds.height - total_gutter_v

        element_width = available_width / cols
        element_height = available_height / rows

        # Constrain sizes
        element_width = max(1.5, min(3.0, element_width))
        element_height = max(0.8, min(1.5, element_height))

        # Center the grid
        actual_width = cols * element_width + total_gutter_h
        actual_height = rows * element_height + total_gutter_v
        start_x = bounds.left + (bounds.width - actual_width) / 2
        start_y = bounds.top + (bounds.height - actual_height) / 2

        for i, block in enumerate(blocks):
            row = i // cols
            col = i % cols

            x = start_x + col * (element_width + gutter_h)
            y = start_y + row * (element_height + gutter_v)

            fill_color = block.color or self.compute_element_color(
                block, template, i, num_elements, palette
            )

            # Get optional styling from metadata
            meta = block.metadata
            shape_type = meta.get('shape', template.element_type.value)

            elements.append(ElementPosition(
                element_id=block.id,
                block_data=block,
                x=x,
                y=y,
                width=element_width,
                height=element_height,
                fill_color=fill_color,
                stroke_color=template.stroke_color,
                shape_type=shape_type,
                corner_radius=template.corner_radius,
                z_order=10,
            ))

        return elements

    def _compute_connectors(
        self,
        connector_data: List[ConnectorData],
        elements: List[ElementPosition],
        palette: ColorPalette,
    ) -> List[ConnectorPosition]:
        """Generate connectors from explicit connector definitions."""
        connectors = []

        # Build element lookup
        element_dict = {e.element_id: e for e in elements}

        for i, conn in enumerate(connector_data):
            from_elem = element_dict.get(conn.from_id)
            to_elem = element_dict.get(conn.to_id)

            if not from_elem or not to_elem:
                continue

            # Calculate connection points
            start_x, start_y, end_x, end_y = self._compute_connector_endpoints(
                from_elem, to_elem
            )

            connectors.append(ConnectorPosition(
                connector_id=f"conn_{i}",
                from_element_id=conn.from_id,
                to_element_id=conn.to_id,
                start_x=start_x,
                start_y=start_y,
                end_x=end_x,
                end_y=end_y,
                style=conn.style.value,
                color=conn.color or palette.connector,
                label=conn.label,
            ))

        return connectors

    def _compute_connector_endpoints(
        self,
        from_elem: ElementPosition,
        to_elem: ElementPosition,
    ) -> tuple:
        """Compute optimal connector endpoints between two elements."""
        # Get centers
        from_cx, from_cy = from_elem.center_x, from_elem.center_y
        to_cx, to_cy = to_elem.center_x, to_elem.center_y

        # Direction vector
        dx = to_cx - from_cx
        dy = to_cy - from_cy

        # Find intersection with element edges
        start_x, start_y = self._intersect_rect_edge(
            from_cx, from_cy, dx, dy,
            from_elem.x, from_elem.y,
            from_elem.width, from_elem.height
        )

        end_x, end_y = self._intersect_rect_edge(
            to_cx, to_cy, -dx, -dy,
            to_elem.x, to_elem.y,
            to_elem.width, to_elem.height
        )

        return (start_x, start_y, end_x, end_y)

    def _intersect_rect_edge(
        self,
        cx: float, cy: float,
        dx: float, dy: float,
        rect_x: float, rect_y: float,
        rect_w: float, rect_h: float
    ) -> tuple:
        """Find intersection of ray from center with rectangle edge."""
        if dx == 0 and dy == 0:
            return (cx, cy)

        left = rect_x
        right = rect_x + rect_w
        top = rect_y
        bottom = rect_y + rect_h

        intersections = []

        if dx != 0:
            # Right edge
            t = (right - cx) / dx
            if t > 0:
                y = cy + t * dy
                if top <= y <= bottom:
                    intersections.append((t, right, y))

            # Left edge
            t = (left - cx) / dx
            if t > 0:
                y = cy + t * dy
                if top <= y <= bottom:
                    intersections.append((t, left, y))

        if dy != 0:
            # Bottom edge
            t = (bottom - cy) / dy
            if t > 0:
                x = cx + t * dx
                if left <= x <= right:
                    intersections.append((t, x, bottom))

            # Top edge
            t = (top - cy) / dy
            if t > 0:
                x = cx + t * dx
                if left <= x <= right:
                    intersections.append((t, x, top))

        if intersections:
            intersections.sort(key=lambda p: p[0])
            return (intersections[0][1], intersections[0][2])

        return (cx, cy)
