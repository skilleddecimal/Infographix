"""
flow_strategy.py — Sequential flow layout strategy.

Used for: Process Flow, Pipeline, Chevron Process
Pattern: Elements arranged in sequence with connecting arrows.
"""

from typing import List, Dict, Any, Optional

from .base_strategy import (
    BaseLayoutStrategy,
    StrategyResult,
    ElementPosition,
    ConnectorPosition,
    ContentBounds,
)
from ..archetype_rules import ArchetypeRules, LayoutDirection, ConnectorPattern
from ..data_models import DiagramInput, ColorPalette


class FlowStrategy(BaseLayoutStrategy):
    """
    Flow layout strategy for sequential processes.

    Key features:
    - Linear sequence of elements
    - Automatic wrapping when too many elements
    - Various connector styles (arrows, chevrons)
    - Support for branching (decision trees)
    """

    def compute(
        self,
        input_data: DiagramInput,
        rules: ArchetypeRules,
        bounds: ContentBounds,
        palette: ColorPalette,
    ) -> StrategyResult:
        """Compute positions for flow layout."""
        blocks = input_data.blocks
        if not blocks:
            return StrategyResult(warnings=["No blocks to layout"])

        template = rules.element_template
        flow_params = rules.flow_params
        direction = rules.primary_direction

        # Get configuration
        wrap_after = flow_params.get('wrap_after', 6)
        connector_gap = flow_params.get('connector_gap', 0.1)

        num_elements = len(blocks)

        if direction == LayoutDirection.HORIZONTAL:
            elements = self._compute_horizontal_flow(
                blocks=blocks,
                bounds=bounds,
                template=template,
                palette=palette,
                wrap_after=wrap_after,
            )
        else:
            elements = self._compute_vertical_flow(
                blocks=blocks,
                bounds=bounds,
                template=template,
                palette=palette,
                wrap_after=wrap_after,
            )

        # Generate connectors
        connectors = []
        if rules.connector_template.pattern == ConnectorPattern.SEQUENTIAL:
            connectors = self._create_flow_connectors(
                elements=elements,
                connector_template=rules.connector_template,
                palette=palette,
                connector_gap=connector_gap,
                direction=direction,
                wrap_after=wrap_after,
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

    def _compute_horizontal_flow(
        self,
        blocks: List,
        bounds: ContentBounds,
        template,
        palette: ColorPalette,
        wrap_after: int,
    ) -> List[ElementPosition]:
        """Compute positions for horizontal flow."""
        elements = []
        num_elements = len(blocks)

        # Determine if wrapping is needed
        elements_per_row = min(wrap_after, num_elements)
        num_rows = (num_elements + elements_per_row - 1) // elements_per_row

        # Calculate element sizes
        gutter_h = 0.3
        gutter_v = 0.4

        total_gutter_h = gutter_h * (elements_per_row - 1)
        available_width = bounds.width - total_gutter_h

        element_width = available_width / elements_per_row
        element_width = max(1.2, min(2.5, element_width))

        element_height = 0.9

        # Recalculate actual row width
        row_width = elements_per_row * element_width + total_gutter_h

        # Total height for all rows
        total_height = num_rows * element_height + (num_rows - 1) * gutter_v
        start_y = bounds.top + (bounds.height - total_height) / 2

        for i, block in enumerate(blocks):
            row = i // elements_per_row
            col = i % elements_per_row

            # Alternate row direction for wrapped flows (snake pattern)
            if row % 2 == 1:
                col = elements_per_row - 1 - col

            # Adjust for actual elements in this row
            elements_in_this_row = min(elements_per_row, num_elements - row * elements_per_row)
            actual_row_width = elements_in_this_row * element_width + (elements_in_this_row - 1) * gutter_h

            start_x = bounds.left + (bounds.width - actual_row_width) / 2

            x = start_x + col * (element_width + gutter_h)
            y = start_y + row * (element_height + gutter_v)

            fill_color = self.compute_element_color(
                block, template, i, num_elements, palette
            )

            elements.append(ElementPosition(
                element_id=block.id,
                block_data=block,
                x=x,
                y=y,
                width=element_width,
                height=element_height,
                fill_color=fill_color,
                stroke_color=template.stroke_color,
                shape_type=template.element_type.value,
                corner_radius=template.corner_radius,
                z_order=10,
            ))

        return elements

    def _compute_vertical_flow(
        self,
        blocks: List,
        bounds: ContentBounds,
        template,
        palette: ColorPalette,
        wrap_after: int,
    ) -> List[ElementPosition]:
        """Compute positions for vertical flow."""
        elements = []
        num_elements = len(blocks)

        # Determine if wrapping is needed
        elements_per_col = min(wrap_after, num_elements)
        num_cols = (num_elements + elements_per_col - 1) // elements_per_col

        # Calculate element sizes
        gutter_h = 0.4
        gutter_v = 0.3

        total_gutter_v = gutter_v * (elements_per_col - 1)
        available_height = bounds.height - total_gutter_v

        element_height = available_height / elements_per_col
        element_height = max(0.7, min(1.2, element_height))

        element_width = 2.0

        # Total width for all columns
        total_width = num_cols * element_width + (num_cols - 1) * gutter_h
        start_x = bounds.left + (bounds.width - total_width) / 2

        for i, block in enumerate(blocks):
            col = i // elements_per_col
            row = i % elements_per_col

            # Adjust for actual elements in this column
            elements_in_this_col = min(elements_per_col, num_elements - col * elements_per_col)
            actual_col_height = elements_in_this_col * element_height + (elements_in_this_col - 1) * gutter_v

            start_y = bounds.top + (bounds.height - actual_col_height) / 2

            x = start_x + col * (element_width + gutter_h)
            y = start_y + row * (element_height + gutter_v)

            fill_color = self.compute_element_color(
                block, template, i, num_elements, palette
            )

            elements.append(ElementPosition(
                element_id=block.id,
                block_data=block,
                x=x,
                y=y,
                width=element_width,
                height=element_height,
                fill_color=fill_color,
                stroke_color=template.stroke_color,
                shape_type=template.element_type.value,
                corner_radius=template.corner_radius,
                z_order=10,
            ))

        return elements

    def _create_flow_connectors(
        self,
        elements: List[ElementPosition],
        connector_template,
        palette: ColorPalette,
        connector_gap: float,
        direction: LayoutDirection,
        wrap_after: int,
    ) -> List[ConnectorPosition]:
        """Create connectors for flow layout."""
        connectors = []

        for i in range(len(elements) - 1):
            e1 = elements[i]
            e2 = elements[i + 1]

            # Detect if this is a wrap (going to next row/column)
            is_wrap = False
            if direction == LayoutDirection.HORIZONTAL:
                # Wrap detected if y changes significantly
                is_wrap = abs(e2.y - e1.y) > 0.1
            else:
                # Wrap detected if x changes significantly
                is_wrap = abs(e2.x - e1.x) > 0.1

            if is_wrap:
                # Create orthogonal connector for wrapping
                conn = self._create_wrap_connector(
                    e1, e2, i, connector_template, palette, direction
                )
            else:
                # Create direct connector
                conn = self._create_direct_connector(
                    e1, e2, i, connector_template, palette, connector_gap, direction
                )

            connectors.append(conn)

        return connectors

    def _create_direct_connector(
        self,
        e1: ElementPosition,
        e2: ElementPosition,
        index: int,
        connector_template,
        palette: ColorPalette,
        gap: float,
        direction: LayoutDirection,
    ) -> ConnectorPosition:
        """Create a direct connector between adjacent elements."""
        if direction == LayoutDirection.HORIZONTAL:
            if e2.x > e1.x:
                start_x = e1.right_edge + gap
                end_x = e2.x - gap
            else:
                start_x = e1.x - gap
                end_x = e2.right_edge + gap
            start_y = e1.center_y
            end_y = e2.center_y
        else:
            if e2.y > e1.y:
                start_y = e1.bottom_edge + gap
                end_y = e2.y - gap
            else:
                start_y = e1.y - gap
                end_y = e2.bottom_edge + gap
            start_x = e1.center_x
            end_x = e2.center_x

        return ConnectorPosition(
            connector_id=f"conn_flow_{index}",
            from_element_id=e1.element_id,
            to_element_id=e2.element_id,
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            style=connector_template.style,
            color=connector_template.color or palette.connector,
            stroke_width=connector_template.stroke_width,
            routing=connector_template.routing,
        )

    def _create_wrap_connector(
        self,
        e1: ElementPosition,
        e2: ElementPosition,
        index: int,
        connector_template,
        palette: ColorPalette,
        direction: LayoutDirection,
    ) -> ConnectorPosition:
        """Create an orthogonal connector for wrapping between rows/columns."""
        waypoints = []

        if direction == LayoutDirection.HORIZONTAL:
            # Going from end of one row to start of next
            # e1 is at right end, e2 is at left end of next row
            start_x = e1.center_x
            start_y = e1.bottom_edge

            end_x = e2.center_x
            end_y = e2.y

            # Add waypoints for L-shaped or U-shaped path
            mid_y = (e1.bottom_edge + e2.y) / 2
            waypoints = [
                (start_x, mid_y),
                (end_x, mid_y),
            ]
        else:
            # Vertical flow wrapping
            start_x = e1.right_edge
            start_y = e1.center_y

            end_x = e2.x
            end_y = e2.center_y

            mid_x = (e1.right_edge + e2.x) / 2
            waypoints = [
                (mid_x, start_y),
                (mid_x, end_y),
            ]

        return ConnectorPosition(
            connector_id=f"conn_wrap_{index}",
            from_element_id=e1.element_id,
            to_element_id=e2.element_id,
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            style=connector_template.style,
            color=connector_template.color or palette.connector,
            stroke_width=connector_template.stroke_width,
            routing='orthogonal',
            waypoints=waypoints,
        )
