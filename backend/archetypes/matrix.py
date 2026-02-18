"""
matrix.py — Matrix / Quadrant Archetype.

Matrix diagrams for 2D categorization:
- 2x2 quadrant (most common)
- 3x3 matrix
- Axis labels
- Items placed in quadrants

Example prompts:
- "Eisenhower matrix (urgent/important)"
- "BCG growth-share matrix"
- "Effort vs Impact prioritization"
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .base import (
    BaseArchetype,
    DiagramInput,
    BlockData,
    LayerData,
    ColorPalette,
)
from ..engine.positioned import (
    PositionedLayout,
    PositionedElement,
    PositionedConnector,
    PositionedText,
    ElementType,
    TextAlignment,
)
from ..engine.units import (
    SLIDE_WIDTH_INCHES,
    SLIDE_HEIGHT_INCHES,
    CONTENT_LEFT,
    CONTENT_TOP,
    CONTENT_WIDTH,
    CONTENT_HEIGHT,
    GUTTER_H,
    GUTTER_V,
    DEFAULT_FONT_FAMILY,
)
from ..engine.text_measure import fit_text_to_width


# =============================================================================
# MATRIX CONFIGURATION
# =============================================================================

class MatrixSize(Enum):
    """Matrix dimensions."""
    MATRIX_2X2 = "2x2"
    MATRIX_3X3 = "3x3"


@dataclass
class MatrixConfig:
    """Configuration options for matrix layout."""
    size: MatrixSize = MatrixSize.MATRIX_2X2
    cell_gutter: float = GUTTER_H * 0.5      # Gap between cells
    axis_label_width: float = 0.8            # Width for axis labels
    show_axis_labels: bool = True            # Show X and Y axis labels
    show_quadrant_labels: bool = True        # Show quadrant/cell labels
    x_axis_label: str = ""                   # Label for X axis
    y_axis_label: str = ""                   # Label for Y axis


# =============================================================================
# MATRIX ARCHETYPE
# =============================================================================

class MatrixArchetype(BaseArchetype):
    """
    Matrix / Quadrant diagram archetype.

    Creates grid-based layouts where:
    - Cells categorize items on two dimensions
    - Axis labels describe the dimensions
    - Items are placed within appropriate quadrants
    - Colors distinguish different quadrants
    """

    name = "matrix_2x2"
    display_name = "2x2 Matrix / Quadrant"
    description = "Four quadrants for categorizing items on two dimensions"
    example_prompts = [
        "Eisenhower matrix: urgent/important",
        "Effort vs Impact prioritization",
        "Risk vs Probability assessment",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[MatrixConfig] = None
    ):
        super().__init__(palette)
        self.config = config or MatrixConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a matrix layout from input data."""
        errors = self.validate_input(input_data)
        if errors:
            return self.create_empty_layout(
                title=input_data.title,
                subtitle=f"Layout error: {errors[0]}"
            )

        if input_data.palette:
            self.palette = input_data.palette

        layout = PositionedLayout(
            slide_width_inches=SLIDE_WIDTH_INCHES,
            slide_height_inches=SLIDE_HEIGHT_INCHES,
            background_color=self.palette.background,
            elements=[],
            connectors=[]
        )

        title_elem, subtitle_elem = self.create_title_element(
            input_data.title,
            input_data.subtitle
        )
        if title_elem:
            layout.title = title_elem
        if subtitle_elem:
            layout.subtitle = subtitle_elem

        content_top = CONTENT_TOP
        if subtitle_elem:
            content_top += 0.3

        content_height = CONTENT_HEIGHT - (content_top - CONTENT_TOP)

        # Create matrix cells
        elements = self._create_matrix_cells(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _create_matrix_cells(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create the matrix cell elements."""
        elements = []

        # Determine grid size
        if self.config.size == MatrixSize.MATRIX_2X2:
            grid_size = 2
        else:
            grid_size = 3

        # Calculate cell dimensions
        axis_space = self.config.axis_label_width if self.config.show_axis_labels else 0
        available_width = CONTENT_WIDTH - axis_space
        available_height = content_height - axis_space

        total_gutter_h = self.config.cell_gutter * (grid_size - 1)
        total_gutter_v = self.config.cell_gutter * (grid_size - 1)

        cell_width = (available_width - total_gutter_h) / grid_size
        cell_height = (available_height - total_gutter_v) / grid_size

        # Starting position (leave room for axis labels)
        start_x = CONTENT_LEFT + axis_space
        start_y = content_top

        # Default quadrant labels for 2x2
        default_labels = [
            "High Priority",      # Top-left
            "Do First",           # Top-right
            "Low Priority",       # Bottom-left
            "Delegate/Schedule",  # Bottom-right
        ]

        # Create cells
        cell_idx = 0
        for row in range(grid_size):
            for col in range(grid_size):
                x = start_x + col * (cell_width + self.config.cell_gutter)
                y = start_y + row * (cell_height + self.config.cell_gutter)

                # Get block data if available
                if cell_idx < len(blocks):
                    block = blocks[cell_idx]
                else:
                    # Use default labels
                    label = default_labels[cell_idx] if cell_idx < len(default_labels) else f"Cell {cell_idx + 1}"
                    block = BlockData(id=f"cell_{cell_idx}", label=label)

                element = self._create_cell_element(
                    block,
                    x,
                    y,
                    cell_width,
                    cell_height,
                    cell_idx,
                    row,
                    col
                )
                elements.append(element)
                cell_idx += 1

        # Add axis labels if configured
        if self.config.show_axis_labels:
            axis_elements = self._create_axis_labels(
                start_x,
                start_y,
                available_width,
                available_height,
                content_top,
                content_height
            )
            elements.extend(axis_elements)

        return elements

    def _create_cell_element(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        height: float,
        cell_idx: int,
        row: int,
        col: int
    ) -> PositionedElement:
        """Create a matrix cell element."""
        # Color varies by quadrant
        fill_color = block.color or self.palette.get_color_for_index(cell_idx)

        # Fit text
        fit_result = fit_text_to_width(
            block.label,
            width - 0.3,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=14,
            min_font_size=10,
            bold=True,
            allow_wrap=True,
            max_lines=3
        )

        text_color = self._contrast_text_color(fill_color)

        cell_text = PositionedText(
            content=block.label,
            lines=fit_result.lines,
            font_size_pt=fit_result.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            color=text_color,
            alignment=TextAlignment.CENTER
        )

        return PositionedElement(
            id=block.id,
            element_type=ElementType.BLOCK,
            x_inches=x,
            y_inches=y,
            width_inches=width,
            height_inches=height,
            fill_color=fill_color,
            stroke_color=self.palette.border,
            stroke_width_pt=1.0,
            corner_radius_inches=0.08,
            text=cell_text,
            z_order=10
        )

    def _create_axis_labels(
        self,
        grid_x: float,
        grid_y: float,
        grid_width: float,
        grid_height: float,
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create axis label elements."""
        elements = []

        # Y-axis label (left side, rotated conceptually)
        if self.config.y_axis_label:
            y_label = PositionedText(
                content=self.config.y_axis_label,
                lines=[self.config.y_axis_label],
                font_size_pt=11,
                font_family=DEFAULT_FONT_FAMILY,
                bold=True,
                color=self.palette.text_dark,
                alignment=TextAlignment.CENTER
            )

            y_axis_elem = PositionedElement(
                id="y_axis_label",
                element_type=ElementType.LABEL,
                x_inches=CONTENT_LEFT,
                y_inches=content_top + content_height / 2 - 0.3,
                width_inches=self.config.axis_label_width,
                height_inches=0.6,
                fill_color="transparent",
                text=y_label,
                z_order=5
            )
            elements.append(y_axis_elem)

        # X-axis label (bottom)
        if self.config.x_axis_label:
            x_label = PositionedText(
                content=self.config.x_axis_label,
                lines=[self.config.x_axis_label],
                font_size_pt=11,
                font_family=DEFAULT_FONT_FAMILY,
                bold=True,
                color=self.palette.text_dark,
                alignment=TextAlignment.CENTER
            )

            x_axis_elem = PositionedElement(
                id="x_axis_label",
                element_type=ElementType.LABEL,
                x_inches=grid_x + grid_width / 2 - 1.0,
                y_inches=grid_y + grid_height + 0.1,
                width_inches=2.0,
                height_inches=0.4,
                fill_color="transparent",
                text=x_label,
                z_order=5
            )
            elements.append(x_axis_elem)

        return elements

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for matrix layout."""
        errors = super().validate_input(input_data)

        expected_cells = 4 if self.config.size == MatrixSize.MATRIX_2X2 else 9

        # We allow fewer blocks (will use defaults)
        if len(input_data.blocks) > expected_cells:
            errors.append(f"Too many items for {self.config.size.value} matrix (max {expected_cells})")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_matrix(
    title: str,
    quadrants: List[str],
    x_axis: str = "",
    y_axis: str = "",
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a 2x2 matrix diagram.

    Args:
        title: Diagram title
        quadrants: List of 4 quadrant labels (top-left, top-right, bottom-left, bottom-right)
        x_axis: Label for X axis
        y_axis: Label for Y axis
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_matrix(
            title="Eisenhower Matrix",
            quadrants=["Important & Urgent", "Important & Not Urgent",
                      "Not Important & Urgent", "Not Important & Not Urgent"],
            x_axis="Urgency",
            y_axis="Importance"
        )
    """
    blocks = [
        BlockData(id=f"quadrant_{i}", label=label)
        for i, label in enumerate(quadrants)
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    config = MatrixConfig(
        x_axis_label=x_axis,
        y_axis_label=y_axis,
        show_axis_labels=bool(x_axis or y_axis)
    )

    archetype = MatrixArchetype(config=config)
    return archetype.generate_layout(input_data)
