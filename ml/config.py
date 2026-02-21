"""ML configuration and hyperparameters."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelPaths(BaseModel):
    """Paths for model storage."""

    base_dir: Path = Path("ml/checkpoints")
    intent_classifier: Path = Field(default_factory=lambda: Path("ml/checkpoints/intent_classifier"))
    layout_generator: Path = Field(default_factory=lambda: Path("ml/checkpoints/layout_generator"))
    style_recommender: Path = Field(default_factory=lambda: Path("ml/checkpoints/style_recommender"))

    def ensure_dirs(self) -> None:
        """Create model directories if they don't exist."""
        for path in [self.base_dir, self.intent_classifier, self.layout_generator, self.style_recommender]:
            path.mkdir(parents=True, exist_ok=True)


class IntentClassifierConfig(BaseModel):
    """Configuration for the Intent Classifier model."""

    # Model architecture
    model_name: str = "distilbert-base-uncased"
    num_labels: int = 14  # Number of archetype classes
    max_length: int = 128
    dropout: float = 0.1

    # Training
    learning_rate: float = 2e-5
    batch_size: int = 16
    epochs: int = 10
    warmup_steps: int = 100
    weight_decay: float = 0.01

    # Labels
    archetypes: list[str] = Field(default_factory=lambda: [
        "funnel",
        "pyramid",
        "timeline",
        "process",
        "cycle",
        "hub_spoke",
        "matrix",
        "comparison",
        "flowchart",
        "org_chart",
        "venn",
        "gauge",
        "bullet_list",
        "other",
    ])


class LayoutGeneratorConfig(BaseModel):
    """Configuration for the Layout Generator model."""

    # Model architecture
    model_name: str = "t5-small"  # 60M params, CPU-trainable
    max_input_length: int = 256
    max_output_length: int = 1024

    # Training
    learning_rate: float = 1e-4
    batch_size: int = 8
    epochs: int = 20
    warmup_ratio: float = 0.1

    # DSL settings
    max_shapes: int = 50
    coordinate_buckets: int = 100  # Discretize coordinates


class StyleRecommenderConfig(BaseModel):
    """Configuration for the Style Recommender model."""

    # Model architecture (simple MLP)
    input_dim: int = 64  # Content embedding + archetype
    hidden_dims: list[int] = Field(default_factory=lambda: [128, 64, 32])
    output_dim: int = 24  # Style tokens (6 colors + 6 fonts + effects)
    dropout: float = 0.2

    # Training
    learning_rate: float = 1e-3
    batch_size: int = 32
    epochs: int = 50

    # Style tokens
    color_tokens: list[str] = Field(default_factory=lambda: [
        "accent1", "accent2", "accent3", "accent4", "accent5", "accent6",
    ])
    effect_tokens: list[str] = Field(default_factory=lambda: [
        "shadow_none", "shadow_soft", "shadow_hard",
        "glow_none", "glow_subtle", "glow_strong",
    ])


class MLSettings(BaseSettings):
    """ML settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ML_",
        extra="ignore",
    )

    # Device settings
    device: Literal["cpu", "cuda", "mps"] = "cpu"
    use_fp16: bool = False  # Half precision (GPU only)

    # Inference settings
    max_batch_size: int = 8
    inference_timeout_ms: int = 5000

    # Model configs
    paths: ModelPaths = Field(default_factory=ModelPaths)
    intent_classifier: IntentClassifierConfig = Field(default_factory=IntentClassifierConfig)
    layout_generator: LayoutGeneratorConfig = Field(default_factory=LayoutGeneratorConfig)
    style_recommender: StyleRecommenderConfig = Field(default_factory=StyleRecommenderConfig)


def get_ml_settings() -> MLSettings:
    """Get ML settings instance."""
    return MLSettings()
