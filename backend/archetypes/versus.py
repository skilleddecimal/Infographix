"""
versus.py — Versus / VS Comparison Archetype.

Head-to-head comparison between two options:
- Two sides with "VS" in the middle
- Great for product comparisons, competitive analysis
- Clear visual distinction between options
- Can include feature lists for each

Example prompts:
- "Product A vs Product B comparison"
- "Old way vs new way"
- "Option 1 versus Option 2"
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
# VERSUS CONFIGURATION
# =============================================================================

@dataclass
class VersusConfig:
    """Configuration options for versus layout."""
    vs_circle_size: float = 0.8               # Size of the VS circle
    panel_padding: float = 0.2                # Padding inside panels
    header_height: float = 0.6                # Height of option headers
    corner_radius: float = 0.12               # Panel corner radius
    left_color: str = "#2196F3"               # Blue for left option
    right_color: str = "#F44336"              # Red for right option


# =============================================================================
# VERSUS ARCHETYPE
# =============================================================================

class VersusArchetype(BaseArchetype):
    """
    Versus Comparison diagram archetype.

    Creates head-to-head comparison where:
    - Left panel shows option A
    - Right panel shows option B
    - VS badge in the center
    - Great for competitive comparisons
    """

    name = "versus"
    display_name = "Versus / VS"
    description = "Head-to-head comparison with VS badge"
    example_prompts = [
        "Product A vs Product B",
        "Old approach vs new approach",
        "Option comparison",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[VersusConfig] = None
    ):
        super().__init__(palette)
        self.config = config or VersusConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a versus layout from input data."""
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

        # Create versus elements
        elements = self._create_versus(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _create_versus(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create the versus panel elements."""
        elements = []

        # Calculate dimensions
        vs_space = self.config.vs_circle_size + 0.2
        panel_width = (CONTENT_WIDTH - vs_space) / 2

        # Get left and right data
        left_block = blocks[0] if len(blocks) > 0 else BlockData(id="left", label="Option A")
        right_block = blocks[1] if len(blocks) > 1 else BlockData(id="right", label="Option B")

        # Left panel
        left_x = CONTENT_LEFT
        left_elements = self._create_panel(
            left_block,
            left_x,
            content_top,
            panel_width,
            content_height,
            self.config.left_color,
            "left",
            0
        )
        elements.extend(left_elements)

        # Right panel
        right_x = CONTENT_LEFT + panel_width + vs_space
        right_elements = self._create_panel(
            right_block,
            right_x,
            content_top,
            panel_width,
            content_height,
            self.config.right_color,
            "right",
            1
        )
        elements.extend(right_elements)

        # VS badge
        vs_elements = self._create_vs_badge(
            CONTENT_LEFT + panel_width + vs_space / 2,
            content_top + content_height / 2
        )
        elements.extend(vs_elements)

        return elements

    def _create_panel(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        height: float,
        color: str,
        side: str,
        panel_idx: int
    ) -> List[PositionedElement]:
        """Create a single versus panel."""
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
            opacity=0.12,
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
            stroke_width_pt=2.5,
            corner_radius_inches=self.config.corner_radius,
            z_order=6 + panel_idx
        )
        elements.append(border_element)

        # Header
        header_fit = fit_text_to_width(
            block.label,
            width - padding * 2,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=18,
            min_font_size=12,
            bold=True,
            allow_wrap=True,
            max_lines=2
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

        # Content (features/description)
        if block.description:
            content_y = y + self.config.header_height + padding * 1.5
            content_height_avail = height - self.config.header_height - padding * 3

            content_fit = fit_text_to_width(
                block.description,
                width - padding * 2,
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=11,
                min_font_size=9,
                bold=False,
                allow_wrap=True,
                max_lines=10
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
                height_inches=content_height_avail,
                fill_color=None,
                stroke_color=None,
                stroke_width_pt=0,
                text=content_text,
                z_order=11 + panel_idx
            )
            elements.append(content_element)

        return elements

    def _create_vs_badge(
        self,
        center_x: float,
        center_y: float
    ) -> List[PositionedElement]:
        """Create the VS badge."""
        elements = []

        size = self.config.vs_circle_size

        # Circle background
        circle = PositionedElement(
            id="vs_circle",
            element_type=ElementType.ELLIPSE,
            x_inches=center_x - size / 2,
            y_inches=center_y - size / 2,
            width_inches=size,
            height_inches=size,
            fill_color="#333333",
            stroke_color="#FFFFFF",
            stroke_width_pt=3.0,
            z_order=20
        )
        elements.append(circle)

        # VS text
        vs_text = PositionedText(
            content="VS",
            lines=["VS"],
            font_size_pt=18,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            color="#FFFFFF",
            alignment=TextAlignment.CENTER
        )

        vs_text_element = PositionedElement(
            id="vs_text",
            element_type=ElementType.TEXT_BOX,
            x_inches=center_x - size / 2,
            y_inches=center_y - 0.2,
            width_inches=size,
            height_inches=0.4,
            fill_color=None,
            stroke_color=None,
            stroke_width_pt=0,
            text=vs_text,
            z_order=21
        )
        elements.append(vs_text_element)

        return elements

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for versus layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 2:
            errors.append("Versus comparison requires exactly 2 options")

        if len(input_data.blocks) > 2:
            errors.append("Versus comparison has exactly 2 sides")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_versus(
    title: str,
    option_a: str,
    option_b: str,
    features_a: str = "",
    features_b: str = "",
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a versus comparison diagram.

    Args:
        title: Diagram title
        option_a: Label for left option
        option_b: Label for right option
        features_a: Features/content for left option
        features_b: Features/content for right option
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_versus(
            title="Solution Comparison",
            option_a="Cloud Hosted",
            option_b="On-Premise",
            features_a="Scalable\\nManaged updates\\nLower upfront cost",
            features_b="Full control\\nData sovereignty\\nOne-time cost"
        )
    """
    blocks = [
        BlockData(id="option_a", label=option_a, description=features_a),
        BlockData(id="option_b", label=option_b, description=features_b),
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    archetype = VersusArchetype()
    return archetype.generate_layout(input_data)
