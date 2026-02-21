"""Snapping constraints for grid and guide alignment."""

from dataclasses import dataclass, field
from enum import Enum

from backend.dsl.schema import BoundingBox, Shape


class SnapTarget(str, Enum):
    """What to snap shapes to."""

    GRID = "grid"
    GUIDES = "guides"
    SHAPES = "shapes"
    CANVAS_CENTER = "canvas_center"
    CANVAS_EDGES = "canvas_edges"


@dataclass
class Guide:
    """A guide line for snapping."""

    position: int  # Position in EMUs
    orientation: str  # "horizontal" or "vertical"
    is_center: bool = False


@dataclass
class SnapResult:
    """Result of a snap operation."""

    snapped: bool
    original_x: int
    original_y: int
    snapped_x: int
    snapped_y: int
    snap_type: str | None = None  # "grid", "guide", "shape", etc.


@dataclass
class SnappingConstraint:
    """Defines snapping behavior for shapes."""

    grid_size: int = 91440  # Default 0.1 inch grid
    snap_threshold: int = 45720  # Snap within 0.05 inch
    guides: list[Guide] = field(default_factory=list)
    snap_targets: list[SnapTarget] = field(
        default_factory=lambda: [SnapTarget.GRID, SnapTarget.GUIDES]
    )
    canvas_width: int = 12192000
    canvas_height: int = 6858000

    def snap_shape(self, shape: Shape) -> tuple[Shape, SnapResult]:
        """Snap a shape to the nearest grid/guide.

        Args:
            shape: Shape to snap.

        Returns:
            Tuple of (snapped shape, snap result).
        """
        best_x = shape.bbox.x
        best_y = shape.bbox.y
        snap_type = None

        # Try each snap target in order
        for target in self.snap_targets:
            if target == SnapTarget.GRID:
                snapped_x, snapped_y, did_snap = self._snap_to_grid(
                    shape.bbox.x, shape.bbox.y
                )
                if did_snap:
                    best_x, best_y = snapped_x, snapped_y
                    snap_type = "grid"

            elif target == SnapTarget.GUIDES:
                snapped_x, snapped_y, did_snap = self._snap_to_guides(
                    shape.bbox.x, shape.bbox.y, shape.bbox
                )
                if did_snap:
                    best_x, best_y = snapped_x, snapped_y
                    snap_type = "guide"

            elif target == SnapTarget.CANVAS_CENTER:
                snapped_x, snapped_y, did_snap = self._snap_to_canvas_center(
                    shape.bbox.x, shape.bbox.y, shape.bbox
                )
                if did_snap:
                    best_x, best_y = snapped_x, snapped_y
                    snap_type = "canvas_center"

            elif target == SnapTarget.CANVAS_EDGES:
                snapped_x, snapped_y, did_snap = self._snap_to_canvas_edges(
                    shape.bbox.x, shape.bbox.y, shape.bbox
                )
                if did_snap:
                    best_x, best_y = snapped_x, snapped_y
                    snap_type = "canvas_edge"

        # Create result
        result = SnapResult(
            snapped=best_x != shape.bbox.x or best_y != shape.bbox.y,
            original_x=shape.bbox.x,
            original_y=shape.bbox.y,
            snapped_x=best_x,
            snapped_y=best_y,
            snap_type=snap_type,
        )

        # Create snapped shape if needed
        if result.snapped:
            new_bbox = BoundingBox(
                x=best_x,
                y=best_y,
                width=shape.bbox.width,
                height=shape.bbox.height,
            )
            shape_dict = shape.model_dump()
            shape_dict["bbox"] = new_bbox
            return Shape(**shape_dict), result

        return shape, result

    def snap_shapes(self, shapes: list[Shape]) -> list[Shape]:
        """Snap multiple shapes.

        Args:
            shapes: Shapes to snap.

        Returns:
            Snapped shapes.
        """
        return [self.snap_shape(s)[0] for s in shapes]

    def _snap_to_grid(
        self, x: int, y: int
    ) -> tuple[int, int, bool]:
        """Snap coordinates to grid.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Tuple of (snapped_x, snapped_y, did_snap).
        """
        # Find nearest grid lines
        grid_x = round(x / self.grid_size) * self.grid_size
        grid_y = round(y / self.grid_size) * self.grid_size

        # Check if within threshold
        x_diff = abs(x - grid_x)
        y_diff = abs(y - grid_y)

        snapped_x = grid_x if x_diff <= self.snap_threshold else x
        snapped_y = grid_y if y_diff <= self.snap_threshold else y

        did_snap = snapped_x != x or snapped_y != y
        return snapped_x, snapped_y, did_snap

    def _snap_to_guides(
        self, x: int, y: int, bbox: BoundingBox
    ) -> tuple[int, int, bool]:
        """Snap to guide lines.

        Args:
            x: X coordinate.
            y: Y coordinate.
            bbox: Shape bounding box (for center/edge snapping).

        Returns:
            Tuple of (snapped_x, snapped_y, did_snap).
        """
        snapped_x = x
        snapped_y = y
        did_snap = False

        for guide in self.guides:
            if guide.orientation == "vertical":
                # Check left edge, center, and right edge
                positions = [
                    (x, x),  # Left edge
                    (x + bbox.width // 2, x + bbox.width // 2 - guide.position),
                    (x + bbox.width, x - bbox.width),  # Right edge
                ]

                for pos, offset in [(x, 0), (x + bbox.width // 2, -bbox.width // 2)]:
                    if abs(pos - guide.position) <= self.snap_threshold:
                        snapped_x = guide.position + offset
                        did_snap = True
                        break

            elif guide.orientation == "horizontal":
                for pos, offset in [(y, 0), (y + bbox.height // 2, -bbox.height // 2)]:
                    if abs(pos - guide.position) <= self.snap_threshold:
                        snapped_y = guide.position + offset
                        did_snap = True
                        break

        return snapped_x, snapped_y, did_snap

    def _snap_to_canvas_center(
        self, x: int, y: int, bbox: BoundingBox
    ) -> tuple[int, int, bool]:
        """Snap shape center to canvas center.

        Args:
            x: X coordinate.
            y: Y coordinate.
            bbox: Shape bounding box.

        Returns:
            Tuple of (snapped_x, snapped_y, did_snap).
        """
        center_x = self.canvas_width // 2
        center_y = self.canvas_height // 2

        shape_center_x = x + bbox.width // 2
        shape_center_y = y + bbox.height // 2

        snapped_x = x
        snapped_y = y
        did_snap = False

        if abs(shape_center_x - center_x) <= self.snap_threshold:
            snapped_x = center_x - bbox.width // 2
            did_snap = True

        if abs(shape_center_y - center_y) <= self.snap_threshold:
            snapped_y = center_y - bbox.height // 2
            did_snap = True

        return snapped_x, snapped_y, did_snap

    def _snap_to_canvas_edges(
        self, x: int, y: int, bbox: BoundingBox
    ) -> tuple[int, int, bool]:
        """Snap shape edges to canvas edges.

        Args:
            x: X coordinate.
            y: Y coordinate.
            bbox: Shape bounding box.

        Returns:
            Tuple of (snapped_x, snapped_y, did_snap).
        """
        snapped_x = x
        snapped_y = y
        did_snap = False

        # Margin for edge snapping
        margin = 457200  # 0.5 inch

        # Left edge
        if abs(x - margin) <= self.snap_threshold:
            snapped_x = margin
            did_snap = True

        # Right edge
        right = x + bbox.width
        if abs(right - (self.canvas_width - margin)) <= self.snap_threshold:
            snapped_x = self.canvas_width - margin - bbox.width
            did_snap = True

        # Top edge
        if abs(y - margin) <= self.snap_threshold:
            snapped_y = margin
            did_snap = True

        # Bottom edge
        bottom = y + bbox.height
        if abs(bottom - (self.canvas_height - margin)) <= self.snap_threshold:
            snapped_y = self.canvas_height - margin - bbox.height
            did_snap = True

        return snapped_x, snapped_y, did_snap


def snap_to_grid(
    shapes: list[Shape],
    grid_size: int = 91440,
    snap_threshold: int = 45720,
) -> list[Shape]:
    """Convenience function to snap shapes to grid.

    Args:
        shapes: Shapes to snap.
        grid_size: Grid cell size in EMUs.
        snap_threshold: Maximum distance to snap.

    Returns:
        Snapped shapes.
    """
    constraint = SnappingConstraint(
        grid_size=grid_size,
        snap_threshold=snap_threshold,
        snap_targets=[SnapTarget.GRID],
    )
    return constraint.snap_shapes(shapes)


def snap_to_guides(
    shapes: list[Shape],
    guides: list[Guide],
    snap_threshold: int = 45720,
) -> list[Shape]:
    """Convenience function to snap shapes to guides.

    Args:
        shapes: Shapes to snap.
        guides: Guide lines.
        snap_threshold: Maximum distance to snap.

    Returns:
        Snapped shapes.
    """
    constraint = SnappingConstraint(
        guides=guides,
        snap_threshold=snap_threshold,
        snap_targets=[SnapTarget.GUIDES],
    )
    return constraint.snap_shapes(shapes)


def create_canvas_guides(
    canvas_width: int = 12192000,
    canvas_height: int = 6858000,
    include_thirds: bool = True,
    include_margins: bool = True,
) -> list[Guide]:
    """Create standard canvas guides.

    Args:
        canvas_width: Canvas width in EMUs.
        canvas_height: Canvas height in EMUs.
        include_thirds: Include rule-of-thirds guides.
        include_margins: Include margin guides.

    Returns:
        List of Guide objects.
    """
    guides = [
        # Center guides
        Guide(position=canvas_width // 2, orientation="vertical", is_center=True),
        Guide(position=canvas_height // 2, orientation="horizontal", is_center=True),
    ]

    if include_thirds:
        # Rule of thirds
        guides.extend([
            Guide(position=canvas_width // 3, orientation="vertical"),
            Guide(position=2 * canvas_width // 3, orientation="vertical"),
            Guide(position=canvas_height // 3, orientation="horizontal"),
            Guide(position=2 * canvas_height // 3, orientation="horizontal"),
        ])

    if include_margins:
        # Standard margins (0.5 inch = 457200 EMUs)
        margin = 457200
        guides.extend([
            Guide(position=margin, orientation="vertical"),
            Guide(position=canvas_width - margin, orientation="vertical"),
            Guide(position=margin, orientation="horizontal"),
            Guide(position=canvas_height - margin, orientation="horizontal"),
        ])

    return guides


def align_to_shape(
    shape_to_align: Shape,
    reference_shape: Shape,
    align_type: str = "center",
    snap_threshold: int = 45720,
) -> Shape:
    """Align one shape to another if within snap threshold.

    Args:
        shape_to_align: Shape to move.
        reference_shape: Shape to align to.
        align_type: "left", "center", "right", "top", "middle", "bottom".
        snap_threshold: Maximum distance to snap.

    Returns:
        Aligned shape.
    """
    bbox = shape_to_align.bbox
    ref_bbox = reference_shape.bbox
    new_x = bbox.x
    new_y = bbox.y

    if align_type == "left":
        if abs(bbox.x - ref_bbox.x) <= snap_threshold:
            new_x = ref_bbox.x
    elif align_type == "center":
        if abs(bbox.center_x - ref_bbox.center_x) <= snap_threshold:
            new_x = ref_bbox.center_x - bbox.width // 2
    elif align_type == "right":
        if abs(bbox.right - ref_bbox.right) <= snap_threshold:
            new_x = ref_bbox.right - bbox.width
    elif align_type == "top":
        if abs(bbox.y - ref_bbox.y) <= snap_threshold:
            new_y = ref_bbox.y
    elif align_type == "middle":
        if abs(bbox.center_y - ref_bbox.center_y) <= snap_threshold:
            new_y = ref_bbox.center_y - bbox.height // 2
    elif align_type == "bottom":
        if abs(bbox.bottom - ref_bbox.bottom) <= snap_threshold:
            new_y = ref_bbox.bottom - bbox.height

    if new_x != bbox.x or new_y != bbox.y:
        new_bbox = BoundingBox(
            x=new_x,
            y=new_y,
            width=bbox.width,
            height=bbox.height,
        )
        shape_dict = shape_to_align.model_dump()
        shape_dict["bbox"] = new_bbox
        return Shape(**shape_dict)

    return shape_to_align
