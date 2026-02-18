"""
pyramid.py — Pyramid / Hierarchy Archetype.

Triangular pyramid diagrams showing hierarchical levels:
- Wide base narrowing to top
- 3-7 levels typical
- Each level represents a tier of importance/hierarchy
- Optional inverted pyramid variant

Example prompts:
- "Maslow's hierarchy of needs"
- "Data-Information-Knowledge-Wisdom pyramid"
- "Organizational pyramid with leadership at top"
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
    GUTTER_V,
    DEFAULT_FONT_FAMILY,
)
from ..engine.text_measure import fit_text_to_width


# =============================================================================
# PYRAMID CONFIGURATION
# =============================================================================

class PyramidDirection(Enum):
    """Direction of the pyramid."""
    UPWARD = "upward"      # Wide base at bottom, narrow top (traditional)
    DOWNWARD = "downward"  # Wide at top, narrow bottom (inverted)


@dataclass
class PyramidConfig:
    """Configuration options for pyramid layout."""
    direction: PyramidDirection = PyramidDirection.UPWARD
    level_gutter: float = GUTTER_V * 0.5    # Gap between levels
    base_width_ratio: float = 0.85           # Base width as ratio of content width
    top_width_ratio: float = 0.25            # Top width as ratio of content width
    min_level_height: float = 0.6            # Minimum height for each level
    max_level_height: float = 1.2            # Maximum height for each level
    show_3d_effect: bool = False             # Add 3D shading effect


# =============================================================================
# PYRAMID ARCHETYPE
# =============================================================================

class PyramidArchetype(BaseArchetype):
    """
    Pyramid diagram archetype.

    Creates triangular pyramid layouts where:
    - Levels stack from wide (base) to narrow (top)
    - Each level represents a hierarchical tier
    - Colors typically progress from darker at base to lighter at top
    - Supports traditional (upward) and inverted (downward) pyramids
    """

    name = "pyramid"
    display_name = "Pyramid / Hierarchy"
    description = "Triangular hierarchy with levels from base to apex"
    example_prompts = [
        "Maslow's hierarchy of needs pyramid",
        "Data-Information-Knowledge-Wisdom hierarchy",
        "Leadership pyramid with executives at top",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[PyramidConfig] = None
    ):
        super().__init__(palette)
        self.config = config or PyramidConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a pyramid layout from input data."""
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

        # Create pyramid levels
        elements = self._create_pyramid_levels(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _create_pyramid_levels(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create the pyramid level elements."""
        elements = []

        if not blocks:
            return elements

        num_levels = len(blocks)

        # Calculate level heights
        total_gutter = self.config.level_gutter * (num_levels - 1)
        available_height = content_height - total_gutter
        level_height = available_height / num_levels
        level_height = max(self.config.min_level_height,
                          min(self.config.max_level_height, level_height))

        # Recalculate total height
        total_height = level_height * num_levels + total_gutter
        start_y = content_top + (content_height - total_height) / 2

        # Width progression from base to top
        base_width = CONTENT_WIDTH * self.config.base_width_ratio
        top_width = CONTENT_WIDTH * self.config.top_width_ratio
        width_step = (base_width - top_width) / (num_levels - 1) if num_levels > 1 else 0

        # Determine order based on pyramid direction
        if self.config.direction == PyramidDirection.UPWARD:
            # Traditional: base at bottom, apex at top
            # First block = top (apex), last block = bottom (base)
            # OR we can interpret first block as base
            # Let's use: first block = base (bottom), last block = apex (top)
            level_order = list(range(num_levels - 1, -1, -1))  # Draw from bottom up
        else:
            # Inverted: wide at top, narrow at bottom
            level_order = list(range(num_levels))  # Draw from top down

        # Create levels
        for draw_idx, block_idx in enumerate(level_order):
            block = blocks[block_idx]

            # Position based on direction
            if self.config.direction == PyramidDirection.UPWARD:
                # Bottom to top: draw_idx 0 is at bottom
                y = start_y + (num_levels - 1 - draw_idx) * (level_height + self.config.level_gutter)
                # Width decreases as we go up (draw_idx increases)
                level_width = base_width - (draw_idx * width_step)
            else:
                # Top to bottom: draw_idx 0 is at top
                y = start_y + draw_idx * (level_height + self.config.level_gutter)
                # Width decreases as we go down
                level_width = base_width - (draw_idx * width_step)

            # Center horizontally
            x = CONTENT_LEFT + (CONTENT_WIDTH - level_width) / 2

            # Create level element
            element = self._create_level_element(
                block,
                x,
                y,
                level_width,
                level_height,
                block_idx,
                num_levels
            )
            elements.append(element)

        return elements

    def _create_level_element(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        height: float,
        level_idx: int,
        total_levels: int
    ) -> PositionedElement:
        """Create a single pyramid level element."""
        # Color progression: use different colors for each level
        fill_color = block.color or self.palette.get_color_for_index(level_idx)

        # Fit text
        fit_result = fit_text_to_width(
            block.label,
            width - 0.4,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=14,
            min_font_size=10,
            bold=True,
            allow_wrap=True,
            max_lines=2
        )

        text_color = self._contrast_text_color(fill_color)

        level_text = PositionedText(
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
            corner_radius_inches=0.04,
            text=level_text,
            z_order=10 + level_idx  # Higher levels on top
        )

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for pyramid layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 2:
            errors.append("Pyramid requires at least 2 levels")

        if len(input_data.blocks) > 7:
            errors.append("Too many levels for pyramid (max 7)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_pyramid(
    title: str,
    levels: List[str],
    subtitle: Optional[str] = None,
    inverted: bool = False
) -> PositionedLayout:
    """
    Quick helper to create a pyramid diagram.

    Args:
        title: Diagram title
        levels: List of level labels from base to apex
        subtitle: Optional subtitle
        inverted: If True, creates inverted pyramid (wide at top)

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_pyramid(
            title="Maslow's Hierarchy",
            levels=[
                "Physiological",
                "Safety",
                "Love/Belonging",
                "Esteem",
                "Self-Actualization"
            ]
        )
    """
    blocks = [
        BlockData(id=f"level_{i}", label=level)
        for i, level in enumerate(levels)
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    config = PyramidConfig(
        direction=PyramidDirection.DOWNWARD if inverted else PyramidDirection.UPWARD
    )

    archetype = PyramidArchetype(config=config)
    return archetype.generate_layout(input_data)
