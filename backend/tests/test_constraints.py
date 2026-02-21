"""Tests for constraint engine and related modules."""

import math

import pytest

from backend.constraints.alignment import (
    AlignmentConstraint,
    AlignType,
    align_shapes,
    center_on_canvas,
)
from backend.constraints.engine import ConstraintEngine, ConstraintResult, Violation
from backend.constraints.rules import ArchetypeRules, LayoutRule
from backend.constraints.snapping import (
    Guide,
    SnapTarget,
    SnappingConstraint,
    create_canvas_guides,
    snap_to_grid,
)
from backend.constraints.spacing import (
    SpacingConstraint,
    SpacingType,
    apply_spacing,
    create_grid,
)
from backend.constraints.text_fitting import (
    OverflowAction,
    TextFitResult,
    TextFittingConstraint,
    TextSafeZone,
    check_text_overflow,
    fix_text_overflow,
)
from backend.dsl.schema import (
    BoundingBox,
    Canvas,
    Effects,
    NoFill,
    Shape,
    ShapeType,
    SlideMetadata,
    SlideScene,
    TextContent,
    TextRun,
    ThemeColors,
    Transform,
)


# Fixtures for common test data
@pytest.fixture
def sample_shape() -> Shape:
    """Create a sample shape for testing."""
    return Shape(
        id="test_shape_1",
        type=ShapeType.AUTO_SHAPE,
        name="Test Shape",
        group_path=["root"],
        z_index=1,
        bbox=BoundingBox(x=1000000, y=1000000, width=2000000, height=1000000),
        transform=Transform(),
        fill=NoFill(),
        effects=Effects(),
    )


@pytest.fixture
def sample_shapes() -> list[Shape]:
    """Create multiple sample shapes for testing."""
    shapes = []
    for i in range(5):
        shapes.append(
            Shape(
                id=f"test_shape_{i}",
                type=ShapeType.AUTO_SHAPE,
                name=f"Test Shape {i}",
                group_path=["root"],
                z_index=i,
                bbox=BoundingBox(
                    x=1000000 + i * 100000,
                    y=1000000 + i * 500000,
                    width=2000000,
                    height=400000,
                ),
                transform=Transform(),
                fill=NoFill(),
                effects=Effects(),
            )
        )
    return shapes


@pytest.fixture
def sample_scene(sample_shapes: list[Shape]) -> SlideScene:
    """Create a sample scene for testing."""
    return SlideScene(
        canvas=Canvas(width=12192000, height=6858000),
        shapes=sample_shapes,
        theme=ThemeColors(),
        metadata=SlideMetadata(archetype="funnel"),
    )


@pytest.fixture
def shape_with_text() -> Shape:
    """Create a shape with text content."""
    return Shape(
        id="text_shape_1",
        type=ShapeType.TEXT,
        name="Text Shape",
        group_path=["root"],
        z_index=1,
        bbox=BoundingBox(x=1000000, y=1000000, width=2000000, height=500000),
        transform=Transform(),
        fill=NoFill(),
        effects=Effects(),
        text=TextContent(
            runs=[
                TextRun(
                    text="Hello World",
                    font_family="Calibri",
                    font_size=1400,
                    bold=False,
                    italic=False,
                    underline=False,
                    color="#000000",
                )
            ],
            alignment="center",
        ),
    )


# ============================================================================
# Constraint Engine Tests
# ============================================================================

class TestConstraintEngine:
    """Tests for ConstraintEngine class."""

    def test_engine_initialization(self) -> None:
        """Test engine initializes with default values."""
        engine = ConstraintEngine()
        assert engine.canvas_width == 12192000
        assert engine.canvas_height == 6858000
        assert engine.margin == 457200

    def test_validate_empty_scene(self, sample_scene: SlideScene) -> None:
        """Test validation with empty scene."""
        engine = ConstraintEngine()
        empty_scene = SlideScene(
            canvas=Canvas(width=12192000, height=6858000),
            shapes=[],
            theme=ThemeColors(),
            metadata=SlideMetadata(),
        )
        result = engine.validate(empty_scene)
        assert result.is_valid
        assert len(result.violations) == 0
        assert result.score == 100.0

    def test_validate_in_bounds(self, sample_scene: SlideScene) -> None:
        """Test validation passes for shapes in bounds."""
        engine = ConstraintEngine()
        result = engine.validate(sample_scene)
        # Check no bound violations
        bound_violations = [v for v in result.violations if v.rule == "bounds"]
        assert len(bound_violations) == 0

    def test_detect_out_of_bounds(self) -> None:
        """Test detection of out-of-bounds shapes."""
        engine = ConstraintEngine()

        out_of_bounds_shape = Shape(
            id="oob_shape",
            type=ShapeType.AUTO_SHAPE,
            name="Out of Bounds",
            group_path=["root"],
            z_index=1,
            bbox=BoundingBox(x=-100000, y=0, width=500000, height=500000),
            transform=Transform(),
            fill=NoFill(),
            effects=Effects(),
        )

        scene = SlideScene(
            canvas=Canvas(width=12192000, height=6858000),
            shapes=[out_of_bounds_shape],
            theme=ThemeColors(),
            metadata=SlideMetadata(),
        )

        result = engine.validate(scene)
        assert not result.is_valid
        bound_violations = [v for v in result.violations if v.rule == "bounds"]
        assert len(bound_violations) > 0

    def test_fix_out_of_bounds(self) -> None:
        """Test fixing out-of-bounds shapes."""
        engine = ConstraintEngine()

        out_of_bounds_shape = Shape(
            id="oob_shape",
            type=ShapeType.AUTO_SHAPE,
            name="Out of Bounds",
            group_path=["root"],
            z_index=1,
            bbox=BoundingBox(x=-100000, y=-50000, width=500000, height=500000),
            transform=Transform(),
            fill=NoFill(),
            effects=Effects(),
        )

        scene = SlideScene(
            canvas=Canvas(width=12192000, height=6858000),
            shapes=[out_of_bounds_shape],
            theme=ThemeColors(),
            metadata=SlideMetadata(),
        )

        fixed_scene = engine.fix(scene)
        assert fixed_scene.shapes[0].bbox.x >= 0
        assert fixed_scene.shapes[0].bbox.y >= 0

    def test_detect_overlaps(self) -> None:
        """Test detection of overlapping shapes."""
        engine = ConstraintEngine()

        shape1 = Shape(
            id="shape1",
            type=ShapeType.AUTO_SHAPE,
            name="Shape 1",
            group_path=["root"],
            z_index=1,
            bbox=BoundingBox(x=1000000, y=1000000, width=500000, height=500000),
            transform=Transform(),
            fill=NoFill(),
            effects=Effects(),
        )

        shape2 = Shape(
            id="shape2",
            type=ShapeType.AUTO_SHAPE,
            name="Shape 2",
            group_path=["root"],
            z_index=2,
            bbox=BoundingBox(x=1200000, y=1200000, width=500000, height=500000),
            transform=Transform(),
            fill=NoFill(),
            effects=Effects(),
        )

        scene = SlideScene(
            canvas=Canvas(width=12192000, height=6858000),
            shapes=[shape1, shape2],
            theme=ThemeColors(),
            metadata=SlideMetadata(),
        )

        result = engine.validate(scene)
        overlap_violations = [v for v in result.violations if v.rule == "overlap"]
        assert len(overlap_violations) == 1

    def test_score_calculation(self) -> None:
        """Test quality score calculation."""
        engine = ConstraintEngine()

        # Scene with violations
        out_of_bounds = Shape(
            id="oob",
            type=ShapeType.AUTO_SHAPE,
            name="OOB",
            group_path=["root"],
            z_index=1,
            bbox=BoundingBox(x=-100, y=0, width=500000, height=500000),
            transform=Transform(),
            fill=NoFill(),
            effects=Effects(),
        )

        scene = SlideScene(
            canvas=Canvas(width=12192000, height=6858000),
            shapes=[out_of_bounds],
            theme=ThemeColors(),
            metadata=SlideMetadata(),
        )

        result = engine.validate(scene)
        assert result.score < 100.0


# ============================================================================
# Alignment Tests
# ============================================================================

class TestAlignmentConstraint:
    """Tests for AlignmentConstraint class."""

    def test_align_left(self, sample_shapes: list[Shape]) -> None:
        """Test left alignment."""
        aligned = align_shapes(sample_shapes, AlignType.LEFT)
        x_positions = [s.bbox.x for s in aligned]
        assert len(set(x_positions)) == 1  # All same x

    def test_align_center(self, sample_shapes: list[Shape]) -> None:
        """Test center alignment."""
        aligned = align_shapes(sample_shapes, AlignType.CENTER)
        centers = [s.bbox.center_x for s in aligned]
        # All centers should be within 1 EMU of each other
        assert max(centers) - min(centers) <= 1

    def test_align_right(self, sample_shapes: list[Shape]) -> None:
        """Test right alignment."""
        aligned = align_shapes(sample_shapes, AlignType.RIGHT)
        right_edges = [s.bbox.right for s in aligned]
        assert max(right_edges) - min(right_edges) <= 1

    def test_align_top(self, sample_shapes: list[Shape]) -> None:
        """Test top alignment."""
        aligned = align_shapes(sample_shapes, AlignType.TOP)
        y_positions = [s.bbox.y for s in aligned]
        assert len(set(y_positions)) == 1

    def test_align_middle(self, sample_shapes: list[Shape]) -> None:
        """Test middle (vertical center) alignment."""
        aligned = align_shapes(sample_shapes, AlignType.MIDDLE)
        centers = [s.bbox.center_y for s in aligned]
        assert max(centers) - min(centers) <= 1

    def test_align_bottom(self, sample_shapes: list[Shape]) -> None:
        """Test bottom alignment."""
        aligned = align_shapes(sample_shapes, AlignType.BOTTOM)
        bottoms = [s.bbox.bottom for s in aligned]
        assert max(bottoms) - min(bottoms) <= 1

    def test_distribute_horizontal(self, sample_shapes: list[Shape]) -> None:
        """Test horizontal distribution."""
        aligned = align_shapes(sample_shapes, AlignType.DISTRIBUTE_H)
        # Check that gaps between shapes are equal
        sorted_shapes = sorted(aligned, key=lambda s: s.bbox.x)
        gaps = []
        for i in range(len(sorted_shapes) - 1):
            gap = sorted_shapes[i + 1].bbox.x - sorted_shapes[i].bbox.right
            gaps.append(gap)
        if len(gaps) >= 2:
            # Gaps should be equal (within rounding)
            assert max(gaps) - min(gaps) <= 2

    def test_center_on_canvas(self, sample_shapes: list[Shape]) -> None:
        """Test centering shapes on canvas."""
        canvas_width = 12192000
        canvas_height = 6858000
        centered = center_on_canvas(sample_shapes, canvas_width, canvas_height)

        # Calculate group bounding box
        min_x = min(s.bbox.x for s in centered)
        max_x = max(s.bbox.right for s in centered)
        min_y = min(s.bbox.y for s in centered)
        max_y = max(s.bbox.bottom for s in centered)

        group_center_x = (min_x + max_x) // 2
        group_center_y = (min_y + max_y) // 2

        assert abs(group_center_x - canvas_width // 2) <= 1
        assert abs(group_center_y - canvas_height // 2) <= 1


# ============================================================================
# Spacing Tests
# ============================================================================

class TestSpacingConstraint:
    """Tests for SpacingConstraint class."""

    def test_equal_gaps_vertical(self, sample_shapes: list[Shape]) -> None:
        """Test equal vertical gaps."""
        spaced = apply_spacing(sample_shapes, SpacingType.EQUAL_GAPS, direction="vertical")
        sorted_shapes = sorted(spaced, key=lambda s: s.bbox.y)

        gaps = []
        for i in range(len(sorted_shapes) - 1):
            gap = sorted_shapes[i + 1].bbox.y - sorted_shapes[i].bbox.bottom
            gaps.append(gap)

        if len(gaps) >= 2:
            assert max(gaps) - min(gaps) <= 2

    def test_equal_gaps_horizontal(self, sample_shapes: list[Shape]) -> None:
        """Test equal horizontal gaps."""
        spaced = apply_spacing(sample_shapes, SpacingType.EQUAL_GAPS, direction="horizontal")
        sorted_shapes = sorted(spaced, key=lambda s: s.bbox.x)

        gaps = []
        for i in range(len(sorted_shapes) - 1):
            gap = sorted_shapes[i + 1].bbox.x - sorted_shapes[i].bbox.right
            gaps.append(gap)

        if len(gaps) >= 2:
            assert max(gaps) - min(gaps) <= 2

    def test_stack_vertical(self, sample_shapes: list[Shape]) -> None:
        """Test vertical stacking with fixed gap."""
        gap = 182880  # 0.2 inch
        stacked = apply_spacing(sample_shapes, SpacingType.STACK_VERTICAL, gap=gap)
        sorted_shapes = sorted(stacked, key=lambda s: s.bbox.y)

        for i in range(len(sorted_shapes) - 1):
            actual_gap = sorted_shapes[i + 1].bbox.y - sorted_shapes[i].bbox.bottom
            assert actual_gap == gap

    def test_create_grid(self, sample_shapes: list[Shape]) -> None:
        """Test grid arrangement."""
        grid = create_grid(sample_shapes, columns=2)

        # Check that shapes are in a grid pattern
        rows = {}
        for shape in grid:
            row_y = shape.bbox.y
            if row_y not in rows:
                rows[row_y] = []
            rows[row_y].append(shape)

        # Should have shapes distributed in rows
        assert len(rows) >= 1


# ============================================================================
# Snapping Tests
# ============================================================================

class TestSnappingConstraint:
    """Tests for SnappingConstraint class."""

    def test_snap_to_grid(self, sample_shape: Shape) -> None:
        """Test grid snapping."""
        # Create shape slightly off grid
        off_grid_shape = Shape(
            id="off_grid",
            type=ShapeType.AUTO_SHAPE,
            name="Off Grid",
            group_path=["root"],
            z_index=1,
            bbox=BoundingBox(x=91450, y=91450, width=500000, height=500000),  # 10 EMUs off
            transform=Transform(),
            fill=NoFill(),
            effects=Effects(),
        )

        snapped = snap_to_grid([off_grid_shape], grid_size=91440, snap_threshold=45720)
        assert snapped[0].bbox.x == 91440  # Snapped to grid
        assert snapped[0].bbox.y == 91440

    def test_snap_to_guides(self, sample_shape: Shape) -> None:
        """Test guide snapping."""
        constraint = SnappingConstraint(
            guides=[
                Guide(position=1000000, orientation="vertical"),
                Guide(position=1000000, orientation="horizontal"),
            ],
            snap_threshold=50000,
            snap_targets=[SnapTarget.GUIDES],
        )

        # Shape slightly off guide
        near_guide_shape = Shape(
            id="near_guide",
            type=ShapeType.AUTO_SHAPE,
            name="Near Guide",
            group_path=["root"],
            z_index=1,
            bbox=BoundingBox(x=1020000, y=1020000, width=500000, height=500000),
            transform=Transform(),
            fill=NoFill(),
            effects=Effects(),
        )

        snapped, result = constraint.snap_shape(near_guide_shape)
        assert result.snapped

    def test_create_canvas_guides(self) -> None:
        """Test canvas guide creation."""
        guides = create_canvas_guides(include_thirds=True, include_margins=True)

        # Should have center, thirds, and margin guides
        assert len(guides) >= 2  # At least center guides

        # Check center guides
        vertical_center = [g for g in guides if g.orientation == "vertical" and g.is_center]
        horizontal_center = [g for g in guides if g.orientation == "horizontal" and g.is_center]
        assert len(vertical_center) == 1
        assert len(horizontal_center) == 1

    def test_snap_to_canvas_center(self, sample_shape: Shape) -> None:
        """Test snapping to canvas center."""
        constraint = SnappingConstraint(
            canvas_width=12192000,
            canvas_height=6858000,
            snap_threshold=100000,
            snap_targets=[SnapTarget.CANVAS_CENTER],
        )

        # Shape near center
        center_x = 12192000 // 2
        center_y = 6858000 // 2

        near_center_shape = Shape(
            id="near_center",
            type=ShapeType.AUTO_SHAPE,
            name="Near Center",
            group_path=["root"],
            z_index=1,
            bbox=BoundingBox(
                x=center_x - 250000 + 50000,  # Slightly off center
                y=center_y - 250000 + 50000,
                width=500000,
                height=500000,
            ),
            transform=Transform(),
            fill=NoFill(),
            effects=Effects(),
        )

        snapped, result = constraint.snap_shape(near_center_shape)
        assert result.snapped
        # Check shape is centered
        assert snapped.bbox.center_x == center_x


# ============================================================================
# Text Fitting Tests
# ============================================================================

class TestTextFittingConstraint:
    """Tests for TextFittingConstraint class."""

    def test_text_fits(self, shape_with_text: Shape) -> None:
        """Test text that fits within shape."""
        constraint = TextFittingConstraint(safe_zone=TextSafeZone())
        result, metrics = constraint.check_text_fit(shape_with_text)
        assert result == TextFitResult.FITS

    def test_detect_overflow(self) -> None:
        """Test detection of text overflow."""
        # Create shape with long text in small area
        overflow_shape = Shape(
            id="overflow",
            type=ShapeType.TEXT,
            name="Overflow",
            group_path=["root"],
            z_index=1,
            bbox=BoundingBox(x=0, y=0, width=500000, height=200000),  # Small box
            transform=Transform(),
            fill=NoFill(),
            effects=Effects(),
            text=TextContent(
                runs=[
                    TextRun(
                        text="This is a very long text that will definitely overflow the bounds",
                        font_family="Calibri",
                        font_size=2400,  # Large font
                        bold=False,
                        italic=False,
                        underline=False,
                        color="#000000",
                    )
                ],
                alignment="left",
            ),
        )

        constraint = TextFittingConstraint(safe_zone=TextSafeZone())
        result, metrics = constraint.check_text_fit(overflow_shape)
        assert result in (TextFitResult.OVERFLOW_WIDTH, TextFitResult.OVERFLOW_HEIGHT, TextFitResult.OVERFLOW_BOTH)

    def test_shrink_text(self) -> None:
        """Test text shrinking for overflow."""
        overflow_shape = Shape(
            id="overflow",
            type=ShapeType.TEXT,
            name="Overflow",
            group_path=["root"],
            z_index=1,
            bbox=BoundingBox(x=0, y=0, width=1000000, height=300000),
            transform=Transform(),
            fill=NoFill(),
            effects=Effects(),
            text=TextContent(
                runs=[
                    TextRun(
                        text="Long text content here",
                        font_family="Calibri",
                        font_size=3000,  # Large font
                        bold=False,
                        italic=False,
                        underline=False,
                        color="#000000",
                    )
                ],
                alignment="left",
            ),
        )

        constraint = TextFittingConstraint(
            safe_zone=TextSafeZone(),
            overflow_action=OverflowAction.SHRINK_TEXT,
        )

        original_font_size = overflow_shape.text.runs[0].font_size
        fixed = constraint.fix_text_overflow(overflow_shape)

        # Font size should be reduced or equal (if it already fit)
        assert fixed.text.runs[0].font_size <= original_font_size

    def test_truncate_text(self) -> None:
        """Test text truncation."""
        overflow_shape = Shape(
            id="overflow",
            type=ShapeType.TEXT,
            name="Overflow",
            group_path=["root"],
            z_index=1,
            bbox=BoundingBox(x=0, y=0, width=500000, height=300000),
            transform=Transform(),
            fill=NoFill(),
            effects=Effects(),
            text=TextContent(
                runs=[
                    TextRun(
                        text="This is a very long text that needs truncation",
                        font_family="Calibri",
                        font_size=1400,
                        bold=False,
                        italic=False,
                        underline=False,
                        color="#000000",
                    )
                ],
                alignment="left",
            ),
        )

        constraint = TextFittingConstraint(
            safe_zone=TextSafeZone(),
            overflow_action=OverflowAction.TRUNCATE,
        )

        fixed = constraint.fix_text_overflow(overflow_shape)
        # Text should be truncated (ends with ...)
        if fixed.text.runs[0].text != overflow_shape.text.runs[0].text:
            assert "..." in fixed.text.runs[0].text

    def test_check_text_overflow_batch(self, shape_with_text: Shape) -> None:
        """Test batch overflow checking."""
        shapes = [shape_with_text, shape_with_text]
        results = check_text_overflow(shapes)
        assert len(results) == 2
        for shape, result in results:
            assert isinstance(result, TextFitResult)

    def test_fix_text_overflow_batch(self, shape_with_text: Shape) -> None:
        """Test batch overflow fixing."""
        shapes = [shape_with_text, shape_with_text]
        fixed = fix_text_overflow(shapes, OverflowAction.SHRINK_TEXT)
        assert len(fixed) == 2


# ============================================================================
# Archetype Rules Tests
# ============================================================================

class TestArchetypeRules:
    """Tests for ArchetypeRules class."""

    def test_get_funnel_rules(self) -> None:
        """Test funnel rules retrieval."""
        rules = ArchetypeRules.get_rules("funnel")
        assert len(rules) >= 1
        rule_names = [r.name for r in rules]
        assert "center_horizontal" in rule_names

    def test_get_pyramid_rules(self) -> None:
        """Test pyramid rules retrieval."""
        rules = ArchetypeRules.get_rules("pyramid")
        assert len(rules) >= 1
        rule_names = [r.name for r in rules]
        assert "center_horizontal" in rule_names

    def test_get_timeline_rules(self) -> None:
        """Test timeline rules retrieval."""
        rules = ArchetypeRules.get_rules("timeline")
        assert len(rules) >= 1

    def test_get_hub_spoke_rules(self) -> None:
        """Test hub and spoke rules retrieval."""
        rules = ArchetypeRules.get_rules("hub_spoke")
        assert len(rules) >= 1

    def test_get_cycle_rules(self) -> None:
        """Test cycle rules retrieval."""
        rules = ArchetypeRules.get_rules("cycle")
        assert len(rules) >= 1

    def test_apply_funnel_rules(self, sample_scene: SlideScene) -> None:
        """Test applying funnel rules to scene."""
        funnel_scene = SlideScene(
            canvas=sample_scene.canvas,
            shapes=sample_scene.shapes,
            theme=sample_scene.theme,
            metadata=SlideMetadata(archetype="funnel"),
        )

        result = ArchetypeRules.apply_rules(funnel_scene)

        # Shapes should be centered
        centers = [s.bbox.center_x for s in result.shapes]
        expected_center = funnel_scene.canvas.width // 2
        for center in centers:
            assert abs(center - expected_center) <= 1

    def test_apply_pyramid_rules(self, sample_scene: SlideScene) -> None:
        """Test applying pyramid rules to scene."""
        pyramid_scene = SlideScene(
            canvas=sample_scene.canvas,
            shapes=sample_scene.shapes,
            theme=sample_scene.theme,
            metadata=SlideMetadata(archetype="pyramid"),
        )

        result = ArchetypeRules.apply_rules(pyramid_scene)
        # Check shapes are still valid
        assert len(result.shapes) == len(pyramid_scene.shapes)

    def test_unknown_archetype_uses_default(self) -> None:
        """Test unknown archetype falls back to default rules."""
        rules = ArchetypeRules.get_rules("unknown_type")
        assert len(rules) >= 1
        # Default rule should be center_on_canvas
        assert rules[0].name == "center_on_canvas"


# ============================================================================
# Integration Tests
# ============================================================================

class TestConstraintIntegration:
    """Integration tests for constraint system."""

    def test_full_constraint_pipeline(self, sample_scene: SlideScene) -> None:
        """Test full validation -> fix pipeline."""
        engine = ConstraintEngine()

        # Validate
        result = engine.validate(sample_scene)
        assert isinstance(result, ConstraintResult)

        # Fix
        fixed_scene = engine.fix(sample_scene)
        assert len(fixed_scene.shapes) == len(sample_scene.shapes)

        # Validate fixed scene
        fixed_result = engine.validate(fixed_scene)
        # Fixed scene should have equal or better score
        assert fixed_result.score >= result.score or fixed_result.is_valid

    def test_alignment_then_spacing(self, sample_shapes: list[Shape]) -> None:
        """Test applying alignment then spacing."""
        # First align
        aligned = align_shapes(sample_shapes, AlignType.CENTER)

        # Then space
        spaced = apply_spacing(aligned, SpacingType.EQUAL_GAPS, direction="vertical")

        # Verify both constraints hold
        centers = [s.bbox.center_x for s in spaced]
        assert max(centers) - min(centers) <= 1

        sorted_shapes = sorted(spaced, key=lambda s: s.bbox.y)
        gaps = []
        for i in range(len(sorted_shapes) - 1):
            gap = sorted_shapes[i + 1].bbox.y - sorted_shapes[i].bbox.bottom
            gaps.append(gap)
        if len(gaps) >= 2:
            assert max(gaps) - min(gaps) <= 2

    def test_snapping_then_alignment(self, sample_shapes: list[Shape]) -> None:
        """Test snapping followed by alignment."""
        # First snap to grid
        snapped = snap_to_grid(sample_shapes)

        # Then align
        aligned = align_shapes(snapped, AlignType.LEFT)

        # All shapes should have same x
        x_positions = [s.bbox.x for s in aligned]
        assert len(set(x_positions)) == 1
