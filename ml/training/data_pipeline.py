"""Data pipeline for preparing training datasets."""

import json
import random
from pathlib import Path
from typing import Any

from ml.config import get_ml_settings
from ml.training.data_generator import SyntheticDataGenerator, TrainingExample


class DataPipeline:
    """Pipeline for preparing and augmenting training data."""

    def __init__(self, output_dir: Path | str = "ml/data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.settings = get_ml_settings()
        self.generator = SyntheticDataGenerator()

    def generate_intent_classifier_data(
        self,
        samples_per_archetype: int = 200,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
    ) -> dict[str, Path]:
        """Generate training data for intent classifier.

        Args:
            samples_per_archetype: Samples per archetype class.
            train_ratio: Training set ratio.
            val_ratio: Validation set ratio.

        Returns:
            Dict with paths to train, val, test files.
        """
        # Generate examples
        examples = self.generator.generate_dataset(
            samples_per_archetype=samples_per_archetype,
        )

        # Augment with variations
        augmented = self._augment_prompts(examples)

        # Split into train/val/test
        random.shuffle(augmented)
        n = len(augmented)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        train_data = augmented[:train_end]
        val_data = augmented[train_end:val_end]
        test_data = augmented[val_end:]

        # Save datasets
        paths = {
            "train": self.output_dir / "prompts" / "train.jsonl",
            "val": self.output_dir / "prompts" / "val.jsonl",
            "test": self.output_dir / "prompts" / "test.jsonl",
        }

        for split, data in [("train", train_data), ("val", val_data), ("test", test_data)]:
            self.generator.save_dataset(data, paths[split])

        # Save label mapping
        label_map = {
            archetype: i
            for i, archetype in enumerate(self.settings.intent_classifier.archetypes)
        }
        with open(self.output_dir / "prompts" / "label_map.json", "w") as f:
            json.dump(label_map, f, indent=2)

        return paths

    def _augment_prompts(self, examples: list[TrainingExample]) -> list[TrainingExample]:
        """Augment prompts with variations.

        Args:
            examples: Original examples.

        Returns:
            Augmented list (including originals).
        """
        augmented = list(examples)

        for example in examples:
            # Add lowercase variation
            augmented.append(TrainingExample(
                prompt=example.prompt.lower(),
                archetype=example.archetype,
                parameters=example.parameters,
            ))

            # Add question form
            if not example.prompt.startswith(("Can", "Could", "How", "What")):
                question_forms = [
                    f"Can you create {example.prompt.lower()}?",
                    f"How do I make {example.prompt.lower()}?",
                    f"I want {example.prompt.lower()}",
                ]
                augmented.append(TrainingExample(
                    prompt=random.choice(question_forms),
                    archetype=example.archetype,
                    parameters=example.parameters,
                ))

            # Add with "please"
            if random.random() < 0.3:
                augmented.append(TrainingExample(
                    prompt=f"Please {example.prompt.lower()}",
                    archetype=example.archetype,
                    parameters=example.parameters,
                ))

        return augmented

    def generate_layout_data(
        self,
        samples_per_archetype: int = 100,
    ) -> dict[str, Path]:
        """Generate training data for layout generator.

        Creates intent-to-DSL pairs for training.

        Args:
            samples_per_archetype: Samples per archetype.

        Returns:
            Dict with paths to generated files.
        """
        # This requires template DSLs to be available
        # For now, create placeholder structure
        layout_dir = self.output_dir / "templates"
        layout_dir.mkdir(parents=True, exist_ok=True)

        # Generate intent specifications
        intents = []
        for archetype in self.settings.intent_classifier.archetypes[:-1]:  # Exclude "other"
            for _ in range(samples_per_archetype):
                intent = self._generate_intent_spec(archetype)
                intents.append(intent)

        # Save intents (DSL targets would come from parsed templates)
        with open(layout_dir / "intents.jsonl", "w") as f:
            for intent in intents:
                f.write(json.dumps(intent) + "\n")

        return {"intents": layout_dir / "intents.jsonl"}

    def _generate_intent_spec(self, archetype: str) -> dict[str, Any]:
        """Generate an intent specification.

        Args:
            archetype: Target archetype.

        Returns:
            Intent specification dict.
        """
        # Base intent structure
        intent = {
            "archetype": archetype,
            "item_count": random.randint(3, 8),
            "style_hints": [],
            "content_hints": [],
        }

        # Add archetype-specific parameters
        if archetype == "funnel":
            intent["taper_ratio"] = random.uniform(0.6, 0.9)
            intent["orientation"] = "vertical"

        elif archetype == "pyramid":
            intent["orientation"] = "vertical"
            intent["inverted"] = random.random() < 0.2

        elif archetype == "timeline":
            intent["orientation"] = random.choice(["horizontal", "vertical"])
            intent["node_shape"] = random.choice(["circle", "diamond", "square"])

        elif archetype == "process":
            intent["connector_style"] = random.choice(["arrow", "line", "chevron"])
            intent["show_numbers"] = random.random() < 0.7

        elif archetype == "cycle":
            intent["item_count"] = random.randint(3, 6)
            intent["rotation_offset"] = random.randint(0, 360)

        elif archetype == "hub_spoke":
            intent["spoke_count"] = random.randint(4, 8)
            intent["hub_size_ratio"] = random.uniform(0.2, 0.4)

        elif archetype == "matrix":
            intent["rows"] = random.randint(2, 4)
            intent["cols"] = random.randint(2, 4)
            intent["item_count"] = intent["rows"] * intent["cols"]

        return intent

    def generate_style_data(
        self,
        samples: int = 1000,
    ) -> dict[str, Path]:
        """Generate training data for style recommender.

        Args:
            samples: Total number of samples.

        Returns:
            Dict with path to generated file.
        """
        style_dir = self.output_dir / "styles"
        style_dir.mkdir(parents=True, exist_ok=True)

        style_examples = []
        for _ in range(samples):
            example = self._generate_style_example()
            style_examples.append(example)

        with open(style_dir / "style_data.jsonl", "w") as f:
            for ex in style_examples:
                f.write(json.dumps(ex) + "\n")

        return {"styles": style_dir / "style_data.jsonl"}

    def _generate_style_example(self) -> dict[str, Any]:
        """Generate a style training example.

        Returns:
            Style example dict.
        """
        # Input: archetype + content features
        archetype = random.choice(self.settings.intent_classifier.archetypes[:-1])
        item_count = random.randint(3, 8)
        has_icons = random.random() < 0.5
        has_descriptions = random.random() < 0.6
        formality = random.choice(["casual", "professional", "corporate"])

        # Output: style recommendations
        color_palette = random.choice([
            ["#0D9488", "#14B8A6", "#2DD4BF"],  # Teal
            ["#3B82F6", "#60A5FA", "#93C5FD"],  # Blue
            ["#8B5CF6", "#A78BFA", "#C4B5FD"],  # Purple
            ["#F59E0B", "#FBBF24", "#FCD34D"],  # Amber
            ["#10B981", "#34D399", "#6EE7B7"],  # Emerald
        ])

        shadow = random.choice(["none", "soft", "hard"])
        glow = random.choice(["none", "subtle", "strong"])
        corner_radius = random.choice(["sharp", "rounded", "pill"])

        return {
            "input": {
                "archetype": archetype,
                "item_count": item_count,
                "has_icons": has_icons,
                "has_descriptions": has_descriptions,
                "formality": formality,
            },
            "output": {
                "color_palette": color_palette,
                "shadow": shadow,
                "glow": glow,
                "corner_radius": corner_radius,
            },
        }

    def prepare_all(
        self,
        intent_samples: int = 200,
        layout_samples: int = 100,
        style_samples: int = 1000,
    ) -> dict[str, dict[str, Path]]:
        """Prepare all training datasets.

        Args:
            intent_samples: Samples per archetype for intent classifier.
            layout_samples: Samples per archetype for layout generator.
            style_samples: Total samples for style recommender.

        Returns:
            Dict with all generated file paths.
        """
        return {
            "intent_classifier": self.generate_intent_classifier_data(intent_samples),
            "layout_generator": self.generate_layout_data(layout_samples),
            "style_recommender": self.generate_style_data(style_samples),
        }
