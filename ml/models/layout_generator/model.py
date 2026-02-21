"""Layout Generator model using T5."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn

from ml.config import LayoutGeneratorConfig, get_ml_settings


@dataclass
class LayoutResult:
    """Result of layout generation."""

    dsl: dict[str, Any]
    confidence: float
    raw_output: str


class LayoutGenerator(nn.Module):
    """T5-based layout generator.

    Generates DSL scene graphs from intent specifications.
    Uses a sequence-to-sequence approach where the input is
    a structured intent and the output is a JSON DSL.
    """

    def __init__(self, config: LayoutGeneratorConfig | None = None):
        """Initialize the model.

        Args:
            config: Model configuration.
        """
        super().__init__()
        self.config = config or get_ml_settings().layout_generator

        self.model = None
        self.tokenizer = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the T5 model."""
        if self._initialized:
            return

        try:
            from transformers import T5ForConditionalGeneration, T5Tokenizer

            self.tokenizer = T5Tokenizer.from_pretrained(self.config.model_name)
            self.model = T5ForConditionalGeneration.from_pretrained(self.config.model_name)

            self._initialized = True

        except ImportError:
            raise ImportError(
                "transformers library required. Install with: pip install transformers"
            )

    def format_input(self, intent: dict[str, Any]) -> str:
        """Format intent specification as model input.

        Args:
            intent: Intent specification dict.

        Returns:
            Formatted input string.
        """
        # Convert intent to a structured prompt
        parts = [f"generate {intent.get('archetype', 'diagram')} layout:"]

        if "item_count" in intent:
            parts.append(f"items={intent['item_count']}")

        if "orientation" in intent:
            parts.append(f"orientation={intent['orientation']}")

        if "style_hints" in intent:
            parts.append(f"style={','.join(intent['style_hints'])}")

        # Add archetype-specific params
        for key, value in intent.items():
            if key not in ["archetype", "item_count", "orientation", "style_hints", "content_hints"]:
                parts.append(f"{key}={value}")

        return " ".join(parts)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        labels: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Forward pass.

        Args:
            input_ids: Input token IDs.
            attention_mask: Attention mask.
            labels: Target token IDs (for training).

        Returns:
            Model outputs (loss if labels provided, logits otherwise).
        """
        if not self._initialized:
            self.initialize()

        return self.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels,
        )

    def generate(
        self,
        intent: dict[str, Any],
        max_length: int | None = None,
        num_beams: int = 4,
    ) -> LayoutResult:
        """Generate DSL from intent.

        Args:
            intent: Intent specification.
            max_length: Maximum output length.
            num_beams: Beam search width.

        Returns:
            Generated layout result.
        """
        if not self._initialized:
            self.initialize()

        self.model.eval()
        max_length = max_length or self.config.max_output_length

        # Format input
        input_text = self.format_input(intent)

        # Tokenize
        encoding = self.tokenizer(
            input_text,
            max_length=self.config.max_input_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=encoding["input_ids"],
                attention_mask=encoding["attention_mask"],
                max_length=max_length,
                num_beams=num_beams,
                early_stopping=True,
            )

        # Decode
        raw_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Parse as JSON
        try:
            dsl = json.loads(raw_output)
            confidence = 0.9  # High confidence if valid JSON
        except json.JSONDecodeError:
            # Return template-based fallback
            dsl = self._generate_fallback(intent)
            confidence = 0.5

        return LayoutResult(
            dsl=dsl,
            confidence=confidence,
            raw_output=raw_output,
        )

    def _generate_fallback(self, intent: dict[str, Any]) -> dict[str, Any]:
        """Generate fallback DSL using templates.

        Args:
            intent: Intent specification.

        Returns:
            Basic DSL structure.
        """
        archetype = intent.get("archetype", "process")
        item_count = intent.get("item_count", 4)

        # Basic canvas
        canvas_width = 12192000  # Standard slide width in EMUs
        canvas_height = 6858000  # Standard slide height in EMUs

        shapes = []

        if archetype == "funnel":
            shapes = self._generate_funnel_shapes(item_count, canvas_width, canvas_height)
        elif archetype == "pyramid":
            shapes = self._generate_pyramid_shapes(item_count, canvas_width, canvas_height)
        elif archetype == "timeline":
            shapes = self._generate_timeline_shapes(item_count, canvas_width, canvas_height)
        elif archetype == "process":
            shapes = self._generate_process_shapes(item_count, canvas_width, canvas_height)
        elif archetype == "cycle":
            shapes = self._generate_cycle_shapes(item_count, canvas_width, canvas_height)
        else:
            shapes = self._generate_process_shapes(item_count, canvas_width, canvas_height)

        return {
            "canvas": {
                "width": canvas_width,
                "height": canvas_height,
            },
            "shapes": shapes,
            "theme": {
                "accent1": "#0D9488",
                "accent2": "#14B8A6",
                "accent3": "#2DD4BF",
            },
            "metadata": {
                "archetype": archetype,
            },
        }

    def _generate_funnel_shapes(
        self,
        count: int,
        canvas_width: int,
        canvas_height: int,
    ) -> list[dict]:
        """Generate funnel layer shapes."""
        shapes = []
        margin = canvas_width // 10
        usable_width = canvas_width - 2 * margin
        layer_height = (canvas_height - 2 * margin) // count

        for i in range(count):
            width_ratio = 1.0 - (i * 0.15)
            layer_width = int(usable_width * width_ratio)
            x = margin + (usable_width - layer_width) // 2
            y = margin + i * layer_height

            shapes.append({
                "id": f"funnel_layer_{i}",
                "type": "autoShape",
                "auto_shape_type": "trapezoid",
                "bbox": {"x": x, "y": y, "width": layer_width, "height": int(layer_height * 0.9)},
                "fill": {"type": "solid", "color": f"accent{(i % 6) + 1}"},
            })

        return shapes

    def _generate_pyramid_shapes(
        self,
        count: int,
        canvas_width: int,
        canvas_height: int,
    ) -> list[dict]:
        """Generate pyramid tier shapes."""
        shapes = []
        margin = canvas_width // 10
        usable_width = canvas_width - 2 * margin
        tier_height = (canvas_height - 2 * margin) // count

        for i in range(count):
            width_ratio = 0.3 + (i * 0.2)
            tier_width = int(usable_width * width_ratio)
            x = margin + (usable_width - tier_width) // 2
            y = margin + i * tier_height

            shapes.append({
                "id": f"pyramid_tier_{i}",
                "type": "autoShape",
                "auto_shape_type": "trapezoid",
                "bbox": {"x": x, "y": y, "width": tier_width, "height": int(tier_height * 0.9)},
                "fill": {"type": "solid", "color": f"accent{(i % 6) + 1}"},
            })

        return shapes

    def _generate_timeline_shapes(
        self,
        count: int,
        canvas_width: int,
        canvas_height: int,
    ) -> list[dict]:
        """Generate timeline node shapes."""
        shapes = []
        margin = canvas_width // 15
        usable_width = canvas_width - 2 * margin
        node_spacing = usable_width // count
        node_size = min(node_spacing // 2, canvas_height // 4)

        center_y = canvas_height // 2

        for i in range(count):
            x = margin + i * node_spacing + (node_spacing - node_size) // 2
            y = center_y - node_size // 2

            shapes.append({
                "id": f"timeline_node_{i}",
                "type": "autoShape",
                "auto_shape_type": "ellipse",
                "bbox": {"x": x, "y": y, "width": node_size, "height": node_size},
                "fill": {"type": "solid", "color": "accent1"},
            })

        return shapes

    def _generate_process_shapes(
        self,
        count: int,
        canvas_width: int,
        canvas_height: int,
    ) -> list[dict]:
        """Generate process step shapes."""
        shapes = []
        margin = canvas_width // 15
        usable_width = canvas_width - 2 * margin
        step_width = (usable_width - (count - 1) * margin // 2) // count
        step_height = canvas_height // 3

        center_y = (canvas_height - step_height) // 2

        for i in range(count):
            x = margin + i * (step_width + margin // 2)

            shapes.append({
                "id": f"process_step_{i}",
                "type": "autoShape",
                "auto_shape_type": "rect",
                "bbox": {"x": x, "y": center_y, "width": step_width, "height": step_height},
                "fill": {"type": "solid", "color": "accent1"},
            })

        return shapes

    def _generate_cycle_shapes(
        self,
        count: int,
        canvas_width: int,
        canvas_height: int,
    ) -> list[dict]:
        """Generate cycle node shapes."""
        import math

        shapes = []
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        radius = min(canvas_width, canvas_height) // 3
        node_size = radius // 2

        for i in range(count):
            angle = (2 * math.pi * i / count) - math.pi / 2  # Start at top
            x = int(center_x + radius * math.cos(angle) - node_size // 2)
            y = int(center_y + radius * math.sin(angle) - node_size // 2)

            shapes.append({
                "id": f"cycle_node_{i}",
                "type": "autoShape",
                "auto_shape_type": "ellipse",
                "bbox": {"x": x, "y": y, "width": node_size, "height": node_size},
                "fill": {"type": "solid", "color": "accent1"},
            })

        return shapes

    def save(self, path: Path | str) -> None:
        """Save model to disk."""
        if not self._initialized:
            return

        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        self.model.save_pretrained(path / "model")
        self.tokenizer.save_pretrained(path / "tokenizer")

        with open(path / "config.json", "w") as f:
            json.dump(self.config.model_dump(), f, indent=2)

    @classmethod
    def load(cls, path: Path | str) -> "LayoutGenerator":
        """Load model from disk."""
        from transformers import T5ForConditionalGeneration, T5Tokenizer

        path = Path(path)

        with open(path / "config.json", "r") as f:
            config_dict = json.load(f)
        config = LayoutGeneratorConfig(**config_dict)

        generator = cls(config)
        generator.model = T5ForConditionalGeneration.from_pretrained(path / "model")
        generator.tokenizer = T5Tokenizer.from_pretrained(path / "tokenizer")
        generator._initialized = True

        return generator
