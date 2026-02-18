"""
hub_spoke.py — Hub & Spoke / Radial Archetype.

Hub and spoke diagrams showing central concept with connections:
- Central hub element
- Surrounding spoke elements
- Connectors from hub to spokes
- Great for showing relationships to a core concept

Example prompts:
- "Core product with feature integrations"
- "Central platform with connected services"
- "Main concept with related topics"
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
    ConnectorStyle,
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
from ..engine.data_models import ConnectorData


# =============================================================================
# HUB SPOKE CONFIGURATION
# =============================================================================

@dataclass
class HubSpokeConfig:
    """Configuration options for hub & spoke layout."""
    hub_size: float = 1.5                    # Hub diameter in inches
    spoke_size: float = 1.2                  # Spoke element size
    orbit_radius_ratio: float = 0.35         # Radius as ratio of content size
    connector_style: ConnectorStyle = ConnectorStyle.PLAIN
    show_connectors: bool = True             # Show lines from hub to spokes
    hub_emphasis: bool = True                # Make hub more prominent
    equal_spacing: bool = True               # Equal angles between spokes


# =============================================================================
# HUB SPOKE ARCHETYPE
# =============================================================================

class HubSpokeArchetype(BaseArchetype):
    """
    Hub & Spoke diagram archetype.

    Creates radial layouts where:
    - A central hub represents the main concept
    - Spoke elements surround the hub
    - Connectors show relationships from hub to spokes
    - Spokes are evenly distributed around the hub
    """

    name = "hub_spoke"
    display_name = "Hub & Spoke"
    description = "Central hub with radiating connections to surrounding items"
    example_prompts = [
        "Core platform with integrated services",
        "Central team with stakeholder connections",
        "Main product with feature modules",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[HubSpokeConfig] = None
    ):
        super().__init__(palette)
        self.config = config or HubSpokeConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a hub & spoke layout from input data."""
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

        # Create hub and spokes
        elements, connectors = self._create_hub_spoke_layout(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)
        layout.connectors.extend(connectors)

        return layout

    def _create_hub_spoke_layout(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> Tuple[List[PositionedElement], List[PositionedConnector]]:
        """Create hub and spoke elements."""
        elements = []
        connectors = []

        if not blocks:
            return elements, connectors

        # First block is the hub, rest are spokes
        hub_block = blocks[0]
        spoke_blocks = blocks[1:]
        num_spokes = len(spoke_blocks)

        # Calculate center of content area
        center_x = CONTENT_LEFT + CONTENT_WIDTH / 2
        center_y = content_top + content_height / 2

        # Calculate orbit radius
        min_dimension = min(CONTENT_WIDTH, content_height)
        orbit_radius = min_dimension * self.config.orbit_radius_ratio

        # Create hub element
        hub_element = self._create_hub_element(
            hub_block,
            center_x,
            center_y
        )
        elements.append(hub_element)

        # Create spoke elements around the hub
        if num_spokes > 0:
            angle_step = 2 * math.pi / num_spokes
            start_angle = -math.pi / 2  # Start at top (12 o'clock)

            for i, spoke_block in enumerate(spoke_blocks):
                angle = start_angle + i * angle_step

                # Calculate spoke position
                spoke_x = center_x + orbit_radius * math.cos(angle)
                spoke_y = center_y + orbit_radius * math.sin(angle)

                # Create spoke element
                spoke_element = self._create_spoke_element(
                    spoke_block,
                    spoke_x,
                    spoke_y,
                    i
                )
                elements.append(spoke_element)

                # Create connector from hub to spoke
                if self.config.show_connectors:
                    connector = self._create_hub_connector(
                        hub_element,
                        spoke_element,
                        i
                    )
                    connectors.append(connector)

        return elements, connectors

    def _create_hub_element(
        self,
        block: BlockData,
        center_x: float,
        center_y: float
    ) -> PositionedElement:
        """Create the central hub element."""
        hub_size = self.config.hub_size

        # Hub gets primary color
        fill_color = block.color or self.palette.primary

        # Fit text
        fit_result = fit_text_to_width(
            block.label,
            hub_size - 0.3,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=14,
            min_font_size=10,
            bold=True,
            allow_wrap=True,
            max_lines=2
        )

        text_color = self._contrast_text_color(fill_color)

        hub_text = PositionedText(
            content=block.label,
            lines=fit_result.lines,
            font_size_pt=fit_result.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            color=text_color,
            alignment=TextAlignment.CENTER
        )

        # Make hub circular
        return PositionedElement(
            id=block.id,
            element_type=ElementType.BLOCK,
            x_inches=center_x - hub_size / 2,
            y_inches=center_y - hub_size / 2,
            width_inches=hub_size,
            height_inches=hub_size,
            fill_color=fill_color,
            stroke_color=self.palette.border,
            stroke_width_pt=2.0 if self.config.hub_emphasis else 1.0,
            corner_radius_inches=hub_size / 2,  # Make circular
            text=hub_text,
            z_order=20  # Hub on top
        )

    def _create_spoke_element(
        self,
        block: BlockData,
        center_x: float,
        center_y: float,
        index: int
    ) -> PositionedElement:
        """Create a spoke element."""
        spoke_size = self.config.spoke_size

        # Spokes get sequential colors
        fill_color = block.color or self.palette.get_color_for_index(index + 1)

        # Fit text
        fit_result = fit_text_to_width(
            block.label,
            spoke_size - 0.2,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=11,
            min_font_size=9,
            bold=False,
            allow_wrap=True,
            max_lines=2
        )

        text_color = self._contrast_text_color(fill_color)

        spoke_text = PositionedText(
            content=block.label,
            lines=fit_result.lines,
            font_size_pt=fit_result.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=False,
            color=text_color,
            alignment=TextAlignment.CENTER
        )

        # Spokes are also circular (or rounded)
        return PositionedElement(
            id=block.id,
            element_type=ElementType.BLOCK,
            x_inches=center_x - spoke_size / 2,
            y_inches=center_y - spoke_size / 2,
            width_inches=spoke_size,
            height_inches=spoke_size,
            fill_color=fill_color,
            stroke_color=self.palette.border,
            stroke_width_pt=1.0,
            corner_radius_inches=spoke_size / 2,  # Circular
            text=spoke_text,
            z_order=10
        )

    def _create_hub_connector(
        self,
        hub_element: PositionedElement,
        spoke_element: PositionedElement,
        index: int
    ) -> PositionedConnector:
        """Create a connector from hub to spoke."""
        # Calculate center points
        hub_cx = hub_element.x_inches + hub_element.width_inches / 2
        hub_cy = hub_element.y_inches + hub_element.height_inches / 2
        spoke_cx = spoke_element.x_inches + spoke_element.width_inches / 2
        spoke_cy = spoke_element.y_inches + spoke_element.height_inches / 2

        # Calculate direction vector
        dx = spoke_cx - hub_cx
        dy = spoke_cy - hub_cy
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            # Normalize
            dx /= distance
            dy /= distance

            # Start at edge of hub
            hub_radius = hub_element.width_inches / 2
            start_x = hub_cx + dx * hub_radius
            start_y = hub_cy + dy * hub_radius

            # End at edge of spoke
            spoke_radius = spoke_element.width_inches / 2
            end_x = spoke_cx - dx * spoke_radius
            end_y = spoke_cy - dy * spoke_radius
        else:
            start_x, start_y = hub_cx, hub_cy
            end_x, end_y = spoke_cx, spoke_cy

        return PositionedConnector(
            id=f"connector_{index}",
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            style=self.config.connector_style,
            color=self.palette.connector,
            stroke_width_pt=1.5,
            from_element_id=hub_element.id,
            to_element_id=spoke_element.id,
        )

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for hub & spoke layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 2:
            errors.append("Hub & Spoke requires at least 2 elements (1 hub + 1 spoke)")

        if len(input_data.blocks) > 10:
            errors.append("Too many elements for hub & spoke (max 10)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_hub_spoke(
    title: str,
    hub: str,
    spokes: List[str],
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a hub & spoke diagram.

    Args:
        title: Diagram title
        hub: Label for the central hub
        spokes: List of labels for surrounding spokes
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_hub_spoke(
            title="Platform Ecosystem",
            hub="Core Platform",
            spokes=["API", "Mobile", "Web", "Analytics", "Integrations"]
        )
    """
    # Hub is first block, spokes follow
    blocks = [BlockData(id="hub", label=hub)]
    blocks.extend([
        BlockData(id=f"spoke_{i}", label=spoke)
        for i, spoke in enumerate(spokes)
    ])

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    archetype = HubSpokeArchetype()
    return archetype.generate_layout(input_data)
