"""Train the Style Recommender model."""

import json
import logging
import random
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_jsonl(path: Path) -> list[dict]:
    """Load data from JSONL file."""
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            data.append(json.loads(line))
    return data


def add_missing_fields(data: list[dict]) -> list[dict]:
    """Add missing font_family to output if not present."""
    fonts = ["Inter", "Roboto", "Open Sans", "Montserrat", "Lato", "Poppins"]

    for item in data:
        if "font_family" not in item["output"]:
            # Assign based on formality
            formality = item["input"].get("formality", "professional")
            if formality == "corporate":
                item["output"]["font_family"] = random.choice(["Inter", "Roboto"])
            elif formality == "casual":
                item["output"]["font_family"] = random.choice(["Poppins", "Montserrat"])
            else:  # professional
                item["output"]["font_family"] = random.choice(["Open Sans", "Lato", "Inter"])

    return data


def train_style_recommender(
    data_path: str = "ml/data/styles/style_data.jsonl",
    output_dir: str = "ml/models/style_recommender/trained",
    epochs: int = 100,
    batch_size: int = 32,
    learning_rate: float = 0.001,
) -> dict:
    """Train the style recommender model.

    Args:
        data_path: Path to style_data.jsonl file.
        output_dir: Directory to save trained model.
        epochs: Number of training epochs.
        batch_size: Training batch size.
        learning_rate: Learning rate.

    Returns:
        Training history.
    """
    from ml.models.style_recommender.model import StyleRecommender, StyleRecommenderTrainer
    from ml.config import StyleRecommenderConfig

    data_path = Path(data_path)
    output_dir = Path(output_dir)

    # Load data
    logger.info("Loading training data...")
    all_data = load_jsonl(data_path)

    # Add missing font_family fields
    random.seed(42)  # For reproducibility
    all_data = add_missing_fields(all_data)

    # Split into train/val (80/20)
    random.shuffle(all_data)
    split_idx = int(len(all_data) * 0.8)
    train_data = all_data[:split_idx]
    val_data = all_data[split_idx:]

    logger.info(f"Train: {len(train_data)}, Val: {len(val_data)}")

    # Create config
    config = StyleRecommenderConfig(
        input_dim=32,
        hidden_dims=[64, 32],
        output_dim=16,
        dropout=0.2,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
    )

    # Create model
    logger.info("Initializing model...")
    model = StyleRecommender(config)

    # Print model architecture
    total_params = sum(p.numel() for p in model.parameters())
    logger.info(f"Model parameters: {total_params:,}")

    # Create trainer
    trainer = StyleRecommenderTrainer(
        model=model,
        train_data=train_data,
        val_data=val_data,
    )

    # Train
    logger.info("Starting training...")
    logger.info(f"Epochs: {epochs}, Batch size: {batch_size}, LR: {learning_rate}")

    history = trainer.train(output_dir=output_dir)

    # Evaluate on validation set
    logger.info("Evaluating on validation set...")
    model.eval()

    correct = {"palette": 0, "shadow": 0, "glow": 0, "corner": 0, "font": 0}
    total = len(val_data)

    import torch
    from ml.models.style_recommender.model import StyleDataset

    for item in val_data:
        x = model.encode_input(item["input"])
        with torch.no_grad():
            outputs = model(x)

        # Get predictions
        palette_pred = outputs["palette"].argmax(dim=-1).item()
        shadow_pred = outputs["shadow"].argmax(dim=-1).item()
        glow_pred = outputs["glow"].argmax(dim=-1).item()
        corner_pred = outputs["corner"].argmax(dim=-1).item()
        font_pred = outputs["font"].argmax(dim=-1).item()

        # Get ground truth
        dataset = StyleDataset([item], model)
        gt = dataset[0]

        if palette_pred == gt["palette"].item():
            correct["palette"] += 1
        if shadow_pred == gt["shadow"].item():
            correct["shadow"] += 1
        if glow_pred == gt["glow"].item():
            correct["glow"] += 1
        if corner_pred == gt["corner"].item():
            correct["corner"] += 1
        if font_pred == gt["font"].item():
            correct["font"] += 1

    # Print accuracies
    logger.info("Validation Accuracies:")
    for key in correct:
        acc = correct[key] / total
        logger.info(f"  {key}: {acc:.4f}")

    avg_acc = sum(correct.values()) / (len(correct) * total)
    logger.info(f"  Average: {avg_acc:.4f}")

    # Save final metrics
    metrics = {
        "train_loss": history["train_loss"][-1] if history["train_loss"] else None,
        "val_accuracy": {k: v / total for k, v in correct.items()},
        "avg_accuracy": avg_acc,
    }

    with open(output_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info(f"Model saved to {output_dir}")
    logger.info("Training complete!")

    return history


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train Style Recommender")
    parser.add_argument("--epochs", type=int, default=100, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--data-path", type=str, default="ml/data/styles/style_data.jsonl", help="Data path")
    parser.add_argument("--output-dir", type=str, default="ml/models/style_recommender/trained", help="Output directory")

    args = parser.parse_args()

    train_style_recommender(
        data_path=args.data_path,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
    )
