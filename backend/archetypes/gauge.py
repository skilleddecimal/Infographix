"""
gauge.py — Gauge / Meter Archetype.

Semicircular gauge showing a single value:
- Dashboard-style meters
- Great for KPIs, performance metrics
- Visual representation of single value
- Color-coded zones (red/yellow/green)

Example prompts:
- "Customer satisfaction score"
- "Performance metric gauge"
- "Health score dashboard"
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
    DEFAULT_FONT_FAMILY,
)
from ..engine.text_measure import fit_text_to_width


# =============================================================================
# GAUGE CONFIGURATION
# =============================================================================

@dataclass
class GaugeConfig:
    """Configuration options for gauge layout."""
    gauge_radius: float = 1.5                 # Radius of the gauge
    arc_thickness: float = 0.3                # Thickness of the arc
    show_zones: bool = True                   # Show red/yellow/green zones
    zone_boundaries: Tuple[float, float] = (33, 66)  # Zone thresholds
    zone_colors: Tuple[str, str, str] = ("#F44336", "#FFC107", "#4CAF50")  # Red, Yellow, Green


# =============================================================================
# GAUGE ARCHETYPE
# =============================================================================

class GaugeArchetype(BaseArchetype):
    """
    Gauge / Meter diagram archetype.

    Creates gauge displays where:
    - Semicircular arc shows value range
    - Needle or filled arc shows current value
    - Optional color zones for status
    - Great for KPIs and dashboard metrics
    """

    name = "gauge"
    display_name = "Gauge / Meter"
    description = "Semicircular gauge showing a single value"
    example_prompts = [
        "Customer satisfaction score",
        "Performance gauge",
        "Health metric",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[GaugeConfig] = None
    ):
        super().__init__(palette)
        self.config = config or GaugeConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a gauge layout from input data."""
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

        # Create gauge elements
        elements = self._create_gauges(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _create_gauges(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create gauge elements (supports 1-3 gauges)."""
        elements = []
        num_gauges = len(blocks)

        if num_gauges == 0:
            return elements

        # Calculate layout for multiple gauges
        if num_gauges == 1:
            cols = 1
        elif num_gauges == 2:
            cols = 2
        else:
            cols = 3

        gauge_width = CONTENT_WIDTH / cols
        gauge_height = content_height

        for i, block in enumerate(blocks):
            col = i % cols
            center_x = CONTENT_LEFT + col * gauge_width + gauge_width / 2
            center_y = content_top + gauge_height / 2 + 0.3

            # Parse value from description
            value = self._parse_value(block.description or "0")

            gauge_elements = self._create_single_gauge(
                block,
                center_x,
                center_y,
                value,
                i
            )
            elements.extend(gauge_elements)

        return elements

    def _parse_value(self, value_str: str) -> float:
        """Parse a value from string (0-100)."""
        try:
            clean = value_str.strip().replace("%", "")
            value = float(clean)
            return max(0, min(100, value))
        except (ValueError, TypeError):
            return 0

    def _create_single_gauge(
        self,
        block: BlockData,
        center_x: float,
        center_y: float,
        value: float,
        gauge_idx: int
    ) -> List[PositionedElement]:
        """Create a single gauge with arc and value."""
        elements = []

        radius = self.config.gauge_radius
        thickness = self.config.arc_thickness

        # For SVG rendering, we'll use multiple arc segments
        # represented as ellipse placeholders. The actual arc
        # rendering would need SVG path support.

        # Background arc (gray)
        bg_element = PositionedElement(
            id=f"{block.id}_bg",
            element_type=ElementType.ELLIPSE,
            x_inches=center_x - radius,
            y_inches=center_y - radius,
            width_inches=radius * 2,
            height_inches=radius * 2,
            fill_color="#E0E0E0",
            stroke_color=None,
            stroke_width_pt=0,
            opacity=0.3,
            z_order=5 + gauge_idx
        )
        elements.append(bg_element)

        # Determine color based on value and zones
        if self.config.show_zones:
            if value < self.config.zone_boundaries[0]:
                fill_color = self.config.zone_colors[0]  # Red
            elif value < self.config.zone_boundaries[1]:
                fill_color = self.config.zone_colors[1]  # Yellow
            else:
                fill_color = self.config.zone_colors[2]  # Green
        else:
            fill_color = block.color or self.palette.primary

        # Value indicator (inner circle showing the color)
        inner_radius = radius * 0.6
        value_element = PositionedElement(
            id=f"{block.id}_value_circle",
            element_type=ElementType.ELLIPSE,
            x_inches=center_x - inner_radius,
            y_inches=center_y - inner_radius,
            width_inches=inner_radius * 2,
            height_inches=inner_radius * 2,
            fill_color=fill_color,
            stroke_color=None,
            stroke_width_pt=0,
            opacity=0.2,
            z_order=6 + gauge_idx
        )
        elements.append(value_element)

        # Center value display
        value_str = f"{int(value)}%"
        value_text = PositionedText(
            content=value_str,
            lines=[value_str],
            font_size_pt=24,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            color=fill_color,
            alignment=TextAlignment.CENTER
        )

        value_text_element = PositionedElement(
            id=f"{block.id}_value_text",
            element_type=ElementType.TEXT_BOX,
            x_inches=center_x - radius * 0.5,
            y_inches=center_y - 0.3,
            width_inches=radius,
            height_inches=0.6,
            fill_color=None,
            stroke_color=None,
            stroke_width_pt=0,
            text=value_text,
            z_order=10 + gauge_idx
        )
        elements.append(value_text_element)

        # Label below gauge
        label_fit = fit_text_to_width(
            block.label,
            radius * 2,
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
            alignment=TextAlignment.CENTER
        )

        label_element = PositionedElement(
            id=f"{block.id}_label",
            element_type=ElementType.TEXT_BOX,
            x_inches=center_x - radius,
            y_inches=center_y + radius * 0.4,
            width_inches=radius * 2,
            height_inches=0.5,
            fill_color=None,
            stroke_color=None,
            stroke_width_pt=0,
            text=label_text,
            z_order=11 + gauge_idx
        )
        elements.append(label_element)

        return elements

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for gauge layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 1:
            errors.append("Gauge requires at least 1 metric")

        if len(input_data.blocks) > 3:
            errors.append("Too many gauges (max 3)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_gauge(
    title: str,
    label: str,
    value: float,
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a single gauge diagram.

    Args:
        title: Diagram title
        label: Metric label
        value: Value (0-100)
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_gauge(
            title="Customer Satisfaction",
            label="NPS Score",
            value=72
        )
    """
    blocks = [
        BlockData(
            id="gauge",
            label=label,
            description=str(value)
        )
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    archetype = GaugeArchetype()
    return archetype.generate_layout(input_data)


def create_multi_gauge(
    title: str,
    metrics: List[Dict[str, any]],
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create multiple gauges.

    Args:
        title: Diagram title
        metrics: List of dicts with 'label' and 'value'
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_multi_gauge(
            title="Performance Dashboard",
            metrics=[
                {"label": "Speed", "value": 85},
                {"label": "Quality", "value": 92},
                {"label": "Cost", "value": 67},
            ]
        )
    """
    blocks = [
        BlockData(
            id=f"gauge_{i}",
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

    archetype = GaugeArchetype()
    return archetype.generate_layout(input_data)
