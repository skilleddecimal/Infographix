"""
roadmap.py — Roadmap Archetype.

Horizontal roadmap showing phases over time:
- Timeline-based view of milestones
- Great for project plans, product roadmaps
- Shows phases with dates or quarters
- Visual progression from now to future

Example prompts:
- "Product roadmap for next year"
- "Project phases and milestones"
- "Q1 to Q4 plan"
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
# ROADMAP CONFIGURATION
# =============================================================================

@dataclass
class RoadmapConfig:
    """Configuration options for roadmap layout."""
    lane_height: float = 0.8                  # Height of each phase lane
    phase_gap: float = 0.15                   # Gap between phases
    timeline_height: float = 0.4              # Height of timeline header
    corner_radius: float = 0.08               # Phase corner radius
    show_now_marker: bool = True              # Show "Now" marker


# =============================================================================
# ROADMAP ARCHETYPE
# =============================================================================

class RoadmapArchetype(BaseArchetype):
    """
    Roadmap diagram archetype.

    Creates horizontal roadmap layouts where:
    - Phases arranged horizontally over time
    - Each phase shows what happens in that period
    - Timeline header shows time periods
    - Great for project and product roadmaps
    """

    name = "roadmap"
    display_name = "Roadmap"
    description = "Timeline-based roadmap with phases"
    example_prompts = [
        "Product roadmap",
        "Project plan phases",
        "Quarterly goals",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[RoadmapConfig] = None
    ):
        super().__init__(palette)
        self.config = config or RoadmapConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a roadmap layout from input data."""
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

        # Create roadmap elements
        elements = self._create_roadmap(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _create_roadmap(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create the roadmap elements."""
        elements = []
        num_phases = len(blocks)

        if num_phases == 0:
            return elements

        # Calculate dimensions
        phase_width = (CONTENT_WIDTH - (num_phases - 1) * self.config.phase_gap) / num_phases
        timeline_y = content_top
        phases_y = content_top + self.config.timeline_height + 0.2

        # Timeline background
        timeline_bg = PositionedElement(
            id="timeline_bg",
            element_type=ElementType.BLOCK,
            x_inches=CONTENT_LEFT,
            y_inches=timeline_y,
            width_inches=CONTENT_WIDTH,
            height_inches=self.config.timeline_height,
            fill_color=self.palette.primary,
            stroke_color=None,
            stroke_width_pt=0,
            corner_radius_inches=self.config.corner_radius,
            opacity=0.1,
            z_order=1
        )
        elements.append(timeline_bg)

        # Create phases
        for i, block in enumerate(blocks):
            x = CONTENT_LEFT + i * (phase_width + self.config.phase_gap)

            # Timeline header for this phase
            header_elements = self._create_phase_header(
                block,
                x,
                timeline_y,
                phase_width,
                i
            )
            elements.extend(header_elements)

            # Phase content
            phase_elements = self._create_phase_content(
                block,
                x,
                phases_y,
                phase_width,
                content_height - self.config.timeline_height - 0.4,
                i
            )
            elements.extend(phase_elements)

        # "Now" marker (optional)
        if self.config.show_now_marker and num_phases > 1:
            marker = self._create_now_marker(
                CONTENT_LEFT + phase_width / 2,
                content_top,
                content_height
            )
            elements.extend(marker)

        return elements

    def _create_phase_header(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        phase_idx: int
    ) -> List[PositionedElement]:
        """Create the timeline header for a phase."""
        elements = []

        # Use layer_id as time label if provided, otherwise use index
        time_label = block.layer_id or f"Phase {phase_idx + 1}"

        fit_result = fit_text_to_width(
            time_label,
            width - 0.1,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=10,
            min_font_size=8,
            bold=True,
            allow_wrap=False,
            max_lines=1
        )

        header_text = PositionedText(
            content=time_label,
            lines=fit_result.lines,
            font_size_pt=fit_result.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            color=self.palette.primary,
            alignment=TextAlignment.CENTER
        )

        header_element = PositionedElement(
            id=f"{block.id}_header",
            element_type=ElementType.TEXT_BOX,
            x_inches=x,
            y_inches=y + 0.1,
            width_inches=width,
            height_inches=self.config.timeline_height - 0.2,
            fill_color=None,
            stroke_color=None,
            stroke_width_pt=0,
            text=header_text,
            z_order=5 + phase_idx
        )
        elements.append(header_element)

        return elements

    def _create_phase_content(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        height: float,
        phase_idx: int
    ) -> List[PositionedElement]:
        """Create the content area for a phase."""
        elements = []

        fill_color = block.color or self.palette.get_color_for_index(phase_idx)

        # Phase background
        bg_element = PositionedElement(
            id=f"{block.id}_bg",
            element_type=ElementType.BLOCK,
            x_inches=x,
            y_inches=y,
            width_inches=width,
            height_inches=height,
            fill_color=fill_color,
            stroke_color=None,
            stroke_width_pt=0,
            corner_radius_inches=self.config.corner_radius,
            opacity=0.2,
            z_order=10 + phase_idx
        )
        elements.append(bg_element)

        # Phase title
        fit_result = fit_text_to_width(
            block.label,
            width - 0.2,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=11,
            min_font_size=8,
            bold=True,
            allow_wrap=True,
            max_lines=2
        )

        title_text = PositionedText(
            content=block.label,
            lines=fit_result.lines,
            font_size_pt=fit_result.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            color=fill_color,
            alignment=TextAlignment.CENTER
        )

        title_element = PositionedElement(
            id=f"{block.id}_title",
            element_type=ElementType.TEXT_BOX,
            x_inches=x + 0.1,
            y_inches=y + 0.15,
            width_inches=width - 0.2,
            height_inches=0.5,
            fill_color=None,
            stroke_color=None,
            stroke_width_pt=0,
            text=title_text,
            z_order=15 + phase_idx
        )
        elements.append(title_element)

        # Phase description
        if block.description:
            desc_fit = fit_text_to_width(
                block.description,
                width - 0.2,
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=9,
                min_font_size=7,
                bold=False,
                allow_wrap=True,
                max_lines=4
            )

            desc_text = PositionedText(
                content=block.description,
                lines=desc_fit.lines,
                font_size_pt=desc_fit.font_size,
                font_family=DEFAULT_FONT_FAMILY,
                bold=False,
                color=self.palette.text_dark,
                alignment=TextAlignment.LEFT
            )

            desc_element = PositionedElement(
                id=f"{block.id}_desc",
                element_type=ElementType.TEXT_BOX,
                x_inches=x + 0.1,
                y_inches=y + 0.65,
                width_inches=width - 0.2,
                height_inches=height - 0.8,
                fill_color=None,
                stroke_color=None,
                stroke_width_pt=0,
                text=desc_text,
                z_order=16 + phase_idx
            )
            elements.append(desc_element)

        return elements

    def _create_now_marker(
        self,
        x: float,
        y: float,
        height: float
    ) -> List[PositionedElement]:
        """Create the 'Now' marker."""
        elements = []

        # Vertical line
        line = PositionedElement(
            id="now_line",
            element_type=ElementType.BLOCK,
            x_inches=x - 0.02,
            y_inches=y - 0.1,
            width_inches=0.04,
            height_inches=height + 0.2,
            fill_color=self.palette.primary,
            stroke_color=None,
            stroke_width_pt=0,
            corner_radius_inches=0.02,
            z_order=50
        )
        elements.append(line)

        return elements

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for roadmap layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 2:
            errors.append("Roadmap requires at least 2 phases")

        if len(input_data.blocks) > 6:
            errors.append("Too many phases for roadmap (max 6)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_roadmap(
    title: str,
    phases: List[Dict[str, str]],
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a roadmap diagram.

    Args:
        title: Diagram title
        phases: List of dicts with 'label', optional 'description' and 'time'
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_roadmap(
            title="Product Roadmap 2024",
            phases=[
                {"label": "Foundation", "time": "Q1", "description": "Core features"},
                {"label": "Growth", "time": "Q2", "description": "Scale up"},
                {"label": "Expansion", "time": "Q3-Q4", "description": "New markets"},
            ]
        )
    """
    blocks = [
        BlockData(
            id=f"phase_{i}",
            label=phase.get("label", ""),
            description=phase.get("description"),
            layer_id=phase.get("time")
        )
        for i, phase in enumerate(phases)
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    archetype = RoadmapArchetype()
    return archetype.generate_layout(input_data)
