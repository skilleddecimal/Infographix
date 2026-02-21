"""Train the Intent Classifier model."""

import json
import logging
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


def train_intent_classifier(
    data_dir: str = "ml/data/prompts",
    output_dir: str = "ml/models/intent_classifier/trained",
    epochs: int = 3,
    batch_size: int = 16,
) -> dict:
    """Train the intent classifier model.

    Args:
        data_dir: Directory containing train/val/test.jsonl files.
        output_dir: Directory to save trained model.
        epochs: Number of training epochs.
        batch_size: Training batch size.

    Returns:
        Training history.
    """
    from ml.models.intent_classifier.model import IntentClassifier, IntentClassifierTrainer
    from ml.config import IntentClassifierConfig

    data_dir = Path(data_dir)
    output_dir = Path(output_dir)

    # Load data
    logger.info("Loading training data...")
    train_data = load_jsonl(data_dir / "train.jsonl")
    val_data = load_jsonl(data_dir / "val.jsonl")
    test_data = load_jsonl(data_dir / "test.jsonl")

    logger.info(f"Train: {len(train_data)}, Val: {len(val_data)}, Test: {len(test_data)}")

    # Load label mapping
    with open(data_dir / "label_map.json") as f:
        label_map = json.load(f)

    archetypes = [None] * len(label_map)
    for name, idx in label_map.items():
        archetypes[idx] = name

    logger.info(f"Archetypes: {archetypes}")

    # Create config
    config = IntentClassifierConfig(
        model_name="distilbert-base-uncased",
        num_labels=len(archetypes),
        archetypes=archetypes,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=2e-5,
        max_length=128,
    )

    # Create model
    logger.info("Initializing model...")
    model = IntentClassifier(config)

    # Create trainer
    trainer = IntentClassifierTrainer(
        model=model,
        train_data=train_data,
        val_data=val_data,
        config=config,
    )

    # Train
    logger.info("Starting training...")
    history = trainer.train(output_dir=output_dir)

    # Evaluate on test set
    logger.info("Evaluating on test set...")
    test_loss, test_acc = trainer._evaluate(test_data)
    logger.info(f"Test Results: loss={test_loss:.4f}, accuracy={test_acc:.4f}")

    # Save final metrics
    metrics = {
        "train_loss": history["train_loss"][-1],
        "train_acc": history["train_acc"][-1],
        "val_loss": history["val_loss"][-1] if history["val_loss"] else None,
        "val_acc": history["val_acc"][-1] if history["val_acc"] else None,
        "test_loss": test_loss,
        "test_acc": test_acc,
    }

    with open(output_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info(f"Model saved to {output_dir}")
    logger.info(f"Final metrics: {metrics}")

    return history


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train Intent Classifier")
    parser.add_argument("--epochs", type=int, default=3, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--data-dir", type=str, default="ml/data/prompts", help="Data directory")
    parser.add_argument("--output-dir", type=str, default="ml/models/intent_classifier/trained", help="Output directory")

    args = parser.parse_args()

    train_intent_classifier(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
    )
