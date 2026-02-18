"""
staircase.py — Staircase / Steps Archetype.

Ascending or descending step diagrams:
- Visual progression through levels
- Great for maturity models, growth stages
- Can go up or down
- Each step represents a milestone or level

Example prompts:
- "Maturity model levels"
- "Career progression ladder"
- "Skill development stages"
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
    DEFAULT_FONT_FAMILY,
)
from ..engine.text_measure import fit_text_to_width


# =============================================================================
# STAIRCASE CONFIGURATION
# =============================================================================

class StaircaseDirection(Enum):
    """Direction of the staircase."""
    ASCENDING = "ascending"    # Steps go up (left to right)
    DESCENDING = "descending"  # Steps go down (left to right)


@dataclass
class StaircaseConfig:
    """Configuration options for staircase layout."""
    direction: StaircaseDirection = StaircaseDirection.ASCENDING
    step_width: float = 1.8                  # Width of each step
    step_height: float = 0.8                 # Height of each step
    step_offset: float = 0.4                 # Vertical offset between steps
    step_gutter: float = GUTTER_H * 0.3      # Horizontal gap between steps


# =============================================================================
# STAIRCASE ARCHETYPE
# =============================================================================

class StaircaseArchetype(BaseArchetype):
    """
    Staircase / Steps diagram archetype.

    Creates step-based layouts where:
    - Steps progress horizontally with vertical offset
    - Each step represents a level or milestone
    - Visual metaphor of climbing/descending
    - Great for maturity models, growth stages
    """

    name = "staircase"
    display_name = "Staircase / Steps"
    description = "Ascending or descending steps showing progression"
    example_prompts = [
        "Capability maturity model",
        "Career growth ladder",
        "Learning progression steps",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[StaircaseConfig] = None
    ):
        super().__init__(palette)
        self.config = config or StaircaseConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a staircase layout from input data."""
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

        # Create staircase steps
        elements = self._create_staircase_steps(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _create_staircase_steps(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create the staircase step elements."""
        elements = []
        num_steps = len(blocks)

        if num_steps == 0:
            return elements

        # Calculate total dimensions
        total_width = num_steps * self.config.step_width + (num_steps - 1) * self.config.step_gutter
        total_height = self.config.step_height + (num_steps - 1) * self.config.step_offset

        # Center horizontally
        start_x = CONTENT_LEFT + (CONTENT_WIDTH - total_width) / 2

        # Position vertically based on direction
        if self.config.direction == StaircaseDirection.ASCENDING:
            # Start at bottom, go up
            start_y = content_top + content_height - self.config.step_height
        else:
            # Start at top, go down
            start_y = content_top

        # Create step elements
        for i, block in enumerate(blocks):
            x = start_x + i * (self.config.step_width + self.config.step_gutter)

            if self.config.direction == StaircaseDirection.ASCENDING:
                y = start_y - i * self.config.step_offset
            else:
                y = start_y + i * self.config.step_offset

            element = self._create_step_element(
                block,
                x,
                y,
                i,
                num_steps
            )
            elements.append(element)

        return elements

    def _create_step_element(
        self,
        block: BlockData,
        x: float,
        y: float,
        step_idx: int,
        total_steps: int
    ) -> PositionedElement:
        """Create a single step element."""
        fill_color = block.color or self.palette.get_color_for_index(step_idx)

        # Fit text
        fit_result = fit_text_to_width(
            block.label,
            self.config.step_width - 0.2,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=12,
            min_font_size=9,
            bold=True,
            allow_wrap=True,
            max_lines=2
        )

        text_color = self._contrast_text_color(fill_color)

        step_text = PositionedText(
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
            width_inches=self.config.step_width,
            height_inches=self.config.step_height,
            fill_color=fill_color,
            stroke_color=self.palette.border,
            stroke_width_pt=1.0,
            corner_radius_inches=0.06,
            text=step_text,
            z_order=10 + step_idx
        )

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for staircase layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 2:
            errors.append("Staircase requires at least 2 steps")

        if len(input_data.blocks) > 8:
            errors.append("Too many steps for staircase (max 8)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_staircase(
    title: str,
    steps: List[str],
    subtitle: Optional[str] = None,
    ascending: bool = True
) -> PositionedLayout:
    """
    Quick helper to create a staircase diagram.

    Args:
        title: Diagram title
        steps: List of step labels from first to last
        subtitle: Optional subtitle
        ascending: If True, steps go up; if False, steps go down

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_staircase(
            title="Maturity Model",
            steps=["Initial", "Managed", "Defined", "Quantified", "Optimizing"]
        )
    """
    blocks = [
        BlockData(id=f"step_{i}", label=step)
        for i, step in enumerate(steps)
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    config = StaircaseConfig(
        direction=StaircaseDirection.ASCENDING if ascending else StaircaseDirection.DESCENDING
    )

    archetype = StaircaseArchetype(config=config)
    return archetype.generate_layout(input_data)
