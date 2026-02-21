"""Tests for the ML module."""

import json
import tempfile
from pathlib import Path

import pytest


class TestSyntheticDataGenerator:
    """Tests for the synthetic data generator."""

    def test_generate_prompt(self):
        """Test generating a single prompt."""
        from ml.training.data_generator import SyntheticDataGenerator

        generator = SyntheticDataGenerator()
        example = generator.generate_prompt("funnel")

        assert example.archetype == "funnel"
        assert len(example.prompt) > 0
        assert isinstance(example.parameters, dict)

    def test_generate_all_archetypes(self):
        """Test generating prompts for all archetypes."""
        from ml.training.data_generator import SyntheticDataGenerator

        generator = SyntheticDataGenerator()

        for archetype in generator.templates.keys():
            example = generator.generate_prompt(archetype)
            assert example.archetype == archetype

    def test_generate_dataset(self):
        """Test generating a complete dataset."""
        from ml.training.data_generator import SyntheticDataGenerator

        generator = SyntheticDataGenerator()
        examples = generator.generate_dataset(samples_per_archetype=5)

        # Should have 5 * num_archetypes examples
        assert len(examples) >= 5 * len(generator.templates)

        # Check all archetypes are represented
        archetypes = {ex.archetype for ex in examples}
        assert archetypes == set(generator.templates.keys())

    def test_save_and_load_dataset(self):
        """Test saving and loading a dataset."""
        from ml.training.data_generator import SyntheticDataGenerator

        generator = SyntheticDataGenerator()
        examples = generator.generate_dataset(samples_per_archetype=2)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.jsonl"
            generator.save_dataset(examples, path)

            loaded = generator.load_dataset(path)

            assert len(loaded) == len(examples)
            assert loaded[0].archetype == examples[0].archetype


class TestDataPipeline:
    """Tests for the data pipeline."""

    def test_generate_intent_classifier_data(self):
        """Test generating intent classifier data."""
        from ml.training.data_pipeline import DataPipeline

        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = DataPipeline(output_dir=tmpdir)
            paths = pipeline.generate_intent_classifier_data(samples_per_archetype=5)

            assert "train" in paths
            assert "val" in paths
            assert "test" in paths

            # Check files exist
            assert paths["train"].exists()

    def test_generate_style_data(self):
        """Test generating style data."""
        from ml.training.data_pipeline import DataPipeline

        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = DataPipeline(output_dir=tmpdir)
            paths = pipeline.generate_style_data(samples=10)

            assert "styles" in paths
            assert paths["styles"].exists()


class TestIntentClassifierInference:
    """Tests for intent classifier inference (fallback mode)."""

    def test_fallback_prediction(self):
        """Test keyword-based fallback prediction."""
        from ml.models.intent_classifier.inference import IntentClassifierInference

        inference = IntentClassifierInference()

        # Test funnel detection
        result = inference._fallback_predict("Create a sales funnel with 5 stages")
        assert result.archetype == "funnel"
        assert result.confidence > 0

    def test_predict_timeline(self):
        """Test timeline prediction."""
        from ml.models.intent_classifier.inference import IntentClassifierInference

        inference = IntentClassifierInference()
        result = inference.predict("Make a project timeline with milestones")

        assert result.archetype == "timeline"

    def test_predict_process(self):
        """Test process prediction."""
        from ml.models.intent_classifier.inference import IntentClassifierInference

        inference = IntentClassifierInference()
        result = inference.predict("Create a workflow with 5 steps")

        assert result.archetype == "process"

    def test_extract_parameters(self):
        """Test parameter extraction from prompt."""
        from ml.models.intent_classifier.inference import IntentClassifierInference

        inference = IntentClassifierInference()

        # Test count extraction
        params = inference.extract_parameters("Create a funnel with 5 stages", "funnel")
        assert params.get("count") == 5

        # Test word numbers
        params = inference.extract_parameters("Make a three step process", "process")
        assert params.get("count") == 3

        # Test orientation
        params = inference.extract_parameters("Create a vertical timeline", "timeline")
        assert params.get("orientation") == "vertical"

    def test_batch_predict(self):
        """Test batch prediction."""
        from ml.models.intent_classifier.inference import IntentClassifierInference

        inference = IntentClassifierInference()
        prompts = [
            "Create a funnel",
            "Make a timeline",
            "Show a process flow",
        ]

        results = inference.batch_predict(prompts)

        assert len(results) == 3
        assert results[0].archetype == "funnel"
        assert results[1].archetype == "timeline"
        assert results[2].archetype == "process"


class TestLayoutGeneratorInference:
    """Tests for layout generator inference (template mode)."""

    def test_template_generation(self):
        """Test template-based layout generation."""
        from ml.models.layout_generator.inference import LayoutGeneratorInference

        inference = LayoutGeneratorInference()
        result = inference.generate({
            "archetype": "funnel",
            "item_count": 4,
        })

        assert result.dsl is not None
        assert "shapes" in result.dsl
        assert len(result.dsl["shapes"]) == 4

    def test_generate_different_archetypes(self):
        """Test generating different archetype layouts."""
        from ml.models.layout_generator.inference import LayoutGeneratorInference

        inference = LayoutGeneratorInference()

        for archetype in ["funnel", "pyramid", "timeline", "process", "cycle"]:
            result = inference.generate({
                "archetype": archetype,
                "item_count": 4,
            })

            assert result.dsl is not None
            assert len(result.dsl["shapes"]) >= 1

    def test_generate_with_content(self):
        """Test generating layout with content."""
        from ml.models.layout_generator.inference import LayoutGeneratorInference

        inference = LayoutGeneratorInference()
        content = [
            {"title": "Step 1"},
            {"title": "Step 2"},
            {"title": "Step 3"},
        ]

        result = inference.generate_with_content(
            intent={"archetype": "process", "item_count": 3},
            content=content,
        )

        assert result.dsl is not None
        # Content should be filled in
        shapes = result.dsl["shapes"]
        assert len(shapes) >= 3

    def test_generate_variations(self):
        """Test generating layout variations."""
        from ml.models.layout_generator.inference import LayoutGeneratorInference

        inference = LayoutGeneratorInference()
        variations = inference.generate_variations(
            intent={"archetype": "process", "item_count": 4},
            count=3,
        )

        assert len(variations) == 3


class TestStyleRecommenderInference:
    """Tests for style recommender inference."""

    def test_rule_based_recommendation(self):
        """Test rule-based style recommendation."""
        from ml.models.style_recommender.inference import StyleRecommenderInference

        inference = StyleRecommenderInference()
        result = inference.recommend({
            "archetype": "funnel",
            "formality": "professional",
        })

        assert result.color_palette is not None
        assert len(result.color_palette) == 6
        assert result.font_family is not None

    def test_brand_colors(self):
        """Test recommendation with brand colors."""
        from ml.models.style_recommender.inference import StyleRecommenderInference

        inference = StyleRecommenderInference()
        brand_colors = ["#FF0000", "#00FF00", "#0000FF"]

        result = inference.recommend_for_brand(
            features={"archetype": "process"},
            brand_colors=brand_colors,
        )

        assert result.color_palette[0] == "#FF0000"
        assert result.color_palette[1] == "#00FF00"
        assert result.color_palette[2] == "#0000FF"

    def test_style_variations(self):
        """Test getting style variations."""
        from ml.models.style_recommender.inference import StyleRecommenderInference

        inference = StyleRecommenderInference()
        variations = inference.get_style_variations(
            features={"archetype": "timeline"},
            count=3,
        )

        assert len(variations) == 3

        # Variations should have different palettes
        palettes = [tuple(v.color_palette) for v in variations]
        assert len(set(palettes)) == 3  # All different


class TestInferenceEngine:
    """Tests for the unified inference engine."""

    def test_full_pipeline(self):
        """Test the complete inference pipeline."""
        from ml.inference.engine import InferenceEngine

        engine = InferenceEngine(use_ml=False)  # Use fallbacks
        result = engine.generate("Create a 4-stage sales funnel")

        assert result.archetype == "funnel"
        assert result.dsl is not None
        assert "shapes" in result.dsl
        assert result.style is not None

    def test_pipeline_with_content(self):
        """Test pipeline with content."""
        from ml.inference.engine import InferenceEngine

        engine = InferenceEngine(use_ml=False)
        content = [
            {"title": "Awareness"},
            {"title": "Interest"},
            {"title": "Decision"},
            {"title": "Action"},
        ]

        result = engine.generate(
            "Create a marketing funnel",
            content=content,
        )

        assert result.archetype == "funnel"
        assert len(result.dsl["shapes"]) >= 4

    def test_pipeline_with_brand(self):
        """Test pipeline with brand guidelines."""
        from ml.inference.engine import InferenceEngine

        engine = InferenceEngine(use_ml=False)
        result = engine.generate(
            "Create a timeline",
            brand_colors=["#FF5733", "#C70039", "#900C3F"],
        )

        # Should use brand colors
        assert result.style.color_palette[0] == "#FF5733"

    def test_generate_variations(self):
        """Test generating variations."""
        from ml.inference.engine import InferenceEngine

        engine = InferenceEngine(use_ml=False)
        variations = engine.generate_variations(
            "Create a process flow",
            count=3,
        )

        assert len(variations) == 3

    def test_classify_only(self):
        """Test classification without generation."""
        from ml.inference.engine import InferenceEngine

        engine = InferenceEngine(use_ml=False)
        result = engine.classify_only("Make a pyramid diagram")

        assert result.archetype == "pyramid"

    def test_style_only(self):
        """Test style recommendation without layout."""
        from ml.inference.engine import InferenceEngine

        engine = InferenceEngine(use_ml=False)
        result = engine.recommend_style_only("cycle", formality="casual")

        assert result.font_family == "Poppins"  # Casual style
        assert result.corner_radius == "pill"


class TestMLConfig:
    """Tests for ML configuration."""

    def test_default_config(self):
        """Test loading default configuration."""
        from ml.config import get_ml_settings

        settings = get_ml_settings()

        assert settings.device in ["cpu", "cuda", "mps"]
        assert settings.intent_classifier.num_labels == 14
        assert settings.layout_generator.model_name == "t5-small"

    def test_config_paths(self):
        """Test model paths configuration."""
        from ml.config import get_ml_settings

        settings = get_ml_settings()

        assert settings.paths.intent_classifier.name == "intent_classifier"
        assert settings.paths.layout_generator.name == "layout_generator"
