"""Tests for the LLM integration module."""

import pytest

from backend.llm.fallback import FallbackParser
from backend.llm.parser import PromptParser, ParsedIntent
from backend.llm.client import LLMConfig


class TestFallbackParser:
    """Tests for the fallback keyword-based parser."""

    def test_classify_funnel(self):
        """Test funnel classification."""
        parser = FallbackParser()

        result = parser.classify("Create a sales funnel with 5 stages")

        assert result["archetype"] == "funnel"
        assert result["confidence"] > 0.5

    def test_classify_timeline(self):
        """Test timeline classification."""
        parser = FallbackParser()

        result = parser.classify("Make a project timeline with milestones")

        assert result["archetype"] == "timeline"

    def test_classify_process(self):
        """Test process classification."""
        parser = FallbackParser()

        result = parser.classify("Show the step by step workflow")

        assert result["archetype"] == "process"

    def test_classify_pyramid(self):
        """Test pyramid classification."""
        parser = FallbackParser()

        result = parser.classify("Create a hierarchy pyramid with 4 tiers")

        assert result["archetype"] == "pyramid"

    def test_classify_cycle(self):
        """Test cycle classification."""
        parser = FallbackParser()

        result = parser.classify("Show a continuous lifecycle diagram")

        assert result["archetype"] == "cycle"

    def test_classify_comparison(self):
        """Test comparison classification."""
        parser = FallbackParser()

        result = parser.classify("Compare option A vs option B")

        assert result["archetype"] == "comparison"

    def test_classify_matrix(self):
        """Test matrix classification."""
        parser = FallbackParser()

        result = parser.classify("Create a 2x2 matrix for prioritization")

        assert result["archetype"] == "matrix"

    def test_classify_venn(self):
        """Test venn classification."""
        parser = FallbackParser()

        result = parser.classify("Show overlapping circles for set relationships")

        assert result["archetype"] == "venn"

    def test_classify_org_chart(self):
        """Test org chart classification."""
        parser = FallbackParser()

        result = parser.classify("Create an organizational chart for our team")

        assert result["archetype"] == "org_chart"

    def test_classify_default(self):
        """Test default classification when no keywords match."""
        parser = FallbackParser()

        result = parser.classify("Create something cool")

        # Should default to process
        assert result["archetype"] == "process"
        assert result["confidence"] < 0.5

    def test_extract_numeric_count(self):
        """Test numeric count extraction."""
        parser = FallbackParser()

        result = parser.parse("Create a funnel with 5 stages")

        assert result["item_count"] == 5

    def test_extract_word_count(self):
        """Test word number count extraction."""
        parser = FallbackParser()

        result = parser.parse("Make a three step process")

        assert result["item_count"] == 3

    def test_extract_orientation_horizontal(self):
        """Test horizontal orientation extraction."""
        parser = FallbackParser()

        result = parser.parse("Create a horizontal timeline")

        assert result["orientation"] == "horizontal"

    def test_extract_orientation_vertical(self):
        """Test vertical orientation extraction."""
        parser = FallbackParser()

        result = parser.parse("Make a vertical process flow from top to bottom")

        assert result["orientation"] == "vertical"

    def test_extract_style_hints(self):
        """Test style hint extraction."""
        parser = FallbackParser()

        result = parser.parse("Create a modern minimalist funnel")

        assert "modern" in result["style_hints"]

    def test_extract_quoted_items(self):
        """Test quoted item extraction."""
        parser = FallbackParser()

        items = parser.extract_items(
            'Create a funnel with "Awareness", "Interest", "Decision", "Action"',
            "funnel"
        )

        assert len(items) == 4
        assert items[0]["title"] == "Awareness"

    def test_extract_list_items(self):
        """Test comma-separated list extraction."""
        parser = FallbackParser()

        items = parser.extract_items(
            "Create a process with stages: Discovery, Design, Develop, Deploy",
            "process"
        )

        assert len(items) == 4
        assert items[0]["title"] == "Discovery"

    def test_full_parse(self):
        """Test full parsing."""
        parser = FallbackParser()

        result = parser.parse(
            "Create a vertical 4-stage sales funnel with modern styling"
        )

        assert result["archetype"] == "funnel"
        assert result["item_count"] == 4
        assert result["orientation"] == "vertical"
        assert "modern" in result["style_hints"]


class TestPromptParser:
    """Tests for the prompt parser."""

    def test_parse_with_fallback(self):
        """Test parsing uses fallback when LLM disabled."""
        parser = PromptParser(use_llm=False)

        result = parser.parse("Create a sales funnel with 5 stages")

        assert isinstance(result, ParsedIntent)
        assert result.archetype == "funnel"
        assert result.item_count == 5
        assert not result.used_llm

    def test_classify_funnel(self):
        """Test classification."""
        parser = PromptParser(use_llm=False)

        archetype, confidence = parser.classify("Make a marketing funnel")

        assert archetype == "funnel"
        assert confidence > 0.5

    def test_extract_content(self):
        """Test content extraction."""
        parser = PromptParser(use_llm=False)

        items = parser.extract_content(
            'Create stages: "Aware", "Consider", "Decide", "Buy"',
            "funnel"
        )

        assert len(items) == 4

    def test_llm_availability_check(self):
        """Test LLM availability check."""
        parser = PromptParser(use_llm=True)

        # Without API key, should return False
        assert parser.is_llm_available() is False


class TestLLMConfig:
    """Tests for LLM configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = LLMConfig()

        assert config.provider == "anthropic"
        assert config.model == "claude-3-haiku-20240307"
        assert config.max_tokens == 1024
        assert config.temperature == 0.3

    def test_custom_config(self):
        """Test custom configuration."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.5,
        )

        assert config.provider == "openai"
        assert config.model == "gpt-4o-mini"
        assert config.temperature == 0.5


class TestParsedIntent:
    """Tests for ParsedIntent dataclass."""

    def test_default_values(self):
        """Test default values."""
        intent = ParsedIntent(
            archetype="funnel",
            confidence=0.9,
        )

        assert intent.archetype == "funnel"
        assert intent.confidence == 0.9
        assert intent.item_count is None
        assert intent.orientation is None
        assert intent.style_hints == []
        assert intent.items == []
        assert not intent.used_llm

    def test_full_intent(self):
        """Test fully populated intent."""
        intent = ParsedIntent(
            archetype="timeline",
            confidence=0.95,
            item_count=6,
            orientation="horizontal",
            style_hints=["modern", "corporate"],
            items=[
                {"title": "Phase 1"},
                {"title": "Phase 2"},
            ],
            parameters={"direction": "ltr"},
            used_llm=True,
        )

        assert intent.archetype == "timeline"
        assert intent.item_count == 6
        assert len(intent.items) == 2
        assert intent.used_llm
