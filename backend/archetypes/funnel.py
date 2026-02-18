"""
funnel.py — Funnel / Conversion Archetype.

Funnel diagrams showing narrowing stages:
- Wide at top, narrow at bottom
- Shows filtering/conversion through stages
- Often used for sales funnels, recruitment pipelines
- Can include metrics/percentages

Example prompts:
- "Sales funnel from leads to customers"
- "Marketing funnel TOFU MOFU BOFU"
- "Recruitment pipeline from applicants to hires"
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
    GUTTER_V,
    DEFAULT_FONT_FAMILY,
)
from ..engine.text_measure import fit_text_to_width


# =============================================================================
# FUNNEL CONFIGURATION
# =============================================================================

@dataclass
class FunnelConfig:
    """Configuration options for funnel layout."""
    stage_gutter: float = GUTTER_V * 0.3     # Small gap between stages
    top_width_ratio: float = 0.9              # Top width as ratio of content width
    bottom_width_ratio: float = 0.25          # Bottom width as ratio of content width
    min_stage_height: float = 0.5             # Minimum height for each stage
    max_stage_height: float = 1.0             # Maximum height for each stage
    show_percentages: bool = False            # Show conversion percentages
    curved_sides: bool = True                 # Use curved sides for funnel effect
    color_gradient: bool = True               # Gradient colors from top to bottom


# =============================================================================
# FUNNEL ARCHETYPE
# =============================================================================

class FunnelArchetype(BaseArchetype):
    """
    Funnel diagram archetype.

    Creates funnel layouts where:
    - Stages narrow from top to bottom
    - Each stage represents a filtering/conversion step
    - Visually shows volume decrease through stages
    - Colors typically progress from cool (top) to warm (bottom)
    """

    name = "funnel"
    display_name = "Funnel / Conversion"
    description = "Narrowing stages showing filtering or conversion"
    example_prompts = [
        "Sales funnel: Awareness → Interest → Decision → Action",
        "Recruitment funnel from applications to hires",
        "Marketing funnel TOFU MOFU BOFU",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[FunnelConfig] = None
    ):
        super().__init__(palette)
        self.config = config or FunnelConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a funnel layout from input data."""
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

        # Create funnel stages
        elements = self._create_funnel_stages(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _create_funnel_stages(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create the funnel stage elements."""
        elements = []

        if not blocks:
            return elements

        num_stages = len(blocks)

        # Calculate stage heights
        total_gutter = self.config.stage_gutter * (num_stages - 1)
        available_height = content_height - total_gutter
        stage_height = available_height / num_stages
        stage_height = max(self.config.min_stage_height,
                          min(self.config.max_stage_height, stage_height))

        # Recalculate total height
        total_height = stage_height * num_stages + total_gutter
        start_y = content_top + (content_height - total_height) / 2

        # Width progression from top to bottom
        top_width = CONTENT_WIDTH * self.config.top_width_ratio
        bottom_width = CONTENT_WIDTH * self.config.bottom_width_ratio

        if num_stages > 1:
            width_step = (top_width - bottom_width) / (num_stages - 1)
        else:
            width_step = 0

        # Create stages from top to bottom
        for i, block in enumerate(blocks):
            y = start_y + i * (stage_height + self.config.stage_gutter)
            stage_width = top_width - (i * width_step)

            # Center horizontally
            x = CONTENT_LEFT + (CONTENT_WIDTH - stage_width) / 2

            # Create stage element
            element = self._create_stage_element(
                block,
                x,
                y,
                stage_width,
                stage_height,
                i,
                num_stages
            )
            elements.append(element)

        return elements

    def _create_stage_element(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        height: float,
        stage_idx: int,
        total_stages: int
    ) -> PositionedElement:
        """Create a single funnel stage element."""
        # Color progression for funnel effect
        if self.config.color_gradient:
            # Use palette colors in order
            fill_color = block.color or self.palette.get_color_for_index(stage_idx)
        else:
            fill_color = block.color or self.palette.primary

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

        # Build display text (optionally include description as metric)
        display_lines = fit_result.lines
        if block.description and self.config.show_percentages:
            # Add description as second line (e.g., "100%" or "1000 leads")
            display_lines = display_lines + [block.description]

        stage_text = PositionedText(
            content=block.label,
            lines=display_lines,
            font_size_pt=fit_result.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            color=text_color,
            alignment=TextAlignment.CENTER
        )

        # Trapezoid-like shape effect through slight corner rounding
        corner_radius = 0.06 if not self.config.curved_sides else 0.15

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
            corner_radius_inches=corner_radius,
            text=stage_text,
            z_order=10 - stage_idx  # Top stages on top visually
        )

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for funnel layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 2:
            errors.append("Funnel requires at least 2 stages")

        if len(input_data.blocks) > 8:
            errors.append("Too many stages for funnel (max 8)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_funnel(
    title: str,
    stages: List[str],
    subtitle: Optional[str] = None,
    percentages: Optional[List[str]] = None
) -> PositionedLayout:
    """
    Quick helper to create a funnel diagram.

    Args:
        title: Diagram title
        stages: List of stage labels from top to bottom
        subtitle: Optional subtitle
        percentages: Optional list of percentages/metrics for each stage

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_funnel(
            title="Sales Funnel",
            stages=["Awareness", "Interest", "Decision", "Action"],
            percentages=["100%", "60%", "30%", "10%"]
        )
    """
    blocks = []
    for i, stage in enumerate(stages):
        desc = percentages[i] if percentages and i < len(percentages) else None
        blocks.append(BlockData(
            id=f"stage_{i}",
            label=stage,
            description=desc
        ))

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    config = FunnelConfig(
        show_percentages=percentages is not None
    )

    archetype = FunnelArchetype(config=config)
    return archetype.generate_layout(input_data)
