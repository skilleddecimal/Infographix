"""
stack_strategy.py — Vertical/horizontal stacking layout strategy.

Used for: Funnel, Pyramid, Timeline, Stacked List
Pattern: Elements arranged in a stack, potentially with progressive sizing.
"""

from typing import List, Dict, Any, Optional

from .base_strategy import (
    BaseLayoutStrategy,
    StrategyResult,
    ElementPosition,
    ConnectorPosition,
    ContentBounds,
)
from ..archetype_rules import (
    ArchetypeRules,
    LayoutDirection,
    SizeRule,
    ElementShape,
)
from ..data_models import DiagramInput, ColorPalette


class StackStrategy(BaseLayoutStrategy):
    """
    Stack layout strategy for vertically or horizontally stacked elements.

    Key features:
    - Elements stacked in sequence
    - Progressive sizing (each element can be larger/smaller than previous)
    - Center alignment with configurable options
    - Support for trapezoid shapes (funnel/pyramid)
    """

    def compute(
        self,
        input_data: DiagramInput,
        rules: ArchetypeRules,
        bounds: ContentBounds,
        palette: ColorPalette,
    ) -> StrategyResult:
        """Compute positions for stacked elements."""
        blocks = input_data.blocks
        if not blocks:
            return StrategyResult(warnings=["No blocks to layout"])

        template = rules.element_template
        stack_params = rules.stack_params
        direction = rules.primary_direction

        # Get configuration
        alignment = stack_params.get('alignment', 'center')
        gutter = stack_params.get('gutter', 0.1)
        top_width_ratio = stack_params.get('top_width_ratio', 0.9)
        bottom_width_ratio = stack_params.get('bottom_width_ratio', 0.25)
        direction_hint = stack_params.get('direction', 'top_wide')  # 'top_wide' or 'top_narrow'

        num_elements = len(blocks)
        elements: List[ElementPosition] = []

        if direction == LayoutDirection.VERTICAL:
            elements = self._compute_vertical_stack(
                blocks=blocks,
                bounds=bounds,
                template=template,
                palette=palette,
                alignment=alignment,
                gutter=gutter,
                top_width_ratio=top_width_ratio,
                bottom_width_ratio=bottom_width_ratio,
                direction_hint=direction_hint,
            )
        else:
            elements = self._compute_horizontal_stack(
                blocks=blocks,
                bounds=bounds,
                template=template,
                palette=palette,
                gutter=gutter,
            )

        # Generate connectors if needed
        connectors = []
        if rules.connector_template.pattern.value == "sequential":
            connectors = self.generate_sequential_connectors(
                elements,
                style=rules.connector_template.style,
                color=rules.connector_template.color or palette.connector,
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

    def _compute_vertical_stack(
        self,
        blocks: List,
        bounds: ContentBounds,
        template,
        palette: ColorPalette,
        alignment: str,
        gutter: float,
        top_width_ratio: float,
        bottom_width_ratio: float,
        direction_hint: str,
    ) -> List[ElementPosition]:
        """Compute positions for vertical stack layout."""
        elements = []
        num_elements = len(blocks)

        # Calculate total height available
        total_gutter = gutter * (num_elements - 1)
        available_height = bounds.height - total_gutter

        # Calculate element heights
        base_height = available_height / num_elements
        min_height = 0.5
        max_height = 1.2
        element_height = max(min_height, min(max_height, base_height))

        # Recalculate to center vertically
        total_height = element_height * num_elements + total_gutter
        start_y = bounds.top + (bounds.height - total_height) / 2

        # Calculate width progression
        if direction_hint == 'top_narrow':
            # Pyramid: narrow at top, wide at bottom
            start_width = bounds.width * bottom_width_ratio
            end_width = bounds.width * top_width_ratio
        else:
            # Funnel: wide at top, narrow at bottom
            start_width = bounds.width * top_width_ratio
            end_width = bounds.width * bottom_width_ratio

        # Width step between elements
        if num_elements > 1:
            width_step = (end_width - start_width) / (num_elements - 1)
        else:
            width_step = 0

        for i, block in enumerate(blocks):
            y = start_y + i * (element_height + gutter)
            element_width = start_width + i * width_step

            # Center horizontally based on alignment
            if alignment == 'center':
                x = bounds.left + (bounds.width - element_width) / 2
            elif alignment == 'left':
                x = bounds.left
            else:  # right
                x = bounds.right - element_width

            # Determine shape type
            shape_type = template.element_type.value
            if shape_type == 'trapezoid':
                # For trapezoids, we need to know if this tapers up or down
                shape_type = 'trapezoid'

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
                shape_type=shape_type,
                corner_radius=template.corner_radius,
                z_order=10 - i,  # Earlier elements on top for funnel effect
            ))

        return elements

    def _compute_horizontal_stack(
        self,
        blocks: List,
        bounds: ContentBounds,
        template,
        palette: ColorPalette,
        gutter: float,
    ) -> List[ElementPosition]:
        """Compute positions for horizontal stack layout."""
        elements = []
        num_elements = len(blocks)

        # Calculate total width available
        total_gutter = gutter * (num_elements - 1)
        available_width = bounds.width - total_gutter

        # Calculate element widths (uniform for horizontal)
        element_width = available_width / num_elements
        min_width = 1.0
        max_width = 3.0
        element_width = max(min_width, min(max_width, element_width))

        # Recalculate to center horizontally
        total_width = element_width * num_elements + total_gutter
        start_x = bounds.left + (bounds.width - total_width) / 2

        # Use fixed height
        element_height = min(1.2, bounds.height * 0.6)
        y = bounds.top + (bounds.height - element_height) / 2

        for i, block in enumerate(blocks):
            x = start_x + i * (element_width + gutter)

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
