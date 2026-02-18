"""
positioned.py — The contract between layout engine and renderers.

The layout engine outputs PositionedLayout objects.
Renderers (PPTX, SVG) consume these — they NEVER compute positions themselves.

All coordinates are in INCHES (converted to EMU/pixels at render time).
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class ElementType(Enum):
    """Types of visual elements."""
    BLOCK = "block"           # Standard entity block
    BAND = "band"             # Full-width horizontal band (cross-cutting layers)
    CONNECTOR = "connector"   # Line connecting two elements
    TITLE = "title"           # Slide title
    SUBTITLE = "subtitle"     # Slide subtitle
    LABEL = "label"           # Standalone text label
    ELLIPSE = "ellipse"       # Circular/oval shape
    TEXT_BOX = "text_box"     # Text-only element (no shape border)


class ConnectorStyle(Enum):
    """Connector line styles."""
    ARROW = "arrow"           # Single arrowhead at end
    BIDIRECTIONAL = "bidirectional"  # Arrowheads at both ends
    DASHED = "dashed"         # Dashed line with arrow
    PLAIN = "plain"           # No arrowhead


class TextAlignment(Enum):
    """Text alignment options."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


@dataclass
class PositionedText:
    """
    Text content with pre-computed sizing.

    The layout engine pre-measures text and determines font size and line breaks
    BEFORE the renderer sees it. Renderers use these values directly.
    """
    content: str                           # Original text
    lines: List[str]                       # Pre-wrapped lines (ready to render)
    font_size_pt: int                      # Pre-computed font size to fit
    font_family: str                       # Font family name
    bold: bool = False
    italic: bool = False
    color: str = "#333333"                 # Hex color
    alignment: TextAlignment = TextAlignment.CENTER

    @property
    def line_count(self) -> int:
        return len(self.lines)


@dataclass
class PositionedElement:
    """
    A fully positioned, render-ready visual element.

    All position and size values are in INCHES.
    The renderer converts to EMU/pixels as needed.
    """
    id: str                                # Unique identifier
    element_type: ElementType              # Type of element
    x_inches: float                        # Left edge position
    y_inches: float                        # Top edge position
    width_inches: float                    # Width
    height_inches: float                   # Height
    fill_color: str                        # Hex color for fill
    stroke_color: Optional[str] = None     # Hex color for border (None = no border)
    stroke_width_pt: float = 1.0           # Border width in points
    corner_radius_inches: float = 0.08     # Corner radius for rounded rects
    text: Optional[PositionedText] = None  # Text content (if any)
    opacity: float = 1.0                   # 0.0 to 1.0
    layer_id: Optional[str] = None         # Which layer this belongs to
    z_order: int = 0                       # Lower = rendered first (behind)

    @property
    def right_edge(self) -> float:
        """Right edge x-coordinate."""
        return self.x_inches + self.width_inches

    @property
    def bottom_edge(self) -> float:
        """Bottom edge y-coordinate."""
        return self.y_inches + self.height_inches

    @property
    def center_x(self) -> float:
        """Horizontal center x-coordinate."""
        return self.x_inches + self.width_inches / 2

    @property
    def center_y(self) -> float:
        """Vertical center y-coordinate."""
        return self.y_inches + self.height_inches / 2


@dataclass
class PositionedConnector:
    """
    A connector line between two elements.

    All coordinates are in INCHES.
    """
    id: str                                # Unique identifier
    start_x: float                         # Start point x
    start_y: float                         # Start point y
    end_x: float                           # End point x
    end_y: float                           # End point y
    style: ConnectorStyle = ConnectorStyle.ARROW
    color: str = "#666666"                 # Line color
    stroke_width_pt: float = 1.5           # Line width in points
    label: Optional[PositionedText] = None # Optional label on connector
    from_element_id: Optional[str] = None  # Source element ID
    to_element_id: Optional[str] = None    # Target element ID

    @property
    def midpoint_x(self) -> float:
        """X-coordinate of connector midpoint."""
        return (self.start_x + self.end_x) / 2

    @property
    def midpoint_y(self) -> float:
        """Y-coordinate of connector midpoint."""
        return (self.start_y + self.end_y) / 2

    @property
    def length(self) -> float:
        """Length of the connector."""
        import math
        return math.sqrt((self.end_x - self.start_x) ** 2 + (self.end_y - self.start_y) ** 2)


@dataclass
class PositionedLayout:
    """
    Complete render-ready layout.

    This is the output of the layout engine and the input to renderers.
    Contains all elements with absolute positions — renderers just plot them.
    """
    slide_width_inches: float
    slide_height_inches: float
    background_color: str = "#FFFFFF"
    elements: List[PositionedElement] = field(default_factory=list)
    connectors: List[PositionedConnector] = field(default_factory=list)
    title: Optional[PositionedElement] = None
    subtitle: Optional[PositionedElement] = None

    def get_element_by_id(self, element_id: str) -> Optional[PositionedElement]:
        """Find an element by its ID."""
        for elem in self.elements:
            if elem.id == element_id:
                return elem
        return None

    def elements_sorted_by_z_order(self) -> List[PositionedElement]:
        """Return elements sorted by z_order (lowest first = behind)."""
        return sorted(self.elements, key=lambda e: e.z_order)

    def validate(self) -> List[str]:
        """
        Validate the layout for common issues.
        Returns list of warning messages (empty if valid).
        """
        warnings = []

        # Check for elements outside slide bounds
        for elem in self.elements:
            if elem.x_inches < 0 or elem.y_inches < 0:
                warnings.append(f"Element {elem.id} has negative position")
            if elem.right_edge > self.slide_width_inches:
                warnings.append(f"Element {elem.id} extends beyond right edge")
            if elem.bottom_edge > self.slide_height_inches:
                warnings.append(f"Element {elem.id} extends beyond bottom edge")

        # Check for overlapping elements (simple bounding box check)
        for i, elem1 in enumerate(self.elements):
            for elem2 in self.elements[i+1:]:
                if self._boxes_overlap(elem1, elem2):
                    # Only warn if same z_order (intentional overlap is ok)
                    if elem1.z_order == elem2.z_order:
                        warnings.append(f"Elements {elem1.id} and {elem2.id} overlap")

        return warnings

    @staticmethod
    def _boxes_overlap(e1: PositionedElement, e2: PositionedElement) -> bool:
        """Check if two elements' bounding boxes overlap."""
        return not (
            e1.right_edge <= e2.x_inches or
            e2.right_edge <= e1.x_inches or
            e1.bottom_edge <= e2.y_inches or
            e2.bottom_edge <= e1.y_inches
        )
