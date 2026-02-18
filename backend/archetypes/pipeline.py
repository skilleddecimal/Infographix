"""
pipeline.py — Pipeline Archetype.

Horizontal pipeline stages diagram:
- Connected rectangular stages
- Great for DevOps, CI/CD, data processing
- Shows flow from input to output
- Each stage represents a transformation

Example prompts:
- "CI/CD pipeline stages"
- "Data processing pipeline"
- "ETL workflow"
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
# PIPELINE CONFIGURATION
# =============================================================================

@dataclass
class PipelineConfig:
    """Configuration options for pipeline layout."""
    stage_height: float = 1.0                 # Height of each stage
    stage_min_width: float = 1.2              # Minimum width of stages
    connector_gap: float = 0.3                # Gap for connector arrows
    show_arrows: bool = True                  # Show connecting arrows
    corner_radius: float = 0.08               # Stage corner radius


# =============================================================================
# PIPELINE ARCHETYPE
# =============================================================================

class PipelineArchetype(BaseArchetype):
    """
    Pipeline diagram archetype.

    Creates horizontal pipeline layouts where:
    - Stages arranged horizontally with arrows
    - Each stage represents a process step
    - Great for DevOps, CI/CD, ETL workflows
    - Clear left-to-right flow
    """

    name = "pipeline"
    display_name = "Pipeline"
    description = "Horizontal pipeline with connected stages"
    example_prompts = [
        "CI/CD pipeline",
        "Data processing stages",
        "ETL workflow",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[PipelineConfig] = None
    ):
        super().__init__(palette)
        self.config = config or PipelineConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a pipeline layout from input data."""
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

        # Create pipeline elements
        elements, connectors = self._create_pipeline(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)
        layout.connectors.extend(connectors)

        return layout

    def _create_pipeline(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> Tuple[List[PositionedElement], List[PositionedConnector]]:
        """Create the pipeline elements and connectors."""
        elements = []
        connectors = []
        num_stages = len(blocks)

        if num_stages == 0:
            return elements, connectors

        # Calculate stage dimensions
        total_connector_space = (num_stages - 1) * self.config.connector_gap if self.config.show_arrows else 0
        available_width = CONTENT_WIDTH - total_connector_space
        stage_width = available_width / num_stages
        stage_width = max(self.config.stage_min_width, stage_width)

        # Recalculate total width and center
        total_width = num_stages * stage_width + total_connector_space
        start_x = CONTENT_LEFT + (CONTENT_WIDTH - total_width) / 2

        # Center vertically
        y = content_top + (content_height - self.config.stage_height) / 2

        # Create stages and connectors
        prev_element = None
        for i, block in enumerate(blocks):
            x = start_x + i * (stage_width + self.config.connector_gap)

            element = self._create_stage_element(
                block,
                x,
                y,
                stage_width,
                i
            )
            elements.append(element)

            # Create connector from previous stage
            if prev_element and self.config.show_arrows:
                connector = PositionedConnector(
                    id=f"conn_{prev_element.id}_{element.id}",
                    from_element_id=prev_element.id,
                    to_element_id=element.id,
                    start_x=prev_element.x_inches + prev_element.width_inches,
                    start_y=y + self.config.stage_height / 2,
                    end_x=x,
                    end_y=y + self.config.stage_height / 2,
                    style=ConnectorStyle.ARROW,
                    color=self.palette.connector,
                    stroke_width_pt=2.0
                )
                connectors.append(connector)

            prev_element = element

        return elements, connectors

    def _create_stage_element(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        stage_idx: int
    ) -> PositionedElement:
        """Create a single pipeline stage element."""
        fill_color = block.color or self.palette.get_color_for_index(stage_idx)

        # Fit text
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
            x_inches=x,
            y_inches=y,
            width_inches=width,
            height_inches=self.config.stage_height,
            fill_color=fill_color,
            stroke_color=self.palette.border,
            stroke_width_pt=1.0,
            corner_radius_inches=self.config.corner_radius,
            text=stage_text,
            z_order=10 + stage_idx
        )

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for pipeline layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 2:
            errors.append("Pipeline requires at least 2 stages")

        if len(input_data.blocks) > 8:
            errors.append("Too many stages for pipeline (max 8)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_pipeline(
    title: str,
    stages: List[str],
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a pipeline diagram.

    Args:
        title: Diagram title
        stages: List of stage labels in order
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_pipeline(
            title="CI/CD Pipeline",
            stages=["Build", "Test", "Stage", "Deploy"]
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

    archetype = PipelineArchetype()
    return archetype.generate_layout(input_data)
