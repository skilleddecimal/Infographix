"""
test_llm_reasoning.py — Tests for LLM reasoning functionality.

Tests:
- InfographBrief dataclass operations
- Brief validation
- Brief enhancement
- Brief <-> dict conversion
- Live API test (optional, requires API key)
"""

import pytest
import sys
import os
from pathlib import Path

# Add paths for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir.parent))

from backend.engine.llm_reasoning import (
    InfographBrief,
    EntityBrief,
    LayerBrief,
    ConnectionBrief,
    validate_brief,
    enhance_brief,
    brief_to_dict,
    dict_to_brief,
)
from backend.engine.data_models import ColorPalette


# =============================================================================
# INFOGRAPH BRIEF TESTS
# =============================================================================

class TestInfographBrief:
    """Test InfographBrief dataclass."""

    def test_create_minimal_brief(self):
        """Test creating a minimal brief."""
        brief = InfographBrief(title="Test Diagram")
        assert brief.title == "Test Diagram"
        assert brief.diagram_type == "marketecture"
        assert brief.entities == []
        assert brief.layers == []
        assert brief.confidence == 1.0

    def test_create_full_brief(self):
        """Test creating a full brief with all fields."""
        brief = InfographBrief(
            title="Web Architecture",
            subtitle="3-Tier Design",
            diagram_type="marketecture",
            entities=[
                EntityBrief(id="react", label="React", layer_id="frontend"),
                EntityBrief(id="api", label="Node.js API", layer_id="backend"),
            ],
            layers=[
                LayerBrief(id="frontend", label="Frontend", entity_ids=["react"]),
                LayerBrief(id="backend", label="Backend", entity_ids=["api"]),
            ],
            connections=[
                ConnectionBrief(from_id="react", to_id="api", style="arrow"),
            ],
            brand_hint="microsoft",
            color_hint="#0078D4",
            confidence=0.95,
        )

        assert brief.title == "Web Architecture"
        assert brief.subtitle == "3-Tier Design"
        assert len(brief.entities) == 2
        assert len(brief.layers) == 2
        assert len(brief.connections) == 1
        assert brief.brand_hint == "microsoft"

    def test_to_diagram_input(self):
        """Test converting brief to DiagramInput."""
        brief = InfographBrief(
            title="Test",
            entities=[
                EntityBrief(id="a", label="Block A", layer_id="layer1"),
            ],
            layers=[
                LayerBrief(id="layer1", label="Layer 1", entity_ids=["a"]),
            ],
        )

        palette = ColorPalette(primary="#FF0000")
        diagram_input = brief.to_diagram_input(palette)

        assert diagram_input.title == "Test"
        assert len(diagram_input.blocks) == 1
        assert diagram_input.blocks[0].id == "a"
        assert diagram_input.palette.primary == "#FF0000"


# =============================================================================
# VALIDATION TESTS
# =============================================================================

class TestBriefValidation:
    """Test brief validation functionality."""

    def test_validate_valid_brief(self):
        """Test validating a valid brief."""
        brief = InfographBrief(
            title="Valid Diagram",
            entities=[
                EntityBrief(id="a", label="A", layer_id="l1"),
                EntityBrief(id="b", label="B", layer_id="l1"),
            ],
            layers=[
                LayerBrief(id="l1", label="Layer 1", entity_ids=["a", "b"]),
            ],
            connections=[
                ConnectionBrief(from_id="a", to_id="b"),
            ],
        )

        warnings = validate_brief(brief)
        assert len(warnings) == 0

    def test_validate_missing_title(self):
        """Test validation catches missing title."""
        brief = InfographBrief(title="")
        warnings = validate_brief(brief)
        assert any("title" in w.lower() for w in warnings)

    def test_validate_no_entities(self):
        """Test validation catches no entities."""
        brief = InfographBrief(title="Empty", entities=[])
        warnings = validate_brief(brief)
        assert any("entities" in w.lower() for w in warnings)

    def test_validate_duplicate_entity_ids(self):
        """Test validation catches duplicate entity IDs."""
        brief = InfographBrief(
            title="Duplicates",
            entities=[
                EntityBrief(id="same", label="First"),
                EntityBrief(id="same", label="Second"),  # Duplicate!
            ],
        )
        warnings = validate_brief(brief)
        assert any("duplicate" in w.lower() for w in warnings)

    def test_validate_invalid_layer_reference(self):
        """Test validation catches invalid layer references."""
        brief = InfographBrief(
            title="Bad Reference",
            entities=[
                EntityBrief(id="a", label="A"),
            ],
            layers=[
                LayerBrief(id="l1", label="Layer", entity_ids=["nonexistent"]),
            ],
        )
        warnings = validate_brief(brief)
        assert any("unknown entity" in w.lower() for w in warnings)

    def test_validate_invalid_connection(self):
        """Test validation catches invalid connections."""
        brief = InfographBrief(
            title="Bad Connection",
            entities=[
                EntityBrief(id="a", label="A"),
            ],
            connections=[
                ConnectionBrief(from_id="a", to_id="nonexistent"),
            ],
        )
        warnings = validate_brief(brief)
        assert any("unknown entity" in w.lower() for w in warnings)

    def test_validate_unknown_diagram_type(self):
        """Test validation catches unknown diagram type."""
        brief = InfographBrief(
            title="Unknown Type",
            diagram_type="unknown_type_xyz",
            entities=[EntityBrief(id="a", label="A")],
        )
        warnings = validate_brief(brief)
        assert any("unknown diagram type" in w.lower() for w in warnings)


# =============================================================================
# ENHANCEMENT TESTS
# =============================================================================

class TestBriefEnhancement:
    """Test brief enhancement functionality."""

    def test_enhance_adds_default_layer(self):
        """Test that enhancement adds default layer when none exist."""
        brief = InfographBrief(
            title="No Layers",
            entities=[
                EntityBrief(id="a", label="A"),
                EntityBrief(id="b", label="B"),
            ],
        )

        enhanced = enhance_brief(brief)

        assert len(enhanced.layers) == 1
        assert enhanced.layers[0].id == "default_layer"
        assert "a" in enhanced.layers[0].entity_ids
        assert "b" in enhanced.layers[0].entity_ids

    def test_enhance_assigns_layer_ids(self):
        """Test that enhancement assigns layer_id to entities."""
        brief = InfographBrief(
            title="Assign Layers",
            entities=[
                EntityBrief(id="a", label="A"),  # No layer_id
                EntityBrief(id="b", label="B"),  # No layer_id
            ],
            layers=[
                LayerBrief(id="l1", label="Layer 1", entity_ids=["a"]),
                LayerBrief(id="l2", label="Layer 2", entity_ids=["b"]),
            ],
        )

        enhanced = enhance_brief(brief)

        # Find entity 'a' and check its layer_id
        entity_a = next(e for e in enhanced.entities if e.id == "a")
        entity_b = next(e for e in enhanced.entities if e.id == "b")

        assert entity_a.layer_id == "l1"
        assert entity_b.layer_id == "l2"

    def test_enhance_preserves_existing_data(self):
        """Test that enhancement preserves existing data."""
        brief = InfographBrief(
            title="Keep This",
            subtitle="And This",
            brand_hint="opentext",
            confidence=0.8,
            entities=[EntityBrief(id="a", label="A")],
        )

        enhanced = enhance_brief(brief)

        assert enhanced.title == "Keep This"
        assert enhanced.subtitle == "And This"
        assert enhanced.brand_hint == "opentext"
        assert enhanced.confidence == 0.8


# =============================================================================
# CONVERSION TESTS
# =============================================================================

class TestBriefConversion:
    """Test brief to/from dict conversion."""

    def test_brief_to_dict(self):
        """Test converting brief to dictionary."""
        brief = InfographBrief(
            title="Test",
            subtitle="Subtitle",
            diagram_type="marketecture",
            entities=[
                EntityBrief(id="a", label="A", description="Desc A"),
            ],
            layers=[
                LayerBrief(id="l1", label="Layer 1", entity_ids=["a"]),
            ],
            connections=[
                ConnectionBrief(from_id="a", to_id="a", label="Self"),
            ],
            brand_hint="microsoft",
            confidence=0.9,
        )

        data = brief_to_dict(brief)

        assert data["title"] == "Test"
        assert data["subtitle"] == "Subtitle"
        assert data["diagram_type"] == "marketecture"
        assert len(data["entities"]) == 1
        assert data["entities"][0]["id"] == "a"
        assert len(data["layers"]) == 1
        assert len(data["connections"]) == 1
        assert data["brand_hint"] == "microsoft"
        assert data["confidence"] == 0.9

    def test_dict_to_brief(self):
        """Test converting dictionary to brief."""
        data = {
            "title": "From Dict",
            "subtitle": "Test",
            "diagram_type": "process_flow",
            "entities": [
                {"id": "x", "label": "X", "layer_id": "l1"},
                {"id": "y", "label": "Y", "layer_id": "l1"},
            ],
            "layers": [
                {"id": "l1", "label": "Layer", "entity_ids": ["x", "y"]},
            ],
            "connections": [
                {"from_id": "x", "to_id": "y", "style": "arrow"},
            ],
            "color_hint": "#FF0000",
            "confidence": 0.85,
        }

        brief = dict_to_brief(data)

        assert brief.title == "From Dict"
        assert brief.diagram_type == "process_flow"
        assert len(brief.entities) == 2
        assert brief.entities[0].id == "x"
        assert len(brief.layers) == 1
        assert len(brief.connections) == 1
        assert brief.color_hint == "#FF0000"
        assert brief.confidence == 0.85

    def test_roundtrip_conversion(self):
        """Test that brief -> dict -> brief preserves data."""
        original = InfographBrief(
            title="Roundtrip Test",
            subtitle="Testing",
            diagram_type="marketecture",
            entities=[
                EntityBrief(id="a", label="A", description="Desc", layer_id="l1"),
                EntityBrief(id="b", label="B", layer_id="l2"),
            ],
            layers=[
                LayerBrief(id="l1", label="L1", entity_ids=["a"]),
                LayerBrief(id="l2", label="L2", entity_ids=["b"], is_cross_cutting=True),
            ],
            connections=[
                ConnectionBrief(from_id="a", to_id="b", label="Link", style="dashed"),
            ],
            brand_hint="google",
            color_hint="#4285F4",
            style_notes="Some notes",
            confidence=0.77,
        )

        # Convert to dict and back
        data = brief_to_dict(original)
        restored = dict_to_brief(data)

        # Check all fields match
        assert restored.title == original.title
        assert restored.subtitle == original.subtitle
        assert restored.diagram_type == original.diagram_type
        assert len(restored.entities) == len(original.entities)
        assert len(restored.layers) == len(original.layers)
        assert len(restored.connections) == len(original.connections)
        assert restored.brand_hint == original.brand_hint
        assert restored.color_hint == original.color_hint
        assert restored.confidence == original.confidence


# =============================================================================
# LIVE API TESTS (Optional - requires API key and credits)
# =============================================================================

class TestLiveAPI:
    """Live API tests - only run if ANTHROPIC_API_KEY is set and --live flag used."""

    @pytest.fixture
    def api_available(self):
        """Check if API is available."""
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key or key == "your-api-key-here":
            pytest.skip("ANTHROPIC_API_KEY not configured")
        return True

    @pytest.mark.live
    def test_analyze_simple_prompt(self, api_available):
        """Test analyzing a simple prompt (costs money!)."""
        from backend.engine.llm_reasoning import analyze_prompt_sync

        brief = analyze_prompt_sync(
            "Create a simple 2-tier architecture with frontend and backend"
        )

        assert brief.title  # Should have a title
        assert len(brief.entities) >= 2  # At least frontend and backend
        assert brief.diagram_type in ["marketecture", "tech_stack", "process_flow"]
        assert brief.confidence > 0.5

    @pytest.mark.live
    def test_analyze_opentext_prompt(self, api_available):
        """Test the validation prompt from CLAUDE.md (costs money!)."""
        from backend.engine.llm_reasoning import analyze_prompt_sync

        brief = analyze_prompt_sync(
            "Build a Marketecture of OpenText Business Units with MyAviator as the AI Layer in standard OpenText blue theme"
        )

        assert "opentext" in brief.title.lower() or "opentext" in (brief.brand_hint or "").lower()
        assert brief.diagram_type == "marketecture"
        # Should have MyAviator
        entity_labels = [e.label.lower() for e in brief.entities]
        assert any("aviator" in label for label in entity_labels)


# =============================================================================
# RUN TESTS
# =============================================================================

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("LLM Reasoning Tests")
    print("=" * 60 + "\n")

    # Check for --live flag
    run_live = "--live" in sys.argv

    try:
        import pytest
        args = [__file__, "-v"]
        if not run_live:
            args.extend(["-m", "not live"])
        sys.exit(pytest.main(args))
    except ImportError:
        # Basic test runner (skip live tests)
        test_classes = [
            TestInfographBrief,
            TestBriefValidation,
            TestBriefEnhancement,
            TestBriefConversion,
        ]

        passed = 0
        failed = 0

        for test_class in test_classes:
            instance = test_class()
            for method_name in dir(instance):
                if method_name.startswith("test_"):
                    try:
                        print(f"Running {test_class.__name__}.{method_name}...", end=" ")
                        getattr(instance, method_name)()
                        print("PASSED")
                        passed += 1
                    except Exception as e:
                        print(f"FAILED: {e}")
                        failed += 1

        print(f"\n{passed} passed, {failed} failed")
        if not run_live:
            print("(Live API tests skipped - use --live to run them)")
        return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
