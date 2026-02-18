"""
base.py — Base archetype abstract class.

All diagram archetypes (Marketecture, Process Flow, Tech Stack, etc.)
inherit from BaseArchetype and implement the generate_layout() method.

Archetypes are responsible for:
1. Validating input data against their schema
2. Applying design rules for their diagram type
3. Generating a PositionedLayout ready for rendering
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple

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
    MARGIN_TOP,
    TITLE_HEIGHT,
    SUBTITLE_HEIGHT,
    DEFAULT_FONT_FAMILY,
    TITLE_FONT_SIZE_PT,
    SUBTITLE_FONT_SIZE_PT,
    DEFAULT_TEXT_COLOR,
    DEFAULT_BACKGROUND_COLOR,
)
from ..engine.text_measure import fit_text_to_width, TextFitResult
from ..engine.grid_layout import compute_grid, compute_centered_block, GridLayout
from ..engine.data_models import (
    ColorPalette,
    BlockData,
    ConnectorData,
    LayerData,
    DiagramInput,
)


# =============================================================================
# BASE ARCHETYPE
# =============================================================================

class BaseArchetype(ABC):
    """
    Abstract base class for all diagram archetypes.

    Each archetype knows how to lay out a specific type of diagram:
    - Marketecture (layered architecture)
    - Process Flow (sequential steps)
    - Tech Stack (vertical layers)
    - Comparison (side-by-side)
    - Timeline (chronological)
    - etc.
    """

    # Archetype metadata (override in subclasses)
    name: str = "base"
    display_name: str = "Base Archetype"
    description: str = "Abstract base archetype"
    example_prompts: List[str] = []

    def __init__(self, palette: Optional[ColorPalette] = None):
        """
        Initialize archetype with optional color palette.

        Args:
            palette: Color palette to use (defaults to ColorPalette())
        """
        self.palette = palette or ColorPalette()

    @abstractmethod
    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """
        Generate a complete positioned layout from input data.

        This is the main entry point for layout generation.
        Subclasses implement the specific layout logic for their diagram type.

        Args:
            input_data: Normalized diagram input data

        Returns:
            PositionedLayout ready for rendering
        """
        pass

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """
        Validate input data for this archetype.

        Override in subclasses to add archetype-specific validation.

        Args:
            input_data: Input data to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not input_data.title:
            errors.append("Title is required")

        if not input_data.blocks:
            errors.append("At least one block is required")

        # Check for duplicate block IDs
        block_ids = [b.id for b in input_data.blocks]
        if len(block_ids) != len(set(block_ids)):
            errors.append("Block IDs must be unique")

        # Validate connector references
        for conn in input_data.connectors:
            if conn.from_id not in block_ids:
                errors.append(f"Connector references unknown block: {conn.from_id}")
            if conn.to_id not in block_ids:
                errors.append(f"Connector references unknown block: {conn.to_id}")

        return errors

    # =========================================================================
    # HELPER METHODS (Available to all archetypes)
    # =========================================================================

    def create_title_element(
        self,
        title: str,
        subtitle: Optional[str] = None
    ) -> Tuple[Optional[PositionedElement], Optional[PositionedElement]]:
        """
        Create title and subtitle elements.

        Args:
            title: Main title text
            subtitle: Optional subtitle text

        Returns:
            Tuple of (title_element, subtitle_element)
        """
        title_element = None
        subtitle_element = None

        if title:
            # Fit title text
            fit_result = fit_text_to_width(
                title,
                CONTENT_WIDTH,
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=TITLE_FONT_SIZE_PT,
                min_font_size=18,
                bold=True,
                allow_wrap=True,
                max_lines=2
            )

            title_text = PositionedText(
                content=title,
                lines=fit_result.lines,
                font_size_pt=fit_result.font_size,
                font_family=DEFAULT_FONT_FAMILY,
                bold=True,
                color=DEFAULT_TEXT_COLOR,
                alignment=TextAlignment.CENTER
            )

            title_element = PositionedElement(
                id="title",
                element_type=ElementType.TITLE,
                x_inches=CONTENT_LEFT,
                y_inches=MARGIN_TOP,
                width_inches=CONTENT_WIDTH,
                height_inches=TITLE_HEIGHT,
                fill_color="transparent",
                text=title_text,
                z_order=100
            )

        if subtitle:
            fit_result = fit_text_to_width(
                subtitle,
                CONTENT_WIDTH,
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=SUBTITLE_FONT_SIZE_PT,
                min_font_size=12,
                bold=False,
                allow_wrap=True,
                max_lines=2
            )

            subtitle_text = PositionedText(
                content=subtitle,
                lines=fit_result.lines,
                font_size_pt=fit_result.font_size,
                font_family=DEFAULT_FONT_FAMILY,
                bold=False,
                color="#666666",
                alignment=TextAlignment.CENTER
            )

            subtitle_element = PositionedElement(
                id="subtitle",
                element_type=ElementType.SUBTITLE,
                x_inches=CONTENT_LEFT,
                y_inches=MARGIN_TOP + TITLE_HEIGHT,
                width_inches=CONTENT_WIDTH,
                height_inches=SUBTITLE_HEIGHT,
                fill_color="transparent",
                text=subtitle_text,
                z_order=100
            )

        return (title_element, subtitle_element)

    def create_block_element(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        height: float,
        color_index: int = 0,
        z_order: int = 10
    ) -> PositionedElement:
        """
        Create a positioned block element from block data.

        Args:
            block: Block input data
            x: X position in inches
            y: Y position in inches
            width: Width in inches
            height: Height in inches
            color_index: Index for palette color selection
            z_order: Rendering order

        Returns:
            PositionedElement ready for rendering
        """
        # Determine fill color
        fill_color = block.color or self.palette.get_color_for_index(color_index)

        # Fit label text
        fit_result = fit_text_to_width(
            block.label,
            width,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            allow_wrap=True,
            max_lines=3
        )

        # Determine text color (light on dark backgrounds)
        text_color = self._contrast_text_color(fill_color)

        block_text = PositionedText(
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
            height_inches=height,
            fill_color=fill_color,
            text=block_text,
            layer_id=block.layer_id,
            z_order=z_order
        )

    def create_connector(
        self,
        conn_data: ConnectorData,
        from_element: PositionedElement,
        to_element: PositionedElement,
        connector_id: str
    ) -> PositionedConnector:
        """
        Create a connector between two elements.

        Automatically determines connection points based on element positions.

        Args:
            conn_data: Connector input data
            from_element: Source element
            to_element: Target element
            connector_id: Unique ID for this connector

        Returns:
            PositionedConnector ready for rendering
        """
        # Determine best connection points
        start_x, start_y, end_x, end_y = self._compute_connection_points(
            from_element, to_element
        )

        # Optional label
        label_text = None
        if conn_data.label:
            fit_result = fit_text_to_width(
                conn_data.label,
                2.0,  # Max label width
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=10,
                min_font_size=8,
                bold=False
            )
            label_text = PositionedText(
                content=conn_data.label,
                lines=fit_result.lines,
                font_size_pt=fit_result.font_size,
                font_family=DEFAULT_FONT_FAMILY,
                color=self.palette.connector
            )

        return PositionedConnector(
            id=connector_id,
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            style=conn_data.style,
            color=conn_data.color or self.palette.connector,
            label=label_text,
            from_element_id=conn_data.from_id,
            to_element_id=conn_data.to_id
        )

    def _compute_connection_points(
        self,
        from_elem: PositionedElement,
        to_elem: PositionedElement
    ) -> Tuple[float, float, float, float]:
        """
        Compute optimal connection points between two elements.

        Uses center-to-center line and finds intersection with each element's edge.
        This produces visually clean connectors regardless of element positions.

        Returns start_x, start_y, end_x, end_y.
        """
        # Get centers
        from_cx, from_cy = from_elem.center_x, from_elem.center_y
        to_cx, to_cy = to_elem.center_x, to_elem.center_y

        # Direction vector from center to center
        dx = to_cx - from_cx
        dy = to_cy - from_cy

        # Find where the center-to-center line exits from_elem
        start_x, start_y = self._intersect_rect_edge(
            from_cx, from_cy,
            dx, dy,
            from_elem.x_inches, from_elem.y_inches,
            from_elem.width_inches, from_elem.height_inches
        )

        # Find where the center-to-center line enters to_elem (reverse direction)
        end_x, end_y = self._intersect_rect_edge(
            to_cx, to_cy,
            -dx, -dy,
            to_elem.x_inches, to_elem.y_inches,
            to_elem.width_inches, to_elem.height_inches
        )

        return (start_x, start_y, end_x, end_y)

    def _intersect_rect_edge(
        self,
        cx: float, cy: float,
        dx: float, dy: float,
        rect_x: float, rect_y: float,
        rect_w: float, rect_h: float
    ) -> Tuple[float, float]:
        """
        Find where a ray from (cx, cy) in direction (dx, dy) intersects rectangle edge.

        Args:
            cx, cy: Starting point (typically center of rectangle)
            dx, dy: Direction vector
            rect_x, rect_y: Top-left corner of rectangle
            rect_w, rect_h: Rectangle dimensions

        Returns:
            (x, y) coordinates of intersection with rectangle edge
        """
        # Handle edge case: no direction
        if dx == 0 and dy == 0:
            return (cx, cy)

        # Rectangle edges
        left = rect_x
        right = rect_x + rect_w
        top = rect_y
        bottom = rect_y + rect_h

        # Find intersection with each edge, keep the closest one
        intersections = []

        if dx != 0:
            # Right edge intersection
            t = (right - cx) / dx
            if t > 0:
                y = cy + t * dy
                if top <= y <= bottom:
                    intersections.append((t, right, y))

            # Left edge intersection
            t = (left - cx) / dx
            if t > 0:
                y = cy + t * dy
                if top <= y <= bottom:
                    intersections.append((t, left, y))

        if dy != 0:
            # Bottom edge intersection
            t = (bottom - cy) / dy
            if t > 0:
                x = cx + t * dx
                if left <= x <= right:
                    intersections.append((t, x, bottom))

            # Top edge intersection
            t = (top - cy) / dy
            if t > 0:
                x = cx + t * dx
                if left <= x <= right:
                    intersections.append((t, x, top))

        # Return the closest intersection point
        if intersections:
            intersections.sort(key=lambda p: p[0])
            return (intersections[0][1], intersections[0][2])

        # Fallback to center if no intersection found
        return (cx, cy)

    def _contrast_text_color(self, bg_color: str) -> str:
        """
        Determine whether to use light or dark text based on background.

        Uses relative luminance calculation.
        """
        # Parse hex color
        bg_color = bg_color.lstrip('#')
        if len(bg_color) != 6:
            return DEFAULT_TEXT_COLOR

        try:
            r = int(bg_color[0:2], 16)
            g = int(bg_color[2:4], 16)
            b = int(bg_color[4:6], 16)
        except ValueError:
            return DEFAULT_TEXT_COLOR

        # Relative luminance
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

        # Use light text on dark backgrounds
        return self.palette.text_light if luminance < 0.5 else self.palette.text_dark

    def create_empty_layout(self, title: str = "", subtitle: str = "") -> PositionedLayout:
        """
        Create an empty layout with just title/subtitle.

        Useful as a starting point or for error states.
        """
        layout = PositionedLayout(
            slide_width_inches=SLIDE_WIDTH_INCHES,
            slide_height_inches=SLIDE_HEIGHT_INCHES,
            background_color=self.palette.background,
            elements=[],
            connectors=[]
        )

        title_elem, subtitle_elem = self.create_title_element(title, subtitle)
        if title_elem:
            layout.title = title_elem
        if subtitle_elem:
            layout.subtitle = subtitle_elem

        return layout
