"""
chevron.py — Chevron Process Archetype.

Chevron arrow diagrams for processes:
- Connected chevron/arrow shapes
- Visual flow and momentum
- Great for phase-based processes
- Sales stages, project phases

Example prompts:
- "Sales process stages"
- "Project lifecycle phases"
- "Customer journey stages"
"""

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
    GUTTER_H,
    DEFAULT_FONT_FAMILY,
)
from ..engine.text_measure import fit_text_to_width


# =============================================================================
# CHEVRON CONFIGURATION
# =============================================================================

@dataclass
class ChevronConfig:
    """Configuration options for chevron layout."""
    chevron_height: float = 1.0              # Height of chevron shapes
    chevron_min_width: float = 1.5           # Minimum width of chevrons
    chevron_max_width: float = 2.5           # Maximum width of chevrons
    chevron_overlap: float = 0.15            # How much chevrons overlap
    arrow_point_ratio: float = 0.15          # Size of arrow point as ratio of width


# =============================================================================
# CHEVRON ARCHETYPE
# =============================================================================

class ChevronArchetype(BaseArchetype):
    """
    Chevron Process diagram archetype.

    Creates horizontal chevron layouts where:
    - Chevron/arrow shapes connect in sequence
    - Each chevron represents a phase or stage
    - Visual momentum from left to right
    - Great for process phases and stages
    """

    name = "chevron_process"
    display_name = "Chevron Process"
    description = "Connected chevron arrows showing process stages"
    example_prompts = [
        "Sales pipeline: Lead → Qualify → Propose → Close",
        "Project phases from initiation to closure",
        "Customer journey touchpoints",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[ChevronConfig] = None
    ):
        super().__init__(palette)
        self.config = config or ChevronConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a chevron layout from input data."""
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

        # Create chevron elements
        elements = self._create_chevrons(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _create_chevrons(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create the chevron elements."""
        elements = []
        num_chevrons = len(blocks)

        if num_chevrons == 0:
            return elements

        # Calculate chevron dimensions
        # Account for overlap
        total_overlap = self.config.chevron_overlap * (num_chevrons - 1)
        available_width = CONTENT_WIDTH + total_overlap
        chevron_width = available_width / num_chevrons
        chevron_width = max(self.config.chevron_min_width,
                           min(self.config.chevron_max_width, chevron_width))

        # Recalculate total width
        total_width = chevron_width * num_chevrons - total_overlap
        start_x = CONTENT_LEFT + (CONTENT_WIDTH - total_width) / 2

        # Center vertically
        y = content_top + (content_height - self.config.chevron_height) / 2

        # Create chevron elements
        for i, block in enumerate(blocks):
            x = start_x + i * (chevron_width - self.config.chevron_overlap)

            element = self._create_chevron_element(
                block,
                x,
                y,
                chevron_width,
                i,
                num_chevrons
            )
            elements.append(element)

        return elements

    def _create_chevron_element(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        chevron_idx: int,
        total_chevrons: int
    ) -> PositionedElement:
        """Create a single chevron element."""
        fill_color = block.color or self.palette.get_color_for_index(chevron_idx)

        # Fit text (leave room for arrow point)
        text_width = width * (1 - self.config.arrow_point_ratio * 2)
        fit_result = fit_text_to_width(
            block.label,
            text_width - 0.2,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=12,
            min_font_size=9,
            bold=True,
            allow_wrap=True,
            max_lines=2
        )

        text_color = self._contrast_text_color(fill_color)

        chevron_text = PositionedText(
            content=block.label,
            lines=fit_result.lines,
            font_size_pt=fit_result.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            color=text_color,
            alignment=TextAlignment.CENTER
        )

        # Use a block element (actual chevron shape would need SVG path)
        # For now, use a slightly pointed rectangle effect via corner radius
        return PositionedElement(
            id=block.id,
            element_type=ElementType.BLOCK,
            x_inches=x,
            y_inches=y,
            width_inches=width,
            height_inches=self.config.chevron_height,
            fill_color=fill_color,
            stroke_color=self.palette.border,
            stroke_width_pt=1.0,
            corner_radius_inches=0.1,  # Slight rounding
            text=chevron_text,
            z_order=total_chevrons - chevron_idx  # Earlier chevrons on top
        )

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for chevron layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 2:
            errors.append("Chevron process requires at least 2 stages")

        if len(input_data.blocks) > 7:
            errors.append("Too many stages for chevron process (max 7)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_chevron(
    title: str,
    stages: List[str],
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a chevron process diagram.

    Args:
        title: Diagram title
        stages: List of stage labels in order
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_chevron(
            title="Sales Pipeline",
            stages=["Lead", "Qualify", "Propose", "Negotiate", "Close"]
        )
    """
    blocks = [
        BlockData(id=f"stage_{i}", label=stage)
        for i, stage in enumerate(stages)
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    archetype = ChevronArchetype()
    return archetype.generate_layout(input_data)
