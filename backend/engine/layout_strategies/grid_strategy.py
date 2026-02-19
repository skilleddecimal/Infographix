"""
grid_strategy.py — Grid-based layout strategy.

Used for: Comparison, Matrix, Card Grid, Icon Grid
Pattern: Elements arranged in rows and columns.
"""

import math
from typing import List, Dict, Any, Optional

from .base_strategy import (
    BaseLayoutStrategy,
    StrategyResult,
    ElementPosition,
    ContentBounds,
)
from ..archetype_rules import ArchetypeRules, LayoutDirection
from ..data_models import DiagramInput, ColorPalette


class GridStrategy(BaseLayoutStrategy):
    """
    Grid layout strategy for row/column arrangements.

    Key features:
    - Auto-calculate optimal row/column count
    - Configurable gutters
    - Support for spanning cells
    - Row/column headers
    """

    def compute(
        self,
        input_data: DiagramInput,
        rules: ArchetypeRules,
        bounds: ContentBounds,
        palette: ColorPalette,
    ) -> StrategyResult:
        """Compute positions for grid layout."""
        blocks = input_data.blocks
        if not blocks:
            return StrategyResult(warnings=["No blocks to layout"])

        template = rules.element_template
        grid_params = rules.grid_params

        # Get configuration
        gutter_h = grid_params.get('gutter_h', 0.25)
        gutter_v = grid_params.get('gutter_v', 0.2)
        cell_aspect_ratio = grid_params.get('cell_aspect_ratio', 1.5)

        num_elements = len(blocks)

        # Determine grid dimensions
        columns = grid_params.get('columns', 'auto')
        rows = grid_params.get('rows', 'auto')

        if columns == 'auto' and rows == 'auto':
            columns, rows = self._calculate_optimal_grid(
                num_elements, bounds, cell_aspect_ratio, gutter_h, gutter_v
            )
        elif columns == 'auto':
            columns = math.ceil(num_elements / rows)
        elif rows == 'auto':
            rows = math.ceil(num_elements / columns)

        # Calculate cell dimensions
        total_gutter_h = gutter_h * (columns - 1)
        total_gutter_v = gutter_v * (rows - 1)

        cell_width = (bounds.width - total_gutter_h) / columns
        cell_height = (bounds.height - total_gutter_v) / rows

        # Constrain cell sizes
        min_cell_width = 1.0
        max_cell_width = 4.0
        min_cell_height = 0.6
        max_cell_height = 2.0

        cell_width = max(min_cell_width, min(max_cell_width, cell_width))
        cell_height = max(min_cell_height, min(max_cell_height, cell_height))

        # Recalculate grid to center content
        actual_width = cell_width * columns + total_gutter_h
        actual_height = cell_height * rows + total_gutter_v
        start_x = bounds.left + (bounds.width - actual_width) / 2
        start_y = bounds.top + (bounds.height - actual_height) / 2

        # Position elements
        elements: List[ElementPosition] = []
        for i, block in enumerate(blocks):
            row = i // columns
            col = i % columns

            x = start_x + col * (cell_width + gutter_h)
            y = start_y + row * (cell_height + gutter_v)

            fill_color = self.compute_element_color(
                block, template, i, num_elements, palette
            )

            elements.append(ElementPosition(
                element_id=block.id,
                block_data=block,
                x=x,
                y=y,
                width=cell_width,
                height=cell_height,
                fill_color=fill_color,
                stroke_color=template.stroke_color,
                shape_type=template.element_type.value,
                corner_radius=template.corner_radius,
                z_order=10,
            ))

        result = StrategyResult(
            elements=elements,
            connectors=[],
            used_bounds=ContentBounds(
                left=start_x,
                top=start_y,
                width=actual_width,
                height=actual_height,
            ),
        )

        # Apply constraints
        if rules.constraints:
            result = self.apply_constraints(result, rules.constraints, bounds)

        return result

    def _calculate_optimal_grid(
        self,
        num_elements: int,
        bounds: ContentBounds,
        aspect_ratio: float,
        gutter_h: float,
        gutter_v: float,
    ) -> tuple:
        """Calculate optimal column and row count for given elements."""
        # Try different configurations and score them
        best_score = float('inf')
        best_config = (1, num_elements)

        for cols in range(1, num_elements + 1):
            rows = math.ceil(num_elements / cols)

            # Calculate what cell size would be
            total_gutter_h = gutter_h * (cols - 1)
            total_gutter_v = gutter_v * (rows - 1)

            cell_width = (bounds.width - total_gutter_h) / cols
            cell_height = (bounds.height - total_gutter_v) / rows

            if cell_width < 0.5 or cell_height < 0.3:
                continue

            # Score based on:
            # 1. How close cell aspect ratio is to target
            actual_ratio = cell_width / cell_height
            ratio_diff = abs(actual_ratio - aspect_ratio) / aspect_ratio

            # 2. How many empty cells
            empty_cells = (cols * rows) - num_elements
            empty_penalty = empty_cells * 0.2

            # 3. Prefer more columns than rows (for horizontal slides)
            orientation_bonus = -0.1 if cols >= rows else 0

            score = ratio_diff + empty_penalty + orientation_bonus

            if score < best_score:
                best_score = score
                best_config = (cols, rows)

        return best_config
