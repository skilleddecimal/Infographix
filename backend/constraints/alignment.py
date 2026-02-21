"""Alignment constraints for layout consistency."""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from backend.dsl.schema import BoundingBox, Shape


class AlignType(str, Enum):
    """Alignment types."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    TOP = "top"
    MIDDLE = "middle"
    BOTTOM = "bottom"
    DISTRIBUTE_H = "distribute_horizontal"
    DISTRIBUTE_V = "distribute_vertical"


@dataclass
class AlignmentConstraint:
    """Defines an alignment constraint between shapes."""

    shapes: list[Shape]
    align_type: AlignType
    reference: int | None = None  # Reference position in EMUs, or None for auto

    def apply(self) -> list[Shape]:
        """Apply the alignment constraint.

        Returns:
            List of shapes with adjusted positions.
        """
        if not self.shapes:
            return []

        if self.align_type == AlignType.LEFT:
            return self._align_left()
        elif self.align_type == AlignType.CENTER:
            return self._align_center_h()
        elif self.align_type == AlignType.RIGHT:
            return self._align_right()
        elif self.align_type == AlignType.TOP:
            return self._align_top()
        elif self.align_type == AlignType.MIDDLE:
            return self._align_center_v()
        elif self.align_type == AlignType.BOTTOM:
            return self._align_bottom()
        elif self.align_type == AlignType.DISTRIBUTE_H:
            return self._distribute_horizontal()
        elif self.align_type == AlignType.DISTRIBUTE_V:
            return self._distribute_vertical()

        return self.shapes

    def _align_left(self) -> list[Shape]:
        """Align shapes to left edge."""
        if self.reference is not None:
            target_x = self.reference
        else:
            target_x = min(s.bbox.x for s in self.shapes)

        return self._update_x(target_x)

    def _align_center_h(self) -> list[Shape]:
        """Align shapes to horizontal center."""
        if self.reference is not None:
            target_center = self.reference
        else:
            centers = [s.bbox.center_x for s in self.shapes]
            target_center = sum(centers) // len(centers)

        fixed = []
        for shape in self.shapes:
            new_x = target_center - shape.bbox.width // 2
            fixed.append(self._update_shape_x(shape, new_x))
        return fixed

    def _align_right(self) -> list[Shape]:
        """Align shapes to right edge."""
        if self.reference is not None:
            target_right = self.reference
        else:
            target_right = max(s.bbox.right for s in self.shapes)

        fixed = []
        for shape in self.shapes:
            new_x = target_right - shape.bbox.width
            fixed.append(self._update_shape_x(shape, new_x))
        return fixed

    def _align_top(self) -> list[Shape]:
        """Align shapes to top edge."""
        if self.reference is not None:
            target_y = self.reference
        else:
            target_y = min(s.bbox.y for s in self.shapes)

        return self._update_y(target_y)

    def _align_center_v(self) -> list[Shape]:
        """Align shapes to vertical center."""
        if self.reference is not None:
            target_center = self.reference
        else:
            centers = [s.bbox.center_y for s in self.shapes]
            target_center = sum(centers) // len(centers)

        fixed = []
        for shape in self.shapes:
            new_y = target_center - shape.bbox.height // 2
            fixed.append(self._update_shape_y(shape, new_y))
        return fixed

    def _align_bottom(self) -> list[Shape]:
        """Align shapes to bottom edge."""
        if self.reference is not None:
            target_bottom = self.reference
        else:
            target_bottom = max(s.bbox.bottom for s in self.shapes)

        fixed = []
        for shape in self.shapes:
            new_y = target_bottom - shape.bbox.height
            fixed.append(self._update_shape_y(shape, new_y))
        return fixed

    def _distribute_horizontal(self) -> list[Shape]:
        """Distribute shapes evenly horizontally."""
        if len(self.shapes) < 3:
            return self.shapes

        sorted_shapes = sorted(self.shapes, key=lambda s: s.bbox.x)
        left = sorted_shapes[0].bbox.x
        right = sorted_shapes[-1].bbox.right
        total_width = sum(s.bbox.width for s in sorted_shapes)
        gap = (right - left - total_width) // (len(sorted_shapes) - 1)

        fixed = []
        current_x = left

        for shape in sorted_shapes:
            fixed.append(self._update_shape_x(shape, current_x))
            current_x += shape.bbox.width + gap

        return fixed

    def _distribute_vertical(self) -> list[Shape]:
        """Distribute shapes evenly vertically."""
        if len(self.shapes) < 3:
            return self.shapes

        sorted_shapes = sorted(self.shapes, key=lambda s: s.bbox.y)
        top = sorted_shapes[0].bbox.y
        bottom = sorted_shapes[-1].bbox.bottom
        total_height = sum(s.bbox.height for s in sorted_shapes)
        gap = (bottom - top - total_height) // (len(sorted_shapes) - 1)

        fixed = []
        current_y = top

        for shape in sorted_shapes:
            fixed.append(self._update_shape_y(shape, current_y))
            current_y += shape.bbox.height + gap

        return fixed

    def _update_x(self, target_x: int) -> list[Shape]:
        """Update x position for all shapes."""
        return [self._update_shape_x(s, target_x) for s in self.shapes]

    def _update_y(self, target_y: int) -> list[Shape]:
        """Update y position for all shapes."""
        return [self._update_shape_y(s, target_y) for s in self.shapes]

    def _update_shape_x(self, shape: Shape, new_x: int) -> Shape:
        """Create a new shape with updated x position."""
        if shape.bbox.x == new_x:
            return shape

        new_bbox = BoundingBox(
            x=new_x,
            y=shape.bbox.y,
            width=shape.bbox.width,
            height=shape.bbox.height,
        )
        shape_dict = shape.model_dump()
        shape_dict["bbox"] = new_bbox
        return Shape(**shape_dict)

    def _update_shape_y(self, shape: Shape, new_y: int) -> Shape:
        """Create a new shape with updated y position."""
        if shape.bbox.y == new_y:
            return shape

        new_bbox = BoundingBox(
            x=shape.bbox.x,
            y=new_y,
            width=shape.bbox.width,
            height=shape.bbox.height,
        )
        shape_dict = shape.model_dump()
        shape_dict["bbox"] = new_bbox
        return Shape(**shape_dict)


def align_shapes(
    shapes: list[Shape],
    align_type: AlignType,
    reference: int | None = None,
) -> list[Shape]:
    """Convenience function to align shapes.

    Args:
        shapes: Shapes to align.
        align_type: Type of alignment.
        reference: Reference position (optional).

    Returns:
        Aligned shapes.
    """
    constraint = AlignmentConstraint(shapes, align_type, reference)
    return constraint.apply()


def center_on_canvas(
    shapes: list[Shape],
    canvas_width: int,
    canvas_height: int,
) -> list[Shape]:
    """Center shapes on canvas.

    Args:
        shapes: Shapes to center.
        canvas_width: Canvas width in EMUs.
        canvas_height: Canvas height in EMUs.

    Returns:
        Centered shapes.
    """
    if not shapes:
        return shapes

    # Calculate bounding box of all shapes
    min_x = min(s.bbox.x for s in shapes)
    max_x = max(s.bbox.right for s in shapes)
    min_y = min(s.bbox.y for s in shapes)
    max_y = max(s.bbox.bottom for s in shapes)

    group_width = max_x - min_x
    group_height = max_y - min_y

    # Calculate offset to center
    offset_x = (canvas_width - group_width) // 2 - min_x
    offset_y = (canvas_height - group_height) // 2 - min_y

    # Apply offset
    fixed = []
    for shape in shapes:
        new_bbox = BoundingBox(
            x=shape.bbox.x + offset_x,
            y=shape.bbox.y + offset_y,
            width=shape.bbox.width,
            height=shape.bbox.height,
        )
        shape_dict = shape.model_dump()
        shape_dict["bbox"] = new_bbox
        fixed.append(Shape(**shape_dict))

    return fixed
