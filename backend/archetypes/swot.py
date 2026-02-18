"""
swot.py — SWOT Analysis Archetype.

Classic SWOT analysis diagram:
- 2x2 grid: Strengths, Weaknesses, Opportunities, Threats
- Color-coded quadrants (positive/negative, internal/external)
- Pre-configured labels and colors
- Great for strategic analysis

Example prompts:
- "SWOT analysis for our product"
- "Strategic analysis"
- "Strengths weaknesses opportunities threats"
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
    GUTTER_V,
    DEFAULT_FONT_FAMILY,
)
from ..engine.text_measure import fit_text_to_width


# =============================================================================
# SWOT CONFIGURATION
# =============================================================================

# Default SWOT colors (positive=green/blue, negative=red/orange)
SWOT_COLORS = {
    "strengths": "#4CAF50",      # Green - positive internal
    "weaknesses": "#F44336",     # Red - negative internal
    "opportunities": "#2196F3",  # Blue - positive external
    "threats": "#FF9800",        # Orange - negative external
}

SWOT_LABELS = ["Strengths", "Weaknesses", "Opportunities", "Threats"]


@dataclass
class SWOTConfig:
    """Configuration options for SWOT layout."""
    quadrant_padding: float = 0.2             # Padding inside quadrants
    header_height: float = 0.4                # Height of quadrant headers
    gap: float = 0.1                          # Gap between quadrants
    corner_radius: float = 0.1                # Quadrant corner radius
    show_axis_labels: bool = True             # Show Internal/External, Positive/Negative labels


# =============================================================================
# SWOT ARCHETYPE
# =============================================================================

class SWOTArchetype(BaseArchetype):
    """
    SWOT Analysis diagram archetype.

    Creates a 2x2 SWOT matrix where:
    - Top-left: Strengths (positive, internal)
    - Top-right: Weaknesses (negative, internal)
    - Bottom-left: Opportunities (positive, external)
    - Bottom-right: Threats (negative, external)
    """

    name = "swot"
    display_name = "SWOT Analysis"
    description = "Strengths, Weaknesses, Opportunities, Threats matrix"
    example_prompts = [
        "SWOT analysis",
        "Strategic SWOT diagram",
        "Strengths and weaknesses analysis",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[SWOTConfig] = None
    ):
        super().__init__(palette)
        self.config = config or SWOTConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a SWOT layout from input data."""
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

        # Create SWOT elements
        elements = self._create_swot_grid(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _create_swot_grid(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create the SWOT grid elements."""
        elements = []

        # Calculate quadrant dimensions
        quadrant_width = (CONTENT_WIDTH - self.config.gap) / 2
        quadrant_height = (content_height - self.config.gap) / 2

        # SWOT positions: [S, W, O, T] in reading order
        positions = [
            (0, 0),  # Strengths - top left
            (1, 0),  # Weaknesses - top right
            (0, 1),  # Opportunities - bottom left
            (1, 1),  # Threats - bottom right
        ]

        # Ensure we have 4 blocks, use defaults if not provided
        swot_blocks = []
        for i in range(4):
            if i < len(blocks):
                swot_blocks.append(blocks[i])
            else:
                swot_blocks.append(BlockData(
                    id=f"swot_{i}",
                    label=SWOT_LABELS[i],
                    description=""
                ))

        # Create quadrants
        for i, (col, row) in enumerate(positions):
            x = CONTENT_LEFT + col * (quadrant_width + self.config.gap)
            y = content_top + row * (quadrant_height + self.config.gap)

            block = swot_blocks[i]
            swot_type = SWOT_LABELS[i].lower()
            color = block.color or SWOT_COLORS[swot_type]

            quadrant_elements = self._create_quadrant(
                block,
                x,
                y,
                quadrant_width,
                quadrant_height,
                SWOT_LABELS[i],
                color,
                i
            )
            elements.extend(quadrant_elements)

        # Add axis labels if configured
        if self.config.show_axis_labels:
            axis_elements = self._create_axis_labels(
                content_top,
                content_height,
                quadrant_width,
                quadrant_height
            )
            elements.extend(axis_elements)

        return elements

    def _create_quadrant(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        height: float,
        header_label: str,
        color: str,
        quadrant_idx: int
    ) -> List[PositionedElement]:
        """Create a single SWOT quadrant."""
        elements = []
        padding = self.config.quadrant_padding

        # Quadrant background
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
            z_order=5 + quadrant_idx
        )
        elements.append(bg_element)

        # Header
        header_fit = fit_text_to_width(
            header_label,
            width - padding * 2,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=14,
            min_font_size=11,
            bold=True,
            allow_wrap=False,
            max_lines=1
        )

        header_text = PositionedText(
            content=header_label,
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
            y_inches=y + padding * 0.5,
            width_inches=width - padding * 2,
            height_inches=self.config.header_height,
            fill_color=None,
            stroke_color=None,
            stroke_width_pt=0,
            text=header_text,
            z_order=10 + quadrant_idx
        )
        elements.append(header_element)

        # Content (bullet points if description provided)
        if block.description:
            content_y = y + self.config.header_height + padding
            content_height = height - self.config.header_height - padding * 2

            content_fit = fit_text_to_width(
                block.description,
                width - padding * 2,
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=10,
                min_font_size=8,
                bold=False,
                allow_wrap=True,
                max_lines=6
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
                z_order=11 + quadrant_idx
            )
            elements.append(content_element)

        return elements

    def _create_axis_labels(
        self,
        content_top: float,
        content_height: float,
        quadrant_width: float,
        quadrant_height: float
    ) -> List[PositionedElement]:
        """Create axis labels (Internal/External, Positive/Negative)."""
        elements = []

        # These are subtle labels, so we'll skip them for now
        # to keep the diagram clean. Can be added later if needed.

        return elements

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for SWOT layout."""
        errors = super().validate_input(input_data)

        # SWOT always has exactly 4 quadrants (we fill defaults if needed)
        if len(input_data.blocks) > 4:
            errors.append("SWOT analysis has exactly 4 quadrants")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_swot(
    title: str,
    strengths: str = "",
    weaknesses: str = "",
    opportunities: str = "",
    threats: str = "",
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a SWOT analysis diagram.

    Args:
        title: Diagram title
        strengths: Bullet points for Strengths quadrant
        weaknesses: Bullet points for Weaknesses quadrant
        opportunities: Bullet points for Opportunities quadrant
        threats: Bullet points for Threats quadrant
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_swot(
            title="Product SWOT Analysis",
            strengths="Strong brand\\nLoyal customers\\nPatented tech",
            weaknesses="High costs\\nLimited reach",
            opportunities="New markets\\nPartnerships",
            threats="Competition\\nRegulation"
        )
    """
    blocks = [
        BlockData(id="strengths", label="Strengths", description=strengths),
        BlockData(id="weaknesses", label="Weaknesses", description=weaknesses),
        BlockData(id="opportunities", label="Opportunities", description=opportunities),
        BlockData(id="threats", label="Threats", description=threats),
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    archetype = SWOTArchetype()
    return archetype.generate_layout(input_data)
