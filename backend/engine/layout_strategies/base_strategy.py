"""
base_strategy.py — Abstract base class for layout strategies.

All layout strategies inherit from BaseLayoutStrategy and implement
the compute() method to generate element positions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

from ..archetype_rules import (
    ArchetypeRules,
    ElementTemplate,
    LayoutConstraint,
    SizeRule,
    ColorRule,
)
from ..data_models import DiagramInput, BlockData, ColorPalette
from ..units import (
    CONTENT_LEFT,
    CONTENT_TOP,
    CONTENT_WIDTH,
    CONTENT_HEIGHT,
    GUTTER_H,
    GUTTER_V,
)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ElementPosition:
    """
    Computed position for a single element.

    This is the output of the strategy computation, before conversion
    to PositionedElement.
    """
    element_id: str
    block_data: BlockData               # Original block data

    # Position
    x: float                            # Left edge in inches
    y: float                            # Top edge in inches
    width: float                        # Width in inches
    height: float                       # Height in inches

    # Styling (computed from rules)
    fill_color: str = "#0073E6"
    stroke_color: Optional[str] = None
    shape_type: str = "rounded_rect"    # Shape to render
    corner_radius: float = 0.08
    z_order: int = 10

    # Text sizing (to be computed by text measurement)
    suggested_font_size: int = 14
    text_lines: List[str] = field(default_factory=list)

    # For special shapes
    custom_path: Optional[List[Any]] = None
    arrow_direction: Optional[str] = None

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2

    @property
    def right_edge(self) -> float:
        return self.x + self.width

    @property
    def bottom_edge(self) -> float:
        return self.y + self.height


@dataclass
class ConnectorPosition:
    """Computed position for a connector."""
    connector_id: str
    from_element_id: str
    to_element_id: str

    start_x: float
    start_y: float
    end_x: float
    end_y: float

    style: str = "arrow"
    color: str = "#666666"
    stroke_width: float = 1.5
    routing: str = "direct"

    # For orthogonal routing
    waypoints: List[Tuple[float, float]] = field(default_factory=list)

    # Optional label
    label: Optional[str] = None
    label_position: str = "middle"


@dataclass
class ContentBounds:
    """
    Bounds for content placement.

    Strategies work within these bounds, which may be adjusted
    if overlays are present.
    """
    left: float = CONTENT_LEFT
    top: float = CONTENT_TOP
    width: float = CONTENT_WIDTH
    height: float = CONTENT_HEIGHT

    @property
    def right(self) -> float:
        return self.left + self.width

    @property
    def bottom(self) -> float:
        return self.top + self.height

    @property
    def center_x(self) -> float:
        return self.left + self.width / 2

    @property
    def center_y(self) -> float:
        return self.top + self.height / 2


@dataclass
class StrategyResult:
    """
    Result from strategy computation.

    Contains all computed positions for elements and connectors.
    """
    elements: List[ElementPosition] = field(default_factory=list)
    connectors: List[ConnectorPosition] = field(default_factory=list)

    # Actual bounds used (may be smaller than available if content is compact)
    used_bounds: Optional[ContentBounds] = None

    # Warnings or notes from computation
    warnings: List[str] = field(default_factory=list)

    def get_element_by_id(self, element_id: str) -> Optional[ElementPosition]:
        """Find an element by ID."""
        for elem in self.elements:
            if elem.element_id == element_id:
                return elem
        return None


# =============================================================================
# BASE STRATEGY
# =============================================================================

class BaseLayoutStrategy(ABC):
    """
    Abstract base class for layout computation strategies.

    Each strategy knows how to arrange elements according to a specific
    pattern (grid, stack, radial, etc.). The strategy is selected based
    on the ArchetypeRules.
    """

    @abstractmethod
    def compute(
        self,
        input_data: DiagramInput,
        rules: ArchetypeRules,
        bounds: ContentBounds,
        palette: ColorPalette,
    ) -> StrategyResult:
        """
        Compute element positions based on input data and rules.

        Args:
            input_data: The diagram input data (blocks, connectors, layers)
            rules: The archetype rules defining layout behavior
            bounds: The content bounds to work within
            palette: Color palette for element colors

        Returns:
            StrategyResult with computed positions
        """
        pass

    # =========================================================================
    # HELPER METHODS (Available to all strategies)
    # =========================================================================

    def compute_element_size(
        self,
        block: BlockData,
        template: ElementTemplate,
        index: int,
        total_count: int,
        base_width: float,
        base_height: float,
    ) -> Tuple[float, float]:
        """
        Compute element size based on size rule.

        Returns (width, height) in inches.
        """
        size_rule = template.size_rule
        params = template.size_params

        if size_rule == SizeRule.UNIFORM:
            return (base_width, base_height)

        elif size_rule == SizeRule.PROGRESSIVE:
            # Size changes progressively
            progression_factor = params.width_progression ** index
            width = base_width * progression_factor
            height_factor = params.height_progression ** index
            height = base_height * height_factor
            return (width, height)

        elif size_rule == SizeRule.PROPORTIONAL:
            # Size based on weight/value (from metadata)
            weight = block.metadata.get('weight', 1.0)
            scale = max(params.min_size, min(params.max_size, weight))
            return (base_width * scale, base_height * scale)

        elif size_rule == SizeRule.FIXED:
            return (params.fixed_width, params.fixed_height)

        elif size_rule == SizeRule.TEXT_FIT:
            # Will be adjusted later by text measurement
            # Return reasonable default for now
            return (base_width, base_height)

        return (base_width, base_height)

    def compute_element_color(
        self,
        block: BlockData,
        template: ElementTemplate,
        index: int,
        total_count: int,
        palette: ColorPalette,
    ) -> str:
        """
        Compute element fill color based on color rule.

        Returns hex color string.
        """
        # Block-specific color override
        if block.color:
            return block.color

        color_rule = template.color_rule
        params = template.color_params

        if color_rule == ColorRule.UNIFORM:
            return params.uniform_color or palette.primary

        elif color_rule == ColorRule.PALETTE_SEQUENCE:
            return palette.get_color_for_index(index)

        elif color_rule == ColorRule.GRADIENT:
            # Interpolate between start and end color
            if params.start_color and params.end_color:
                return self._interpolate_color(
                    params.start_color,
                    params.end_color,
                    index / max(1, total_count - 1)
                )
            return palette.get_color_for_index(index)

        elif color_rule == ColorRule.EMPHASIS_BASED:
            # Based on emphasis level in block metadata
            emphasis = block.metadata.get('emphasis', 'normal')
            if emphasis == 'primary':
                return params.primary_color or palette.primary
            elif emphasis == 'secondary':
                return params.secondary_color or palette.secondary
            elif emphasis == 'accent':
                return params.accent_color or palette.tertiary
            return palette.secondary

        elif color_rule == ColorRule.LAYER_BASED:
            # Based on layer membership
            # This would need layer information passed in
            return palette.get_color_for_index(index)

        return palette.get_color_for_index(index)

    def _interpolate_color(
        self,
        start_color: str,
        end_color: str,
        ratio: float
    ) -> str:
        """Interpolate between two hex colors."""
        # Parse hex colors
        start = start_color.lstrip('#')
        end = end_color.lstrip('#')

        sr, sg, sb = int(start[0:2], 16), int(start[2:4], 16), int(start[4:6], 16)
        er, eg, eb = int(end[0:2], 16), int(end[2:4], 16), int(end[4:6], 16)

        # Interpolate
        r = int(sr + (er - sr) * ratio)
        g = int(sg + (eg - sg) * ratio)
        b = int(sb + (eb - sb) * ratio)

        return f"#{r:02x}{g:02x}{b:02x}"

    def apply_constraints(
        self,
        result: StrategyResult,
        constraints: List[LayoutConstraint],
        bounds: ContentBounds,
    ) -> StrategyResult:
        """
        Apply layout constraints to adjust positions.

        Called after initial layout computation to ensure constraints are met.
        """
        for constraint in sorted(constraints, key=lambda c: -c.priority):
            ct = constraint.constraint_type

            if ct == "min_spacing":
                result = self._apply_min_spacing(result, constraint.params)

            elif ct == "no_overlap":
                result = self._resolve_overlaps(result)

            elif ct == "within_bounds":
                result = self._ensure_within_bounds(result, bounds, constraint.params)

            elif ct == "alignment":
                result = self._apply_alignment(result, constraint.params)

        return result

    def _apply_min_spacing(
        self,
        result: StrategyResult,
        params: Dict[str, Any]
    ) -> StrategyResult:
        """Ensure minimum spacing between elements."""
        min_h = params.get('horizontal', GUTTER_H)
        min_v = params.get('vertical', GUTTER_V)

        # Sort elements by position
        elements = sorted(result.elements, key=lambda e: (e.y, e.x))

        for i, elem1 in enumerate(elements):
            for elem2 in elements[i+1:]:
                # Check horizontal spacing
                if self._elements_horizontally_adjacent(elem1, elem2):
                    gap = elem2.x - elem1.right_edge
                    if gap < min_h:
                        # Push elem2 right
                        elem2.x += (min_h - gap)

                # Check vertical spacing
                if self._elements_vertically_adjacent(elem1, elem2):
                    gap = elem2.y - elem1.bottom_edge
                    if gap < min_v:
                        # Push elem2 down
                        elem2.y += (min_v - gap)

        return result

    def _elements_horizontally_adjacent(
        self,
        e1: ElementPosition,
        e2: ElementPosition
    ) -> bool:
        """Check if two elements are horizontally adjacent."""
        # They're horizontally adjacent if they overlap vertically
        return (e1.y < e2.bottom_edge and e2.y < e1.bottom_edge)

    def _elements_vertically_adjacent(
        self,
        e1: ElementPosition,
        e2: ElementPosition
    ) -> bool:
        """Check if two elements are vertically adjacent."""
        # They're vertically adjacent if they overlap horizontally
        return (e1.x < e2.right_edge and e2.x < e1.right_edge)

    def _resolve_overlaps(self, result: StrategyResult) -> StrategyResult:
        """Resolve overlapping elements by adjusting positions."""
        # Simple approach: push overlapping elements apart
        max_iterations = 10
        for _ in range(max_iterations):
            any_overlap = False
            for i, elem1 in enumerate(result.elements):
                for elem2 in result.elements[i+1:]:
                    if self._elements_overlap(elem1, elem2):
                        any_overlap = True
                        self._separate_elements(elem1, elem2)
            if not any_overlap:
                break
        return result

    def _elements_overlap(
        self,
        e1: ElementPosition,
        e2: ElementPosition
    ) -> bool:
        """Check if two elements overlap."""
        return not (
            e1.right_edge <= e2.x or
            e2.right_edge <= e1.x or
            e1.bottom_edge <= e2.y or
            e2.bottom_edge <= e1.y
        )

    def _separate_elements(
        self,
        e1: ElementPosition,
        e2: ElementPosition
    ) -> None:
        """Push overlapping elements apart."""
        # Find overlap amounts
        overlap_x = min(e1.right_edge, e2.right_edge) - max(e1.x, e2.x)
        overlap_y = min(e1.bottom_edge, e2.bottom_edge) - max(e1.y, e2.y)

        # Move the element with smaller ID to maintain determinism
        if overlap_x < overlap_y:
            # Separate horizontally
            if e1.x < e2.x:
                e2.x += overlap_x / 2 + 0.1
                e1.x -= overlap_x / 2
            else:
                e1.x += overlap_x / 2 + 0.1
                e2.x -= overlap_x / 2
        else:
            # Separate vertically
            if e1.y < e2.y:
                e2.y += overlap_y / 2 + 0.1
                e1.y -= overlap_y / 2
            else:
                e1.y += overlap_y / 2 + 0.1
                e2.y -= overlap_y / 2

    def _ensure_within_bounds(
        self,
        result: StrategyResult,
        bounds: ContentBounds,
        params: Dict[str, Any]
    ) -> StrategyResult:
        """Ensure all elements are within bounds."""
        margin = params.get('margin', 0.1)

        for elem in result.elements:
            # Clamp to bounds
            if elem.x < bounds.left + margin:
                elem.x = bounds.left + margin
            if elem.y < bounds.top + margin:
                elem.y = bounds.top + margin
            if elem.right_edge > bounds.right - margin:
                elem.x = bounds.right - margin - elem.width
            if elem.bottom_edge > bounds.bottom - margin:
                elem.y = bounds.bottom - margin - elem.height

        return result

    def _apply_alignment(
        self,
        result: StrategyResult,
        params: Dict[str, Any]
    ) -> StrategyResult:
        """Apply alignment constraints."""
        align_type = params.get('type', 'center')
        axis = params.get('axis', 'horizontal')

        if axis == 'horizontal':
            if align_type == 'center':
                # Find center x of all elements
                if result.elements:
                    center_x = sum(e.center_x for e in result.elements) / len(result.elements)
                    for elem in result.elements:
                        elem.x = center_x - elem.width / 2
        elif axis == 'vertical':
            if align_type == 'center':
                if result.elements:
                    center_y = sum(e.center_y for e in result.elements) / len(result.elements)
                    for elem in result.elements:
                        elem.y = center_y - elem.height / 2

        return result

    def generate_sequential_connectors(
        self,
        elements: List[ElementPosition],
        style: str = "arrow",
        color: str = "#666666",
        routing: str = "direct",
    ) -> List[ConnectorPosition]:
        """Generate connectors between sequential elements."""
        connectors = []
        for i in range(len(elements) - 1):
            e1, e2 = elements[i], elements[i + 1]

            # Determine connection points based on relative positions
            if abs(e2.center_y - e1.center_y) < 0.1:
                # Horizontal connection
                if e2.x > e1.x:
                    start_x, start_y = e1.right_edge, e1.center_y
                    end_x, end_y = e2.x, e2.center_y
                else:
                    start_x, start_y = e1.x, e1.center_y
                    end_x, end_y = e2.right_edge, e2.center_y
            else:
                # Vertical connection
                if e2.y > e1.y:
                    start_x, start_y = e1.center_x, e1.bottom_edge
                    end_x, end_y = e2.center_x, e2.y
                else:
                    start_x, start_y = e1.center_x, e1.y
                    end_x, end_y = e2.center_x, e2.bottom_edge

            connectors.append(ConnectorPosition(
                connector_id=f"conn_{i}",
                from_element_id=e1.element_id,
                to_element_id=e2.element_id,
                start_x=start_x,
                start_y=start_y,
                end_x=end_x,
                end_y=end_y,
                style=style,
                color=color,
                routing=routing,
            ))

        return connectors
