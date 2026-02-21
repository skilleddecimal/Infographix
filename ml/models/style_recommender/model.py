"""Style Recommender model using MLP."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn

from ml.config import StyleRecommenderConfig, get_ml_settings


@dataclass
class StyleResult:
    """Result of style recommendation."""

    color_palette: list[str]
    shadow: str
    glow: str
    corner_radius: str
    font_family: str
    confidence: float


class StyleRecommender(nn.Module):
    """MLP-based style recommender.

    Recommends visual styles based on archetype and content features.
    This is a simple model that can be trained on CPU.
    """

    # Predefined style palettes
    PALETTES = {
        "teal": ["#0D9488", "#14B8A6", "#2DD4BF", "#5EEAD4", "#99F6E4", "#CCFBF1"],
        "blue": ["#1D4ED8", "#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE", "#DBEAFE"],
        "purple": ["#7C3AED", "#8B5CF6", "#A78BFA", "#C4B5FD", "#DDD6FE", "#EDE9FE"],
        "amber": ["#D97706", "#F59E0B", "#FBBF24", "#FCD34D", "#FDE68A", "#FEF3C7"],
        "emerald": ["#059669", "#10B981", "#34D399", "#6EE7B7", "#A7F3D0", "#D1FAE5"],
        "rose": ["#E11D48", "#F43F5E", "#FB7185", "#FDA4AF", "#FECDD3", "#FFE4E6"],
        "slate": ["#334155", "#475569", "#64748B", "#94A3B8", "#CBD5E1", "#E2E8F0"],
    }

    FONT_FAMILIES = ["Inter", "Roboto", "Open Sans", "Montserrat", "Lato", "Poppins"]

    def __init__(self, config: StyleRecommenderConfig | None = None):
        """Initialize the model.

        Args:
            config: Model configuration.
        """
        super().__init__()
        self.config = config or get_ml_settings().style_recommender

        # Build MLP layers
        layers = []
        input_dim = self.config.input_dim

        for hidden_dim in self.config.hidden_dims:
            layers.append(nn.Linear(input_dim, hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(self.config.dropout))
            input_dim = hidden_dim

        layers.append(nn.Linear(input_dim, self.config.output_dim))

        self.mlp = nn.Sequential(*layers)

        # Output heads
        self.palette_head = nn.Linear(self.config.output_dim, len(self.PALETTES))
        self.shadow_head = nn.Linear(self.config.output_dim, 3)  # none, soft, hard
        self.glow_head = nn.Linear(self.config.output_dim, 3)  # none, subtle, strong
        self.corner_head = nn.Linear(self.config.output_dim, 3)  # sharp, rounded, pill
        self.font_head = nn.Linear(self.config.output_dim, len(self.FONT_FAMILIES))

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        """Forward pass.

        Args:
            x: Input features.

        Returns:
            Dict of output logits for each style aspect.
        """
        features = self.mlp(x)

        return {
            "palette": self.palette_head(features),
            "shadow": self.shadow_head(features),
            "glow": self.glow_head(features),
            "corner": self.corner_head(features),
            "font": self.font_head(features),
        }

    def encode_input(self, features: dict[str, Any]) -> torch.Tensor:
        """Encode input features to tensor.

        Args:
            features: Input feature dict.

        Returns:
            Encoded tensor.
        """
        # Create feature vector
        vec = torch.zeros(self.config.input_dim)

        # Encode archetype (one-hot, positions 0-13)
        archetypes = get_ml_settings().intent_classifier.archetypes
        archetype = features.get("archetype", "other")
        if archetype in archetypes:
            vec[archetypes.index(archetype)] = 1.0

        # Encode item count (normalized, position 14)
        item_count = features.get("item_count", 4)
        vec[14] = min(item_count / 10.0, 1.0)

        # Encode boolean features (positions 15-20)
        vec[15] = 1.0 if features.get("has_icons", False) else 0.0
        vec[16] = 1.0 if features.get("has_descriptions", False) else 0.0
        vec[17] = 1.0 if features.get("has_images", False) else 0.0

        # Encode formality (positions 21-23)
        formality = features.get("formality", "professional")
        if formality == "casual":
            vec[21] = 1.0
        elif formality == "professional":
            vec[22] = 1.0
        elif formality == "corporate":
            vec[23] = 1.0

        return vec.unsqueeze(0)  # Add batch dimension

    def recommend(self, features: dict[str, Any]) -> StyleResult:
        """Recommend styles for given features.

        Args:
            features: Input features dict.

        Returns:
            Style recommendation result.
        """
        self.eval()

        x = self.encode_input(features)

        with torch.no_grad():
            outputs = self.forward(x)

        # Get predictions
        palette_names = list(self.PALETTES.keys())
        shadow_options = ["none", "soft", "hard"]
        glow_options = ["none", "subtle", "strong"]
        corner_options = ["sharp", "rounded", "pill"]

        palette_idx = outputs["palette"].argmax(dim=-1).item()
        shadow_idx = outputs["shadow"].argmax(dim=-1).item()
        glow_idx = outputs["glow"].argmax(dim=-1).item()
        corner_idx = outputs["corner"].argmax(dim=-1).item()
        font_idx = outputs["font"].argmax(dim=-1).item()

        # Get confidence (average of max probabilities)
        confidences = [
            torch.softmax(outputs["palette"], dim=-1).max().item(),
            torch.softmax(outputs["shadow"], dim=-1).max().item(),
            torch.softmax(outputs["glow"], dim=-1).max().item(),
            torch.softmax(outputs["corner"], dim=-1).max().item(),
            torch.softmax(outputs["font"], dim=-1).max().item(),
        ]
        avg_confidence = sum(confidences) / len(confidences)

        return StyleResult(
            color_palette=self.PALETTES[palette_names[palette_idx]],
            shadow=shadow_options[shadow_idx],
            glow=glow_options[glow_idx],
            corner_radius=corner_options[corner_idx],
            font_family=self.FONT_FAMILIES[font_idx],
            confidence=avg_confidence,
        )

    def save(self, path: Path | str) -> None:
        """Save model to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        torch.save(self.state_dict(), path / "model.pt")

        with open(path / "config.json", "w") as f:
            json.dump(self.config.model_dump(), f, indent=2)

    @classmethod
    def load(cls, path: Path | str) -> "StyleRecommender":
        """Load model from disk."""
        path = Path(path)

        with open(path / "config.json", "r") as f:
            config_dict = json.load(f)
        config = StyleRecommenderConfig(**config_dict)

        model = cls(config)
        state_dict = torch.load(path / "model.pt", map_location="cpu")
        model.load_state_dict(state_dict)

        return model


class StyleRecommenderTrainer:
    """Trainer for the Style Recommender model."""

    def __init__(
        self,
        model: StyleRecommender,
        train_data: list[dict],
        val_data: list[dict] | None = None,
    ):
        """Initialize trainer.

        Args:
            model: Model to train.
            train_data: Training data.
            val_data: Validation data.
        """
        self.model = model
        self.train_data = train_data
        self.val_data = val_data or []

    def train(self, output_dir: Path | str | None = None) -> dict[str, list[float]]:
        """Train the model.

        Args:
            output_dir: Directory to save checkpoints.

        Returns:
            Training history.
        """
        from torch.utils.data import DataLoader
        from torch.optim import Adam

        # Create datasets
        train_dataset = StyleDataset(self.train_data, self.model)
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.model.config.batch_size,
            shuffle=True,
        )

        # Optimizer
        optimizer = Adam(
            self.model.parameters(),
            lr=self.model.config.learning_rate,
        )

        # Loss function
        criterion = nn.CrossEntropyLoss()

        # Training loop
        history = {"train_loss": []}

        for epoch in range(self.model.config.epochs):
            self.model.train()
            epoch_loss = 0.0

            for batch in train_loader:
                optimizer.zero_grad()

                x = batch["input"]
                outputs = self.model(x)

                # Compute loss for each head
                loss = 0.0
                loss += criterion(outputs["palette"], batch["palette"])
                loss += criterion(outputs["shadow"], batch["shadow"])
                loss += criterion(outputs["glow"], batch["glow"])
                loss += criterion(outputs["corner"], batch["corner"])
                loss += criterion(outputs["font"], batch["font"])

                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()

            avg_loss = epoch_loss / len(train_loader)
            history["train_loss"].append(avg_loss)

            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch + 1}: loss={avg_loss:.4f}")

        # Save model
        if output_dir:
            self.model.save(output_dir)

        return history


class StyleDataset(torch.utils.data.Dataset):
    """Dataset for style recommendation training."""

    PALETTE_MAP = {name: i for i, name in enumerate(StyleRecommender.PALETTES.keys())}
    SHADOW_MAP = {"none": 0, "soft": 1, "hard": 2}
    GLOW_MAP = {"none": 0, "subtle": 1, "strong": 2}
    CORNER_MAP = {"sharp": 0, "rounded": 1, "pill": 2}
    FONT_MAP = {name: i for i, name in enumerate(StyleRecommender.FONT_FAMILIES)}

    def __init__(self, data: list[dict], model: StyleRecommender):
        self.data = data
        self.model = model

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        item = self.data[idx]
        input_features = item["input"]
        output = item["output"]

        x = self.model.encode_input(input_features).squeeze(0)

        # Find matching palette
        palette_name = self._find_palette(output.get("color_palette", []))

        return {
            "input": x,
            "palette": torch.tensor(self.PALETTE_MAP.get(palette_name, 0)),
            "shadow": torch.tensor(self.SHADOW_MAP.get(output.get("shadow", "none"), 0)),
            "glow": torch.tensor(self.GLOW_MAP.get(output.get("glow", "none"), 0)),
            "corner": torch.tensor(self.CORNER_MAP.get(output.get("corner_radius", "rounded"), 1)),
            "font": torch.tensor(self.FONT_MAP.get(output.get("font_family", "Inter"), 0)),
        }

    def _find_palette(self, colors: list[str]) -> str:
        """Find the closest matching palette."""
        if not colors:
            return "teal"

        first_color = colors[0].lower()

        for name, palette in StyleRecommender.PALETTES.items():
            if first_color in [c.lower() for c in palette]:
                return name

        return "teal"
