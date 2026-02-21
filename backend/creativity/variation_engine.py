"""Variation engine for generating creative infographic variations."""

import copy
import random
from dataclasses import dataclass, field
from typing import Any

from backend.creativity.operators import (
    VariationOperator,
    VariationParams,
    PaletteVariation,
    TaperVariation,
    ScaleVariation,
    SpacingVariation,
    AccentStyleVariation,
    DepthVariation,
    CornerRadiusVariation,
    LabelPlacementVariation,
    OrientationVariation,
    AlignmentVariation,
)
from backend.creativity.constraints import BrandConstraintChecker, BrandGuidelines
from backend.creativity.sampling import VariationSampler, SamplingConfig


@dataclass
class VariationResult:
    """Result of applying a variation."""

    dsl: dict[str, Any]
    operators_applied: list[str]
    constraint_score: float = 1.0
    is_valid: bool = True
    seed: int | None = None


class VariationEngine:
    """Engine for generating controlled variations of infographics.

    Combines variation operators, constraint checking, and sampling
    to produce diverse but brand-compliant variations.
    """

    def __init__(
        self,
        brand_guidelines: BrandGuidelines | None = None,
    ):
        """Initialize variation engine.

        Args:
            brand_guidelines: Brand constraints to enforce.
        """
        self.brand_guidelines = brand_guidelines or BrandGuidelines()
        self.constraint_checker = BrandConstraintChecker(self.brand_guidelines)

        # Initialize all operators
        self.operators: dict[str, VariationOperator] = {
            "palette": PaletteVariation(),
            "taper": TaperVariation(),
            "scale": ScaleVariation(),
            "spacing": SpacingVariation(),
            "accent_style": AccentStyleVariation(),
            "depth": DepthVariation(),
            "corner_radius": CornerRadiusVariation(),
            "label_placement": LabelPlacementVariation(),
            "orientation": OrientationVariation(),
            "alignment": AlignmentVariation(),
        }

    def apply_variation(
        self,
        dsl: dict[str, Any],
        operator_name: str,
        params: VariationParams | None = None,
    ) -> VariationResult:
        """Apply a single variation operator.

        Args:
            dsl: Input DSL scene graph.
            operator_name: Name of operator to apply.
            params: Variation parameters.

        Returns:
            VariationResult with modified DSL.
        """
        operator = self.operators.get(operator_name)
        if not operator:
            raise ValueError(f"Unknown operator: {operator_name}")

        params = params or VariationParams()

        # Apply variation
        varied_dsl = operator.apply(dsl, params)

        # Check constraints
        result = self.constraint_checker.check(varied_dsl)

        # Auto-fix if needed
        if not result.is_valid:
            varied_dsl, result = self.constraint_checker.enforce(varied_dsl)

        return VariationResult(
            dsl=varied_dsl,
            operators_applied=[operator_name],
            constraint_score=result.score,
            is_valid=result.is_valid,
            seed=params.seed,
        )

    def apply_chain(
        self,
        dsl: dict[str, Any],
        operations: list[tuple[str, VariationParams]],
    ) -> VariationResult:
        """Apply a chain of variations.

        Args:
            dsl: Input DSL.
            operations: List of (operator_name, params) tuples.

        Returns:
            VariationResult with all variations applied.
        """
        current_dsl = copy.deepcopy(dsl)
        applied = []

        for operator_name, params in operations:
            result = self.apply_variation(current_dsl, operator_name, params)
            current_dsl = result.dsl
            applied.append(operator_name)

        # Final constraint check
        final_result = self.constraint_checker.check(current_dsl)

        return VariationResult(
            dsl=current_dsl,
            operators_applied=applied,
            constraint_score=final_result.score,
            is_valid=final_result.is_valid,
        )

    def generate_variations(
        self,
        dsl: dict[str, Any],
        count: int = 3,
        strategy: str = "diverse",
        seed: int | None = None,
    ) -> list[VariationResult]:
        """Generate multiple variations of a DSL.

        Args:
            dsl: Input DSL.
            count: Number of variations to generate.
            strategy: Sampling strategy ("random", "grid", "diverse").
            seed: Random seed for reproducibility.

        Returns:
            List of VariationResults.
        """
        config = SamplingConfig(
            num_variations=count,
            seed=seed,
            diversity=0.7 if strategy == "diverse" else 0.5,
        )
        sampler = VariationSampler(
            operators=list(self.operators.values()),
            config=config,
        )

        # Sample variations
        if strategy == "random":
            samples = sampler.sample_random(dsl, count)
        elif strategy == "grid":
            samples = sampler.sample_grid(dsl)[:count]
        elif strategy == "diverse":
            samples = sampler.sample_diverse(dsl, count)
        else:
            samples = sampler.sample_random(dsl, count)

        # Apply variations
        results = []
        for op_name, params in samples:
            try:
                result = self.apply_variation(dsl, op_name, params)
                results.append(result)
            except Exception:
                # Skip failed variations
                continue

        return results

    def generate_combination_variations(
        self,
        dsl: dict[str, Any],
        count: int = 3,
        operators_per_variation: int = 2,
        seed: int | None = None,
    ) -> list[VariationResult]:
        """Generate variations using operator combinations.

        Args:
            dsl: Input DSL.
            count: Number of variations.
            operators_per_variation: Operators to combine per variation.
            seed: Random seed.

        Returns:
            List of VariationResults.
        """
        config = SamplingConfig(
            num_variations=count,
            seed=seed,
        )
        sampler = VariationSampler(
            operators=list(self.operators.values()),
            config=config,
        )

        combinations = sampler.sample_combination(
            dsl,
            operators_per_variation=operators_per_variation,
            count=count,
        )

        results = []
        for combo in combinations:
            try:
                result = self.apply_chain(dsl, combo)
                results.append(result)
            except Exception:
                continue

        return results

    def apply_preset(
        self,
        dsl: dict[str, Any],
        preset: str,
    ) -> VariationResult:
        """Apply a preset variation combination.

        Args:
            dsl: Input DSL.
            preset: Preset name.

        Returns:
            VariationResult.
        """
        presets = {
            "modern": [
                ("palette", VariationParams(intensity=0.5, extra={"mode": "preset", "preset": "slate"})),
                ("corner_radius", VariationParams(intensity=0.7, extra={"preset": "rounded"})),
                ("depth", VariationParams(intensity=0.4, extra={"preset": "soft"})),
            ],
            "vibrant": [
                ("palette", VariationParams(intensity=0.8, extra={"mode": "preset", "preset": "berry"})),
                ("accent_style", VariationParams(intensity=0.7, extra={"style": "glow"})),
                ("depth", VariationParams(intensity=0.6, extra={"preset": "elevated"})),
            ],
            "minimal": [
                ("palette", VariationParams(intensity=0.3, extra={"mode": "monochromatic", "base_color": "#334155"})),
                ("corner_radius", VariationParams(intensity=0.2, extra={"preset": "sharp"})),
                ("depth", VariationParams(intensity=0.1, extra={"preset": "flat"})),
                ("accent_style", VariationParams(intensity=0.1, extra={"style": "none"})),
            ],
            "corporate": [
                ("palette", VariationParams(intensity=0.5, extra={"mode": "preset", "preset": "teal"})),
                ("corner_radius", VariationParams(intensity=0.4, extra={"preset": "subtle"})),
                ("depth", VariationParams(intensity=0.5, extra={"preset": "subtle"})),
            ],
            "playful": [
                ("palette", VariationParams(intensity=0.9, extra={"mode": "preset", "preset": "sunset"})),
                ("corner_radius", VariationParams(intensity=1.0, extra={"preset": "pill"})),
                ("accent_style", VariationParams(intensity=0.8, extra={"style": "ring"})),
            ],
        }

        operations = presets.get(preset, presets["modern"])
        return self.apply_chain(dsl, operations)

    def get_available_operators(self, dsl: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Get operators applicable to the given DSL.

        Args:
            dsl: Input DSL.

        Returns:
            Dict of operator_name -> variation_range.
        """
        available = {}
        archetype = dsl.get("archetype", "")

        for name, op in self.operators.items():
            if not op.applicable_archetypes or archetype in op.applicable_archetypes:
                available[name] = {
                    "description": op.description,
                    "variation_range": op.get_variation_range(dsl),
                }

        return available

    def preview_variation(
        self,
        dsl: dict[str, Any],
        operator_name: str,
        intensities: list[float] | None = None,
    ) -> list[VariationResult]:
        """Preview variation at different intensities.

        Args:
            dsl: Input DSL.
            operator_name: Operator to preview.
            intensities: List of intensity values to try.

        Returns:
            List of VariationResults at each intensity.
        """
        intensities = intensities or [0.2, 0.5, 0.8]
        results = []

        for intensity in intensities:
            params = VariationParams(
                intensity=intensity,
                seed=42,  # Fixed seed for comparison
            )
            result = self.apply_variation(dsl, operator_name, params)
            results.append(result)

        return results
