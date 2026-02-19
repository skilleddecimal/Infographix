"""
positioned.py — The contract between layout engine and renderers.

The layout engine outputs PositionedLayout objects.
Renderers (PPTX, SVG) consume these — they NEVER compute positions themselves.

All coordinates are in INCHES (converted to EMU/pixels at render time).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
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


class RoutingStyle(Enum):
    """Connector routing styles for smart connectors."""
    DIRECT = "direct"         # Straight line between points
    ORTHOGONAL = "orthogonal" # Right-angle routing (horizontal/vertical only)
    CURVED = "curved"         # Smooth bezier curve
    STEPPED = "stepped"       # Single step (L-shaped)


class AnchorPosition(Enum):
    """Anchor positions on element edges for connectors."""
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    AUTO = "auto"             # Automatically determine best anchor


class IconPosition(Enum):
    """Icon position within an element."""
    LEFT = "left"             # Icon on left, text on right
    RIGHT = "right"           # Icon on right, text on left
    TOP = "top"               # Icon above text
    BOTTOM = "bottom"         # Icon below text
    CENTER = "center"         # Icon centered (text may overlay or be below)
    BACKGROUND = "background" # Icon as background watermark


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
    shape_hint: Optional[str] = None       # Shape type hint: "trapezoid", "arrow", "chevron", etc.
    arrow_direction: Optional[str] = None  # For arrows: "up", "down", "left", "right"
    custom_path: Optional[List] = None     # For freeform shapes: list of path segments from learned shapes

    # Icon fields (Phase 1: Icon System)
    icon_id: Optional[str] = None          # Icon identifier from icon library (e.g., "database", "cloud")
    icon_position: IconPosition = IconPosition.LEFT  # Where to place icon relative to text
    icon_size_ratio: float = 0.4           # Icon size as ratio of element height (0.0 to 1.0)
    icon_color: Optional[str] = None       # Icon fill color (None = use text color)

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

    # Smart connector routing fields (Phase 2: Smart Connectors)
    waypoints: List[Tuple[float, float]] = field(default_factory=list)  # Intermediate points for polyline routing
    routing_style: RoutingStyle = RoutingStyle.DIRECT  # How to route the connector
    from_anchor: AnchorPosition = AnchorPosition.AUTO  # Where connector leaves source element
    to_anchor: AnchorPosition = AnchorPosition.AUTO    # Where connector enters target element
    corner_radius_inches: float = 0.05     # Rounding radius for orthogonal corners

    @property
    def is_polyline(self) -> bool:
        """Whether this connector has intermediate waypoints."""
        return len(self.waypoints) > 0

    @property
    def all_points(self) -> List[Tuple[float, float]]:
        """Get all points including start, waypoints, and end."""
        return [(self.start_x, self.start_y)] + self.waypoints + [(self.end_x, self.end_y)]

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
    Complete render-ready layout for a single slide.

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
    slide_number: int = 1  # 1-indexed slide number
    slide_id: Optional[str] = None  # Unique identifier for the slide
    speaker_notes: Optional[str] = None  # Speaker notes for this slide
    archetype: Optional[str] = None  # Archetype used (e.g., "pyramid", "marketecture")

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


@dataclass
class MultiSlidePresentation:
    """
    A multi-slide presentation containing multiple PositionedLayout slides.

    This is the container for multi-slide PPTX generation.
    """
    slides: List[PositionedLayout] = field(default_factory=list)
    presentation_title: str = "Presentation"
    author: Optional[str] = None
    created_at: Optional[str] = None  # ISO format timestamp
    metadata: dict = field(default_factory=dict)

    @property
    def slide_count(self) -> int:
        """Total number of slides."""
        return len(self.slides)

    @property
    def slide_width_inches(self) -> float:
        """Width from first slide (all slides should be same size)."""
        if self.slides:
            return self.slides[0].slide_width_inches
        return 13.333  # Default 16:9

    @property
    def slide_height_inches(self) -> float:
        """Height from first slide (all slides should be same size)."""
        if self.slides:
            return self.slides[0].slide_height_inches
        return 7.5  # Default 16:9

    def add_slide(self, slide: PositionedLayout) -> None:
        """Add a slide to the presentation."""
        slide.slide_number = len(self.slides) + 1
        if not slide.slide_id:
            slide.slide_id = f"slide_{slide.slide_number}"
        self.slides.append(slide)

    def get_slide(self, index: int) -> Optional[PositionedLayout]:
        """Get slide by index (0-based)."""
        if 0 <= index < len(self.slides):
            return self.slides[index]
        return None

    def get_slide_by_id(self, slide_id: str) -> Optional[PositionedLayout]:
        """Get slide by its ID."""
        for slide in self.slides:
            if slide.slide_id == slide_id:
                return slide
        return None

    def reorder_slides(self, new_order: List[int]) -> None:
        """Reorder slides by providing new indices."""
        if len(new_order) != len(self.slides):
            raise ValueError("New order must include all slides")
        if set(new_order) != set(range(len(self.slides))):
            raise ValueError("Invalid slide indices")

        self.slides = [self.slides[i] for i in new_order]
        # Update slide numbers
        for i, slide in enumerate(self.slides):
            slide.slide_number = i + 1

    def remove_slide(self, index: int) -> Optional[PositionedLayout]:
        """Remove slide at index and return it."""
        if 0 <= index < len(self.slides):
            removed = self.slides.pop(index)
            # Update remaining slide numbers
            for i, slide in enumerate(self.slides):
                slide.slide_number = i + 1
            return removed
        return None

    def duplicate_slide(self, index: int) -> Optional[PositionedLayout]:
        """Duplicate a slide and insert after the original."""
        if 0 <= index < len(self.slides):
            import copy
            original = self.slides[index]
            duplicate = copy.deepcopy(original)
            duplicate.slide_id = f"{original.slide_id}_copy"
            self.slides.insert(index + 1, duplicate)
            # Update slide numbers
            for i, slide in enumerate(self.slides):
                slide.slide_number = i + 1
            return duplicate
        return None

    def validate(self) -> List[str]:
        """Validate all slides and return warnings."""
        warnings = []

        if not self.slides:
            warnings.append("Presentation has no slides")
            return warnings

        # Check all slides have same dimensions
        base_width = self.slides[0].slide_width_inches
        base_height = self.slides[0].slide_height_inches
        for i, slide in enumerate(self.slides):
            if slide.slide_width_inches != base_width or slide.slide_height_inches != base_height:
                warnings.append(f"Slide {i+1} has different dimensions than other slides")

        # Validate each slide
        for i, slide in enumerate(self.slides):
            slide_warnings = slide.validate()
            for w in slide_warnings:
                warnings.append(f"Slide {i+1}: {w}")

        return warnings
