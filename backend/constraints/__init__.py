"""Constraint engine module - layout rules for professional polish."""

from backend.constraints.alignment import AlignmentConstraint, AlignType, align_shapes, center_on_canvas
from backend.constraints.engine import ConstraintEngine, ConstraintResult, Violation
from backend.constraints.rules import ArchetypeRules, LayoutRule
from backend.constraints.snapping import (
    Guide,
    SnapTarget,
    SnappingConstraint,
    create_canvas_guides,
    snap_to_grid,
    snap_to_guides,
)
from backend.constraints.spacing import SpacingConstraint, SpacingType, apply_spacing, create_grid
from backend.constraints.text_fitting import (
    OverflowAction,
    TextFitResult,
    TextFittingConstraint,
    TextSafeZone,
    check_text_overflow,
    fix_text_overflow,
)

__all__ = [
    # Engine
    "ConstraintEngine",
    "ConstraintResult",
    "Violation",
    # Alignment
    "AlignmentConstraint",
    "AlignType",
    "align_shapes",
    "center_on_canvas",
    # Spacing
    "SpacingConstraint",
    "SpacingType",
    "apply_spacing",
    "create_grid",
    # Snapping
    "Guide",
    "SnapTarget",
    "SnappingConstraint",
    "create_canvas_guides",
    "snap_to_grid",
    "snap_to_guides",
    # Text Fitting
    "OverflowAction",
    "TextFitResult",
    "TextFittingConstraint",
    "TextSafeZone",
    "check_text_overflow",
    "fix_text_overflow",
    # Rules
    "ArchetypeRules",
    "LayoutRule",
]
