"""Variation sampling system."""

import random
from dataclasses import dataclass, field
from typing import Any

from backend.creativity.operators.base import VariationOperator, VariationParams


@dataclass
class SamplingConfig:
    """Configuration for variation sampling."""

    # Number of variations to generate
    num_variations: int = 3

    # Random seed for reproducibility
    seed: int | None = None

    # Diversity preference (0.0 = similar, 1.0 = diverse)
    diversity: float = 0.5

    # Operator weights (operator_name -> weight)
    operator_weights: dict[str, float] = field(default_factory=dict)

    # Intensity range for variations
    min_intensity: float = 0.2
    max_intensity: float = 0.8


class VariationSampler:
    """Sample from variation space to generate diverse outputs.

    Uses different strategies to explore the variation space:
    - Random: Random combinations of operators
    - Grid: Systematic grid search
    - Diverse: Maximize diversity between variations
    """

    def __init__(
        self,
        operators: list[VariationOperator],
        config: SamplingConfig | None = None,
    ):
        """Initialize sampler.

        Args:
            operators: Available variation operators.
            config: Sampling configuration.
        """
        self.operators = {op.name: op for op in operators}
        self.config = config or SamplingConfig()

        if self.config.seed is not None:
            random.seed(self.config.seed)

    def sample_random(
        self,
        dsl: dict[str, Any],
        count: int | None = None,
    ) -> list[tuple[str, VariationParams]]:
        """Sample random operator-params combinations.

        Args:
            dsl: Input DSL for context.
            count: Number of samples.

        Returns:
            List of (operator_name, params) tuples.
        """
        count = count or self.config.num_variations
        samples = []

        applicable_ops = self._get_applicable_operators(dsl)
        if not applicable_ops:
            return samples

        for _ in range(count):
            op_name = self._weighted_choice(applicable_ops)
            intensity = random.uniform(
                self.config.min_intensity,
                self.config.max_intensity,
            )
            params = VariationParams(
                intensity=intensity,
                seed=random.randint(0, 2**31),
            )
            samples.append((op_name, params))

        return samples

    def sample_grid(
        self,
        dsl: dict[str, Any],
        operators: list[str] | None = None,
        intensity_steps: int = 3,
    ) -> list[tuple[str, VariationParams]]:
        """Sample using grid search over intensity levels.

        Args:
            dsl: Input DSL.
            operators: Specific operators to sample (None = all).
            intensity_steps: Number of intensity levels.

        Returns:
            List of (operator_name, params) tuples.
        """
        samples = []

        applicable_ops = self._get_applicable_operators(dsl)
        if operators:
            applicable_ops = [op for op in applicable_ops if op in operators]

        intensities = [
            self.config.min_intensity + (self.config.max_intensity - self.config.min_intensity) * i / (intensity_steps - 1)
            for i in range(intensity_steps)
        ]

        for op_name in applicable_ops:
            for intensity in intensities:
                params = VariationParams(
                    intensity=intensity,
                    seed=random.randint(0, 2**31),
                )
                samples.append((op_name, params))

        return samples

    def sample_diverse(
        self,
        dsl: dict[str, Any],
        count: int | None = None,
    ) -> list[tuple[str, VariationParams]]:
        """Sample to maximize diversity between variations.

        Args:
            dsl: Input DSL.
            count: Number of samples.

        Returns:
            List of (operator_name, params) tuples.
        """
        count = count or self.config.num_variations
        samples = []

        applicable_ops = self._get_applicable_operators(dsl)
        if not applicable_ops:
            return samples

        # Categorize operators
        categories = {
            "color": ["palette"],
            "geometry": ["taper", "scale", "spacing"],
            "style": ["accent_style", "depth", "corner_radius"],
            "layout": ["label_placement", "orientation", "alignment"],
        }

        # Reverse mapping
        op_to_category = {}
        for category, ops in categories.items():
            for op in ops:
                op_to_category[op] = category

        # Sample from different categories to maximize diversity
        used_categories = set()
        for i in range(count):
            # Prefer unused categories
            available = [
                op for op in applicable_ops
                if op_to_category.get(op, "other") not in used_categories
            ]

            if not available:
                # All categories used, reset
                used_categories.clear()
                available = applicable_ops

            op_name = self._weighted_choice(available)
            category = op_to_category.get(op_name, "other")
            used_categories.add(category)

            # Vary intensity based on diversity setting
            if self.config.diversity > 0.5:
                # High diversity: more extreme intensities
                intensity = random.choice([
                    self.config.min_intensity,
                    self.config.max_intensity,
                ])
            else:
                # Low diversity: moderate intensities
                intensity = random.uniform(0.4, 0.6)

            params = VariationParams(
                intensity=intensity,
                seed=random.randint(0, 2**31),
            )
            samples.append((op_name, params))

        return samples

    def sample_combination(
        self,
        dsl: dict[str, Any],
        operators_per_variation: int = 2,
        count: int | None = None,
    ) -> list[list[tuple[str, VariationParams]]]:
        """Sample combinations of operators.

        Args:
            dsl: Input DSL.
            operators_per_variation: Number of operators to combine.
            count: Number of variations.

        Returns:
            List of operator-params lists.
        """
        count = count or self.config.num_variations
        combinations = []

        applicable_ops = self._get_applicable_operators(dsl)
        if len(applicable_ops) < operators_per_variation:
            operators_per_variation = len(applicable_ops)

        for _ in range(count):
            # Select diverse operators
            selected = random.sample(applicable_ops, operators_per_variation)

            combo = []
            for op_name in selected:
                intensity = random.uniform(
                    self.config.min_intensity,
                    self.config.max_intensity,
                )
                params = VariationParams(
                    intensity=intensity * 0.7,  # Lower intensity for combinations
                    seed=random.randint(0, 2**31),
                )
                combo.append((op_name, params))

            combinations.append(combo)

        return combinations

    def _get_applicable_operators(self, dsl: dict[str, Any]) -> list[str]:
        """Get operators applicable to the DSL."""
        applicable = []
        archetype = dsl.get("archetype", "")

        for name, op in self.operators.items():
            # Check if operator is applicable
            if not op.applicable_archetypes:
                # No restrictions, always applicable
                applicable.append(name)
            elif archetype in op.applicable_archetypes:
                applicable.append(name)
            elif op.validate(dsl):
                applicable.append(name)

        return applicable

    def _weighted_choice(self, operators: list[str]) -> str:
        """Choose operator with weights."""
        if not operators:
            raise ValueError("No operators to choose from")

        weights = [
            self.config.operator_weights.get(op, 1.0)
            for op in operators
        ]

        total = sum(weights)
        r = random.uniform(0, total)

        cumulative = 0
        for op, weight in zip(operators, weights):
            cumulative += weight
            if r <= cumulative:
                return op

        return operators[-1]
