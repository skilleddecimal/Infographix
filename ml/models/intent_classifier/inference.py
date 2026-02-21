"""Inference module for Intent Classifier."""

import json
from pathlib import Path
from typing import Any

from ml.config import get_ml_settings
from ml.models.intent_classifier.model import ClassificationResult, IntentClassifier


class IntentClassifierInference:
    """Production inference wrapper for Intent Classifier.

    Handles model loading, caching, and efficient inference.
    """

    def __init__(self, model_path: Path | str | None = None):
        """Initialize inference engine.

        Args:
            model_path: Path to saved model. Uses default if None.
        """
        self.settings = get_ml_settings()
        self.model_path = Path(model_path) if model_path else self.settings.paths.intent_classifier
        self._model = None
        self._fallback_rules = self._load_fallback_rules()

    def _load_fallback_rules(self) -> dict[str, list[str]]:
        """Load keyword-based fallback rules."""
        return {
            "funnel": ["funnel", "conversion", "sales", "leads", "pipeline", "stages"],
            "pyramid": ["pyramid", "hierarchy", "levels", "tiers", "maslow", "priorities"],
            "timeline": ["timeline", "roadmap", "milestones", "schedule", "history", "dates"],
            "process": ["process", "workflow", "steps", "procedure", "flow", "sequence"],
            "cycle": ["cycle", "wheel", "loop", "circular", "recurring", "continuous"],
            "hub_spoke": ["hub", "spoke", "radial", "central", "core", "connected"],
            "matrix": ["matrix", "grid", "quadrant", "swot", "2x2", "table"],
            "comparison": ["comparison", "versus", "vs", "compare", "pros", "cons", "before after"],
            "org_chart": ["org chart", "organization", "hierarchy", "reporting", "structure"],
            "venn": ["venn", "overlap", "intersection", "circles"],
            "gauge": ["gauge", "meter", "speedometer", "kpi", "progress"],
            "bullet_list": ["bullet", "list", "checklist", "points", "features"],
            "flowchart": ["flowchart", "decision", "algorithm", "branch", "if then"],
        }

    @property
    def model(self) -> IntentClassifier:
        """Lazy load the model."""
        if self._model is None:
            self._model = self._load_model()
        return self._model

    def _load_model(self) -> IntentClassifier:
        """Load the model from disk or create a new one."""
        if (self.model_path / "model.pt").exists():
            return IntentClassifier.load(self.model_path)
        else:
            # Return uninitialized model (will use fallback rules)
            model = IntentClassifier()
            return model

    def predict(
        self,
        prompt: str,
        use_fallback: bool = True,
    ) -> ClassificationResult:
        """Predict archetype for a prompt.

        Args:
            prompt: User prompt text.
            use_fallback: Whether to use fallback rules if model unavailable.

        Returns:
            Classification result.
        """
        try:
            # Try ML model first
            if self._model is not None or (self.model_path / "model.pt").exists():
                return self.model.predict(prompt)
        except Exception as e:
            if not use_fallback:
                raise

        # Fallback to keyword matching
        return self._fallback_predict(prompt)

    def _fallback_predict(self, prompt: str) -> ClassificationResult:
        """Keyword-based fallback prediction.

        Args:
            prompt: User prompt text.

        Returns:
            Classification result based on keywords.
        """
        prompt_lower = prompt.lower()
        scores = {}

        for archetype, keywords in self._fallback_rules.items():
            score = 0.0
            for keyword in keywords:
                if keyword in prompt_lower:
                    score += 1.0
            scores[archetype] = score / len(keywords)

        # Get best match
        if scores:
            best_archetype = max(scores, key=scores.get)
            confidence = scores[best_archetype]

            # Normalize scores
            total = sum(scores.values())
            if total > 0:
                all_scores = {k: v / total for k, v in scores.items()}
                confidence = all_scores[best_archetype]
            else:
                all_scores = scores
                best_archetype = "other"
                confidence = 0.0
        else:
            best_archetype = "other"
            confidence = 0.0
            all_scores = {"other": 1.0}

        return ClassificationResult(
            archetype=best_archetype,
            confidence=confidence,
            all_scores=all_scores,
        )

    def batch_predict(
        self,
        prompts: list[str],
    ) -> list[ClassificationResult]:
        """Predict archetypes for multiple prompts.

        Args:
            prompts: List of prompts.

        Returns:
            List of classification results.
        """
        # For now, sequential prediction
        # TODO: Implement batched inference for efficiency
        return [self.predict(prompt) for prompt in prompts]

    def extract_parameters(
        self,
        prompt: str,
        archetype: str,
    ) -> dict[str, Any]:
        """Extract parameters from prompt for a given archetype.

        Args:
            prompt: User prompt text.
            archetype: Detected archetype.

        Returns:
            Extracted parameters.
        """
        params = {}
        prompt_lower = prompt.lower()

        # Extract count (e.g., "5 steps", "three stages")
        number_words = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        }

        # Check for number words
        for word, num in number_words.items():
            if word in prompt_lower:
                params["count"] = num
                break

        # Check for digits
        import re
        numbers = re.findall(r"\b(\d+)\b", prompt)
        if numbers and "count" not in params:
            params["count"] = int(numbers[0])

        # Extract orientation hints
        if "vertical" in prompt_lower:
            params["orientation"] = "vertical"
        elif "horizontal" in prompt_lower:
            params["orientation"] = "horizontal"

        # Extract style hints
        if "simple" in prompt_lower or "minimal" in prompt_lower:
            params["style"] = "minimal"
        elif "detailed" in prompt_lower or "complex" in prompt_lower:
            params["style"] = "detailed"

        # Archetype-specific extraction
        if archetype == "matrix":
            # Look for NxM pattern
            grid_pattern = re.search(r"(\d+)\s*[xX]\s*(\d+)", prompt)
            if grid_pattern:
                params["rows"] = int(grid_pattern.group(1))
                params["cols"] = int(grid_pattern.group(2))

        elif archetype == "timeline":
            # Look for year/quarter patterns
            years = re.findall(r"\b(20\d{2})\b", prompt)
            if years:
                params["years"] = years
            quarters = re.findall(r"\b(Q[1-4])\b", prompt, re.IGNORECASE)
            if quarters:
                params["quarters"] = quarters

        return params
