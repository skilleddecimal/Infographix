"""Intent Classifier model - classifies user prompts into archetypes."""

from ml.models.intent_classifier.model import IntentClassifier
from ml.models.intent_classifier.inference import IntentClassifierInference

__all__ = [
    "IntentClassifier",
    "IntentClassifierInference",
]
