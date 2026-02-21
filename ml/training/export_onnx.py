"""Export trained models to ONNX format for inference."""

import json
import logging
from pathlib import Path

import torch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_intent_classifier(
    model_path: str = "ml/models/intent_classifier/trained",
    output_path: str = "ml/models/intent_classifier/trained/model.onnx",
) -> None:
    """Export Intent Classifier to ONNX.

    Args:
        model_path: Path to trained model.
        output_path: Path for ONNX output.
    """
    from ml.models.intent_classifier.model import IntentClassifier

    model_path = Path(model_path)
    output_path = Path(output_path)

    logger.info(f"Loading Intent Classifier from {model_path}")

    # Load model
    model = IntentClassifier.load(model_path)
    model.eval()

    # Create dummy input (batch_size=1, sequence_length=128)
    dummy_input_ids = torch.ones(1, 128, dtype=torch.long)
    dummy_attention_mask = torch.ones(1, 128, dtype=torch.long)

    # Export to ONNX (use legacy export)
    logger.info(f"Exporting to {output_path}")

    # The model's forward method takes (input_ids, attention_mask)
    torch.onnx.export(
        model,
        (dummy_input_ids, dummy_attention_mask),
        str(output_path),
        input_names=["input_ids", "attention_mask"],
        output_names=["logits"],
        dynamic_axes={
            "input_ids": {0: "batch_size", 1: "sequence"},
            "attention_mask": {0: "batch_size", 1: "sequence"},
            "logits": {0: "batch_size"},
        },
        opset_version=14,
        do_constant_folding=True,
        dynamo=False,  # Use legacy export
    )

    logger.info("Intent Classifier exported successfully!")


def export_style_recommender(
    model_path: str = "ml/models/style_recommender/trained",
    output_path: str = "ml/models/style_recommender/trained/model.onnx",
) -> None:
    """Export Style Recommender to ONNX.

    Args:
        model_path: Path to trained model.
        output_path: Path for ONNX output.
    """
    from ml.models.style_recommender.model import StyleRecommender

    model_path = Path(model_path)
    output_path = Path(output_path)

    logger.info(f"Loading Style Recommender from {model_path}")

    # Load model
    model = StyleRecommender.load(model_path)
    model.eval()

    # Create dummy input
    dummy_input = torch.zeros(1, model.config.input_dim)

    # Wrap model to return tuple instead of dict
    class ONNXWrapper(torch.nn.Module):
        def __init__(self, model):
            super().__init__()
            self.model = model

        def forward(self, x):
            outputs = self.model(x)
            return (
                outputs["palette"],
                outputs["shadow"],
                outputs["glow"],
                outputs["corner"],
                outputs["font"],
            )

    wrapper = ONNXWrapper(model)

    # Export to ONNX (use legacy export)
    logger.info(f"Exporting to {output_path}")

    torch.onnx.export(
        wrapper,
        dummy_input,
        str(output_path),
        input_names=["features"],
        output_names=["palette", "shadow", "glow", "corner", "font"],
        dynamic_axes={
            "features": {0: "batch_size"},
            "palette": {0: "batch_size"},
            "shadow": {0: "batch_size"},
            "glow": {0: "batch_size"},
            "corner": {0: "batch_size"},
            "font": {0: "batch_size"},
        },
        opset_version=14,
        do_constant_folding=True,
        dynamo=False,  # Use legacy export
    )

    logger.info("Style Recommender exported successfully!")


def verify_onnx(onnx_path: str) -> bool:
    """Verify ONNX model is valid.

    Args:
        onnx_path: Path to ONNX model.

    Returns:
        True if valid.
    """
    try:
        import onnx
        model = onnx.load(onnx_path)
        onnx.checker.check_model(model)
        logger.info(f"ONNX model verified: {onnx_path}")
        return True
    except ImportError:
        logger.warning("onnx package not installed, skipping verification")
        return True
    except Exception as e:
        logger.error(f"ONNX verification failed: {e}")
        return False


def export_all(
    models_dir: str = "ml/models",
) -> dict[str, bool]:
    """Export all trained models to ONNX.

    Args:
        models_dir: Base directory for models.

    Returns:
        Dict of model name -> success status.
    """
    models_dir = Path(models_dir)
    results = {}

    # Export Intent Classifier
    intent_path = models_dir / "intent_classifier/trained"
    if (intent_path / "model.pt").exists():
        try:
            export_intent_classifier(
                model_path=str(intent_path),
                output_path=str(intent_path / "model.onnx"),
            )
            results["intent_classifier"] = verify_onnx(str(intent_path / "model.onnx"))
        except Exception as e:
            logger.error(f"Failed to export Intent Classifier: {e}")
            results["intent_classifier"] = False
    else:
        logger.warning("Intent Classifier not found, skipping")
        results["intent_classifier"] = False

    # Export Style Recommender
    style_path = models_dir / "style_recommender/trained"
    if (style_path / "model.pt").exists():
        try:
            export_style_recommender(
                model_path=str(style_path),
                output_path=str(style_path / "model.onnx"),
            )
            results["style_recommender"] = verify_onnx(str(style_path / "model.onnx"))
        except Exception as e:
            logger.error(f"Failed to export Style Recommender: {e}")
            results["style_recommender"] = False
    else:
        logger.warning("Style Recommender not found, skipping")
        results["style_recommender"] = False

    # Layout Generator would need GPU-trained model
    layout_path = models_dir / "layout_generator/trained"
    if (layout_path / "model.pt").exists():
        logger.info("Layout Generator found but T5 export requires special handling")
        results["layout_generator"] = False
    else:
        logger.warning("Layout Generator not trained yet")
        results["layout_generator"] = False

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Export models to ONNX")
    parser.add_argument(
        "--model",
        type=str,
        choices=["intent_classifier", "style_recommender", "all"],
        default="all",
        help="Which model to export",
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default="ml/models",
        help="Base directory for models",
    )

    args = parser.parse_args()

    if args.model == "all":
        results = export_all(args.models_dir)
        logger.info(f"Export results: {results}")
    elif args.model == "intent_classifier":
        export_intent_classifier()
    elif args.model == "style_recommender":
        export_style_recommender()
