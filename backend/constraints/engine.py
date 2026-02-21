"""Constraint engine for enforcing layout rules."""

from dataclasses import dataclass
from typing import Callable

from backend.dsl.schema import BoundingBox, Shape, SlideScene


@dataclass
class Violation:
    """Represents a constraint violation."""

    rule: str
    message: str
    severity: str  # "error", "warning", "info"
    shape_ids: list[str]
    suggested_fix: dict | None = None


@dataclass
class ConstraintResult:
    """Result of constraint validation."""

    is_valid: bool
    violations: list[Violation]
    score: float  # 0-100 quality score
    fixed_scene: SlideScene | None = None


class ConstraintEngine:
    """Validates and fixes layout constraints."""

    def __init__(self, canvas_width: int = 12192000, canvas_height: int = 6858000) -> None:
        """Initialize the constraint engine.

        Args:
            canvas_width: Slide width in EMUs.
            canvas_height: Slide height in EMUs.
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.margin = 457200  # 0.5 inch margin

    def validate(self, scene: SlideScene) -> ConstraintResult:
        """Validate a scene against layout constraints.

        Args:
            scene: The SlideScene to validate.

        Returns:
            ConstraintResult with violations and score.
        """
        violations: list[Violation] = []

        # Check bounds
        violations.extend(self._check_bounds(scene.shapes))

        # Check overlaps
        violations.extend(self._check_overlaps(scene.shapes))

        # Check alignment
        violations.extend(self._check_alignment(scene.shapes))

        # Check spacing
        violations.extend(self._check_spacing(scene.shapes))

        # Calculate score
        score = self._calculate_score(violations)

        return ConstraintResult(
            is_valid=len([v for v in violations if v.severity == "error"]) == 0,
            violations=violations,
            score=score,
        )

    def fix(self, scene: SlideScene) -> SlideScene:
        """Apply automatic fixes to a scene.

        Args:
            scene: The SlideScene to fix.

        Returns:
            Fixed SlideScene.
        """
        shapes = list(scene.shapes)

        # Fix bounds violations
        shapes = self._fix_bounds(shapes)

        # Fix overlaps
        shapes = self._fix_overlaps(shapes)

        # Apply alignment
        shapes = self._apply_alignment(shapes)

        # Apply spacing
        shapes = self._apply_spacing(shapes)

        return SlideScene(
            canvas=scene.canvas,
            shapes=shapes,
            theme=scene.theme,
            metadata=scene.metadata,
        )

    def _check_bounds(self, shapes: list[Shape]) -> list[Violation]:
        """Check if shapes are within canvas bounds.

        Args:
            shapes: List of shapes to check.

        Returns:
            List of violations.
        """
        violations = []

        for shape in shapes:
            bbox = shape.bbox

            if bbox.x < 0:
                violations.append(
                    Violation(
                        rule="bounds",
                        message=f"Shape {shape.id} extends beyond left edge",
                        severity="error",
                        shape_ids=[shape.id],
                        suggested_fix={"x": 0},
                    )
                )

            if bbox.y < 0:
                violations.append(
                    Violation(
                        rule="bounds",
                        message=f"Shape {shape.id} extends beyond top edge",
                        severity="error",
                        shape_ids=[shape.id],
                        suggested_fix={"y": 0},
                    )
                )

            if bbox.right > self.canvas_width:
                violations.append(
                    Violation(
                        rule="bounds",
                        message=f"Shape {shape.id} extends beyond right edge",
                        severity="error",
                        shape_ids=[shape.id],
                        suggested_fix={"x": self.canvas_width - bbox.width},
                    )
                )

            if bbox.bottom > self.canvas_height:
                violations.append(
                    Violation(
                        rule="bounds",
                        message=f"Shape {shape.id} extends beyond bottom edge",
                        severity="error",
                        shape_ids=[shape.id],
                        suggested_fix={"y": self.canvas_height - bbox.height},
                    )
                )

        return violations

    def _check_overlaps(self, shapes: list[Shape]) -> list[Violation]:
        """Check for unwanted shape overlaps.

        Args:
            shapes: List of shapes to check.

        Returns:
            List of violations.
        """
        violations = []

        for i, shape1 in enumerate(shapes):
            for shape2 in shapes[i + 1:]:
                if self._shapes_overlap(shape1.bbox, shape2.bbox):
                    violations.append(
                        Violation(
                            rule="overlap",
                            message=f"Shapes {shape1.id} and {shape2.id} overlap",
                            severity="warning",
                            shape_ids=[shape1.id, shape2.id],
                        )
                    )

        return violations

    def _check_alignment(self, shapes: list[Shape]) -> list[Violation]:
        """Check alignment consistency.

        Args:
            shapes: List of shapes to check.

        Returns:
            List of violations.
        """
        violations = []

        if len(shapes) < 2:
            return violations

        # Check if shapes that should be centered are centered
        canvas_center = self.canvas_width // 2
        tolerance = 91440  # 0.1 inch tolerance

        centered_shapes = [s for s in shapes if abs(s.bbox.center_x - canvas_center) < tolerance * 5]

        if len(centered_shapes) >= 2:
            centers = [s.bbox.center_x for s in centered_shapes]
            if max(centers) - min(centers) > tolerance:
                violations.append(
                    Violation(
                        rule="alignment",
                        message="Centered shapes are not perfectly aligned",
                        severity="info",
                        shape_ids=[s.id for s in centered_shapes],
                    )
                )

        return violations

    def _check_spacing(self, shapes: list[Shape]) -> list[Violation]:
        """Check spacing consistency.

        Args:
            shapes: List of shapes to check.

        Returns:
            List of violations.
        """
        violations = []

        if len(shapes) < 3:
            return violations

        # Sort shapes by vertical position
        sorted_shapes = sorted(shapes, key=lambda s: s.bbox.y)

        # Check vertical spacing consistency
        gaps = []
        for i in range(len(sorted_shapes) - 1):
            gap = sorted_shapes[i + 1].bbox.y - sorted_shapes[i].bbox.bottom
            if gap > 0:
                gaps.append(gap)

        if len(gaps) >= 2:
            avg_gap = sum(gaps) / len(gaps)
            tolerance = avg_gap * 0.2  # 20% tolerance

            for i, gap in enumerate(gaps):
                if abs(gap - avg_gap) > tolerance:
                    violations.append(
                        Violation(
                            rule="spacing",
                            message=f"Inconsistent vertical spacing between shapes",
                            severity="info",
                            shape_ids=[sorted_shapes[i].id, sorted_shapes[i + 1].id],
                            suggested_fix={"gap": int(avg_gap)},
                        )
                    )

        return violations

    def _shapes_overlap(self, bbox1: BoundingBox, bbox2: BoundingBox) -> bool:
        """Check if two bounding boxes overlap.

        Args:
            bbox1: First bounding box.
            bbox2: Second bounding box.

        Returns:
            True if they overlap.
        """
        return (
            bbox1.x < bbox2.right
            and bbox1.right > bbox2.x
            and bbox1.y < bbox2.bottom
            and bbox1.bottom > bbox2.y
        )

    def _fix_bounds(self, shapes: list[Shape]) -> list[Shape]:
        """Fix shapes that are out of bounds.

        Args:
            shapes: List of shapes.

        Returns:
            Fixed shapes.
        """
        fixed = []

        for shape in shapes:
            bbox = shape.bbox
            new_x = max(0, min(bbox.x, self.canvas_width - bbox.width))
            new_y = max(0, min(bbox.y, self.canvas_height - bbox.height))

            if new_x != bbox.x or new_y != bbox.y:
                new_bbox = BoundingBox(
                    x=new_x,
                    y=new_y,
                    width=bbox.width,
                    height=bbox.height,
                )
                # Create new shape with fixed bbox
                shape_dict = shape.model_dump()
                shape_dict["bbox"] = new_bbox
                fixed.append(Shape(**shape_dict))
            else:
                fixed.append(shape)

        return fixed

    def _fix_overlaps(self, shapes: list[Shape]) -> list[Shape]:
        """Fix overlapping shapes by adjusting positions.

        Args:
            shapes: List of shapes.

        Returns:
            Fixed shapes.
        """
        # Sort by z-index to maintain visual order
        sorted_shapes = sorted(shapes, key=lambda s: s.z_index)
        fixed = list(sorted_shapes)

        # Simple overlap resolution - push shapes down
        for i in range(1, len(fixed)):
            for j in range(i):
                if self._shapes_overlap(fixed[i].bbox, fixed[j].bbox):
                    # Push shape i below shape j
                    new_y = fixed[j].bbox.bottom + 91440  # 0.1 inch gap
                    if new_y + fixed[i].bbox.height <= self.canvas_height:
                        bbox = fixed[i].bbox
                        new_bbox = BoundingBox(
                            x=bbox.x,
                            y=new_y,
                            width=bbox.width,
                            height=bbox.height,
                        )
                        shape_dict = fixed[i].model_dump()
                        shape_dict["bbox"] = new_bbox
                        fixed[i] = Shape(**shape_dict)

        return fixed

    def _apply_alignment(self, shapes: list[Shape]) -> list[Shape]:
        """Apply center alignment to shapes.

        Args:
            shapes: List of shapes.

        Returns:
            Aligned shapes.
        """
        if not shapes:
            return shapes

        canvas_center = self.canvas_width // 2
        fixed = []

        for shape in shapes:
            # Center horizontally
            new_x = canvas_center - shape.bbox.width // 2

            if new_x != shape.bbox.x:
                new_bbox = BoundingBox(
                    x=new_x,
                    y=shape.bbox.y,
                    width=shape.bbox.width,
                    height=shape.bbox.height,
                )
                shape_dict = shape.model_dump()
                shape_dict["bbox"] = new_bbox
                fixed.append(Shape(**shape_dict))
            else:
                fixed.append(shape)

        return fixed

    def _apply_spacing(self, shapes: list[Shape]) -> list[Shape]:
        """Apply consistent spacing between shapes.

        Args:
            shapes: List of shapes.

        Returns:
            Spaced shapes.
        """
        if len(shapes) < 2:
            return shapes

        # Sort by vertical position
        sorted_shapes = sorted(shapes, key=lambda s: s.bbox.y)

        # Calculate total height and determine spacing
        total_shape_height = sum(s.bbox.height for s in sorted_shapes)
        available_height = self.canvas_height - 2 * self.margin
        total_gap = available_height - total_shape_height
        gap = max(91440, total_gap // (len(sorted_shapes) - 1)) if len(sorted_shapes) > 1 else 0

        # Reposition shapes
        fixed = []
        current_y = self.margin

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

    def _calculate_score(self, violations: list[Violation]) -> float:
        """Calculate a quality score based on violations.

        Args:
            violations: List of violations.

        Returns:
            Score from 0-100.
        """
        score = 100.0

        for violation in violations:
            if violation.severity == "error":
                score -= 20
            elif violation.severity == "warning":
                score -= 10
            elif violation.severity == "info":
                score -= 2

        return max(0, score)
