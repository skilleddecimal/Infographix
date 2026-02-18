"""
validation_feedback.py — Feedback loop for validation-driven improvement.

This module provides:
1. Auto-correction: Regenerate diagrams based on validation feedback
2. Learning system: Store validation results for continuous improvement
3. Pattern detection: Identify common issues and apply preventive fixes
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict

from .visual_validator import ValidationResult, ValidationIssue, ValidationSeverity
from .data_models import ColorPalette, DiagramInput

logger = logging.getLogger(__name__)


# =============================================================================
# VALIDATION LEARNING DATABASE
# =============================================================================

@dataclass
class ValidationFeedbackEntry:
    """A single validation feedback entry for learning."""
    timestamp: str
    diagram_type: str
    title: str
    score: float
    issues: List[Dict[str, Any]]
    corrections_applied: List[str] = field(default_factory=list)
    final_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationFeedbackEntry":
        return cls(**data)


class ValidationLearningDB:
    """
    Persistent storage for validation feedback to enable learning.

    Stores validation results and corrections to:
    - Identify common issues by diagram type
    - Track which corrections work
    - Adjust default parameters based on patterns
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "data", "validation_feedback.json"
            )
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        """Load existing feedback data."""
        if self.db_path.exists():
            try:
                with open(self.db_path, "r") as f:
                    data = json.load(f)
                self.entries = [
                    ValidationFeedbackEntry.from_dict(e)
                    for e in data.get("entries", [])
                ]
                self.issue_patterns = data.get("issue_patterns", {})
                self.correction_effectiveness = data.get("correction_effectiveness", {})
            except Exception as e:
                logger.warning(f"Could not load validation DB: {e}")
                self._init_empty()
        else:
            self._init_empty()

    def _init_empty(self):
        """Initialize empty database."""
        self.entries: List[ValidationFeedbackEntry] = []
        self.issue_patterns: Dict[str, Dict[str, int]] = {}  # diagram_type -> {issue_category: count}
        self.correction_effectiveness: Dict[str, Dict[str, float]] = {}  # correction -> {success_rate, count}

    def _save(self):
        """Save feedback data to disk."""
        try:
            data = {
                "entries": [e.to_dict() for e in self.entries[-1000:]],  # Keep last 1000
                "issue_patterns": self.issue_patterns,
                "correction_effectiveness": self.correction_effectiveness,
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.db_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save validation DB: {e}")

    def record_validation(
        self,
        diagram_type: str,
        title: str,
        result: ValidationResult,
        corrections_applied: List[str] = None,
        final_score: Optional[float] = None,
    ):
        """Record a validation result for learning."""
        entry = ValidationFeedbackEntry(
            timestamp=datetime.now().isoformat(),
            diagram_type=diagram_type,
            title=title,
            score=result.score,
            issues=[
                {
                    "severity": i.severity.value,
                    "category": i.category,
                    "message": i.message,
                }
                for i in result.issues
            ],
            corrections_applied=corrections_applied or [],
            final_score=final_score,
        )
        self.entries.append(entry)

        # Update issue patterns
        if diagram_type not in self.issue_patterns:
            self.issue_patterns[diagram_type] = {}

        for issue in result.issues:
            cat = issue.category
            self.issue_patterns[diagram_type][cat] = \
                self.issue_patterns[diagram_type].get(cat, 0) + 1

        # Update correction effectiveness if we have before/after scores
        if corrections_applied and final_score is not None:
            improvement = final_score - result.score
            for correction in corrections_applied:
                if correction not in self.correction_effectiveness:
                    self.correction_effectiveness[correction] = {
                        "total_improvement": 0,
                        "count": 0,
                    }
                self.correction_effectiveness[correction]["total_improvement"] += improvement
                self.correction_effectiveness[correction]["count"] += 1

        self._save()

    def get_common_issues(self, diagram_type: str, top_n: int = 5) -> List[Tuple[str, int]]:
        """Get the most common issues for a diagram type."""
        if diagram_type not in self.issue_patterns:
            return []

        issues = self.issue_patterns[diagram_type]
        sorted_issues = sorted(issues.items(), key=lambda x: x[1], reverse=True)
        return sorted_issues[:top_n]

    def get_effective_corrections(self, min_count: int = 3) -> List[Tuple[str, float]]:
        """Get corrections sorted by effectiveness (average improvement)."""
        effective = []
        for correction, stats in self.correction_effectiveness.items():
            if stats["count"] >= min_count:
                avg_improvement = stats["total_improvement"] / stats["count"]
                effective.append((correction, avg_improvement))

        return sorted(effective, key=lambda x: x[1], reverse=True)

    def get_preventive_adjustments(self, diagram_type: str) -> Dict[str, Any]:
        """
        Get recommended parameter adjustments based on past issues.

        Returns adjustments that can be applied BEFORE generation
        to prevent common issues.
        """
        common_issues = self.get_common_issues(diagram_type)
        adjustments = {}

        for issue_category, count in common_issues:
            if count < 3:  # Need enough data points
                continue

            # Map common issues to preventive parameter adjustments
            if issue_category == "visual_balance":
                adjustments["balance_weights"] = True
                adjustments["equalize_heights"] = True

            elif issue_category == "spacing":
                adjustments["consistent_spacing"] = True
                adjustments["spacing_multiplier"] = 1.1  # Slightly more space

            elif issue_category == "text_alignment":
                adjustments["center_text"] = True
                adjustments["text_margin_multiplier"] = 1.2

            elif issue_category == "color_contrast":
                adjustments["enforce_contrast"] = True
                adjustments["min_contrast_ratio"] = 4.5

        return adjustments


# =============================================================================
# AUTO-CORRECTION ENGINE
# =============================================================================

@dataclass
class CorrectionAction:
    """A correction action to apply based on validation feedback."""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)


class AutoCorrectionEngine:
    """
    Automatically corrects diagrams based on validation feedback.

    Takes validation issues and generates correction actions that
    can be applied during regeneration.
    """

    # Map issue categories to correction strategies
    CORRECTION_STRATEGIES = {
        "visual_balance": [
            CorrectionAction(
                name="equalize_section_heights",
                description="Make pyramid/layer sections more equal in height",
                parameters={"height_ratio": "equal"}
            ),
            CorrectionAction(
                name="adjust_width_distribution",
                description="Redistribute widths for better balance",
                parameters={"distribution": "balanced"}
            ),
        ],
        "spacing": [
            CorrectionAction(
                name="normalize_spacing",
                description="Apply consistent spacing between elements",
                parameters={"spacing_mode": "uniform"}
            ),
            CorrectionAction(
                name="increase_margins",
                description="Increase margins around elements",
                parameters={"margin_multiplier": 1.15}
            ),
        ],
        "text_alignment": [
            CorrectionAction(
                name="center_text_in_shapes",
                description="Ensure text is centered within shapes",
                parameters={"alignment": "center"}
            ),
            CorrectionAction(
                name="adjust_text_box_size",
                description="Resize text boxes to fit content",
                parameters={"auto_fit": True}
            ),
        ],
        "color_contrast": [
            CorrectionAction(
                name="increase_contrast",
                description="Darken or lighten colors for better contrast",
                parameters={"min_contrast": 4.5}
            ),
            CorrectionAction(
                name="use_high_contrast_text",
                description="Use white or black text based on background",
                parameters={"auto_text_color": True}
            ),
        ],
        "context": [
            CorrectionAction(
                name="enhance_context_elements",
                description="Add context-appropriate visual elements",
                parameters={"add_icons": True}
            ),
        ],
    }

    def __init__(self, learning_db: Optional[ValidationLearningDB] = None):
        self.learning_db = learning_db or ValidationLearningDB()

    def analyze_issues(
        self,
        validation_result: ValidationResult,
        diagram_type: str,
    ) -> List[CorrectionAction]:
        """
        Analyze validation issues and return correction actions.

        Prioritizes corrections based on:
        1. Severity (errors first, then warnings)
        2. Historical effectiveness
        3. Feasibility
        """
        corrections = []

        # Sort issues by severity
        sorted_issues = sorted(
            validation_result.issues,
            key=lambda i: (
                0 if i.severity == ValidationSeverity.ERROR else
                1 if i.severity == ValidationSeverity.WARNING else 2
            )
        )

        for issue in sorted_issues:
            if issue.category in self.CORRECTION_STRATEGIES:
                strategies = self.CORRECTION_STRATEGIES[issue.category]

                # Add the first applicable strategy
                # (could be extended to select based on historical effectiveness)
                if strategies:
                    correction = strategies[0]
                    if correction not in corrections:
                        corrections.append(correction)

        return corrections

    def generate_layout_adjustments(
        self,
        corrections: List[CorrectionAction],
        diagram_type: str,
    ) -> Dict[str, Any]:
        """
        Convert correction actions to layout engine parameters.

        Returns a dict that can be passed to LayoutEngine to adjust
        the generation process.
        """
        adjustments = {
            "apply_corrections": True,
            "correction_names": [c.name for c in corrections],
        }

        for correction in corrections:
            if correction.name == "equalize_section_heights":
                if diagram_type == "pyramid":
                    adjustments["pyramid_height_mode"] = "equal"
                else:
                    adjustments["layer_height_mode"] = "equal"

            elif correction.name == "normalize_spacing":
                adjustments["uniform_spacing"] = True
                adjustments["spacing_px"] = 20  # Consistent 20px gaps

            elif correction.name == "center_text_in_shapes":
                adjustments["text_anchor"] = "middle"
                adjustments["text_valign"] = "center"

            elif correction.name == "increase_margins":
                multiplier = correction.parameters.get("margin_multiplier", 1.15)
                adjustments["margin_multiplier"] = multiplier

            elif correction.name == "increase_contrast":
                adjustments["enforce_wcag_contrast"] = True
                adjustments["min_contrast_ratio"] = correction.parameters.get("min_contrast", 4.5)

        return adjustments

    def should_retry(
        self,
        validation_result: ValidationResult,
        attempt: int,
        max_attempts: int = 2,
    ) -> bool:
        """
        Determine if we should retry generation with corrections.

        Returns True if:
        - Score is below threshold (e.g., 70)
        - There are fixable issues
        - We haven't exceeded max attempts
        """
        if attempt >= max_attempts:
            return False

        if validation_result.score >= 85:
            return False  # Good enough

        # Check if there are fixable issues
        fixable_categories = set(self.CORRECTION_STRATEGIES.keys())
        has_fixable = any(
            issue.category in fixable_categories
            for issue in validation_result.issues
            if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.WARNING]
        )

        return has_fixable


# =============================================================================
# INTEGRATED FEEDBACK PROCESSOR
# =============================================================================

class ValidationFeedbackProcessor:
    """
    Main interface for the validation feedback system.

    Combines learning and auto-correction into a single processor
    that can be used by the generation pipeline.
    """

    def __init__(self):
        self.learning_db = ValidationLearningDB()
        self.correction_engine = AutoCorrectionEngine(self.learning_db)

    def get_preventive_adjustments(self, diagram_type: str) -> Dict[str, Any]:
        """Get adjustments to apply BEFORE generation based on past learning."""
        return self.learning_db.get_preventive_adjustments(diagram_type)

    def process_validation(
        self,
        validation_result: ValidationResult,
        diagram_type: str,
        title: str,
        attempt: int = 1,
    ) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Process a validation result and determine next steps.

        Returns:
            - should_retry: Whether to regenerate with corrections
            - adjustments: Layout adjustments to apply if retrying
            - correction_names: Names of corrections being applied
        """
        # Record the validation for learning
        self.learning_db.record_validation(
            diagram_type=diagram_type,
            title=title,
            result=validation_result,
        )

        # Check if we should retry
        should_retry = self.correction_engine.should_retry(
            validation_result, attempt
        )

        if not should_retry:
            return False, {}, []

        # Generate corrections
        corrections = self.correction_engine.analyze_issues(
            validation_result, diagram_type
        )

        # Convert to layout adjustments
        adjustments = self.correction_engine.generate_layout_adjustments(
            corrections, diagram_type
        )

        correction_names = [c.name for c in corrections]

        return True, adjustments, correction_names

    def record_final_result(
        self,
        diagram_type: str,
        title: str,
        initial_result: ValidationResult,
        final_result: ValidationResult,
        corrections_applied: List[str],
    ):
        """Record the final result after corrections for learning."""
        self.learning_db.record_validation(
            diagram_type=diagram_type,
            title=title,
            result=initial_result,
            corrections_applied=corrections_applied,
            final_score=final_result.score,
        )

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about what the system has learned."""
        return {
            "total_validations": len(self.learning_db.entries),
            "issue_patterns": self.learning_db.issue_patterns,
            "effective_corrections": self.learning_db.get_effective_corrections(),
            "entries_by_type": self._count_by_type(),
        }

    def _count_by_type(self) -> Dict[str, int]:
        """Count entries by diagram type."""
        counts = {}
        for entry in self.learning_db.entries:
            counts[entry.diagram_type] = counts.get(entry.diagram_type, 0) + 1
        return counts


# Singleton instance for use across the application
_feedback_processor: Optional[ValidationFeedbackProcessor] = None

def get_feedback_processor() -> ValidationFeedbackProcessor:
    """Get the singleton feedback processor instance."""
    global _feedback_processor
    if _feedback_processor is None:
        _feedback_processor = ValidationFeedbackProcessor()
    return _feedback_processor
