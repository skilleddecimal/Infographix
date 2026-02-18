"""
icon_grid.py — Icon Grid Archetype.

Grid layouts with icons and labels:
- Features, capabilities, benefits lists
- Icons paired with text for visual appeal
- Consistent grid arrangement
- Great for feature highlights, service offerings

Example prompts:
- "Key features of our product"
- "Core capabilities"
- "Benefits of our service"
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
# ICON GRID CONFIGURATION
# =============================================================================

class IconGridStyle(Enum):
    """Style of icon grid layout."""
    ICON_ABOVE = "icon_above"      # Icon centered above text
    ICON_LEFT = "icon_left"        # Icon to the left of text
    ICON_ONLY = "icon_only"        # Large icons with small labels


@dataclass
class IconGridConfig:
    """Configuration options for icon grid layout."""
    style: IconGridStyle = IconGridStyle.ICON_ABOVE
    icon_size: float = 0.5                    # Size of icon placeholder
    cell_padding: float = 0.15                # Padding inside each cell
    max_columns: int = 4                      # Maximum columns
    min_columns: int = 2                      # Minimum columns
    show_border: bool = False                 # Show border around cells


# =============================================================================
# ICON GRID ARCHETYPE
# =============================================================================

class IconGridArchetype(BaseArchetype):
    """
    Icon Grid diagram archetype.

    Creates grid layouts where:
    - Items displayed in uniform grid cells
    - Each cell has an icon placeholder and text
    - Great for features, capabilities, benefits
    - Visual consistency with clear organization
    """

    name = "icon_grid"
    display_name = "Icon Grid"
    description = "Grid of items with icons and labels"
    example_prompts = [
        "Key product features",
        "Our core capabilities",
        "Service benefits",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[IconGridConfig] = None
    ):
        super().__init__(palette)
        self.config = config or IconGridConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate an icon grid layout from input data."""
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

        # Create grid elements
        elements = self._create_icon_grid(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _calculate_grid_dimensions(self, num_items: int) -> Tuple[int, int]:
        """Calculate optimal rows and columns for the grid."""
        # Try to make it as square as possible, but prefer wider layouts
        import math

        if num_items <= self.config.max_columns:
            return 1, num_items

        # Find best column count
        for cols in range(self.config.max_columns, self.config.min_columns - 1, -1):
            rows = math.ceil(num_items / cols)
            if rows * cols >= num_items:
                return rows, cols

        # Fallback
        cols = self.config.min_columns
        rows = math.ceil(num_items / cols)
        return rows, cols

    def _create_icon_grid(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create the icon grid elements."""
        elements = []
        num_items = len(blocks)

        if num_items == 0:
            return elements

        rows, cols = self._calculate_grid_dimensions(num_items)

        # Calculate cell dimensions
        cell_width = (CONTENT_WIDTH - (cols - 1) * GUTTER_H) / cols
        cell_height = (content_height - (rows - 1) * GUTTER_V) / rows

        # Limit cell height to maintain proportions
        max_cell_height = cell_width * 1.2  # Aspect ratio limit
        if cell_height > max_cell_height:
            cell_height = max_cell_height
            # Recenter vertically
            total_height = rows * cell_height + (rows - 1) * GUTTER_V
            content_top = content_top + (content_height - total_height) / 2

        # Create grid cells
        for i, block in enumerate(blocks):
            row = i // cols
            col = i % cols

            x = CONTENT_LEFT + col * (cell_width + GUTTER_H)
            y = content_top + row * (cell_height + GUTTER_V)

            cell_elements = self._create_grid_cell(
                block,
                x,
                y,
                cell_width,
                cell_height,
                i
            )
            elements.extend(cell_elements)

        return elements

    def _create_grid_cell(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        height: float,
        cell_idx: int
    ) -> List[PositionedElement]:
        """Create a single grid cell with icon placeholder and text."""
        elements = []

        fill_color = block.color or self.palette.get_color_for_index(cell_idx)
        padding = self.config.cell_padding

        if self.config.style == IconGridStyle.ICON_ABOVE:
            # Icon centered above, text below
            icon_size = self.config.icon_size
            icon_x = x + (width - icon_size) / 2
            icon_y = y + padding

            text_y = icon_y + icon_size + padding
            text_height = height - icon_size - padding * 3

            # Icon placeholder (circle)
            icon_element = PositionedElement(
                id=f"{block.id}_icon",
                element_type=ElementType.ELLIPSE,
                x_inches=icon_x,
                y_inches=icon_y,
                width_inches=icon_size,
                height_inches=icon_size,
                fill_color=fill_color,
                stroke_color=None,
                stroke_width_pt=0,
                z_order=10 + cell_idx
            )
            elements.append(icon_element)

            # Text label
            fit_result = fit_text_to_width(
                block.label,
                width - padding * 2,
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=11,
                min_font_size=8,
                bold=True,
                allow_wrap=True,
                max_lines=2
            )

            label_text = PositionedText(
                content=block.label,
                lines=fit_result.lines,
                font_size_pt=fit_result.font_size,
                font_family=DEFAULT_FONT_FAMILY,
                bold=True,
                color=self.palette.text_dark,
                alignment=TextAlignment.CENTER
            )

            text_element = PositionedElement(
                id=f"{block.id}_text",
                element_type=ElementType.TEXT_BOX,
                x_inches=x + padding,
                y_inches=text_y,
                width_inches=width - padding * 2,
                height_inches=text_height,
                fill_color=None,
                stroke_color=None,
                stroke_width_pt=0,
                text=label_text,
                z_order=11 + cell_idx
            )
            elements.append(text_element)

        elif self.config.style == IconGridStyle.ICON_LEFT:
            # Icon on left, text on right
            icon_size = min(self.config.icon_size, height - padding * 2)
            icon_x = x + padding
            icon_y = y + (height - icon_size) / 2

            text_x = icon_x + icon_size + padding
            text_width = width - icon_size - padding * 3

            # Icon placeholder (circle)
            icon_element = PositionedElement(
                id=f"{block.id}_icon",
                element_type=ElementType.ELLIPSE,
                x_inches=icon_x,
                y_inches=icon_y,
                width_inches=icon_size,
                height_inches=icon_size,
                fill_color=fill_color,
                stroke_color=None,
                stroke_width_pt=0,
                z_order=10 + cell_idx
            )
            elements.append(icon_element)

            # Text label
            fit_result = fit_text_to_width(
                block.label,
                text_width,
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=11,
                min_font_size=8,
                bold=True,
                allow_wrap=True,
                max_lines=3
            )

            label_text = PositionedText(
                content=block.label,
                lines=fit_result.lines,
                font_size_pt=fit_result.font_size,
                font_family=DEFAULT_FONT_FAMILY,
                bold=True,
                color=self.palette.text_dark,
                alignment=TextAlignment.LEFT
            )

            text_element = PositionedElement(
                id=f"{block.id}_text",
                element_type=ElementType.TEXT_BOX,
                x_inches=text_x,
                y_inches=y + padding,
                width_inches=text_width,
                height_inches=height - padding * 2,
                fill_color=None,
                stroke_color=None,
                stroke_width_pt=0,
                text=label_text,
                z_order=11 + cell_idx
            )
            elements.append(text_element)

        else:  # ICON_ONLY
            # Large icon with small label below
            icon_size = min(self.config.icon_size * 1.5, width - padding * 2, height * 0.6)
            icon_x = x + (width - icon_size) / 2
            icon_y = y + padding

            # Icon placeholder (circle)
            icon_element = PositionedElement(
                id=f"{block.id}_icon",
                element_type=ElementType.ELLIPSE,
                x_inches=icon_x,
                y_inches=icon_y,
                width_inches=icon_size,
                height_inches=icon_size,
                fill_color=fill_color,
                stroke_color=None,
                stroke_width_pt=0,
                z_order=10 + cell_idx
            )
            elements.append(icon_element)

            # Small label
            fit_result = fit_text_to_width(
                block.label,
                width - padding * 2,
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=9,
                min_font_size=7,
                bold=False,
                allow_wrap=True,
                max_lines=1
            )

            label_text = PositionedText(
                content=block.label,
                lines=fit_result.lines,
                font_size_pt=fit_result.font_size,
                font_family=DEFAULT_FONT_FAMILY,
                bold=False,
                color=self.palette.text_dark,
                alignment=TextAlignment.CENTER
            )

            text_element = PositionedElement(
                id=f"{block.id}_text",
                element_type=ElementType.TEXT_BOX,
                x_inches=x + padding,
                y_inches=icon_y + icon_size + padding * 0.5,
                width_inches=width - padding * 2,
                height_inches=height - icon_size - padding * 2.5,
                fill_color=None,
                stroke_color=None,
                stroke_width_pt=0,
                text=label_text,
                z_order=11 + cell_idx
            )
            elements.append(text_element)

        # Optional border around cell
        if self.config.show_border:
            border_element = PositionedElement(
                id=f"{block.id}_border",
                element_type=ElementType.BLOCK,
                x_inches=x,
                y_inches=y,
                width_inches=width,
                height_inches=height,
                fill_color=None,
                stroke_color=self.palette.border,
                stroke_width_pt=0.5,
                corner_radius_inches=0.08,
                z_order=5 + cell_idx
            )
            elements.append(border_element)

        return elements

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for icon grid layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 2:
            errors.append("Icon grid requires at least 2 items")

        if len(input_data.blocks) > 12:
            errors.append("Too many items for icon grid (max 12)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_icon_grid(
    title: str,
    items: List[str],
    subtitle: Optional[str] = None,
    style: str = "icon_above"
) -> PositionedLayout:
    """
    Quick helper to create an icon grid diagram.

    Args:
        title: Diagram title
        items: List of item labels
        subtitle: Optional subtitle
        style: Layout style - "icon_above", "icon_left", or "icon_only"

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_icon_grid(
            title="Key Features",
            items=["Fast", "Secure", "Scalable", "Reliable"]
        )
    """
    blocks = [
        BlockData(id=f"item_{i}", label=item)
        for i, item in enumerate(items)
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    style_enum = IconGridStyle.ICON_ABOVE
    if style == "icon_left":
        style_enum = IconGridStyle.ICON_LEFT
    elif style == "icon_only":
        style_enum = IconGridStyle.ICON_ONLY

    config = IconGridConfig(style=style_enum)

    archetype = IconGridArchetype(config=config)
    return archetype.generate_layout(input_data)
