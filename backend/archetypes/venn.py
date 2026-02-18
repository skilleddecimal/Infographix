"""
venn.py — Venn Diagram Archetype.

Venn diagrams showing overlapping circles:
- 2-4 overlapping circles
- Shows relationships and intersections
- Labels for each circle and intersection areas
- Great for showing shared attributes

Example prompts:
- "Venn diagram of skills overlap between teams"
- "Show intersection of marketing, sales, and product"
- "Compare three approaches with overlapping benefits"
"""

import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

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
    DEFAULT_FONT_FAMILY,
)
from ..engine.text_measure import fit_text_to_width


# =============================================================================
# VENN CONFIGURATION
# =============================================================================

@dataclass
class VennConfig:
    """Configuration options for Venn diagram layout."""
    circle_opacity: float = 0.6              # Opacity of circles (for overlap effect)
    circle_size_ratio: float = 0.45          # Circle size as ratio of content area
    overlap_ratio: float = 0.35              # How much circles overlap (0-1)
    show_intersection_labels: bool = True    # Show labels in intersection areas


# =============================================================================
# VENN ARCHETYPE
# =============================================================================

class VennArchetype(BaseArchetype):
    """
    Venn diagram archetype.

    Creates overlapping circle layouts where:
    - 2-4 circles represent sets or categories
    - Overlap areas show shared elements
    - Semi-transparent fills show intersections
    - Labels identify each circle and optionally intersections
    """

    name = "venn_diagram"
    display_name = "Venn Diagram"
    description = "Overlapping circles showing relationships and intersections"
    example_prompts = [
        "Venn diagram of Data Science, ML, and AI",
        "Skills overlap between frontend and backend",
        "Compare product, design, and engineering",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[VennConfig] = None
    ):
        super().__init__(palette)
        self.config = config or VennConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a Venn diagram layout from input data."""
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

        # Create Venn circles
        elements = self._create_venn_circles(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _create_venn_circles(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create the Venn circle elements."""
        elements = []
        num_circles = len(blocks)

        if num_circles == 0:
            return elements

        # Calculate center of content area
        center_x = CONTENT_LEFT + CONTENT_WIDTH / 2
        center_y = content_top + content_height / 2

        # Calculate circle size
        min_dimension = min(CONTENT_WIDTH, content_height)
        circle_diameter = min_dimension * self.config.circle_size_ratio

        # Position circles based on count
        if num_circles == 2:
            positions = self._get_two_circle_positions(center_x, center_y, circle_diameter)
        elif num_circles == 3:
            positions = self._get_three_circle_positions(center_x, center_y, circle_diameter)
        elif num_circles == 4:
            positions = self._get_four_circle_positions(center_x, center_y, circle_diameter)
        else:
            positions = [(center_x, center_y)]

        # Create circle elements
        for i, (block, (cx, cy)) in enumerate(zip(blocks, positions)):
            element = self._create_circle_element(
                block,
                cx,
                cy,
                circle_diameter,
                i
            )
            elements.append(element)

        return elements

    def _get_two_circle_positions(
        self,
        center_x: float,
        center_y: float,
        diameter: float
    ) -> List[Tuple[float, float]]:
        """Get positions for 2-circle Venn."""
        offset = diameter * (1 - self.config.overlap_ratio) / 2
        return [
            (center_x - offset, center_y),
            (center_x + offset, center_y),
        ]

    def _get_three_circle_positions(
        self,
        center_x: float,
        center_y: float,
        diameter: float
    ) -> List[Tuple[float, float]]:
        """Get positions for 3-circle Venn (triangle arrangement)."""
        offset = diameter * (1 - self.config.overlap_ratio) / 2
        # Equilateral triangle arrangement
        angle_offset = -math.pi / 2  # Start at top
        positions = []
        for i in range(3):
            angle = angle_offset + i * (2 * math.pi / 3)
            x = center_x + offset * math.cos(angle)
            y = center_y + offset * math.sin(angle)
            positions.append((x, y))
        return positions

    def _get_four_circle_positions(
        self,
        center_x: float,
        center_y: float,
        diameter: float
    ) -> List[Tuple[float, float]]:
        """Get positions for 4-circle Venn (square arrangement)."""
        offset = diameter * (1 - self.config.overlap_ratio) / 2 * 0.8
        return [
            (center_x - offset, center_y - offset),  # Top-left
            (center_x + offset, center_y - offset),  # Top-right
            (center_x - offset, center_y + offset),  # Bottom-left
            (center_x + offset, center_y + offset),  # Bottom-right
        ]

    def _create_circle_element(
        self,
        block: BlockData,
        center_x: float,
        center_y: float,
        diameter: float,
        index: int
    ) -> PositionedElement:
        """Create a Venn circle element."""
        fill_color = block.color or self.palette.get_color_for_index(index)

        # Fit text
        fit_result = fit_text_to_width(
            block.label,
            diameter * 0.6,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=12,
            min_font_size=9,
            bold=True,
            allow_wrap=True,
            max_lines=2
        )

        text_color = self._contrast_text_color(fill_color)

        circle_text = PositionedText(
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
            x_inches=center_x - diameter / 2,
            y_inches=center_y - diameter / 2,
            width_inches=diameter,
            height_inches=diameter,
            fill_color=fill_color,
            stroke_color=self.palette.border,
            stroke_width_pt=2.0,
            corner_radius_inches=diameter / 2,  # Make circular
            opacity=self.config.circle_opacity,
            text=circle_text,
            z_order=10 + index
        )

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for Venn diagram layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 2:
            errors.append("Venn diagram requires at least 2 circles")

        if len(input_data.blocks) > 4:
            errors.append("Too many circles for Venn diagram (max 4)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_venn(
    title: str,
    circles: List[str],
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a Venn diagram.

    Args:
        title: Diagram title
        circles: List of circle labels (2-4)
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_venn(
            title="Data Science Skills",
            circles=["Statistics", "Programming", "Domain Knowledge"]
        )
    """
    blocks = [
        BlockData(id=f"circle_{i}", label=circle)
        for i, circle in enumerate(circles)
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    archetype = VennArchetype()
    return archetype.generate_layout(input_data)
