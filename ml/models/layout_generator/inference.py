"""Inference module for Layout Generator."""

from pathlib import Path
from typing import Any

from ml.config import get_ml_settings
from ml.models.layout_generator.model import LayoutGenerator, LayoutResult


class LayoutGeneratorInference:
    """Production inference wrapper for Layout Generator.

    Uses template-based generation with ML enhancement when available.
    """

    def __init__(self, model_path: Path | str | None = None):
        """Initialize inference engine.

        Args:
            model_path: Path to saved model.
        """
        self.settings = get_ml_settings()
        self.model_path = Path(model_path) if model_path else self.settings.paths.layout_generator
        self._model = None

    @property
    def model(self) -> LayoutGenerator:
        """Lazy load the model."""
        if self._model is None:
            self._model = self._load_model()
        return self._model

    def _load_model(self) -> LayoutGenerator:
        """Load the model."""
        if (self.model_path / "model").exists():
            return LayoutGenerator.load(self.model_path)
        else:
            # Return uninitialized model (will use fallback templates)
            return LayoutGenerator()

    def generate(
        self,
        intent: dict[str, Any],
        use_ml: bool = True,
    ) -> LayoutResult:
        """Generate DSL from intent.

        Args:
            intent: Intent specification.
            use_ml: Whether to use ML model (if available).

        Returns:
            Layout generation result.
        """
        # Check if ML model is available and requested
        if use_ml and self._model is not None and self._model._initialized:
            try:
                return self.model.generate(intent)
            except Exception:
                pass

        # Fall back to template-based generation
        return self._template_generate(intent)

    def _template_generate(self, intent: dict[str, Any]) -> LayoutResult:
        """Generate layout using templates.

        Args:
            intent: Intent specification.

        Returns:
            Template-based layout result.
        """
        # Use the model's fallback generation
        model = LayoutGenerator()
        dsl = model._generate_fallback(intent)

        return LayoutResult(
            dsl=dsl,
            confidence=0.7,  # Template-based, reasonable confidence
            raw_output="",
        )

    def generate_with_content(
        self,
        intent: dict[str, Any],
        content: list[dict[str, str]],
    ) -> LayoutResult:
        """Generate layout with content filled in.

        Args:
            intent: Intent specification.
            content: List of content items with 'title' and optional 'description'.

        Returns:
            Layout result with content integrated.
        """
        result = self.generate(intent)

        # Fill in content
        dsl = result.dsl
        shapes = dsl.get("shapes", [])

        for i, shape in enumerate(shapes):
            if i < len(content):
                item = content[i]
                if "text" not in shape:
                    shape["text"] = {}
                shape["text"]["runs"] = [{"text": item.get("title", "")}]

        return LayoutResult(
            dsl=dsl,
            confidence=result.confidence,
            raw_output=result.raw_output,
        )

    def generate_variations(
        self,
        intent: dict[str, Any],
        count: int = 3,
    ) -> list[LayoutResult]:
        """Generate multiple layout variations.

        Args:
            intent: Intent specification.
            count: Number of variations.

        Returns:
            List of layout variations.
        """
        import copy

        variations = []

        # Variation 1: Standard
        variations.append(self.generate(intent))

        # Variation 2: Different orientation
        intent_v2 = copy.deepcopy(intent)
        current_orientation = intent.get("orientation", "horizontal")
        intent_v2["orientation"] = "vertical" if current_orientation == "horizontal" else "horizontal"
        variations.append(self.generate(intent_v2))

        # Variation 3: Different count if applicable
        if count >= 3:
            intent_v3 = copy.deepcopy(intent)
            current_count = intent.get("item_count", 4)
            intent_v3["item_count"] = max(3, current_count - 1)
            variations.append(self.generate(intent_v3))

        return variations[:count]
