"""Train the Layout Generator (T5) model."""

import json
import logging
import random
from pathlib import Path

import torch
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from transformers import T5ForConditionalGeneration, T5Tokenizer, get_linear_schedule_with_warmup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_jsonl(path: Path) -> list[dict]:
    """Load data from JSONL file."""
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


class LayoutDataset(Dataset):
    """Dataset for layout generation training."""

    def __init__(
        self,
        data: list[dict],
        tokenizer: T5Tokenizer,
        max_input_length: int = 128,
        max_output_length: int = 512,
    ):
        self.data = data
        self.tokenizer = tokenizer
        self.max_input_length = max_input_length
        self.max_output_length = max_output_length

    def __len__(self) -> int:
        return len(self.data)

    def format_input(self, intent: dict) -> str:
        """Format intent as input string."""
        parts = [f"generate {intent.get('archetype', 'diagram')} layout:"]

        if "item_count" in intent:
            parts.append(f"items={intent['item_count']}")

        if "orientation" in intent:
            parts.append(f"orientation={intent['orientation']}")

        # Add archetype-specific params
        for key, value in intent.items():
            if key not in ["archetype", "item_count", "orientation", "style_hints", "content_hints", "dsl"]:
                if isinstance(value, float):
                    parts.append(f"{key}={value:.2f}")
                else:
                    parts.append(f"{key}={value}")

        return " ".join(parts)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        item = self.data[idx]

        # Input: intent specification
        input_text = self.format_input(item)

        # Output: DSL JSON (use provided or generate template)
        if "dsl" in item:
            output_text = json.dumps(item["dsl"], separators=(",", ":"))
        else:
            output_text = self._generate_template_dsl(item)

        # Tokenize input
        input_encoding = self.tokenizer(
            input_text,
            max_length=self.max_input_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        # Tokenize output
        output_encoding = self.tokenizer(
            output_text,
            max_length=self.max_output_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        labels = output_encoding["input_ids"].squeeze(0)
        # Replace padding token id with -100 so it's ignored in loss
        labels[labels == self.tokenizer.pad_token_id] = -100

        return {
            "input_ids": input_encoding["input_ids"].squeeze(0),
            "attention_mask": input_encoding["attention_mask"].squeeze(0),
            "labels": labels,
        }

    def _generate_template_dsl(self, intent: dict) -> str:
        """Generate template DSL for an intent."""
        import math

        archetype = intent.get("archetype", "process")
        item_count = intent.get("item_count", 4)

        canvas_width = 12192000
        canvas_height = 6858000
        margin = canvas_width // 10

        shapes = []

        if archetype == "funnel":
            taper_ratio = intent.get("taper_ratio", 0.7)
            usable_width = canvas_width - 2 * margin
            layer_height = (canvas_height - 2 * margin) // item_count

            for i in range(item_count):
                width_ratio = 1.0 - (i * (1 - taper_ratio) / item_count)
                layer_width = int(usable_width * width_ratio)
                x = margin + (usable_width - layer_width) // 2
                y = margin + i * layer_height

                shapes.append({
                    "id": f"layer_{i}",
                    "type": "trapezoid",
                    "x": x, "y": y,
                    "w": layer_width, "h": int(layer_height * 0.9)
                })

        elif archetype == "pyramid":
            usable_width = canvas_width - 2 * margin
            tier_height = (canvas_height - 2 * margin) // item_count

            for i in range(item_count):
                width_ratio = 0.3 + (i * 0.7 / item_count)
                tier_width = int(usable_width * width_ratio)
                x = margin + (usable_width - tier_width) // 2
                y = margin + i * tier_height

                shapes.append({
                    "id": f"tier_{i}",
                    "type": "trapezoid",
                    "x": x, "y": y,
                    "w": tier_width, "h": int(tier_height * 0.9)
                })

        elif archetype == "timeline":
            usable_width = canvas_width - 2 * margin
            node_spacing = usable_width // item_count
            node_size = min(node_spacing // 2, canvas_height // 4)
            center_y = canvas_height // 2

            for i in range(item_count):
                x = margin + i * node_spacing + (node_spacing - node_size) // 2
                y = center_y - node_size // 2

                shapes.append({
                    "id": f"node_{i}",
                    "type": "ellipse",
                    "x": x, "y": y,
                    "w": node_size, "h": node_size
                })

        elif archetype == "cycle":
            center_x = canvas_width // 2
            center_y = canvas_height // 2
            radius = min(canvas_width, canvas_height) // 3
            node_size = radius // 2

            for i in range(item_count):
                angle = (2 * math.pi * i / item_count) - math.pi / 2
                x = int(center_x + radius * math.cos(angle) - node_size // 2)
                y = int(center_y + radius * math.sin(angle) - node_size // 2)

                shapes.append({
                    "id": f"node_{i}",
                    "type": "ellipse",
                    "x": x, "y": y,
                    "w": node_size, "h": node_size
                })

        elif archetype == "hub_spoke":
            center_x = canvas_width // 2
            center_y = canvas_height // 2
            hub_size = canvas_height // 4
            radius = min(canvas_width, canvas_height) // 3
            spoke_size = hub_size // 2

            # Hub
            shapes.append({
                "id": "hub",
                "type": "ellipse",
                "x": center_x - hub_size // 2,
                "y": center_y - hub_size // 2,
                "w": hub_size, "h": hub_size
            })

            # Spokes
            for i in range(item_count - 1):
                angle = (2 * math.pi * i / (item_count - 1)) - math.pi / 2
                x = int(center_x + radius * math.cos(angle) - spoke_size // 2)
                y = int(center_y + radius * math.sin(angle) - spoke_size // 2)

                shapes.append({
                    "id": f"spoke_{i}",
                    "type": "ellipse",
                    "x": x, "y": y,
                    "w": spoke_size, "h": spoke_size
                })

        elif archetype == "matrix":
            cols = int(math.ceil(math.sqrt(item_count)))
            rows = int(math.ceil(item_count / cols))
            cell_width = (canvas_width - 2 * margin) // cols
            cell_height = (canvas_height - 2 * margin) // rows

            for i in range(item_count):
                row = i // cols
                col = i % cols
                x = margin + col * cell_width + cell_width // 10
                y = margin + row * cell_height + cell_height // 10

                shapes.append({
                    "id": f"cell_{i}",
                    "type": "rect",
                    "x": x, "y": y,
                    "w": int(cell_width * 0.8),
                    "h": int(cell_height * 0.8)
                })

        else:  # process/default
            usable_width = canvas_width - 2 * margin
            step_width = (usable_width - (item_count - 1) * margin // 4) // item_count
            step_height = canvas_height // 3
            center_y = (canvas_height - step_height) // 2

            for i in range(item_count):
                x = margin + i * (step_width + margin // 4)

                shapes.append({
                    "id": f"step_{i}",
                    "type": "rect",
                    "x": x, "y": center_y,
                    "w": step_width, "h": step_height
                })

        dsl = {
            "canvas": {"w": canvas_width, "h": canvas_height},
            "shapes": shapes,
            "archetype": archetype
        }

        return json.dumps(dsl, separators=(",", ":"))


def train_layout_generator(
    data_path: str = "ml/data/templates/intents.jsonl",
    output_dir: str = "ml/models/layout_generator/trained",
    model_name: str = "t5-small",
    epochs: int = 10,
    batch_size: int = 8,
    learning_rate: float = 5e-5,
    warmup_steps: int = 100,
    max_input_length: int = 128,
    max_output_length: int = 512,
) -> dict:
    """Train the Layout Generator model.

    Args:
        data_path: Path to intents.jsonl file.
        output_dir: Directory to save trained model.
        model_name: Base T5 model name.
        epochs: Number of training epochs.
        batch_size: Training batch size.
        learning_rate: Learning rate.
        warmup_steps: Warmup steps for scheduler.
        max_input_length: Max input sequence length.
        max_output_length: Max output sequence length.

    Returns:
        Training history.
    """
    data_path = Path(data_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    if device.type == "cuda":
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # Load tokenizer and model
    logger.info(f"Loading model: {model_name}")
    tokenizer = T5Tokenizer.from_pretrained(model_name)
    model = T5ForConditionalGeneration.from_pretrained(model_name)
    model.to(device)

    # Load data
    logger.info(f"Loading data from {data_path}")
    all_data = load_jsonl(data_path)
    logger.info(f"Total samples: {len(all_data)}")

    # Split data
    random.seed(42)
    random.shuffle(all_data)
    split_idx = int(len(all_data) * 0.9)
    train_data = all_data[:split_idx]
    val_data = all_data[split_idx:]
    logger.info(f"Train: {len(train_data)}, Val: {len(val_data)}")

    # Create datasets
    train_dataset = LayoutDataset(
        train_data, tokenizer,
        max_input_length=max_input_length,
        max_output_length=max_output_length
    )
    val_dataset = LayoutDataset(
        val_data, tokenizer,
        max_input_length=max_input_length,
        max_output_length=max_output_length
    )

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)

    # Optimizer and scheduler
    optimizer = AdamW(model.parameters(), lr=learning_rate)
    total_steps = len(train_loader) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps
    )

    # Training loop
    history = {"train_loss": [], "val_loss": []}
    best_val_loss = float("inf")

    logger.info(f"Starting training: {epochs} epochs, {len(train_loader)} batches/epoch")

    for epoch in range(epochs):
        # Training
        model.train()
        epoch_loss = 0.0

        for batch_idx, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            optimizer.zero_grad()

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )

            loss = outputs.loss
            loss.backward()
            optimizer.step()
            scheduler.step()

            epoch_loss += loss.item()

            if (batch_idx + 1) % 50 == 0:
                logger.info(f"Epoch {epoch+1}, Batch {batch_idx+1}/{len(train_loader)}, Loss: {loss.item():.4f}")

        avg_train_loss = epoch_loss / len(train_loader)
        history["train_loss"].append(avg_train_loss)

        # Validation
        model.eval()
        val_loss = 0.0

        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels = batch["labels"].to(device)

                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )

                val_loss += outputs.loss.item()

        avg_val_loss = val_loss / len(val_loader)
        history["val_loss"].append(avg_val_loss)

        logger.info(f"Epoch {epoch+1}/{epochs}: train_loss={avg_train_loss:.4f}, val_loss={avg_val_loss:.4f}")

        # Save best model
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            logger.info(f"New best model! Saving to {output_dir}")
            model.save_pretrained(output_dir / "model")
            tokenizer.save_pretrained(output_dir / "tokenizer")

    # Save final config
    config = {
        "model_name": model_name,
        "max_input_length": max_input_length,
        "max_output_length": max_output_length,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "best_val_loss": best_val_loss,
    }
    with open(output_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    # Save metrics
    with open(output_dir / "metrics.json", "w") as f:
        json.dump({
            "train_loss": history["train_loss"][-1],
            "val_loss": history["val_loss"][-1],
            "best_val_loss": best_val_loss,
        }, f, indent=2)

    logger.info("Training complete!")
    logger.info(f"Best validation loss: {best_val_loss:.4f}")
    logger.info(f"Model saved to: {output_dir}")

    return history


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train Layout Generator (T5)")
    parser.add_argument("--model", type=str, default="t5-small", help="T5 model name")
    parser.add_argument("--epochs", type=int, default=10, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size")
    parser.add_argument("--lr", type=float, default=5e-5, help="Learning rate")
    parser.add_argument("--data-path", type=str, default="ml/data/templates/intents.jsonl")
    parser.add_argument("--output-dir", type=str, default="ml/models/layout_generator/trained")

    args = parser.parse_args()

    train_layout_generator(
        data_path=args.data_path,
        output_dir=args.output_dir,
        model_name=args.model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
    )
