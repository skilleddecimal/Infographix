"""Spacing constraints for layout consistency."""

from dataclasses import dataclass
from enum import Enum

from backend.dsl.schema import BoundingBox, Shape


class SpacingType(str, Enum):
    """Spacing distribution types."""

    EQUAL_GAPS = "equal_gaps"
    EQUAL_CENTERS = "equal_centers"
    FIXED_GAP = "fixed_gap"
    STACK_VERTICAL = "stack_vertical"
    STACK_HORIZONTAL = "stack_horizontal"


@dataclass
class SpacingConstraint:
    """Defines a spacing constraint between shapes."""

    shapes: list[Shape]
    spacing_type: SpacingType
    gap: int = 91440  # Default 0.1 inch
    direction: str = "vertical"  # "vertical" or "horizontal"

    def apply(self) -> list[Shape]:
        """Apply the spacing constraint.

        Returns:
            List of shapes with adjusted positions.
        """
        if len(self.shapes) < 2:
            return self.shapes

        if self.spacing_type == SpacingType.EQUAL_GAPS:
            return self._equal_gaps()
        elif self.spacing_type == SpacingType.EQUAL_CENTERS:
            return self._equal_centers()
        elif self.spacing_type == SpacingType.FIXED_GAP:
            return self._fixed_gap()
        elif self.spacing_type == SpacingType.STACK_VERTICAL:
            return self._stack_vertical()
        elif self.spacing_type == SpacingType.STACK_HORIZONTAL:
            return self._stack_horizontal()

        return self.shapes

    def _equal_gaps(self) -> list[Shape]:
        """Space shapes with equal gaps between them."""
        if self.direction == "vertical":
            return self._equal_gaps_vertical()
        else:
            return self._equal_gaps_horizontal()

    def _equal_gaps_vertical(self) -> list[Shape]:
        """Equal vertical gaps between shapes."""
        sorted_shapes = sorted(self.shapes, key=lambda s: s.bbox.y)

        # Calculate total height needed
        total_shape_height = sum(s.bbox.height for s in sorted_shapes)
        first_y = sorted_shapes[0].bbox.y
        last_bottom = sorted_shapes[-1].bbox.bottom
        total_space = last_bottom - first_y

        # Calculate gap
        num_gaps = len(sorted_shapes) - 1
        available_for_gaps = total_space - total_shape_height
        gap = available_for_gaps // num_gaps if num_gaps > 0 else 0

        # Apply spacing
        fixed = []
        current_y = first_y

        for shape in sorted_shapes:
            new_bbox = BoundingBox(
                x=shape.bbox.x,
                y=current_y,
                width=shape.bbox.width,
                height=shape.bbox.height,
            )
            shape_dict = shape.model_dump()
            shape_dict["bbox"] = new_bbox
            fixed.append(Shape(**shape_dict))
            current_y += shape.bbox.height + gap

        return fixed

    def _equal_gaps_horizontal(self) -> list[Shape]:
        """Equal horizontal gaps between shapes."""
        sorted_shapes = sorted(self.shapes, key=lambda s: s.bbox.x)

        total_shape_width = sum(s.bbox.width for s in sorted_shapes)
        first_x = sorted_shapes[0].bbox.x
        last_right = sorted_shapes[-1].bbox.right
        total_space = last_right - first_x

        num_gaps = len(sorted_shapes) - 1
        available_for_gaps = total_space - total_shape_width
        gap = available_for_gaps // num_gaps if num_gaps > 0 else 0

        fixed = []
        current_x = first_x

        for shape in sorted_shapes:
            new_bbox = BoundingBox(
                x=current_x,
                y=shape.bbox.y,
                width=shape.bbox.width,
                height=shape.bbox.height,
            )
            shape_dict = shape.model_dump()
            shape_dict["bbox"] = new_bbox
            fixed.append(Shape(**shape_dict))
            current_x += shape.bbox.width + gap

        return fixed

    def _equal_centers(self) -> list[Shape]:
        """Space shapes with equal distance between centers."""
        if self.direction == "vertical":
            sorted_shapes = sorted(self.shapes, key=lambda s: s.bbox.center_y)
            first_center = sorted_shapes[0].bbox.center_y
            last_center = sorted_shapes[-1].bbox.center_y
            total_distance = last_center - first_center
            step = total_distance // (len(sorted_shapes) - 1) if len(sorted_shapes) > 1 else 0

            fixed = []
            for i, shape in enumerate(sorted_shapes):
                new_center_y = first_center + i * step
                new_y = new_center_y - shape.bbox.height // 2
                new_bbox = BoundingBox(
                    x=shape.bbox.x,
                    y=new_y,
                    width=shape.bbox.width,
                    height=shape.bbox.height,
                )
                shape_dict = shape.model_dump()
                shape_dict["bbox"] = new_bbox
                fixed.append(Shape(**shape_dict))
            return fixed
        else:
            sorted_shapes = sorted(self.shapes, key=lambda s: s.bbox.center_x)
            first_center = sorted_shapes[0].bbox.center_x
            last_center = sorted_shapes[-1].bbox.center_x
            total_distance = last_center - first_center
            step = total_distance // (len(sorted_shapes) - 1) if len(sorted_shapes) > 1 else 0

            fixed = []
            for i, shape in enumerate(sorted_shapes):
                new_center_x = first_center + i * step
                new_x = new_center_x - shape.bbox.width // 2
                new_bbox = BoundingBox(
                    x=new_x,
                    y=shape.bbox.y,
                    width=shape.bbox.width,
                    height=shape.bbox.height,
                )
                shape_dict = shape.model_dump()
                shape_dict["bbox"] = new_bbox
                fixed.append(Shape(**shape_dict))
            return fixed

    def _fixed_gap(self) -> list[Shape]:
        """Space shapes with a fixed gap."""
        if self.direction == "vertical":
            return self._stack_vertical()
        else:
            return self._stack_horizontal()

    def _stack_vertical(self) -> list[Shape]:
        """Stack shapes vertically with fixed gap."""
        sorted_shapes = sorted(self.shapes, key=lambda s: s.bbox.y)

        fixed = []
        current_y = sorted_shapes[0].bbox.y

        for shape in sorted_shapes:
            new_bbox = BoundingBox(
                x=shape.bbox.x,
                y=current_y,
                width=shape.bbox.width,
                height=shape.bbox.height,
            )
            shape_dict = shape.model_dump()
            shape_dict["bbox"] = new_bbox
            fixed.append(Shape(**shape_dict))
            current_y += shape.bbox.height + self.gap

        return fixed

    def _stack_horizontal(self) -> list[Shape]:
        """Stack shapes horizontally with fixed gap."""
        sorted_shapes = sorted(self.shapes, key=lambda s: s.bbox.x)

        fixed = []
        current_x = sorted_shapes[0].bbox.x

        for shape in sorted_shapes:
            new_bbox = BoundingBox(
                x=current_x,
                y=shape.bbox.y,
                width=shape.bbox.width,
                height=shape.bbox.height,
            )
            shape_dict = shape.model_dump()
            shape_dict["bbox"] = new_bbox
            fixed.append(Shape(**shape_dict))
            current_x += shape.bbox.width + self.gap

        return fixed


def apply_spacing(
    shapes: list[Shape],
    spacing_type: SpacingType,
    gap: int = 91440,
    direction: str = "vertical",
) -> list[Shape]:
    """Convenience function to apply spacing.

    Args:
        shapes: Shapes to space.
        spacing_type: Type of spacing.
        gap: Gap size in EMUs (for fixed gap types).
        direction: "vertical" or "horizontal".

    Returns:
        Spaced shapes.
    """
    constraint = SpacingConstraint(shapes, spacing_type, gap, direction)
    return constraint.apply()


def create_grid(
    shapes: list[Shape],
    columns: int,
    row_gap: int = 182880,  # 0.2 inch
    col_gap: int = 182880,
    start_x: int = 914400,  # 1 inch margin
    start_y: int = 914400,
) -> list[Shape]:
    """Arrange shapes in a grid.

    Args:
        shapes: Shapes to arrange.
        columns: Number of columns.
        row_gap: Gap between rows in EMUs.
        col_gap: Gap between columns in EMUs.
        start_x: Starting X position.
        start_y: Starting Y position.

    Returns:
        Grid-arranged shapes.
    """
    if not shapes:
        return shapes

    # Get max dimensions for uniform cell size
    max_width = max(s.bbox.width for s in shapes)
    max_height = max(s.bbox.height for s in shapes)

    fixed = []
    for i, shape in enumerate(shapes):
        row = i // columns
        col = i % columns

        new_x = start_x + col * (max_width + col_gap) + (max_width - shape.bbox.width) // 2
        new_y = start_y + row * (max_height + row_gap) + (max_height - shape.bbox.height) // 2

        new_bbox = BoundingBox(
            x=new_x,
            y=new_y,
            width=shape.bbox.width,
            height=shape.bbox.height,
        )
        shape_dict = shape.model_dump()
        shape_dict["bbox"] = new_bbox
        fixed.append(Shape(**shape_dict))

    return fixed
