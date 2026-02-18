"""
process_flow.py — Process Flow / Workflow Archetype.

Sequential process diagrams showing workflow steps:
- Horizontal or vertical arrangement of steps
- Arrows showing flow direction
- Optional decision diamonds
- Support for parallel branches

Example prompts:
- "Create a CI/CD pipeline showing build, test, and deploy stages"
- "User signup flow with email verification and onboarding"
- "Order processing workflow from cart to delivery"
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
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
    GUTTER_H,
    GUTTER_V,
    DEFAULT_FONT_FAMILY,
    DEFAULT_TEXT_COLOR,
)
from ..engine.text_measure import fit_text_to_width
from ..engine.data_models import ConnectorData


# =============================================================================
# PROCESS FLOW CONFIGURATION
# =============================================================================

class FlowDirection(Enum):
    """Direction of the process flow."""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


@dataclass
class ProcessFlowConfig:
    """Configuration options for process flow layout."""
    direction: FlowDirection = FlowDirection.HORIZONTAL
    step_gutter: float = GUTTER_H * 2       # Gap between steps
    step_min_width: float = 1.5              # Minimum step width
    step_max_width: float = 2.5              # Maximum step width
    step_height: float = 1.0                 # Step height (horizontal mode)
    step_width: float = 2.0                  # Step width (vertical mode)
    show_step_numbers: bool = False          # Show step numbers
    arrow_style: ConnectorStyle = ConnectorStyle.ARROW
    center_vertically: bool = True           # Center flow vertically in content area


# =============================================================================
# PROCESS FLOW ARCHETYPE
# =============================================================================

class ProcessFlowArchetype(BaseArchetype):
    """
    Process Flow diagram archetype.

    Creates sequential process/workflow diagrams where:
    - Steps flow horizontally (left to right) or vertically (top to bottom)
    - Arrows connect steps showing flow direction
    - Blocks represent process steps, actions, or states
    - Supports linear and branching flows
    """

    name = "process_flow"
    display_name = "Process Flow / Workflow"
    description = "Sequential steps connected by arrows showing workflow or process"
    example_prompts = [
        "Create a CI/CD pipeline: Code Push → Build → Test → Deploy → Monitor",
        "User registration flow with email verification",
        "Order processing from cart through payment to fulfillment",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[ProcessFlowConfig] = None
    ):
        super().__init__(palette)
        self.config = config or ProcessFlowConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """
        Generate a process flow layout from input data.

        Layout strategy:
        1. Arrange steps in sequence (horizontal or vertical)
        2. Size steps to fit content
        3. Create arrow connectors between steps
        4. Handle branches if layers indicate parallel paths
        """
        # Validate input
        errors = self.validate_input(input_data)
        if errors:
            return self.create_empty_layout(
                title=input_data.title,
                subtitle=f"Layout error: {errors[0]}"
            )

        # Use palette from input if provided
        if input_data.palette:
            self.palette = input_data.palette

        # Create base layout
        layout = PositionedLayout(
            slide_width_inches=SLIDE_WIDTH_INCHES,
            slide_height_inches=SLIDE_HEIGHT_INCHES,
            background_color=self.palette.background,
            elements=[],
            connectors=[]
        )

        # Add title and subtitle
        title_elem, subtitle_elem = self.create_title_element(
            input_data.title,
            input_data.subtitle
        )
        if title_elem:
            layout.title = title_elem
        if subtitle_elem:
            layout.subtitle = subtitle_elem

        # Adjust content area
        content_top = CONTENT_TOP
        if subtitle_elem:
            content_top += 0.3

        content_height = CONTENT_HEIGHT - (content_top - CONTENT_TOP)

        # Check for branching (multiple layers = parallel paths)
        if input_data.layers and len(input_data.layers) > 1:
            elements, connectors = self._create_branched_flow(
                input_data,
                content_top,
                content_height
            )
        else:
            elements, connectors = self._create_linear_flow(
                input_data.blocks,
                input_data.connectors,
                content_top,
                content_height
            )

        layout.elements.extend(elements)
        layout.connectors.extend(connectors)

        return layout

    def _create_linear_flow(
        self,
        blocks: List[BlockData],
        connectors: List[ConnectorData],
        content_top: float,
        content_height: float
    ) -> Tuple[List[PositionedElement], List[PositionedConnector]]:
        """
        Create a simple linear flow of steps.
        """
        elements = []
        positioned_connectors = []
        block_positions: Dict[str, PositionedElement] = {}

        if not blocks:
            return elements, positioned_connectors

        num_steps = len(blocks)

        if self.config.direction == FlowDirection.HORIZONTAL:
            # Horizontal flow (left to right)
            elements, block_positions = self._layout_horizontal(
                blocks,
                content_top,
                content_height
            )
        else:
            # Vertical flow (top to bottom)
            elements, block_positions = self._layout_vertical(
                blocks,
                content_top,
                content_height
            )

        # Create connectors
        # If no explicit connectors, create sequential arrows
        if not connectors and num_steps > 1:
            for i in range(num_steps - 1):
                from_id = blocks[i].id
                to_id = blocks[i + 1].id
                if from_id in block_positions and to_id in block_positions:
                    connector = self.create_connector(
                        ConnectorData(
                            from_id=from_id,
                            to_id=to_id,
                            style=self.config.arrow_style
                        ),
                        block_positions[from_id],
                        block_positions[to_id],
                        f"connector_{i}"
                    )
                    positioned_connectors.append(connector)
        else:
            # Use explicit connectors
            for i, conn in enumerate(connectors):
                if conn.from_id in block_positions and conn.to_id in block_positions:
                    connector = self.create_connector(
                        conn,
                        block_positions[conn.from_id],
                        block_positions[conn.to_id],
                        f"connector_{i}"
                    )
                    positioned_connectors.append(connector)

        return elements, positioned_connectors

    def _layout_horizontal(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> Tuple[List[PositionedElement], Dict[str, PositionedElement]]:
        """
        Layout blocks horizontally (left to right).
        """
        elements = []
        block_positions = {}

        num_steps = len(blocks)
        if num_steps == 0:
            return elements, block_positions

        # Calculate step dimensions
        total_gutter = self.config.step_gutter * (num_steps - 1)
        available_width = CONTENT_WIDTH - total_gutter
        step_width = available_width / num_steps

        # Clamp width
        step_width = max(self.config.step_min_width, min(self.config.step_max_width, step_width))

        # Recalculate starting position if steps don't fill width
        actual_total_width = step_width * num_steps + total_gutter
        start_x = CONTENT_LEFT + (CONTENT_WIDTH - actual_total_width) / 2

        # Calculate vertical position (centered in content area)
        step_height = self.config.step_height
        if self.config.center_vertically:
            y = content_top + (content_height - step_height) / 2
        else:
            y = content_top

        # Create step elements
        for i, block in enumerate(blocks):
            x = start_x + i * (step_width + self.config.step_gutter)

            # Add step number to label if configured
            label = block.label
            if self.config.show_step_numbers:
                label = f"{i + 1}. {label}"

            modified_block = BlockData(
                id=block.id,
                label=label,
                layer_id=block.layer_id,
                color=block.color,
                description=block.description
            )

            element = self.create_block_element(
                modified_block,
                x=x,
                y=y,
                width=step_width,
                height=step_height,
                color_index=i,
                z_order=10
            )
            elements.append(element)
            block_positions[block.id] = element

        return elements, block_positions

    def _layout_vertical(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> Tuple[List[PositionedElement], Dict[str, PositionedElement]]:
        """
        Layout blocks vertically (top to bottom).
        """
        elements = []
        block_positions = {}

        num_steps = len(blocks)
        if num_steps == 0:
            return elements, block_positions

        # Calculate step dimensions
        total_gutter = self.config.step_gutter * (num_steps - 1)
        available_height = content_height - total_gutter
        step_height = available_height / num_steps

        # Clamp height
        step_height = max(0.7, min(1.5, step_height))

        # Center horizontally
        step_width = self.config.step_width
        x = CONTENT_LEFT + (CONTENT_WIDTH - step_width) / 2

        # Create step elements
        current_y = content_top
        for i, block in enumerate(blocks):
            label = block.label
            if self.config.show_step_numbers:
                label = f"{i + 1}. {label}"

            modified_block = BlockData(
                id=block.id,
                label=label,
                layer_id=block.layer_id,
                color=block.color,
                description=block.description
            )

            element = self.create_block_element(
                modified_block,
                x=x,
                y=current_y,
                width=step_width,
                height=step_height,
                color_index=i,
                z_order=10
            )
            elements.append(element)
            block_positions[block.id] = element

            current_y += step_height + self.config.step_gutter

        return elements, block_positions

    def _create_branched_flow(
        self,
        input_data: DiagramInput,
        content_top: float,
        content_height: float
    ) -> Tuple[List[PositionedElement], List[PositionedConnector]]:
        """
        Create a flow with parallel branches (multiple layers).

        Each layer represents a parallel path in the flow.
        """
        elements = []
        positioned_connectors = []
        block_positions: Dict[str, PositionedElement] = {}

        # Group blocks by layer
        layer_blocks: Dict[str, List[BlockData]] = {}
        unassigned: List[BlockData] = []

        for block in input_data.blocks:
            if block.layer_id:
                if block.layer_id not in layer_blocks:
                    layer_blocks[block.layer_id] = []
                layer_blocks[block.layer_id].append(block)
            else:
                unassigned.append(block)

        # Order layers as defined
        ordered_layers = [layer.id for layer in input_data.layers]
        num_lanes = len(ordered_layers)

        if num_lanes == 0:
            # No layers, fall back to linear
            return self._create_linear_flow(
                input_data.blocks,
                input_data.connectors,
                content_top,
                content_height
            )

        # Calculate lane heights
        lane_gutter = GUTTER_V
        total_lane_gutter = lane_gutter * (num_lanes - 1)
        available_height = content_height - total_lane_gutter
        lane_height = available_height / num_lanes

        # Process each lane
        current_y = content_top
        for layer_id in ordered_layers:
            blocks = layer_blocks.get(layer_id, [])
            if not blocks:
                current_y += lane_height + lane_gutter
                continue

            # Layout blocks in this lane horizontally
            lane_elements, lane_positions = self._layout_horizontal_in_lane(
                blocks,
                current_y,
                lane_height
            )
            elements.extend(lane_elements)
            block_positions.update(lane_positions)

            current_y += lane_height + lane_gutter

        # Create connectors
        for i, conn in enumerate(input_data.connectors):
            if conn.from_id in block_positions and conn.to_id in block_positions:
                connector = self.create_connector(
                    conn,
                    block_positions[conn.from_id],
                    block_positions[conn.to_id],
                    f"connector_{i}"
                )
                positioned_connectors.append(connector)

        return elements, positioned_connectors

    def _layout_horizontal_in_lane(
        self,
        blocks: List[BlockData],
        y: float,
        height: float
    ) -> Tuple[List[PositionedElement], Dict[str, PositionedElement]]:
        """
        Layout blocks horizontally within a specific lane (row).
        """
        elements = []
        block_positions = {}

        num_steps = len(blocks)
        if num_steps == 0:
            return elements, block_positions

        # Calculate step dimensions
        total_gutter = self.config.step_gutter * (num_steps - 1)
        available_width = CONTENT_WIDTH - total_gutter
        step_width = available_width / num_steps
        step_width = max(self.config.step_min_width, min(self.config.step_max_width, step_width))

        # Center blocks
        actual_total_width = step_width * num_steps + total_gutter
        start_x = CONTENT_LEFT + (CONTENT_WIDTH - actual_total_width) / 2

        # Step height within lane
        step_height = min(height * 0.8, self.config.step_height)
        step_y = y + (height - step_height) / 2

        for i, block in enumerate(blocks):
            x = start_x + i * (step_width + self.config.step_gutter)

            element = self.create_block_element(
                block,
                x=x,
                y=step_y,
                width=step_width,
                height=step_height,
                color_index=i,
                z_order=10
            )
            elements.append(element)
            block_positions[block.id] = element

        return elements, block_positions

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """
        Validate input for process flow layout.
        """
        errors = super().validate_input(input_data)

        # Process flow specific validation
        if len(input_data.blocks) > 12:
            errors.append("Too many steps for process flow (max 12)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_process_flow(
    title: str,
    steps: List[str],
    subtitle: Optional[str] = None,
    direction: FlowDirection = FlowDirection.HORIZONTAL,
    show_numbers: bool = False
) -> PositionedLayout:
    """
    Quick helper to create a process flow diagram from a list of step names.

    Args:
        title: Diagram title
        steps: List of step labels in order
        subtitle: Optional subtitle
        direction: Flow direction (horizontal or vertical)
        show_numbers: Whether to show step numbers

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_process_flow(
            title="CI/CD Pipeline",
            steps=["Code Push", "Build", "Test", "Deploy", "Monitor"],
            direction=FlowDirection.HORIZONTAL
        )
    """
    # Build input data
    blocks = [
        BlockData(id=f"step_{i}", label=step)
        for i, step in enumerate(steps)
    ]

    # Sequential connectors
    connectors = []
    for i in range(len(steps) - 1):
        connectors.append(ConnectorData(
            from_id=f"step_{i}",
            to_id=f"step_{i + 1}",
            style=ConnectorStyle.ARROW
        ))

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks,
        connectors=connectors
    )

    config = ProcessFlowConfig(
        direction=direction,
        show_step_numbers=show_numbers
    )

    archetype = ProcessFlowArchetype(config=config)
    return archetype.generate_layout(input_data)
