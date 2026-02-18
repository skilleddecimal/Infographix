"""
timeline.py — Timeline / Chronological Archetype.

Timeline diagrams showing chronological events or milestones:
- Horizontal or vertical timeline axis
- Event markers with dates and descriptions
- Alternating positions for visual clarity
- Support for milestones and phases

Example prompts:
- "Company history from founding to IPO"
- "Project roadmap for Q1-Q4 2024"
- "Product evolution timeline"
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


# =============================================================================
# TIMELINE CONFIGURATION
# =============================================================================

class TimelineDirection(Enum):
    """Direction of the timeline."""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


@dataclass
class TimelineConfig:
    """Configuration options for timeline layout."""
    direction: TimelineDirection = TimelineDirection.HORIZONTAL
    event_gutter: float = GUTTER_H * 1.5      # Gap between events
    event_width: float = 1.8                   # Width of event blocks
    event_height: float = 0.8                  # Height of event blocks
    axis_thickness: float = 0.06               # Timeline axis line thickness
    marker_radius: float = 0.12                # Radius of event markers on axis
    alternate_positions: bool = True           # Alternate events above/below axis
    show_dates: bool = True                    # Show date labels
    date_font_size: int = 10                   # Font size for dates


# =============================================================================
# TIMELINE ARCHETYPE
# =============================================================================

class TimelineArchetype(BaseArchetype):
    """
    Timeline diagram archetype.

    Creates chronological timeline diagrams where:
    - Events are positioned along a horizontal or vertical axis
    - Events can alternate above/below (or left/right) the axis
    - Markers indicate event positions on the timeline
    - Dates or labels can be shown for each event
    """

    name = "timeline"
    display_name = "Timeline / Chronology"
    description = "Chronological events or milestones along a timeline axis"
    example_prompts = [
        "Company history: Founded 2010 → Series A 2015 → IPO 2020",
        "Project roadmap from planning through launch phases",
        "Product evolution from v1.0 to v4.0",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[TimelineConfig] = None
    ):
        super().__init__(palette)
        self.config = config or TimelineConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """
        Generate a timeline layout from input data.

        Layout strategy:
        1. Draw central timeline axis
        2. Position events along the axis
        3. Alternate event positions if configured
        4. Add markers and date labels
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

        # Create timeline elements
        if self.config.direction == TimelineDirection.HORIZONTAL:
            elements, connectors = self._create_horizontal_timeline(
                input_data.blocks,
                content_top,
                content_height
            )
        else:
            elements, connectors = self._create_vertical_timeline(
                input_data.blocks,
                content_top,
                content_height
            )

        layout.elements.extend(elements)
        layout.connectors.extend(connectors)

        return layout

    def _create_horizontal_timeline(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> Tuple[List[PositionedElement], List[PositionedConnector]]:
        """
        Create a horizontal timeline (events left to right).
        """
        elements = []
        connectors = []

        if not blocks:
            return elements, connectors

        num_events = len(blocks)

        # Calculate timeline axis position (center of content area)
        axis_y = content_top + content_height / 2

        # Calculate event spacing
        total_gutter = self.config.event_gutter * (num_events - 1)
        available_width = CONTENT_WIDTH - total_gutter
        event_width = min(self.config.event_width, available_width / num_events)

        # Center events
        actual_total_width = event_width * num_events + total_gutter
        start_x = CONTENT_LEFT + (CONTENT_WIDTH - actual_total_width) / 2

        # Create timeline axis (as a band element)
        axis_element = PositionedElement(
            id="timeline_axis",
            element_type=ElementType.BAND,
            x_inches=start_x - 0.3,
            y_inches=axis_y - self.config.axis_thickness / 2,
            width_inches=actual_total_width + 0.6,
            height_inches=self.config.axis_thickness,
            fill_color=self.palette.border,
            z_order=1
        )
        elements.append(axis_element)

        # Create event elements
        for i, block in enumerate(blocks):
            x = start_x + i * (event_width + self.config.event_gutter)

            # Alternate position above/below axis
            if self.config.alternate_positions:
                above = (i % 2 == 0)
            else:
                above = True

            # Calculate event block position
            if above:
                event_y = axis_y - self.config.marker_radius - 0.15 - self.config.event_height
            else:
                event_y = axis_y + self.config.marker_radius + 0.15

            # Create event marker (circle on axis)
            marker = self._create_marker(
                f"marker_{i}",
                x + event_width / 2,
                axis_y,
                i
            )
            elements.append(marker)

            # Create event block
            event_elem = self._create_event_block(
                block,
                x,
                event_y,
                event_width,
                self.config.event_height,
                i
            )
            elements.append(event_elem)

            # Create connector from marker to event block
            if above:
                conn_start_y = axis_y - self.config.marker_radius
                conn_end_y = event_y + self.config.event_height
            else:
                conn_start_y = axis_y + self.config.marker_radius
                conn_end_y = event_y

            connector = PositionedConnector(
                id=f"conn_{i}",
                start_x=x + event_width / 2,
                start_y=conn_start_y,
                end_x=x + event_width / 2,
                end_y=conn_end_y,
                style=ConnectorStyle.PLAIN,
                color=self.palette.border,
                stroke_width_pt=1.0,
            )
            connectors.append(connector)

            # Create date label if block has description (used as date)
            if self.config.show_dates and block.description:
                date_elem = self._create_date_label(
                    f"date_{i}",
                    block.description,
                    x + event_width / 2,
                    axis_y + (0.25 if above else -0.25),
                    not above
                )
                elements.append(date_elem)

        return elements, connectors

    def _create_vertical_timeline(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> Tuple[List[PositionedElement], List[PositionedConnector]]:
        """
        Create a vertical timeline (events top to bottom).
        """
        elements = []
        connectors = []

        if not blocks:
            return elements, connectors

        num_events = len(blocks)

        # Calculate timeline axis position (center horizontally)
        axis_x = CONTENT_LEFT + CONTENT_WIDTH / 2

        # Calculate event spacing
        total_gutter = self.config.event_gutter * (num_events - 1)
        available_height = content_height - total_gutter
        event_height = min(self.config.event_height, available_height / num_events)

        # Start from top
        start_y = content_top

        # Create timeline axis
        axis_element = PositionedElement(
            id="timeline_axis",
            element_type=ElementType.BAND,
            x_inches=axis_x - self.config.axis_thickness / 2,
            y_inches=start_y - 0.2,
            width_inches=self.config.axis_thickness,
            height_inches=content_height + 0.4,
            fill_color=self.palette.border,
            z_order=1
        )
        elements.append(axis_element)

        # Create event elements
        for i, block in enumerate(blocks):
            y = start_y + i * (event_height + self.config.event_gutter)

            # Alternate position left/right of axis
            if self.config.alternate_positions:
                left_side = (i % 2 == 0)
            else:
                left_side = True

            # Calculate event block position
            event_width = self.config.event_width
            if left_side:
                event_x = axis_x - self.config.marker_radius - 0.15 - event_width
            else:
                event_x = axis_x + self.config.marker_radius + 0.15

            # Create event marker
            marker = self._create_marker(
                f"marker_{i}",
                axis_x,
                y + event_height / 2,
                i
            )
            elements.append(marker)

            # Create event block
            event_elem = self._create_event_block(
                block,
                event_x,
                y,
                event_width,
                event_height,
                i
            )
            elements.append(event_elem)

            # Create connector from marker to event block
            if left_side:
                conn_start_x = axis_x - self.config.marker_radius
                conn_end_x = event_x + event_width
            else:
                conn_start_x = axis_x + self.config.marker_radius
                conn_end_x = event_x

            connector = PositionedConnector(
                id=f"conn_{i}",
                start_x=conn_start_x,
                start_y=y + event_height / 2,
                end_x=conn_end_x,
                end_y=y + event_height / 2,
                style=ConnectorStyle.PLAIN,
                color=self.palette.border,
                stroke_width_pt=1.0,
            )
            connectors.append(connector)

            # Create date label
            if self.config.show_dates and block.description:
                date_x = axis_x + (0.3 if left_side else -0.3)
                date_elem = self._create_date_label(
                    f"date_{i}",
                    block.description,
                    date_x,
                    y + event_height / 2,
                    left_side
                )
                elements.append(date_elem)

        return elements, connectors

    def _create_marker(
        self,
        marker_id: str,
        x: float,
        y: float,
        index: int
    ) -> PositionedElement:
        """
        Create a circular marker on the timeline axis.
        """
        # Use primary color for markers
        fill_color = self.palette.primary

        return PositionedElement(
            id=marker_id,
            element_type=ElementType.BLOCK,
            x_inches=x - self.config.marker_radius,
            y_inches=y - self.config.marker_radius,
            width_inches=self.config.marker_radius * 2,
            height_inches=self.config.marker_radius * 2,
            fill_color=fill_color,
            stroke_color=self.palette.background,
            stroke_width_pt=2.0,
            corner_radius_inches=self.config.marker_radius,  # Make it circular
            z_order=15
        )

    def _create_event_block(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        height: float,
        index: int
    ) -> PositionedElement:
        """
        Create an event block element.
        """
        fill_color = block.color or self.palette.get_color_for_index(index)

        # Fit text
        fit_result = fit_text_to_width(
            block.label,
            width - 0.2,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=12,
            min_font_size=9,
            bold=False,
            allow_wrap=True,
            max_lines=3
        )

        text_color = self._contrast_text_color(fill_color)

        event_text = PositionedText(
            content=block.label,
            lines=fit_result.lines,
            font_size_pt=fit_result.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=False,
            color=text_color,
            alignment=TextAlignment.CENTER
        )

        return PositionedElement(
            id=block.id,
            element_type=ElementType.BLOCK,
            x_inches=x,
            y_inches=y,
            width_inches=width,
            height_inches=height,
            fill_color=fill_color,
            stroke_color=self.palette.border,
            stroke_width_pt=1.0,
            corner_radius_inches=0.06,
            text=event_text,
            z_order=10
        )

    def _create_date_label(
        self,
        label_id: str,
        date_text: str,
        x: float,
        y: float,
        align_left: bool
    ) -> PositionedElement:
        """
        Create a date label element.
        """
        label_text = PositionedText(
            content=date_text,
            lines=[date_text],
            font_size_pt=self.config.date_font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=False,
            color=self.palette.border,  # Use subdued color for dates
            alignment=TextAlignment.LEFT if align_left else TextAlignment.RIGHT
        )

        return PositionedElement(
            id=label_id,
            element_type=ElementType.LABEL,
            x_inches=x - 0.5 if not align_left else x,
            y_inches=y - 0.15,
            width_inches=1.0,
            height_inches=0.3,
            fill_color="transparent",
            text=label_text,
            z_order=5
        )

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """
        Validate input for timeline layout.
        """
        errors = super().validate_input(input_data)

        # Timeline specific validation
        if len(input_data.blocks) > 10:
            errors.append("Too many events for timeline (max 10)")

        if len(input_data.blocks) < 2:
            errors.append("Timeline requires at least 2 events")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_timeline(
    title: str,
    events: List[Dict[str, str]],
    subtitle: Optional[str] = None,
    direction: TimelineDirection = TimelineDirection.HORIZONTAL,
    alternate: bool = True
) -> PositionedLayout:
    """
    Quick helper to create a timeline diagram.

    Args:
        title: Diagram title
        events: List of dicts with 'label' and optional 'date' keys
        subtitle: Optional subtitle
        direction: Timeline direction (horizontal or vertical)
        alternate: Whether to alternate event positions

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_timeline(
            title="Company History",
            events=[
                {"label": "Founded", "date": "2010"},
                {"label": "Series A", "date": "2015"},
                {"label": "IPO", "date": "2020"},
            ],
            direction=TimelineDirection.HORIZONTAL
        )
    """
    # Build input data
    blocks = [
        BlockData(
            id=f"event_{i}",
            label=event["label"],
            description=event.get("date")  # Use description for date
        )
        for i, event in enumerate(events)
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    config = TimelineConfig(
        direction=direction,
        alternate_positions=alternate
    )

    archetype = TimelineArchetype(config=config)
    return archetype.generate_layout(input_data)
