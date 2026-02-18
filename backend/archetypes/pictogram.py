"""
pictogram.py — Pictogram Archetype.

Visual data representation using icons/shapes:
- Shows quantities using repeated symbols
- Great for making data more visual and memorable
- Each icon represents a unit
- Good for statistics, survey results

Example prompts:
- "10 out of 100 people affected"
- "Customer survey results visual"
- "Population statistics"
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import math

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
# PICTOGRAM CONFIGURATION
# =============================================================================

@dataclass
class PictogramConfig:
    """Configuration options for pictogram layout."""
    icon_size: float = 0.25                   # Size of each icon
    icon_spacing: float = 0.08                # Spacing between icons
    icons_per_row: int = 10                   # Icons per row (for percentage display)
    total_icons: int = 10                     # Total icons to show (each = 10%)
    show_legend: bool = True                  # Show legend/labels


# =============================================================================
# PICTOGRAM ARCHETYPE
# =============================================================================

class PictogramArchetype(BaseArchetype):
    """
    Pictogram diagram archetype.

    Creates visual data displays where:
    - Repeated icons represent quantities
    - Filled vs unfilled shows proportion
    - Great for making percentages memorable
    - Simple visual statistical display
    """

    name = "pictogram"
    display_name = "Pictogram"
    description = "Visual data using repeated icons"
    example_prompts = [
        "7 out of 10 customers satisfied",
        "Population breakdown visual",
        "Survey results pictogram",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[PictogramConfig] = None
    ):
        super().__init__(palette)
        self.config = config or PictogramConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a pictogram layout from input data."""
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

        # Create pictogram elements
        elements = self._create_pictograms(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _create_pictograms(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create pictogram elements."""
        elements = []
        num_metrics = len(blocks)

        if num_metrics == 0:
            return elements

        # Calculate layout
        metric_height = content_height / num_metrics

        for i, block in enumerate(blocks):
            y = content_top + i * metric_height

            # Parse value from description
            value = self._parse_value(block.description or "0")

            metric_elements = self._create_metric_pictogram(
                block,
                CONTENT_LEFT,
                y,
                CONTENT_WIDTH,
                metric_height - 0.2,
                value,
                i
            )
            elements.extend(metric_elements)

        return elements

    def _parse_value(self, value_str: str) -> float:
        """Parse a value from string (0-100)."""
        try:
            clean = value_str.strip().replace("%", "")
            value = float(clean)
            return max(0, min(100, value))
        except (ValueError, TypeError):
            return 0

    def _create_metric_pictogram(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        height: float,
        value: float,
        metric_idx: int
    ) -> List[PositionedElement]:
        """Create a single metric with icon grid."""
        elements = []

        fill_color = block.color or self.palette.get_color_for_index(metric_idx)

        # Label
        label_width = 2.0
        label_fit = fit_text_to_width(
            block.label,
            label_width - 0.1,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=12,
            min_font_size=9,
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
            alignment=TextAlignment.LEFT
        )

        label_element = PositionedElement(
            id=f"{block.id}_label",
            element_type=ElementType.TEXT_BOX,
            x_inches=x,
            y_inches=y + 0.1,
            width_inches=label_width,
            height_inches=height - 0.2,
            fill_color=None,
            stroke_color=None,
            stroke_width_pt=0,
            text=label_text,
            z_order=10 + metric_idx
        )
        elements.append(label_element)

        # Icons grid
        icons_x = x + label_width + 0.2
        icons_width = width - label_width - 0.4

        num_filled = int(round(value / (100 / self.config.total_icons)))
        icon_step = self.config.icon_size + self.config.icon_spacing

        # Calculate how many icons per row fit
        icons_per_row = min(self.config.icons_per_row, int(icons_width / icon_step))
        num_rows = math.ceil(self.config.total_icons / icons_per_row)

        # Center icons vertically
        total_icon_height = num_rows * icon_step
        icons_y = y + (height - total_icon_height) / 2

        for i in range(self.config.total_icons):
            row = i // icons_per_row
            col = i % icons_per_row

            icon_x = icons_x + col * icon_step
            icon_y = icons_y + row * icon_step

            is_filled = i < num_filled

            icon = PositionedElement(
                id=f"{block.id}_icon_{i}",
                element_type=ElementType.ELLIPSE,
                x_inches=icon_x,
                y_inches=icon_y,
                width_inches=self.config.icon_size,
                height_inches=self.config.icon_size,
                fill_color=fill_color if is_filled else "#E0E0E0",
                stroke_color=None,
                stroke_width_pt=0,
                opacity=1.0 if is_filled else 0.5,
                z_order=5 + metric_idx
            )
            elements.append(icon)

        # Value display
        value_str = f"{int(value)}%"
        value_text = PositionedText(
            content=value_str,
            lines=[value_str],
            font_size_pt=14,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            color=fill_color,
            alignment=TextAlignment.RIGHT
        )

        value_element = PositionedElement(
            id=f"{block.id}_value",
            element_type=ElementType.TEXT_BOX,
            x_inches=x + width - 0.8,
            y_inches=y + 0.1,
            width_inches=0.7,
            height_inches=height - 0.2,
            fill_color=None,
            stroke_color=None,
            stroke_width_pt=0,
            text=value_text,
            z_order=11 + metric_idx
        )
        elements.append(value_element)

        return elements

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for pictogram layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 1:
            errors.append("Pictogram requires at least 1 metric")

        if len(input_data.blocks) > 4:
            errors.append("Too many metrics for pictogram (max 4)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_pictogram(
    title: str,
    metrics: List[Dict[str, any]],
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a pictogram diagram.

    Args:
        title: Diagram title
        metrics: List of dicts with 'label' and 'value' (0-100)
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_pictogram(
            title="Customer Satisfaction",
            metrics=[
                {"label": "Very Satisfied", "value": 45},
                {"label": "Satisfied", "value": 30},
                {"label": "Neutral", "value": 15},
                {"label": "Unsatisfied", "value": 10},
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

    archetype = PictogramArchetype()
    return archetype.generate_layout(input_data)
