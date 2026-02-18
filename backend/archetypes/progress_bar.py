"""
progress_bar.py — Progress Bar Archetype.

Horizontal progress bars showing completion:
- Multiple metrics with percentage bars
- Great for KPIs, completion status, surveys
- Shows values visually as filled bars
- Can display labels and percentages

Example prompts:
- "Project completion status"
- "Survey results"
- "KPI progress dashboard"
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
# PROGRESS BAR CONFIGURATION
# =============================================================================

@dataclass
class ProgressBarConfig:
    """Configuration options for progress bar layout."""
    bar_height: float = 0.35                  # Height of each bar
    bar_spacing: float = 0.5                  # Vertical spacing between bars
    label_width: float = 2.0                  # Width for label column
    value_width: float = 0.6                  # Width for value display
    corner_radius: float = 0.05               # Bar corner radius
    show_values: bool = True                  # Show percentage values


# =============================================================================
# PROGRESS BAR ARCHETYPE
# =============================================================================

class ProgressBarArchetype(BaseArchetype):
    """
    Progress Bar diagram archetype.

    Creates horizontal bar chart where:
    - Each bar represents a metric
    - Fill level shows percentage complete
    - Labels on left, values on right
    - Great for KPIs, surveys, completion tracking
    """

    name = "progress_bar"
    display_name = "Progress Bars"
    description = "Horizontal bars showing progress or percentages"
    example_prompts = [
        "Project completion status",
        "Survey results visualization",
        "KPI progress dashboard",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[ProgressBarConfig] = None
    ):
        super().__init__(palette)
        self.config = config or ProgressBarConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a progress bar layout from input data."""
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

        # Create progress bar elements
        elements = self._create_progress_bars(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _create_progress_bars(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create the progress bar elements."""
        elements = []
        num_bars = len(blocks)

        if num_bars == 0:
            return elements

        # Calculate layout
        total_bar_space = num_bars * self.config.bar_height + (num_bars - 1) * self.config.bar_spacing
        start_y = content_top + (content_height - total_bar_space) / 2

        bar_width = CONTENT_WIDTH - self.config.label_width - self.config.value_width - 0.3
        bar_x = CONTENT_LEFT + self.config.label_width + 0.15

        # Create each bar
        for i, block in enumerate(blocks):
            y = start_y + i * (self.config.bar_height + self.config.bar_spacing)

            # Parse value from description (expect percentage like "75" or "75%")
            value = self._parse_percentage(block.description or "0")

            bar_elements = self._create_single_bar(
                block,
                bar_x,
                y,
                bar_width,
                value,
                i
            )
            elements.extend(bar_elements)

        return elements

    def _parse_percentage(self, value_str: str) -> float:
        """Parse a percentage value from string."""
        try:
            # Remove % sign and convert
            clean = value_str.strip().replace("%", "")
            value = float(clean)
            # Clamp to 0-100
            return max(0, min(100, value))
        except (ValueError, TypeError):
            return 0

    def _create_single_bar(
        self,
        block: BlockData,
        bar_x: float,
        y: float,
        bar_width: float,
        value: float,
        bar_idx: int
    ) -> List[PositionedElement]:
        """Create a single progress bar with label and value."""
        elements = []

        fill_color = block.color or self.palette.get_color_for_index(bar_idx)

        # Label (left side)
        label_fit = fit_text_to_width(
            block.label,
            self.config.label_width - 0.1,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=11,
            min_font_size=8,
            bold=True,
            allow_wrap=True,
            max_lines=2
        )

        label_text = PositionedText(
            content=block.label,
            lines=label_fit.lines,
            font_size_pt=label_fit.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            color=self.palette.text_dark,
            alignment=TextAlignment.RIGHT
        )

        label_element = PositionedElement(
            id=f"{block.id}_label",
            element_type=ElementType.TEXT_BOX,
            x_inches=CONTENT_LEFT,
            y_inches=y,
            width_inches=self.config.label_width,
            height_inches=self.config.bar_height,
            fill_color=None,
            stroke_color=None,
            stroke_width_pt=0,
            text=label_text,
            z_order=10 + bar_idx
        )
        elements.append(label_element)

        # Bar background (gray track)
        bg_element = PositionedElement(
            id=f"{block.id}_bg",
            element_type=ElementType.BLOCK,
            x_inches=bar_x,
            y_inches=y,
            width_inches=bar_width,
            height_inches=self.config.bar_height,
            fill_color="#E0E0E0",
            stroke_color=None,
            stroke_width_pt=0,
            corner_radius_inches=self.config.corner_radius,
            z_order=5 + bar_idx
        )
        elements.append(bg_element)

        # Filled portion
        if value > 0:
            fill_width = bar_width * (value / 100)
            fill_element = PositionedElement(
                id=f"{block.id}_fill",
                element_type=ElementType.BLOCK,
                x_inches=bar_x,
                y_inches=y,
                width_inches=fill_width,
                height_inches=self.config.bar_height,
                fill_color=fill_color,
                stroke_color=None,
                stroke_width_pt=0,
                corner_radius_inches=self.config.corner_radius,
                z_order=6 + bar_idx
            )
            elements.append(fill_element)

        # Value display (right side)
        if self.config.show_values:
            value_str = f"{int(value)}%"
            value_text = PositionedText(
                content=value_str,
                lines=[value_str],
                font_size_pt=11,
                font_family=DEFAULT_FONT_FAMILY,
                bold=True,
                color=fill_color,
                alignment=TextAlignment.LEFT
            )

            value_element = PositionedElement(
                id=f"{block.id}_value",
                element_type=ElementType.TEXT_BOX,
                x_inches=bar_x + bar_width + 0.15,
                y_inches=y,
                width_inches=self.config.value_width,
                height_inches=self.config.bar_height,
                fill_color=None,
                stroke_color=None,
                stroke_width_pt=0,
                text=value_text,
                z_order=11 + bar_idx
            )
            elements.append(value_element)

        return elements

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for progress bar layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 1:
            errors.append("Progress bars require at least 1 metric")

        if len(input_data.blocks) > 8:
            errors.append("Too many metrics for progress bars (max 8)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_progress_bars(
    title: str,
    metrics: List[Dict[str, any]],
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a progress bar diagram.

    Args:
        title: Diagram title
        metrics: List of dicts with 'label' and 'value' (0-100)
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_progress_bars(
            title="Project Status",
            metrics=[
                {"label": "Design", "value": 100},
                {"label": "Development", "value": 75},
                {"label": "Testing", "value": 45},
                {"label": "Documentation", "value": 20},
            ]
        )
    """
    blocks = [
        BlockData(
            id=f"metric_{i}",
            label=metric.get("label", ""),
            description=str(metric.get("value", 0))
        )
        for i, metric in enumerate(metrics)
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    archetype = ProgressBarArchetype()
    return archetype.generate_layout(input_data)
