"""
cycle.py — Circular Cycle Archetype.

Cycle diagrams showing continuous/repeating processes:
- Items arranged in a circle
- Arrows showing flow direction
- Great for iterative processes
- Supports 3-8 stages

Example prompts:
- "PDCA cycle (Plan-Do-Check-Act)"
- "Agile sprint cycle"
- "Customer lifecycle"
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


# =============================================================================
# CYCLE CONFIGURATION
# =============================================================================

@dataclass
class CycleConfig:
    """Configuration options for cycle layout."""
    stage_size: float = 1.3                  # Size of each stage block
    orbit_radius_ratio: float = 0.35         # Radius as ratio of content area
    show_arrows: bool = True                 # Show directional arrows
    clockwise: bool = True                   # Direction of flow
    start_angle: float = -90                 # Starting angle in degrees (top = -90)


# =============================================================================
# CYCLE ARCHETYPE
# =============================================================================

class CycleArchetype(BaseArchetype):
    """
    Circular cycle diagram archetype.

    Creates circular flow layouts where:
    - Stages are arranged around a circle
    - Arrows connect stages showing flow direction
    - Flow can be clockwise or counter-clockwise
    - Represents iterative or continuous processes
    """

    name = "circular_cycle"
    display_name = "Circular Cycle"
    description = "Items arranged in a circle with arrows showing continuous flow"
    example_prompts = [
        "PDCA cycle: Plan, Do, Check, Act",
        "Agile sprint cycle",
        "Customer lifecycle stages",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[CycleConfig] = None
    ):
        super().__init__(palette)
        self.config = config or CycleConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a cycle layout from input data."""
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

        # Create cycle stages and connectors
        elements, connectors = self._create_cycle_layout(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)
        layout.connectors.extend(connectors)

        return layout

    def _create_cycle_layout(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> Tuple[List[PositionedElement], List[PositionedConnector]]:
        """Create cycle stage elements and connectors."""
        elements = []
        connectors = []
        num_stages = len(blocks)

        if num_stages == 0:
            return elements, connectors

        # Calculate center and radius
        center_x = CONTENT_LEFT + CONTENT_WIDTH / 2
        center_y = content_top + content_height / 2

        min_dimension = min(CONTENT_WIDTH, content_height)
        orbit_radius = min_dimension * self.config.orbit_radius_ratio

        # Calculate angle step
        angle_step = 360 / num_stages
        if not self.config.clockwise:
            angle_step = -angle_step

        start_angle_rad = math.radians(self.config.start_angle)

        # Create stage elements
        stage_positions = []
        for i, block in enumerate(blocks):
            angle_rad = start_angle_rad + math.radians(i * angle_step)

            # Calculate position
            cx = center_x + orbit_radius * math.cos(angle_rad)
            cy = center_y + orbit_radius * math.sin(angle_rad)

            stage_positions.append((cx, cy, angle_rad))

            element = self._create_stage_element(
                block,
                cx,
                cy,
                i
            )
            elements.append(element)

        # Create curved arrow connectors
        if self.config.show_arrows and num_stages > 1:
            for i in range(num_stages):
                next_i = (i + 1) % num_stages
                connector = self._create_cycle_connector(
                    stage_positions[i],
                    stage_positions[next_i],
                    i,
                    center_x,
                    center_y
                )
                connectors.append(connector)

        return elements, connectors

    def _create_stage_element(
        self,
        block: BlockData,
        center_x: float,
        center_y: float,
        index: int
    ) -> PositionedElement:
        """Create a cycle stage element."""
        stage_size = self.config.stage_size
        fill_color = block.color or self.palette.get_color_for_index(index)

        # Fit text
        fit_result = fit_text_to_width(
            block.label,
            stage_size - 0.3,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=12,
            min_font_size=9,
            bold=True,
            allow_wrap=True,
            max_lines=2
        )

        text_color = self._contrast_text_color(fill_color)

        stage_text = PositionedText(
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
            x_inches=center_x - stage_size / 2,
            y_inches=center_y - stage_size / 2,
            width_inches=stage_size,
            height_inches=stage_size,
            fill_color=fill_color,
            stroke_color=self.palette.border,
            stroke_width_pt=1.5,
            corner_radius_inches=stage_size / 2,  # Circular
            text=stage_text,
            z_order=10
        )

    def _create_cycle_connector(
        self,
        from_pos: Tuple[float, float, float],
        to_pos: Tuple[float, float, float],
        index: int,
        center_x: float,
        center_y: float
    ) -> PositionedConnector:
        """Create a connector between cycle stages."""
        from_cx, from_cy, from_angle = from_pos
        to_cx, to_cy, to_angle = to_pos

        stage_radius = self.config.stage_size / 2

        # Calculate edge points (on the outer edge of each stage, towards the next)
        # Use angle bisector approach for curved appearance
        dx = to_cx - from_cx
        dy = to_cy - from_cy
        dist = math.sqrt(dx * dx + dy * dy)

        if dist > 0:
            dx /= dist
            dy /= dist

            # Start at edge of from-stage (towards to-stage)
            start_x = from_cx + dx * stage_radius
            start_y = from_cy + dy * stage_radius

            # End at edge of to-stage (from from-stage)
            end_x = to_cx - dx * stage_radius
            end_y = to_cy - dy * stage_radius
        else:
            start_x, start_y = from_cx, from_cy
            end_x, end_y = to_cx, to_cy

        return PositionedConnector(
            id=f"arrow_{index}",
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            style=ConnectorStyle.ARROW,
            color=self.palette.connector,
            stroke_width_pt=2.0,
        )

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for cycle layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 3:
            errors.append("Cycle requires at least 3 stages")

        if len(input_data.blocks) > 8:
            errors.append("Too many stages for cycle (max 8)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_cycle(
    title: str,
    stages: List[str],
    subtitle: Optional[str] = None,
    clockwise: bool = True
) -> PositionedLayout:
    """
    Quick helper to create a cycle diagram.

    Args:
        title: Diagram title
        stages: List of stage labels in order
        subtitle: Optional subtitle
        clockwise: Direction of flow

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_cycle(
            title="PDCA Cycle",
            stages=["Plan", "Do", "Check", "Act"]
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

    config = CycleConfig(clockwise=clockwise)
    archetype = CycleArchetype(config=config)
    return archetype.generate_layout(input_data)
