"""Unified inference engine for Infographix ML pipeline."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ml.config import get_ml_settings
from ml.models.intent_classifier.inference import IntentClassifierInference
from ml.models.intent_classifier.model import ClassificationResult
from ml.models.layout_generator.inference import LayoutGeneratorInference
from ml.models.layout_generator.model import LayoutResult
from ml.models.style_recommender.inference import StyleRecommenderInference
from ml.models.style_recommender.model import StyleResult


@dataclass
class InferenceResult:
    """Complete result of the ML inference pipeline."""

    # Classification
    archetype: str
    classification_confidence: float
    all_archetype_scores: dict[str, float]

    # Parameters extracted from prompt
    parameters: dict[str, Any]

    # Generated layout
    dsl: dict[str, Any]
    layout_confidence: float

    # Style recommendations
    style: StyleResult

    # Raw results for debugging
    classification_result: ClassificationResult | None = None
    layout_result: LayoutResult | None = None

    @property
    def confidence(self) -> float:
        """Overall confidence score."""
        return (
            self.classification_confidence * 0.4 +
            self.layout_confidence * 0.4 +
            self.style.confidence * 0.2
        )


class InferenceEngine:
    """Unified inference engine combining all ML models.

    Pipeline:
    1. Intent Classification: Prompt -> Archetype + Parameters
    2. Layout Generation: Intent -> DSL Scene Graph
    3. Style Recommendation: Features -> Style Tokens
    """

    def __init__(
        self,
        models_dir: Path | str | None = None,
        use_ml: bool = True,
    ):
        """Initialize the inference engine.

        Args:
            models_dir: Base directory for model checkpoints.
            use_ml: Whether to use ML models (vs rule-based fallbacks).
        """
        self.settings = get_ml_settings()
        self.models_dir = Path(models_dir) if models_dir else Path("ml/checkpoints")
        self.use_ml = use_ml

        # Lazy-loaded model inference wrappers
        self._intent_classifier = None
        self._layout_generator = None
        self._style_recommender = None

    @property
    def intent_classifier(self) -> IntentClassifierInference:
        """Get intent classifier inference wrapper."""
        if self._intent_classifier is None:
            self._intent_classifier = IntentClassifierInference(
                model_path=self.models_dir / "intent_classifier"
            )
        return self._intent_classifier

    @property
    def layout_generator(self) -> LayoutGeneratorInference:
        """Get layout generator inference wrapper."""
        if self._layout_generator is None:
            self._layout_generator = LayoutGeneratorInference(
                model_path=self.models_dir / "layout_generator"
            )
        return self._layout_generator

    @property
    def style_recommender(self) -> StyleRecommenderInference:
        """Get style recommender inference wrapper."""
        if self._style_recommender is None:
            self._style_recommender = StyleRecommenderInference(
                model_path=self.models_dir / "style_recommender"
            )
        return self._style_recommender

    def generate(
        self,
        prompt: str,
        content: list[dict[str, str]] | None = None,
        brand_colors: list[str] | None = None,
        brand_fonts: list[str] | None = None,
        formality: str = "professional",
    ) -> InferenceResult:
        """Generate infographic from prompt.

        Args:
            prompt: User's natural language prompt.
            content: Optional content items to fill in.
            brand_colors: Optional brand color palette.
            brand_fonts: Optional brand fonts.
            formality: Style formality level.

        Returns:
            Complete inference result with DSL and styles.
        """
        # Step 1: Classify intent
        classification = self.intent_classifier.predict(prompt)

        # Step 2: Extract parameters
        parameters = self.intent_classifier.extract_parameters(
            prompt=prompt,
            archetype=classification.archetype,
        )

        # Step 3: Build intent specification
        intent = {
            "archetype": classification.archetype,
            "item_count": parameters.get("count", 4),
            "orientation": parameters.get("orientation", "horizontal"),
            "style_hints": [],
            **parameters,
        }

        # Step 4: Generate layout
        if content:
            layout = self.layout_generator.generate_with_content(intent, content)
        else:
            layout = self.layout_generator.generate(intent, use_ml=self.use_ml)

        # Step 5: Recommend styles
        style_features = {
            "archetype": classification.archetype,
            "item_count": intent["item_count"],
            "has_icons": "icon" in prompt.lower(),
            "has_descriptions": content is not None and any("description" in c for c in content),
            "formality": formality,
        }

        if brand_colors:
            style = self.style_recommender.recommend_for_brand(
                features=style_features,
                brand_colors=brand_colors,
                brand_fonts=brand_fonts,
            )
        else:
            style = self.style_recommender.recommend(
                features=style_features,
                use_ml=self.use_ml,
            )

        # Step 6: Apply styles to DSL
        styled_dsl = self._apply_styles(layout.dsl, style)

        return InferenceResult(
            archetype=classification.archetype,
            classification_confidence=classification.confidence,
            all_archetype_scores=classification.all_scores,
            parameters=parameters,
            dsl=styled_dsl,
            layout_confidence=layout.confidence,
            style=style,
            classification_result=classification,
            layout_result=layout,
        )

    def generate_variations(
        self,
        prompt: str,
        count: int = 3,
        **kwargs,
    ) -> list[InferenceResult]:
        """Generate multiple variations of an infographic.

        Args:
            prompt: User's prompt.
            count: Number of variations.
            **kwargs: Additional arguments passed to generate().

        Returns:
            List of inference results.
        """
        # Get base result
        base = self.generate(prompt, **kwargs)

        variations = [base]

        # Get layout variations
        intent = {
            "archetype": base.archetype,
            "item_count": base.parameters.get("count", 4),
            **base.parameters,
        }
        layout_variations = self.layout_generator.generate_variations(intent, count=count)

        # Get style variations
        style_features = {
            "archetype": base.archetype,
            "item_count": intent["item_count"],
            "formality": kwargs.get("formality", "professional"),
        }
        style_variations = self.style_recommender.get_style_variations(style_features, count=count)

        # Combine variations
        for i in range(1, min(count, len(layout_variations), len(style_variations))):
            styled_dsl = self._apply_styles(layout_variations[i].dsl, style_variations[i])

            variations.append(InferenceResult(
                archetype=base.archetype,
                classification_confidence=base.classification_confidence,
                all_archetype_scores=base.all_archetype_scores,
                parameters=base.parameters,
                dsl=styled_dsl,
                layout_confidence=layout_variations[i].confidence,
                style=style_variations[i],
            ))

        return variations[:count]

    def _apply_styles(self, dsl: dict[str, Any], style: StyleResult) -> dict[str, Any]:
        """Apply style recommendations to DSL.

        Args:
            dsl: Layout DSL.
            style: Style recommendations.

        Returns:
            Styled DSL.
        """
        import copy
        styled = copy.deepcopy(dsl)

        # Update theme colors
        if "theme" not in styled:
            styled["theme"] = {}

        for i, color in enumerate(style.color_palette[:6]):
            styled["theme"][f"accent{i + 1}"] = color

        # Update shapes with styles
        for shape in styled.get("shapes", []):
            # Apply corner radius
            if style.corner_radius == "rounded":
                if shape.get("auto_shape_type") == "rect":
                    shape["auto_shape_type"] = "roundRect"
            elif style.corner_radius == "pill":
                if shape.get("auto_shape_type") in ["rect", "roundRect"]:
                    shape["corner_radius"] = "50%"

            # Apply shadow
            if style.shadow != "none":
                if "effects" not in shape:
                    shape["effects"] = {}
                shape["effects"]["shadow"] = {
                    "type": style.shadow,
                    "blur": 4 if style.shadow == "soft" else 2,
                    "offset_x": 2,
                    "offset_y": 2,
                    "color": "#00000040",
                }

            # Apply glow
            if style.glow != "none":
                if "effects" not in shape:
                    shape["effects"] = {}
                shape["effects"]["glow"] = {
                    "type": style.glow,
                    "radius": 4 if style.glow == "subtle" else 8,
                }

            # Resolve color tokens
            fill = shape.get("fill", {})
            if isinstance(fill, dict) and "color" in fill:
                color = fill["color"]
                if color.startswith("accent"):
                    try:
                        idx = int(color.replace("accent", "")) - 1
                        fill["color"] = style.color_palette[idx]
                    except (ValueError, IndexError):
                        pass

        # Add font information
        styled["font_family"] = style.font_family

        return styled

    def classify_only(self, prompt: str) -> ClassificationResult:
        """Classify prompt without generating layout.

        Args:
            prompt: User prompt.

        Returns:
            Classification result.
        """
        return self.intent_classifier.predict(prompt)

    def recommend_style_only(
        self,
        archetype: str,
        formality: str = "professional",
    ) -> StyleResult:
        """Get style recommendation without layout.

        Args:
            archetype: Infographic archetype.
            formality: Style formality.

        Returns:
            Style recommendation.
        """
        features = {
            "archetype": archetype,
            "item_count": 4,
            "formality": formality,
        }
        return self.style_recommender.recommend(features)
