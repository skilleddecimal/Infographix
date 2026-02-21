"""Archetype-specific layout rules."""

from dataclasses import dataclass
from typing import Callable

from backend.dsl.schema import BoundingBox, Shape, SlideScene
from backend.constraints.alignment import AlignType, align_shapes, center_on_canvas
from backend.constraints.spacing import SpacingType, apply_spacing


@dataclass
class LayoutRule:
    """A single layout rule."""

    name: str
    description: str
    apply: Callable[[list[Shape], int, int], list[Shape]]


class ArchetypeRules:
    """Layout rules for specific diagram archetypes."""

    @staticmethod
    def get_rules(archetype: str) -> list[LayoutRule]:
        """Get layout rules for an archetype.

        Args:
            archetype: Archetype name (funnel, pyramid, timeline, etc.).

        Returns:
            List of applicable layout rules.
        """
        rules_map = {
            "funnel": ArchetypeRules._funnel_rules(),
            "pyramid": ArchetypeRules._pyramid_rules(),
            "timeline": ArchetypeRules._timeline_rules(),
            "process": ArchetypeRules._process_rules(),
            "process_flow": ArchetypeRules._process_rules(),
            "hub_spoke": ArchetypeRules._hub_spoke_rules(),
            "cycle": ArchetypeRules._cycle_rules(),
            "comparison": ArchetypeRules._comparison_rules(),
            "matrix": ArchetypeRules._matrix_rules(),
        }
        return rules_map.get(archetype.lower(), ArchetypeRules._default_rules())

    @staticmethod
    def apply_rules(scene: SlideScene) -> SlideScene:
        """Apply archetype rules to a scene.

        Args:
            scene: The scene to process.

        Returns:
            Scene with rules applied.
        """
        archetype = scene.metadata.archetype
        if not archetype:
            return scene

        rules = ArchetypeRules.get_rules(archetype)
        shapes = list(scene.shapes)

        canvas_width = scene.canvas.width
        canvas_height = scene.canvas.height

        for rule in rules:
            shapes = rule.apply(shapes, canvas_width, canvas_height)

        return SlideScene(
            canvas=scene.canvas,
            shapes=shapes,
            theme=scene.theme,
            metadata=scene.metadata,
        )

    @staticmethod
    def _funnel_rules() -> list[LayoutRule]:
        """Rules for funnel diagrams."""
        return [
            LayoutRule(
                name="center_horizontal",
                description="Center all funnel stages horizontally",
                apply=lambda shapes, w, h: align_shapes(shapes, AlignType.CENTER, w // 2),
            ),
            LayoutRule(
                name="stack_vertical",
                description="Stack funnel stages vertically with consistent spacing",
                apply=lambda shapes, w, h: apply_spacing(
                    shapes, SpacingType.EQUAL_GAPS, direction="vertical"
                ),
            ),
            LayoutRule(
                name="decreasing_width",
                description="Ensure widths decrease from top to bottom",
                apply=ArchetypeRules._apply_funnel_widths,
            ),
        ]

    @staticmethod
    def _pyramid_rules() -> list[LayoutRule]:
        """Rules for pyramid diagrams."""
        return [
            LayoutRule(
                name="center_horizontal",
                description="Center all pyramid levels horizontally",
                apply=lambda shapes, w, h: align_shapes(shapes, AlignType.CENTER, w // 2),
            ),
            LayoutRule(
                name="stack_vertical",
                description="Stack pyramid levels vertically",
                apply=lambda shapes, w, h: apply_spacing(
                    shapes, SpacingType.STACK_VERTICAL, gap=0, direction="vertical"
                ),
            ),
            LayoutRule(
                name="increasing_width",
                description="Ensure widths increase from top to bottom",
                apply=ArchetypeRules._apply_pyramid_widths,
            ),
        ]

    @staticmethod
    def _timeline_rules() -> list[LayoutRule]:
        """Rules for timeline diagrams."""
        return [
            LayoutRule(
                name="align_vertical_center",
                description="Align timeline items to vertical center",
                apply=lambda shapes, w, h: align_shapes(shapes, AlignType.MIDDLE, h // 2),
            ),
            LayoutRule(
                name="distribute_horizontal",
                description="Distribute timeline items evenly",
                apply=lambda shapes, w, h: apply_spacing(
                    shapes, SpacingType.EQUAL_GAPS, direction="horizontal"
                ),
            ),
        ]

    @staticmethod
    def _process_rules() -> list[LayoutRule]:
        """Rules for process flow diagrams."""
        return [
            LayoutRule(
                name="align_horizontal_center",
                description="Align process steps to horizontal center line",
                apply=lambda shapes, w, h: align_shapes(shapes, AlignType.MIDDLE, h // 2),
            ),
            LayoutRule(
                name="equal_spacing",
                description="Equal horizontal spacing between steps",
                apply=lambda shapes, w, h: apply_spacing(
                    shapes, SpacingType.EQUAL_GAPS, direction="horizontal"
                ),
            ),
        ]

    @staticmethod
    def _hub_spoke_rules() -> list[LayoutRule]:
        """Rules for hub and spoke diagrams."""
        return [
            LayoutRule(
                name="center_hub",
                description="Center the hub element",
                apply=ArchetypeRules._center_first_shape,
            ),
            LayoutRule(
                name="radial_spokes",
                description="Arrange spoke elements radially",
                apply=ArchetypeRules._apply_radial_layout,
            ),
        ]

    @staticmethod
    def _cycle_rules() -> list[LayoutRule]:
        """Rules for cycle diagrams."""
        return [
            LayoutRule(
                name="circular_layout",
                description="Arrange elements in a circle",
                apply=ArchetypeRules._apply_circular_layout,
            ),
        ]

    @staticmethod
    def _comparison_rules() -> list[LayoutRule]:
        """Rules for comparison diagrams."""
        return [
            LayoutRule(
                name="two_column",
                description="Arrange in two columns",
                apply=ArchetypeRules._apply_two_column,
            ),
            LayoutRule(
                name="equal_widths",
                description="Make comparison items equal width",
                apply=ArchetypeRules._equalize_widths,
            ),
        ]

    @staticmethod
    def _matrix_rules() -> list[LayoutRule]:
        """Rules for matrix diagrams."""
        return [
            LayoutRule(
                name="grid_layout",
                description="Arrange in a grid",
                apply=ArchetypeRules._apply_grid_layout,
            ),
        ]

    @staticmethod
    def _default_rules() -> list[LayoutRule]:
        """Default rules for unknown archetypes."""
        return [
            LayoutRule(
                name="center_on_canvas",
                description="Center all shapes on canvas",
                apply=lambda shapes, w, h: center_on_canvas(shapes, w, h),
            ),
        ]

    # Helper methods for complex rules

    @staticmethod
    def _apply_funnel_widths(
        shapes: list[Shape],
        canvas_width: int,
        canvas_height: int,
    ) -> list[Shape]:
        """Apply decreasing widths for funnel stages."""
        if not shapes:
            return shapes

        sorted_shapes = sorted(shapes, key=lambda s: s.bbox.y)
        max_width = canvas_width - 2 * 914400  # 1 inch margins
        min_width = max_width // 4

        fixed = []
        num_shapes = len(sorted_shapes)

        for i, shape in enumerate(sorted_shapes):
            # Calculate width ratio (100% at top, 25% at bottom)
            ratio = 1.0 - (i / num_shapes) * 0.75
            new_width = int(max_width * ratio)
            new_width = max(new_width, min_width)

            # Center the shape
            new_x = (canvas_width - new_width) // 2

            new_bbox = BoundingBox(
                x=new_x,
                y=shape.bbox.y,
                width=new_width,
                height=shape.bbox.height,
            )
            shape_dict = shape.model_dump()
            shape_dict["bbox"] = new_bbox
            fixed.append(Shape(**shape_dict))

        return fixed

    @staticmethod
    def _apply_pyramid_widths(
        shapes: list[Shape],
        canvas_width: int,
        canvas_height: int,
    ) -> list[Shape]:
        """Apply increasing widths for pyramid levels."""
        if not shapes:
            return shapes

        sorted_shapes = sorted(shapes, key=lambda s: s.bbox.y)
        max_width = canvas_width - 2 * 914400
        min_width = max_width // 4

        fixed = []
        num_shapes = len(sorted_shapes)

        for i, shape in enumerate(sorted_shapes):
            # Calculate width ratio (25% at top, 100% at bottom)
            ratio = 0.25 + (i / (num_shapes - 1)) * 0.75 if num_shapes > 1 else 1.0
            new_width = int(max_width * ratio)

            new_x = (canvas_width - new_width) // 2

            new_bbox = BoundingBox(
                x=new_x,
                y=shape.bbox.y,
                width=new_width,
                height=shape.bbox.height,
            )
            shape_dict = shape.model_dump()
            shape_dict["bbox"] = new_bbox
            fixed.append(Shape(**shape_dict))

        return fixed

    @staticmethod
    def _center_first_shape(
        shapes: list[Shape],
        canvas_width: int,
        canvas_height: int,
    ) -> list[Shape]:
        """Center the first (hub) shape."""
        if not shapes:
            return shapes

        fixed = list(shapes)
        hub = fixed[0]

        new_x = (canvas_width - hub.bbox.width) // 2
        new_y = (canvas_height - hub.bbox.height) // 2

        new_bbox = BoundingBox(
            x=new_x,
            y=new_y,
            width=hub.bbox.width,
            height=hub.bbox.height,
        )
        shape_dict = hub.model_dump()
        shape_dict["bbox"] = new_bbox
        fixed[0] = Shape(**shape_dict)

        return fixed

    @staticmethod
    def _apply_radial_layout(
        shapes: list[Shape],
        canvas_width: int,
        canvas_height: int,
    ) -> list[Shape]:
        """Apply radial layout for hub and spoke."""
        import math

        if len(shapes) < 2:
            return shapes

        fixed = [shapes[0]]  # Keep hub as-is
        spokes = shapes[1:]

        center_x = canvas_width // 2
        center_y = canvas_height // 2
        radius = min(canvas_width, canvas_height) // 3

        for i, spoke in enumerate(spokes):
            angle = (2 * math.pi * i) / len(spokes) - math.pi / 2  # Start at top
            new_x = int(center_x + radius * math.cos(angle) - spoke.bbox.width // 2)
            new_y = int(center_y + radius * math.sin(angle) - spoke.bbox.height // 2)

            new_bbox = BoundingBox(
                x=new_x,
                y=new_y,
                width=spoke.bbox.width,
                height=spoke.bbox.height,
            )
            shape_dict = spoke.model_dump()
            shape_dict["bbox"] = new_bbox
            fixed.append(Shape(**shape_dict))

        return fixed

    @staticmethod
    def _apply_circular_layout(
        shapes: list[Shape],
        canvas_width: int,
        canvas_height: int,
    ) -> list[Shape]:
        """Arrange shapes in a circle."""
        import math

        if not shapes:
            return shapes

        center_x = canvas_width // 2
        center_y = canvas_height // 2
        radius = min(canvas_width, canvas_height) // 3

        fixed = []
        for i, shape in enumerate(shapes):
            angle = (2 * math.pi * i) / len(shapes) - math.pi / 2
            new_x = int(center_x + radius * math.cos(angle) - shape.bbox.width // 2)
            new_y = int(center_y + radius * math.sin(angle) - shape.bbox.height // 2)

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

    @staticmethod
    def _apply_two_column(
        shapes: list[Shape],
        canvas_width: int,
        canvas_height: int,
    ) -> list[Shape]:
        """Arrange shapes in two columns."""
        if not shapes:
            return shapes

        margin = 914400  # 1 inch
        gap = 457200  # 0.5 inch
        column_width = (canvas_width - 2 * margin - gap) // 2

        fixed = []
        left_y = margin
        right_y = margin

        for i, shape in enumerate(shapes):
            if i % 2 == 0:
                # Left column
                new_x = margin
                new_y = left_y
                left_y += shape.bbox.height + gap
            else:
                # Right column
                new_x = margin + column_width + gap
                new_y = right_y
                right_y += shape.bbox.height + gap

            new_bbox = BoundingBox(
                x=new_x,
                y=new_y,
                width=column_width,
                height=shape.bbox.height,
            )
            shape_dict = shape.model_dump()
            shape_dict["bbox"] = new_bbox
            fixed.append(Shape(**shape_dict))

        return fixed

    @staticmethod
    def _equalize_widths(
        shapes: list[Shape],
        canvas_width: int,
        canvas_height: int,
    ) -> list[Shape]:
        """Make all shapes equal width."""
        if not shapes:
            return shapes

        max_width = max(s.bbox.width for s in shapes)

        fixed = []
        for shape in shapes:
            if shape.bbox.width != max_width:
                # Adjust x to keep centered
                width_diff = max_width - shape.bbox.width
                new_x = shape.bbox.x - width_diff // 2

                new_bbox = BoundingBox(
                    x=new_x,
                    y=shape.bbox.y,
                    width=max_width,
                    height=shape.bbox.height,
                )
                shape_dict = shape.model_dump()
                shape_dict["bbox"] = new_bbox
                fixed.append(Shape(**shape_dict))
            else:
                fixed.append(shape)

        return fixed

    @staticmethod
    def _apply_grid_layout(
        shapes: list[Shape],
        canvas_width: int,
        canvas_height: int,
    ) -> list[Shape]:
        """Arrange shapes in a 2x2 grid (for matrix)."""
        import math

        if not shapes:
            return shapes

        columns = int(math.ceil(math.sqrt(len(shapes))))
        margin = 914400
        gap = 182880

        cell_width = (canvas_width - 2 * margin - (columns - 1) * gap) // columns
        cell_height = cell_width  # Square cells

        fixed = []
        for i, shape in enumerate(shapes):
            row = i // columns
            col = i % columns

            new_x = margin + col * (cell_width + gap) + (cell_width - shape.bbox.width) // 2
            new_y = margin + row * (cell_height + gap) + (cell_height - shape.bbox.height) // 2

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
