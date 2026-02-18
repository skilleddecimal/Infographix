"""
target.py — Target / Bullseye Archetype.

Concentric circle diagrams showing layers of focus:
- Concentric rings from outside to center
- Center represents core/priority
- Outer rings represent peripheral items
- Great for priority, focus, or containment

Example prompts:
- "Target customer segments"
- "Core vs peripheral features"
- "Priority focus areas"
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
    DEFAULT_FONT_FAMILY,
)
from ..engine.text_measure import fit_text_to_width


# =============================================================================
# TARGET CONFIGURATION
# =============================================================================

@dataclass
class TargetConfig:
    """Configuration options for target layout."""
    outer_radius_ratio: float = 0.45         # Outer ring as ratio of content area
    center_radius_ratio: float = 0.15        # Center circle as ratio of content area
    ring_opacity: float = 0.85               # Opacity of rings
    show_ring_labels: bool = True            # Show labels on rings


# =============================================================================
# TARGET ARCHETYPE
# =============================================================================

class TargetArchetype(BaseArchetype):
    """
    Target / Bullseye diagram archetype.

    Creates concentric circle layouts where:
    - Rings represent layers from outside to center
    - Center is the core/priority/focus
    - Outer rings are peripheral/supporting
    - Visually emphasizes the center
    """

    name = "target"
    display_name = "Target / Bullseye"
    description = "Concentric circles showing layers from outside to center"
    example_prompts = [
        "Target market segments",
        "Core vs extended features",
        "Priority focus bullseye",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[TargetConfig] = None
    ):
        super().__init__(palette)
        self.config = config or TargetConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a target layout from input data."""
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

        # Create target rings
        elements = self._create_target_rings(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _create_target_rings(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create the target ring elements."""
        elements = []
        num_rings = len(blocks)

        if num_rings == 0:
            return elements

        # Calculate center
        center_x = CONTENT_LEFT + CONTENT_WIDTH / 2
        center_y = content_top + content_height / 2

        # Calculate radii
        min_dimension = min(CONTENT_WIDTH, content_height)
        outer_radius = min_dimension * self.config.outer_radius_ratio
        center_radius = min_dimension * self.config.center_radius_ratio

        # Calculate ring radii (outer ring drawn first, then inner)
        # Blocks: first block = outermost, last block = center
        radius_step = (outer_radius - center_radius) / num_rings

        # Draw from outside in (so outer rings are behind inner ones)
        for i, block in enumerate(blocks):
            ring_idx = i
            # Radius for this ring (outer edge)
            ring_radius = outer_radius - (ring_idx * radius_step)

            element = self._create_ring_element(
                block,
                center_x,
                center_y,
                ring_radius,
                ring_idx,
                num_rings
            )
            elements.append(element)

        return elements

    def _create_ring_element(
        self,
        block: BlockData,
        center_x: float,
        center_y: float,
        radius: float,
        ring_idx: int,
        total_rings: int
    ) -> PositionedElement:
        """Create a target ring element."""
        # Color progression: outer rings lighter, inner darker/brighter
        # Reverse color index so center is primary
        color_idx = total_rings - 1 - ring_idx
        fill_color = block.color or self.palette.get_color_for_index(color_idx)

        diameter = radius * 2

        # Fit text - use smaller text for outer rings
        max_font = 14 if ring_idx == total_rings - 1 else 11
        fit_result = fit_text_to_width(
            block.label,
            radius * 0.8,  # Use most of the radius for text
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=max_font,
            min_font_size=9,
            bold=(ring_idx == total_rings - 1),  # Bold only center
            allow_wrap=True,
            max_lines=2
        )

        text_color = self._contrast_text_color(fill_color)

        ring_text = PositionedText(
            content=block.label,
            lines=fit_result.lines,
            font_size_pt=fit_result.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=(ring_idx == total_rings - 1),
            color=text_color,
            alignment=TextAlignment.CENTER
        )

        return PositionedElement(
            id=block.id,
            element_type=ElementType.BLOCK,
            x_inches=center_x - radius,
            y_inches=center_y - radius,
            width_inches=diameter,
            height_inches=diameter,
            fill_color=fill_color,
            stroke_color=self.palette.background,  # Use background for ring separation
            stroke_width_pt=3.0,
            corner_radius_inches=radius,  # Make circular
            opacity=self.config.ring_opacity,
            text=ring_text,
            z_order=ring_idx + 1  # Inner rings on top
        )

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for target layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 2:
            errors.append("Target requires at least 2 rings")

        if len(input_data.blocks) > 5:
            errors.append("Too many rings for target (max 5)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_target(
    title: str,
    rings: List[str],
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a target/bullseye diagram.

    Args:
        title: Diagram title
        rings: List of ring labels from outside to center
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_target(
            title="Customer Segments",
            rings=["Mass Market", "Target Audience", "Early Adopters", "Core Users"]
        )
    """
    blocks = [
        BlockData(id=f"ring_{i}", label=ring)
        for i, ring in enumerate(rings)
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    archetype = TargetArchetype()
    return archetype.generate_layout(input_data)
