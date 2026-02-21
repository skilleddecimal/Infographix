"""Inference module for Style Recommender."""

from pathlib import Path
from typing import Any

from ml.config import get_ml_settings
from ml.models.style_recommender.model import StyleRecommender, StyleResult


class StyleRecommenderInference:
    """Production inference wrapper for Style Recommender.

    Uses rule-based recommendations with ML enhancement when available.
    """

    # Rule-based palette mappings
    ARCHETYPE_PALETTES = {
        "funnel": "teal",
        "pyramid": "amber",
        "timeline": "blue",
        "process": "emerald",
        "cycle": "purple",
        "hub_spoke": "teal",
        "matrix": "slate",
        "comparison": "rose",
        "org_chart": "blue",
        "venn": "purple",
        "gauge": "emerald",
        "bullet_list": "slate",
        "flowchart": "blue",
    }

    FORMALITY_STYLES = {
        "casual": {
            "shadow": "none",
            "glow": "subtle",
            "corner_radius": "pill",
            "font_family": "Poppins",
        },
        "professional": {
            "shadow": "soft",
            "glow": "none",
            "corner_radius": "rounded",
            "font_family": "Inter",
        },
        "corporate": {
            "shadow": "hard",
            "glow": "none",
            "corner_radius": "sharp",
            "font_family": "Roboto",
        },
    }

    def __init__(self, model_path: Path | str | None = None):
        """Initialize inference engine.

        Args:
            model_path: Path to saved model.
        """
        self.settings = get_ml_settings()
        self.model_path = Path(model_path) if model_path else self.settings.paths.style_recommender
        self._model = None

    @property
    def model(self) -> StyleRecommender:
        """Lazy load the model."""
        if self._model is None:
            self._model = self._load_model()
        return self._model

    def _load_model(self) -> StyleRecommender:
        """Load the model."""
        if (self.model_path / "model.pt").exists():
            return StyleRecommender.load(self.model_path)
        else:
            return StyleRecommender()

    def recommend(
        self,
        features: dict[str, Any],
        use_ml: bool = True,
    ) -> StyleResult:
        """Recommend styles for given features.

        Args:
            features: Input features (archetype, item_count, formality, etc.).
            use_ml: Whether to use ML model.

        Returns:
            Style recommendation.
        """
        # Try ML model first
        if use_ml and (self.model_path / "model.pt").exists():
            try:
                return self.model.recommend(features)
            except Exception:
                pass

        # Fall back to rule-based recommendations
        return self._rule_based_recommend(features)

    def _rule_based_recommend(self, features: dict[str, Any]) -> StyleResult:
        """Rule-based style recommendation.

        Args:
            features: Input features.

        Returns:
            Style recommendation.
        """
        archetype = features.get("archetype", "process")
        formality = features.get("formality", "professional")

        # Get palette
        palette_name = self.ARCHETYPE_PALETTES.get(archetype, "teal")
        palette = StyleRecommender.PALETTES[palette_name]

        # Get formality-based styles
        styles = self.FORMALITY_STYLES.get(formality, self.FORMALITY_STYLES["professional"])

        return StyleResult(
            color_palette=palette,
            shadow=styles["shadow"],
            glow=styles["glow"],
            corner_radius=styles["corner_radius"],
            font_family=styles["font_family"],
            confidence=0.7,  # Rule-based confidence
        )

    def recommend_for_brand(
        self,
        features: dict[str, Any],
        brand_colors: list[str],
        brand_fonts: list[str] | None = None,
    ) -> StyleResult:
        """Recommend styles that fit brand guidelines.

        Args:
            features: Input features.
            brand_colors: Brand color palette.
            brand_fonts: Brand font families.

        Returns:
            Brand-compliant style recommendation.
        """
        # Start with base recommendation
        base = self.recommend(features)

        # Override with brand colors
        if brand_colors:
            # Extend brand colors to 6 if needed
            palette = brand_colors.copy()
            while len(palette) < 6:
                palette.append(palette[-1])
            palette = palette[:6]
        else:
            palette = base.color_palette

        # Override font if specified
        font = brand_fonts[0] if brand_fonts else base.font_family

        return StyleResult(
            color_palette=palette,
            shadow=base.shadow,
            glow=base.glow,
            corner_radius=base.corner_radius,
            font_family=font,
            confidence=base.confidence,
        )

    def get_style_variations(
        self,
        features: dict[str, Any],
        count: int = 3,
    ) -> list[StyleResult]:
        """Get multiple style variations.

        Args:
            features: Input features.
            count: Number of variations.

        Returns:
            List of style recommendations.
        """
        variations = []

        # Base recommendation
        variations.append(self.recommend(features))

        # Alternative palettes
        archetype = features.get("archetype", "process")
        base_palette = self.ARCHETYPE_PALETTES.get(archetype, "teal")

        alternative_palettes = [
            name for name in StyleRecommender.PALETTES.keys()
            if name != base_palette
        ]

        for alt_palette in alternative_palettes[:count - 1]:
            palette = StyleRecommender.PALETTES[alt_palette]
            base = variations[0]

            variations.append(StyleResult(
                color_palette=palette,
                shadow=base.shadow,
                glow=base.glow,
                corner_radius=base.corner_radius,
                font_family=base.font_family,
                confidence=0.6,
            ))

        return variations[:count]
