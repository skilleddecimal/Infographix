"""
connector_router.py — Smart connector routing with obstacle avoidance.

Provides orthogonal (right-angle) connector routing that avoids overlapping
with other elements on the slide. Uses A* pathfinding on a grid.

Usage:
    from backend.engine.connector_router import ConnectorRouter

    router = ConnectorRouter(elements)
    waypoints = router.route(from_element, to_element)
"""

import math
import heapq
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum

from .positioned import (
    PositionedElement,
    PositionedConnector,
    RoutingStyle,
    AnchorPosition,
    ConnectorStyle,
)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class Point:
    """A 2D point in inches."""
    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        """Euclidean distance to another point."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def manhattan_distance_to(self, other: "Point") -> float:
        """Manhattan distance to another point (for orthogonal routing)."""
        return abs(self.x - other.x) + abs(self.y - other.y)

    def __hash__(self):
        return hash((round(self.x, 4), round(self.y, 4)))

    def __eq__(self, other):
        if not isinstance(other, Point):
            return False
        return abs(self.x - other.x) < 0.001 and abs(self.y - other.y) < 0.001


@dataclass
class BoundingBox:
    """Axis-aligned bounding box."""
    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def center(self) -> Point:
        return Point((self.left + self.right) / 2, (self.top + self.bottom) / 2)

    def expanded(self, margin: float) -> "BoundingBox":
        """Return a new box expanded by margin on all sides."""
        return BoundingBox(
            self.left - margin,
            self.top - margin,
            self.right + margin,
            self.bottom + margin,
        )

    def contains_point(self, p: Point) -> bool:
        """Check if a point is inside this box."""
        return self.left <= p.x <= self.right and self.top <= p.y <= self.bottom

    def intersects(self, other: "BoundingBox") -> bool:
        """Check if this box intersects another box."""
        return not (
            self.right < other.left or
            other.right < self.left or
            self.bottom < other.top or
            other.bottom < self.top
        )

    @classmethod
    def from_element(cls, elem: PositionedElement) -> "BoundingBox":
        """Create bounding box from a positioned element."""
        return cls(
            left=elem.x_inches,
            top=elem.y_inches,
            right=elem.x_inches + elem.width_inches,
            bottom=elem.y_inches + elem.height_inches,
        )


@dataclass
class GridCell:
    """A cell in the obstacle grid."""
    row: int
    col: int
    blocked: bool = False


# =============================================================================
# ANCHOR POINT CALCULATION
# =============================================================================

def get_anchor_point(
    element: PositionedElement,
    anchor: AnchorPosition,
    target: Optional[Point] = None
) -> Point:
    """
    Get the anchor point on an element's edge.

    Args:
        element: The element to get anchor from
        anchor: Which edge/position to anchor to
        target: Optional target point for AUTO anchor selection

    Returns:
        Point at the anchor position
    """
    box = BoundingBox.from_element(element)
    center = box.center

    if anchor == AnchorPosition.TOP:
        return Point(center.x, box.top)
    elif anchor == AnchorPosition.BOTTOM:
        return Point(center.x, box.bottom)
    elif anchor == AnchorPosition.LEFT:
        return Point(box.left, center.y)
    elif anchor == AnchorPosition.RIGHT:
        return Point(box.right, center.y)
    elif anchor == AnchorPosition.CENTER:
        return center
    elif anchor == AnchorPosition.AUTO and target:
        # Auto-select best anchor based on target position
        return _auto_select_anchor(element, target)
    else:
        return center


def _auto_select_anchor(element: PositionedElement, target: Point) -> Point:
    """
    Automatically select the best anchor point based on target position.

    Chooses the anchor that is closest to the target while maintaining
    clean orthogonal routing.
    """
    box = BoundingBox.from_element(element)
    center = box.center

    # Calculate direction to target
    dx = target.x - center.x
    dy = target.y - center.y

    # Choose based on primary direction
    if abs(dx) > abs(dy):
        # Horizontal is dominant
        if dx > 0:
            return Point(box.right, center.y)  # Right anchor
        else:
            return Point(box.left, center.y)   # Left anchor
    else:
        # Vertical is dominant
        if dy > 0:
            return Point(center.x, box.bottom)  # Bottom anchor
        else:
            return Point(center.x, box.top)     # Top anchor


def get_best_anchors(
    from_elem: PositionedElement,
    to_elem: PositionedElement
) -> Tuple[AnchorPosition, AnchorPosition]:
    """
    Determine optimal anchor positions for both elements.

    Returns the pair of anchors that would result in the shortest
    orthogonal path.
    """
    from_box = BoundingBox.from_element(from_elem)
    to_box = BoundingBox.from_element(to_elem)

    from_center = from_box.center
    to_center = to_box.center

    dx = to_center.x - from_center.x
    dy = to_center.y - from_center.y

    # Determine if elements are primarily horizontally or vertically separated
    if abs(dx) > abs(dy):
        # Horizontal separation dominates
        if dx > 0:
            # Target is to the right
            return (AnchorPosition.RIGHT, AnchorPosition.LEFT)
        else:
            # Target is to the left
            return (AnchorPosition.LEFT, AnchorPosition.RIGHT)
    else:
        # Vertical separation dominates
        if dy > 0:
            # Target is below
            return (AnchorPosition.BOTTOM, AnchorPosition.TOP)
        else:
            # Target is above
            return (AnchorPosition.TOP, AnchorPosition.BOTTOM)


# =============================================================================
# OBSTACLE GRID
# =============================================================================

class ObstacleGrid:
    """
    Grid-based representation of obstacles for pathfinding.

    Converts element bounding boxes into a grid where blocked cells
    cannot be traversed.
    """

    def __init__(
        self,
        width_inches: float,
        height_inches: float,
        cell_size: float = 0.1,
        margin: float = 0.05
    ):
        """
        Initialize the obstacle grid.

        Args:
            width_inches: Total width of the slide
            height_inches: Total height of the slide
            cell_size: Size of each grid cell in inches
            margin: Margin around obstacles to avoid
        """
        self.width = width_inches
        self.height = height_inches
        self.cell_size = cell_size
        self.margin = margin

        self.cols = int(math.ceil(width_inches / cell_size))
        self.rows = int(math.ceil(height_inches / cell_size))

        # Grid of blocked cells (True = blocked)
        self.grid: List[List[bool]] = [
            [False for _ in range(self.cols)]
            for _ in range(self.rows)
        ]

    def add_obstacle(self, box: BoundingBox) -> None:
        """Mark all cells within a bounding box as blocked."""
        expanded = box.expanded(self.margin)

        min_col = max(0, int(expanded.left / self.cell_size))
        max_col = min(self.cols - 1, int(expanded.right / self.cell_size))
        min_row = max(0, int(expanded.top / self.cell_size))
        max_row = min(self.rows - 1, int(expanded.bottom / self.cell_size))

        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                self.grid[row][col] = True

    def add_element(self, element: PositionedElement) -> None:
        """Add an element as an obstacle."""
        self.add_obstacle(BoundingBox.from_element(element))

    def is_blocked(self, row: int, col: int) -> bool:
        """Check if a cell is blocked."""
        if row < 0 or row >= self.rows or col < 0 or col >= self.cols:
            return True  # Out of bounds is blocked
        return self.grid[row][col]

    def point_to_cell(self, p: Point) -> Tuple[int, int]:
        """Convert a point to grid cell coordinates."""
        col = int(p.x / self.cell_size)
        row = int(p.y / self.cell_size)
        return (row, col)

    def cell_to_point(self, row: int, col: int) -> Point:
        """Convert grid cell to center point."""
        return Point(
            (col + 0.5) * self.cell_size,
            (row + 0.5) * self.cell_size
        )

    def get_neighbors(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get valid (non-blocked) orthogonal neighbors of a cell."""
        neighbors = []
        # Only orthogonal movement (4-connected)
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = row + dr, col + dc
            if not self.is_blocked(nr, nc):
                neighbors.append((nr, nc))
        return neighbors


# =============================================================================
# A* PATHFINDING
# =============================================================================

def astar_path(
    grid: ObstacleGrid,
    start: Point,
    end: Point
) -> Optional[List[Point]]:
    """
    Find shortest orthogonal path using A* algorithm.

    Args:
        grid: Obstacle grid
        start: Starting point
        end: Ending point

    Returns:
        List of waypoints (excluding start/end), or None if no path found
    """
    start_cell = grid.point_to_cell(start)
    end_cell = grid.point_to_cell(end)

    # Temporarily unblock start and end cells
    start_row, start_col = start_cell
    end_row, end_col = end_cell

    # Handle out of bounds
    if (start_row < 0 or start_row >= grid.rows or
        start_col < 0 or start_col >= grid.cols or
        end_row < 0 or end_row >= grid.rows or
        end_col < 0 or end_col >= grid.cols):
        return None

    # Priority queue: (f_score, g_score, row, col, path)
    open_set: List[Tuple[float, float, int, int, List[Tuple[int, int]]]] = []
    heapq.heappush(open_set, (0, 0, start_row, start_col, []))

    # Track visited cells
    visited: Set[Tuple[int, int]] = set()

    while open_set:
        f_score, g_score, row, col, path = heapq.heappop(open_set)

        if (row, col) in visited:
            continue
        visited.add((row, col))

        # Check if we reached the goal
        if row == end_row and col == end_col:
            # Convert path to points
            waypoints = []
            for r, c in path:
                waypoints.append(grid.cell_to_point(r, c))
            return waypoints

        # Explore neighbors
        for nr, nc in grid.get_neighbors(row, col):
            if (nr, nc) in visited:
                continue

            # Allow traversing to end cell even if blocked
            if (nr, nc) != (end_row, end_col) and grid.is_blocked(nr, nc):
                continue

            new_g = g_score + 1  # Cost of one step
            h = abs(nr - end_row) + abs(nc - end_col)  # Manhattan heuristic
            new_f = new_g + h

            new_path = path + [(row, col)]
            heapq.heappush(open_set, (new_f, new_g, nr, nc, new_path))

    return None  # No path found


# =============================================================================
# PATH SIMPLIFICATION
# =============================================================================

def simplify_path(points: List[Point]) -> List[Point]:
    """
    Simplify a path by removing collinear intermediate points.

    This reduces the number of waypoints while maintaining the same path shape.
    """
    if len(points) <= 2:
        return points

    simplified = [points[0]]

    for i in range(1, len(points) - 1):
        prev = simplified[-1]
        curr = points[i]
        next_pt = points[i + 1]

        # Check if current point is collinear with prev and next
        # (same x or same y for orthogonal paths)
        same_x = abs(prev.x - curr.x) < 0.001 and abs(curr.x - next_pt.x) < 0.001
        same_y = abs(prev.y - curr.y) < 0.001 and abs(curr.y - next_pt.y) < 0.001

        if not (same_x or same_y):
            # Keep this point as it's a turn
            simplified.append(curr)

    simplified.append(points[-1])
    return simplified


def smooth_corners(
    points: List[Point],
    radius: float = 0.05
) -> List[Tuple[str, List[Point]]]:
    """
    Convert sharp corners to rounded arcs.

    Returns a list of (segment_type, points) tuples where segment_type
    is either "line" or "arc".
    """
    if len(points) <= 2:
        return [("line", points)]

    segments = []

    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]

        if i == 0:
            # First segment starts at p1
            segments.append(("line", [p1, p2]))
        elif i == len(points) - 2:
            # Last segment ends at p2 (handled by previous iteration)
            pass
        else:
            # Middle segment - add rounded corner
            # For simplicity, we'll just add a small arc indicator
            # Full arc rendering is handled by the renderer
            segments.append(("corner", [p1, radius]))
            segments.append(("line", [p1, p2]))

    return segments


# =============================================================================
# CONNECTOR ROUTER
# =============================================================================

class ConnectorRouter:
    """
    Smart connector routing with obstacle avoidance.

    Computes optimal paths between elements while avoiding overlaps
    with other shapes on the slide.
    """

    def __init__(
        self,
        slide_width: float,
        slide_height: float,
        elements: Optional[List[PositionedElement]] = None,
        cell_size: float = 0.1,
        obstacle_margin: float = 0.1
    ):
        """
        Initialize the connector router.

        Args:
            slide_width: Width of the slide in inches
            slide_height: Height of the slide in inches
            elements: List of elements to treat as obstacles
            cell_size: Grid cell size for pathfinding
            obstacle_margin: Margin around obstacles to avoid
        """
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.cell_size = cell_size
        self.obstacle_margin = obstacle_margin

        self.grid = ObstacleGrid(
            slide_width,
            slide_height,
            cell_size=cell_size,
            margin=obstacle_margin
        )

        self._elements: Dict[str, PositionedElement] = {}

        if elements:
            for elem in elements:
                self.add_obstacle(elem)

    def add_obstacle(self, element: PositionedElement) -> None:
        """Add an element as an obstacle."""
        self._elements[element.id] = element
        self.grid.add_element(element)

    def remove_obstacle(self, element_id: str) -> None:
        """Remove an element from obstacles."""
        if element_id in self._elements:
            del self._elements[element_id]
            # Rebuild grid (simple approach)
            self._rebuild_grid()

    def _rebuild_grid(self) -> None:
        """Rebuild the obstacle grid from current elements."""
        self.grid = ObstacleGrid(
            self.slide_width,
            self.slide_height,
            cell_size=self.cell_size,
            margin=self.obstacle_margin
        )
        for elem in self._elements.values():
            self.grid.add_element(elem)

    def route(
        self,
        from_element: PositionedElement,
        to_element: PositionedElement,
        routing_style: RoutingStyle = RoutingStyle.ORTHOGONAL,
        from_anchor: AnchorPosition = AnchorPosition.AUTO,
        to_anchor: AnchorPosition = AnchorPosition.AUTO,
    ) -> List[Tuple[float, float]]:
        """
        Compute the optimal route between two elements.

        Args:
            from_element: Source element
            to_element: Target element
            routing_style: How to route (direct, orthogonal, etc.)
            from_anchor: Anchor on source element
            to_anchor: Anchor on target element

        Returns:
            List of waypoint coordinates (excluding start/end points)
        """
        # Determine anchor points
        if from_anchor == AnchorPosition.AUTO or to_anchor == AnchorPosition.AUTO:
            auto_from, auto_to = get_best_anchors(from_element, to_element)
            if from_anchor == AnchorPosition.AUTO:
                from_anchor = auto_from
            if to_anchor == AnchorPosition.AUTO:
                to_anchor = auto_to

        # Get anchor positions
        to_center = BoundingBox.from_element(to_element).center
        from_center = BoundingBox.from_element(from_element).center

        start_point = get_anchor_point(from_element, from_anchor, to_center)
        end_point = get_anchor_point(to_element, to_anchor, from_center)

        if routing_style == RoutingStyle.DIRECT:
            # Direct line - no waypoints
            return []

        elif routing_style == RoutingStyle.STEPPED:
            # Single L-shaped step
            return self._route_stepped(start_point, end_point)

        elif routing_style == RoutingStyle.ORTHOGONAL:
            # Full A* orthogonal routing
            return self._route_orthogonal(
                start_point, end_point,
                from_element, to_element
            )

        elif routing_style == RoutingStyle.CURVED:
            # Curved routing (use bezier control points as waypoints)
            return self._route_curved(start_point, end_point)

        return []

    def _route_stepped(
        self,
        start: Point,
        end: Point
    ) -> List[Tuple[float, float]]:
        """
        Create a simple L-shaped route with one turn.
        """
        # Decide whether to go horizontal-then-vertical or vice versa
        dx = end.x - start.x
        dy = end.y - start.y

        if abs(dx) > abs(dy):
            # Horizontal first, then vertical
            mid = Point(start.x + dx / 2, start.y)
            return [(mid.x, mid.y), (mid.x, end.y)]
        else:
            # Vertical first, then horizontal
            mid = Point(start.x, start.y + dy / 2)
            return [(mid.x, mid.y), (end.x, mid.y)]

    def _route_orthogonal(
        self,
        start: Point,
        end: Point,
        from_elem: PositionedElement,
        to_elem: PositionedElement
    ) -> List[Tuple[float, float]]:
        """
        Route using A* pathfinding with obstacle avoidance.
        """
        # Temporarily remove source and target from obstacles
        # (they shouldn't block their own connection)
        original_grid = self.grid

        temp_grid = ObstacleGrid(
            self.slide_width,
            self.slide_height,
            cell_size=self.cell_size,
            margin=self.obstacle_margin
        )

        for elem_id, elem in self._elements.items():
            if elem_id != from_elem.id and elem_id != to_elem.id:
                temp_grid.add_element(elem)

        # Find path
        path_points = astar_path(temp_grid, start, end)

        if path_points is None:
            # Fallback to stepped routing if no path found
            return self._route_stepped(start, end)

        # Add start and end points
        full_path = [start] + path_points + [end]

        # Simplify the path
        simplified = simplify_path(full_path)

        # Return waypoints (excluding start and end)
        waypoints = [(p.x, p.y) for p in simplified[1:-1]]

        return waypoints

    def _route_curved(
        self,
        start: Point,
        end: Point
    ) -> List[Tuple[float, float]]:
        """
        Create bezier curve control points for a smooth curve.

        Returns two control points for a cubic bezier curve.
        """
        dx = end.x - start.x
        dy = end.y - start.y

        # Control points at 1/3 and 2/3 of the way
        # Offset perpendicular to the line for a smooth curve
        mid_x = (start.x + end.x) / 2
        mid_y = (start.y + end.y) / 2

        # Perpendicular offset based on direction
        if abs(dx) > abs(dy):
            # Primarily horizontal - curve vertically
            offset = abs(dx) * 0.2
            cp1 = (start.x + dx * 0.3, start.y + offset * (1 if dy > 0 else -1))
            cp2 = (start.x + dx * 0.7, end.y - offset * (1 if dy > 0 else -1))
        else:
            # Primarily vertical - curve horizontally
            offset = abs(dy) * 0.2
            cp1 = (start.x + offset * (1 if dx > 0 else -1), start.y + dy * 0.3)
            cp2 = (end.x - offset * (1 if dx > 0 else -1), start.y + dy * 0.7)

        return [cp1, cp2]

    def route_connector(
        self,
        connector: PositionedConnector,
        elements_by_id: Dict[str, PositionedElement]
    ) -> PositionedConnector:
        """
        Route a connector and update its waypoints.

        Args:
            connector: The connector to route
            elements_by_id: Dictionary of elements by ID

        Returns:
            Updated connector with waypoints
        """
        from_elem = elements_by_id.get(connector.from_element_id)
        to_elem = elements_by_id.get(connector.to_element_id)

        if not from_elem or not to_elem:
            return connector

        waypoints = self.route(
            from_elem,
            to_elem,
            routing_style=connector.routing_style,
            from_anchor=connector.from_anchor,
            to_anchor=connector.to_anchor,
        )

        connector.waypoints = waypoints

        # Update start/end points based on anchors
        to_center = BoundingBox.from_element(to_elem).center
        from_center = BoundingBox.from_element(from_elem).center

        if connector.from_anchor == AnchorPosition.AUTO:
            auto_from, _ = get_best_anchors(from_elem, to_elem)
            start_point = get_anchor_point(from_elem, auto_from, to_center)
        else:
            start_point = get_anchor_point(from_elem, connector.from_anchor, to_center)

        if connector.to_anchor == AnchorPosition.AUTO:
            _, auto_to = get_best_anchors(from_elem, to_elem)
            end_point = get_anchor_point(to_elem, auto_to, from_center)
        else:
            end_point = get_anchor_point(to_elem, connector.to_anchor, from_center)

        connector.start_x = start_point.x
        connector.start_y = start_point.y
        connector.end_x = end_point.x
        connector.end_y = end_point.y

        return connector


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def route_all_connectors(
    connectors: List[PositionedConnector],
    elements: List[PositionedElement],
    slide_width: float,
    slide_height: float,
    routing_style: RoutingStyle = RoutingStyle.ORTHOGONAL
) -> List[PositionedConnector]:
    """
    Route all connectors in a layout with obstacle avoidance.

    Args:
        connectors: List of connectors to route
        elements: List of elements (obstacles)
        slide_width: Slide width in inches
        slide_height: Slide height in inches
        routing_style: Default routing style for connectors

    Returns:
        Updated list of connectors with waypoints
    """
    router = ConnectorRouter(
        slide_width=slide_width,
        slide_height=slide_height,
        elements=elements
    )

    elements_by_id = {e.id: e for e in elements}

    for connector in connectors:
        if connector.routing_style == RoutingStyle.DIRECT:
            # Skip direct connectors
            continue

        if connector.routing_style == RoutingStyle.DIRECT:
            connector.routing_style = routing_style

        router.route_connector(connector, elements_by_id)

    return connectors
