"""Intent Classifier model using DistilBERT."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn

from ml.config import IntentClassifierConfig, get_ml_settings


@dataclass
class ClassificationResult:
    """Result of intent classification."""

    archetype: str
    confidence: float
    all_scores: dict[str, float]
    parameters: dict[str, Any] | None = None


class IntentClassifier(nn.Module):
    """DistilBERT-based intent classifier.

    Classifies user prompts into infographic archetype categories.
    """

    def __init__(self, config: IntentClassifierConfig | None = None):
        """Initialize the model.

        Args:
            config: Model configuration.
        """
        super().__init__()
        self.config = config or get_ml_settings().intent_classifier

        # These will be initialized when transformers is available
        self.encoder = None
        self.classifier = None
        self.tokenizer = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the model components.

        Lazy initialization to avoid import errors if transformers not installed.
        """
        if self._initialized:
            return

        try:
            from transformers import AutoModel, AutoTokenizer

            # Load pre-trained encoder
            self.encoder = AutoModel.from_pretrained(self.config.model_name)
            self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)

            # Classification head
            hidden_size = self.encoder.config.hidden_size
            self.classifier = nn.Sequential(
                nn.Dropout(self.config.dropout),
                nn.Linear(hidden_size, hidden_size // 2),
                nn.ReLU(),
                nn.Dropout(self.config.dropout),
                nn.Linear(hidden_size // 2, self.config.num_labels),
            )

            self._initialized = True

        except ImportError:
            raise ImportError(
                "transformers library required. Install with: pip install transformers"
            )

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        """Forward pass.

        Args:
            input_ids: Tokenized input IDs.
            attention_mask: Attention mask.

        Returns:
            Logits for each archetype class.
        """
        if not self._initialized:
            self.initialize()

        # Get encoder output
        outputs = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask,
        )

        # Use [CLS] token representation
        pooled = outputs.last_hidden_state[:, 0, :]

        # Classify
        logits = self.classifier(pooled)

        return logits

    def predict(self, prompt: str) -> ClassificationResult:
        """Predict archetype for a prompt.

        Args:
            prompt: User prompt text.

        Returns:
            Classification result with archetype and confidence.
        """
        if not self._initialized:
            self.initialize()

        self.eval()

        # Tokenize
        encoding = self.tokenizer(
            prompt,
            max_length=self.config.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        # Get device
        device = next(self.parameters()).device
        input_ids = encoding["input_ids"].to(device)
        attention_mask = encoding["attention_mask"].to(device)

        # Forward pass
        with torch.no_grad():
            logits = self.forward(input_ids, attention_mask)
            probs = torch.softmax(logits, dim=-1)

        # Get prediction
        confidence, pred_idx = probs.max(dim=-1)
        archetype = self.config.archetypes[pred_idx.item()]

        # All scores
        all_scores = {
            self.config.archetypes[i]: probs[0, i].item()
            for i in range(len(self.config.archetypes))
        }

        return ClassificationResult(
            archetype=archetype,
            confidence=confidence.item(),
            all_scores=all_scores,
        )

    def save(self, path: Path | str) -> None:
        """Save model to disk.

        Args:
            path: Directory to save model.
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        # Save model weights
        torch.save(self.state_dict(), path / "model.pt")

        # Save config
        import json
        with open(path / "config.json", "w") as f:
            json.dump(self.config.model_dump(), f, indent=2)

    @classmethod
    def load(cls, path: Path | str) -> "IntentClassifier":
        """Load model from disk.

        Args:
            path: Directory containing saved model.

        Returns:
            Loaded IntentClassifier.
        """
        import json

        path = Path(path)

        # Load config
        with open(path / "config.json", "r") as f:
            config_dict = json.load(f)
        config = IntentClassifierConfig(**config_dict)

        # Create model
        model = cls(config)
        model.initialize()

        # Load weights
        state_dict = torch.load(path / "model.pt", map_location="cpu")
        model.load_state_dict(state_dict)

        return model


class IntentClassifierTrainer:
    """Trainer for the Intent Classifier model."""

    def __init__(
        self,
        model: IntentClassifier,
        train_data: list[dict],
        val_data: list[dict] | None = None,
        config: IntentClassifierConfig | None = None,
    ):
        """Initialize trainer.

        Args:
            model: Model to train.
            train_data: Training data (list of {prompt, archetype}).
            val_data: Validation data.
            config: Training configuration.
        """
        self.model = model
        self.train_data = train_data
        self.val_data = val_data or []
        self.config = config or model.config

        # Initialize model if needed
        self.model.initialize()

        # Create label mapping
        self.label_to_idx = {
            label: i for i, label in enumerate(self.config.archetypes)
        }

    def train(self, output_dir: Path | str | None = None) -> dict[str, list[float]]:
        """Train the model.

        Args:
            output_dir: Directory to save checkpoints.

        Returns:
            Training history (loss, accuracy per epoch).
        """
        from torch.utils.data import DataLoader, Dataset
        from torch.optim import AdamW
        from torch.optim.lr_scheduler import LinearLR

        # Prepare dataset
        train_dataset = self._create_dataset(self.train_data)
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
        )

        # Optimizer
        optimizer = AdamW(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )

        # Scheduler
        total_steps = len(train_loader) * self.config.epochs
        scheduler = LinearLR(
            optimizer,
            start_factor=0.1,
            end_factor=1.0,
            total_iters=self.config.warmup_steps,
        )

        # Loss function
        criterion = nn.CrossEntropyLoss()

        # Training loop
        history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}

        for epoch in range(self.config.epochs):
            # Train
            self.model.train()
            epoch_loss = 0.0
            correct = 0
            total = 0

            for batch in train_loader:
                optimizer.zero_grad()

                input_ids = batch["input_ids"]
                attention_mask = batch["attention_mask"]
                labels = batch["labels"]

                logits = self.model(input_ids, attention_mask)
                loss = criterion(logits, labels)

                loss.backward()
                optimizer.step()
                scheduler.step()

                epoch_loss += loss.item()
                _, predicted = logits.max(dim=-1)
                correct += (predicted == labels).sum().item()
                total += labels.size(0)

            avg_loss = epoch_loss / len(train_loader)
            accuracy = correct / total
            history["train_loss"].append(avg_loss)
            history["train_acc"].append(accuracy)

            # Validate
            if self.val_data:
                val_loss, val_acc = self._evaluate(self.val_data)
                history["val_loss"].append(val_loss)
                history["val_acc"].append(val_acc)
                print(f"Epoch {epoch + 1}: loss={avg_loss:.4f}, acc={accuracy:.4f}, "
                      f"val_loss={val_loss:.4f}, val_acc={val_acc:.4f}")
            else:
                print(f"Epoch {epoch + 1}: loss={avg_loss:.4f}, acc={accuracy:.4f}")

        # Save final model
        if output_dir:
            self.model.save(output_dir)

        return history

    def _create_dataset(self, data: list[dict]) -> "IntentDataset":
        """Create a PyTorch dataset from data."""
        return IntentDataset(
            data=data,
            tokenizer=self.model.tokenizer,
            label_to_idx=self.label_to_idx,
            max_length=self.config.max_length,
        )

    def _evaluate(self, data: list[dict]) -> tuple[float, float]:
        """Evaluate model on data.

        Args:
            data: Evaluation data.

        Returns:
            Tuple of (loss, accuracy).
        """
        from torch.utils.data import DataLoader

        dataset = self._create_dataset(data)
        loader = DataLoader(dataset, batch_size=self.config.batch_size)

        criterion = nn.CrossEntropyLoss()

        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for batch in loader:
                input_ids = batch["input_ids"]
                attention_mask = batch["attention_mask"]
                labels = batch["labels"]

                logits = self.model(input_ids, attention_mask)
                loss = criterion(logits, labels)

                total_loss += loss.item()
                _, predicted = logits.max(dim=-1)
                correct += (predicted == labels).sum().item()
                total += labels.size(0)

        return total_loss / len(loader), correct / total


class IntentDataset(torch.utils.data.Dataset):
    """Dataset for intent classification."""

    def __init__(
        self,
        data: list[dict],
        tokenizer,
        label_to_idx: dict[str, int],
        max_length: int = 128,
    ):
        self.data = data
        self.tokenizer = tokenizer
        self.label_to_idx = label_to_idx
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        item = self.data[idx]

        encoding = self.tokenizer(
            item["prompt"],
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        label = self.label_to_idx.get(item["archetype"], len(self.label_to_idx) - 1)

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(label),
        }
