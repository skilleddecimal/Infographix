"""Base class for variation operators."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VariationParams:
    """Parameters for variation operations."""

    # Intensity of variation (0.0 = no change, 1.0 = maximum change)
    intensity: float = 0.5

    # Random seed for reproducibility
    seed: int | None = None

    # Additional parameters specific to each operator
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate parameters."""
        if not 0.0 <= self.intensity <= 1.0:
            raise ValueError("Intensity must be between 0.0 and 1.0")


class VariationOperator(ABC):
    """Abstract base class for variation operators.

    Variation operators transform DSL scene graphs while preserving
    structural integrity and brand constraints.
    """

    # Operator name for registry
    name: str = "base"

    # Description for UI/docs
    description: str = "Base variation operator"

    # Which archetypes this operator is applicable to
    applicable_archetypes: list[str] = []

    @abstractmethod
    def apply(self, dsl: dict[str, Any], params: VariationParams) -> dict[str, Any]:
        """Apply variation to DSL.

        Args:
            dsl: Input DSL scene graph.
            params: Variation parameters.

        Returns:
            Modified DSL scene graph.
        """
        pass

    @abstractmethod
    def get_variation_range(self, dsl: dict[str, Any]) -> dict[str, Any]:
        """Get the range of possible variations.

        Args:
            dsl: Input DSL scene graph.

        Returns:
            Dictionary describing variation bounds.
        """
        pass

    def validate(self, dsl: dict[str, Any]) -> bool:
        """Check if this operator can be applied to the DSL.

        Args:
            dsl: Input DSL scene graph.

        Returns:
            True if operator is applicable.
        """
        return True

    def _deep_copy(self, dsl: dict[str, Any]) -> dict[str, Any]:
        """Create a deep copy of the DSL."""
        import copy
        return copy.deepcopy(dsl)
