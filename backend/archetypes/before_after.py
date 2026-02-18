"""
before_after.py — Before/After Comparison Archetype.

Side-by-side comparison showing transformation:
- Two panels: Before (left) and After (right)
- Great for showing improvements, changes, transformations
- Clear visual contrast between states
- Can include bullet points in each panel

Example prompts:
- "Before and after our solution"
- "Current state vs future state"
- "Problem vs solution comparison"
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
    ConnectorStyle,
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
# BEFORE/AFTER CONFIGURATION
# =============================================================================

@dataclass
class BeforeAfterConfig:
    """Configuration options for before/after layout."""
    panel_gap: float = 0.4                    # Gap between panels
    header_height: float = 0.5                # Height of panel headers
    panel_padding: float = 0.2                # Padding inside panels
    corner_radius: float = 0.1                # Panel corner radius
    show_arrow: bool = True                   # Show arrow between panels
    before_color: str = "#E57373"             # Red-ish for "before" (problem)
    after_color: str = "#81C784"              # Green-ish for "after" (solution)


# =============================================================================
# BEFORE/AFTER ARCHETYPE
# =============================================================================

class BeforeAfterArchetype(BaseArchetype):
    """
    Before/After Comparison diagram archetype.

    Creates side-by-side comparison where:
    - Left panel shows "Before" state
    - Right panel shows "After" state
    - Optional arrow connecting them
    - Great for transformations, improvements
    """

    name = "before_after"
    display_name = "Before / After"
    description = "Side-by-side comparison showing transformation"
    example_prompts = [
        "Before and after comparison",
        "Current vs future state",
        "Problem and solution",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[BeforeAfterConfig] = None
    ):
        super().__init__(palette)
        self.config = config or BeforeAfterConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a before/after layout from input data."""
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

        # Create before/after elements
        elements, connectors = self._create_before_after(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)
        layout.connectors.extend(connectors)

        return layout

    def _create_before_after(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> Tuple[List[PositionedElement], List[PositionedConnector]]:
        """Create the before/after panel elements."""
        elements = []
        connectors = []

        # Calculate panel dimensions
        arrow_space = 0.5 if self.config.show_arrow else 0
        panel_width = (CONTENT_WIDTH - self.config.panel_gap - arrow_space) / 2

        # Get before and after data
        before_block = blocks[0] if len(blocks) > 0 else BlockData(id="before", label="Before")
        after_block = blocks[1] if len(blocks) > 1 else BlockData(id="after", label="After")

        # Before panel (left)
        before_x = CONTENT_LEFT
        before_elements = self._create_panel(
            before_block,
            before_x,
            content_top,
            panel_width,
            content_height,
            self.config.before_color,
            "before",
            0
        )
        elements.extend(before_elements)

        # After panel (right)
        after_x = CONTENT_LEFT + panel_width + self.config.panel_gap + arrow_space
        after_elements = self._create_panel(
            after_block,
            after_x,
            content_top,
            panel_width,
            content_height,
            self.config.after_color,
            "after",
            1
        )
        elements.extend(after_elements)

        # Arrow between panels
        if self.config.show_arrow:
            arrow_x = CONTENT_LEFT + panel_width + self.config.panel_gap / 2
            arrow_y = content_top + content_height / 2

            connector = PositionedConnector(
                id="before_after_arrow",
                from_element_id=before_block.id,
                to_element_id=after_block.id,
                start_x=arrow_x,
                start_y=arrow_y,
                end_x=arrow_x + arrow_space,
                end_y=arrow_y,
                style=ConnectorStyle.ARROW,
                color=self.palette.connector,
                stroke_width_pt=3.0
            )
            connectors.append(connector)

        return elements, connectors

    def _create_panel(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        height: float,
        color: str,
        panel_type: str,
        panel_idx: int
    ) -> List[PositionedElement]:
        """Create a single before/after panel."""
        elements = []
        padding = self.config.panel_padding

        # Panel background
        bg_element = PositionedElement(
            id=f"{block.id}_bg",
            element_type=ElementType.BLOCK,
            x_inches=x,
            y_inches=y,
            width_inches=width,
            height_inches=height,
            fill_color=color,
            stroke_color=None,
            stroke_width_pt=0,
            corner_radius_inches=self.config.corner_radius,
            opacity=0.15,
            z_order=5 + panel_idx
        )
        elements.append(bg_element)

        # Panel border
        border_element = PositionedElement(
            id=f"{block.id}_border",
            element_type=ElementType.BLOCK,
            x_inches=x,
            y_inches=y,
            width_inches=width,
            height_inches=height,
            fill_color=None,
            stroke_color=color,
            stroke_width_pt=2.0,
            corner_radius_inches=self.config.corner_radius,
            z_order=6 + panel_idx
        )
        elements.append(border_element)

        # Header
        header_fit = fit_text_to_width(
            block.label,
            width - padding * 2,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=16,
            min_font_size=12,
            bold=True,
            allow_wrap=False,
            max_lines=1
        )

        header_text = PositionedText(
            content=block.label,
            lines=header_fit.lines,
            font_size_pt=header_fit.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            color=color,
            alignment=TextAlignment.CENTER
        )

        header_element = PositionedElement(
            id=f"{block.id}_header",
            element_type=ElementType.TEXT_BOX,
            x_inches=x + padding,
            y_inches=y + padding,
            width_inches=width - padding * 2,
            height_inches=self.config.header_height,
            fill_color=None,
            stroke_color=None,
            stroke_width_pt=0,
            text=header_text,
            z_order=10 + panel_idx
        )
        elements.append(header_element)

        # Content
        if block.description:
            content_y = y + self.config.header_height + padding * 1.5
            content_height = height - self.config.header_height - padding * 3

            content_fit = fit_text_to_width(
                block.description,
                width - padding * 2,
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=11,
                min_font_size=9,
                bold=False,
                allow_wrap=True,
                max_lines=8
            )

            content_text = PositionedText(
                content=block.description,
                lines=content_fit.lines,
                font_size_pt=content_fit.font_size,
                font_family=DEFAULT_FONT_FAMILY,
                bold=False,
                color=self.palette.text_dark,
                alignment=TextAlignment.LEFT
            )

            content_element = PositionedElement(
                id=f"{block.id}_content",
                element_type=ElementType.TEXT_BOX,
                x_inches=x + padding,
                y_inches=content_y,
                width_inches=width - padding * 2,
                height_inches=content_height,
                fill_color=None,
                stroke_color=None,
                stroke_width_pt=0,
                text=content_text,
                z_order=11 + panel_idx
            )
            elements.append(content_element)

        return elements

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for before/after layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 2:
            errors.append("Before/After comparison requires exactly 2 items")

        if len(input_data.blocks) > 2:
            errors.append("Before/After comparison has exactly 2 panels")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_before_after(
    title: str,
    before_label: str,
    after_label: str,
    before_content: str = "",
    after_content: str = "",
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a before/after comparison diagram.

    Args:
        title: Diagram title
        before_label: Header for the "before" panel
        after_label: Header for the "after" panel
        before_content: Bullet points or description for before
        after_content: Bullet points or description for after
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_before_after(
            title="Digital Transformation",
            before_label="Current State",
            after_label="Future State",
            before_content="Manual processes\\nSiloed data\\nSlow decisions",
            after_content="Automated workflows\\nUnified platform\\nReal-time insights"
        )
    """
    blocks = [
        BlockData(id="before", label=before_label, description=before_content),
        BlockData(id="after", label=after_label, description=after_content),
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    archetype = BeforeAfterArchetype()
    return archetype.generate_layout(input_data)
