"""Tests for the component library and template system."""

import tempfile
from pathlib import Path

import pytest

from backend.dsl.schema import (
    BoundingBox,
    Canvas,
    Shape,
    SlideMetadata,
    SlideScene,
    SolidFill,
    TextContent,
    TextRun,
    ThemeColors,
    Transform,
)


class TestComponentParameters:
    """Tests for component parameter schemas."""

    def test_funnel_layer_params_defaults(self):
        """Test FunnelLayerParams with defaults."""
        from backend.components.parameters import FunnelLayerParams

        params = FunnelLayerParams(layer_index=0, total_layers=4)
        assert params.layer_index == 0
        assert params.total_layers == 4
        assert params.taper_ratio == 0.8
        assert params.color.color_token == "accent1"

    def test_timeline_node_params(self):
        """Test TimelineNodeParams."""
        from backend.components.parameters import TimelineNodeParams

        params = TimelineNodeParams(
            node_index=1,
            total_nodes=5,
            date_label="Q1 2024",
            position="above",
        )
        assert params.node_index == 1
        assert params.date_label == "Q1 2024"
        assert params.position == "above"

    def test_pyramid_tier_params(self):
        """Test PyramidTierParams."""
        from backend.components.parameters import PyramidTierParams

        params = PyramidTierParams(
            tier_index=2,
            total_tiers=3,
            tier_shape="trapezoid",
        )
        assert params.tier_index == 2
        assert params.tier_shape == "trapezoid"

    def test_process_step_params(self):
        """Test ProcessStepParams."""
        from backend.components.parameters import ProcessStepParams

        params = ProcessStepParams(
            step_index=0,
            total_steps=5,
            step_number=1,
            show_number=True,
        )
        assert params.step_index == 0
        assert params.step_number == 1
        assert params.show_number is True

    def test_validate_params_function(self):
        """Test the validate_params helper function."""
        from backend.components.parameters import validate_params

        params = validate_params(
            "funnel_layer",
            {"layer_index": 1, "total_layers": 4},
        )
        assert params.layer_index == 1

    def test_validate_params_unknown_type(self):
        """Test validate_params with unknown component type."""
        from backend.components.parameters import validate_params

        with pytest.raises(ValueError, match="Unknown component type"):
            validate_params("unknown_type", {})


class TestComponentRegistry:
    """Tests for the component registry."""

    def test_registry_singleton(self):
        """Test that registry is a singleton."""
        from backend.components.registry import ComponentRegistry

        r1 = ComponentRegistry()
        r2 = ComponentRegistry()
        assert r1 is r2

    def test_register_and_get_component(self):
        """Test registering and retrieving a component."""
        from backend.components import init_components, registry

        # Clear and re-register
        registry.clear()
        init_components()

        # Should be able to get funnel_layer
        component = registry.get("funnel_layer")
        assert component is not None
        assert component.name == "funnel_layer"

    def test_list_components(self):
        """Test listing all registered components."""
        from backend.components import init_components, registry

        registry.clear()
        init_components()

        components = registry.list_components()
        assert "funnel_layer" in components
        assert "timeline_node" in components
        assert "pyramid_tier" in components

    def test_list_by_archetype(self):
        """Test listing components by archetype."""
        from backend.components import init_components, registry

        registry.clear()
        init_components()

        funnel_components = registry.list_by_archetype("funnel")
        assert "funnel_layer" in funnel_components

    def test_get_component_info(self):
        """Test getting component info."""
        from backend.components import init_components, registry

        registry.clear()
        init_components()

        info = registry.get_component_info("funnel_layer")
        assert info is not None
        assert info["name"] == "funnel_layer"
        assert info["archetype"] == "funnel"
        assert "parameters" in info


class TestComponentGeneration:
    """Tests for component shape generation."""

    def test_funnel_layer_generation(self):
        """Test generating a funnel layer."""
        from backend.components import init_components, registry

        registry.clear()
        init_components()

        bbox = BoundingBox(x=1000000, y=1000000, width=6000000, height=800000)
        instance = registry.create_instance(
            component_name="funnel_layer",
            params={"layer_index": 0, "total_layers": 4},
            bbox=bbox,
            instance_id="test_funnel_1",
        )

        assert instance is not None
        assert len(instance.shapes) >= 1
        assert instance.metadata.component_type == "funnel_layer"

    def test_timeline_node_generation(self):
        """Test generating a timeline node."""
        from backend.components import init_components, registry

        registry.clear()
        init_components()

        bbox = BoundingBox(x=500000, y=2000000, width=10000000, height=2000000)
        instance = registry.create_instance(
            component_name="timeline_node",
            params={
                "node_index": 0,
                "total_nodes": 4,
                "text": {"title": "Milestone 1"},
            },
            bbox=bbox,
            instance_id="test_timeline_1",
        )

        assert instance is not None
        assert len(instance.shapes) >= 1

    def test_pyramid_tier_generation(self):
        """Test generating a pyramid tier."""
        from backend.components import init_components, registry

        registry.clear()
        init_components()

        bbox = BoundingBox(x=1000000, y=500000, width=8000000, height=600000)
        instance = registry.create_instance(
            component_name="pyramid_tier",
            params={
                "tier_index": 0,
                "total_tiers": 3,
                "text": {"title": "Top Tier"},
            },
            bbox=bbox,
            instance_id="test_pyramid_1",
        )

        assert instance is not None
        assert len(instance.shapes) >= 1

    def test_process_step_generation(self):
        """Test generating a process step."""
        from backend.components import init_components, registry

        registry.clear()
        init_components()

        bbox = BoundingBox(x=500000, y=2000000, width=10000000, height=2000000)
        instance = registry.create_instance(
            component_name="process_step",
            params={
                "step_index": 0,
                "total_steps": 5,
                "step_number": 1,
                "text": {"title": "Step 1"},
            },
            bbox=bbox,
            instance_id="test_process_1",
        )

        assert instance is not None
        assert len(instance.shapes) >= 1

    def test_cycle_node_generation(self):
        """Test generating a cycle node."""
        from backend.components import init_components, registry

        registry.clear()
        init_components()

        bbox = BoundingBox(x=1000000, y=1000000, width=5000000, height=5000000)
        instance = registry.create_instance(
            component_name="cycle_node",
            params={
                "node_index": 0,
                "total_nodes": 4,
                "angle": 0.0,
                "text": {"title": "Phase 1"},
            },
            bbox=bbox,
            instance_id="test_cycle_1",
        )

        assert instance is not None
        assert len(instance.shapes) >= 1

    def test_hub_spoke_node_generation(self):
        """Test generating a hub spoke node."""
        from backend.components import init_components, registry

        registry.clear()
        init_components()

        bbox = BoundingBox(x=1000000, y=1000000, width=5000000, height=5000000)

        # Test hub
        hub_instance = registry.create_instance(
            component_name="hub_spoke_node",
            params={
                "is_hub": True,
                "spoke_index": 0,
                "total_spokes": 4,
                "text": {"title": "Core"},
            },
            bbox=bbox,
            instance_id="test_hub_1",
        )

        assert hub_instance is not None
        assert len(hub_instance.shapes) >= 1

        # Test spoke
        spoke_instance = registry.create_instance(
            component_name="hub_spoke_node",
            params={
                "is_hub": False,
                "spoke_index": 1,
                "total_spokes": 4,
                "text": {"title": "Spoke 1"},
            },
            bbox=bbox,
            instance_id="test_spoke_1",
        )

        assert spoke_instance is not None
        assert len(spoke_instance.shapes) >= 1


class TestComponentDetector:
    """Tests for the component detector."""

    def test_detect_funnel_archetype(self):
        """Test detecting funnel archetype."""
        from backend.components.detector import ComponentDetector

        # Create shapes that look like a funnel
        shapes = [
            Shape(
                id=f"funnel_{i}",
                type="autoShape",
                bbox=BoundingBox(
                    x=2000000,
                    y=1000000 + i * 800000,
                    width=6000000 - i * 1000000,
                    height=600000,
                ),
                transform=Transform(),
                fill=SolidFill(color="#0D9488"),
                auto_shape_type="trapezoid",
            )
            for i in range(4)
        ]

        scene = SlideScene(
            canvas=Canvas(),
            shapes=shapes,
            theme=ThemeColors(),
            metadata=SlideMetadata(),
        )

        detector = ComponentDetector()
        result = detector.detect(scene)

        assert result.archetype == "funnel"
        assert len(result.components) == 4

    def test_detect_pyramid_archetype(self):
        """Test detecting pyramid archetype."""
        from backend.components.detector import ComponentDetector

        # Create shapes that look like a pyramid (widths increase)
        shapes = [
            Shape(
                id=f"pyramid_{i}",
                type="autoShape",
                bbox=BoundingBox(
                    x=3000000 - i * 500000,
                    y=500000 + i * 600000,
                    width=4000000 + i * 1000000,
                    height=500000,
                ),
                transform=Transform(),
                fill=SolidFill(color="#0D9488"),
                auto_shape_type="trapezoid",
            )
            for i in range(3)
        ]

        scene = SlideScene(
            canvas=Canvas(),
            shapes=shapes,
            theme=ThemeColors(),
            metadata=SlideMetadata(),
        )

        detector = ComponentDetector()
        result = detector.detect(scene)

        assert result.archetype == "pyramid"
        assert len(result.components) == 3

    def test_detect_timeline_archetype(self):
        """Test detecting timeline archetype."""
        from backend.components.detector import ComponentDetector

        # Create horizontally arranged circles
        shapes = [
            Shape(
                id=f"timeline_{i}",
                type="autoShape",
                bbox=BoundingBox(
                    x=1000000 + i * 2500000,
                    y=3000000,
                    width=800000,
                    height=800000,
                ),
                transform=Transform(),
                fill=SolidFill(color="#0D9488"),
                auto_shape_type="ellipse",
            )
            for i in range(4)
        ]

        scene = SlideScene(
            canvas=Canvas(),
            shapes=shapes,
            theme=ThemeColors(),
            metadata=SlideMetadata(),
        )

        detector = ComponentDetector()
        result = detector.detect(scene)

        assert result.archetype in ["timeline", "process"]

    def test_detection_confidence(self):
        """Test that detection includes confidence scores."""
        from backend.components.detector import ComponentDetector

        shapes = [
            Shape(
                id=f"shape_{i}",
                type="autoShape",
                bbox=BoundingBox(
                    x=1000000 + i * 2000000,
                    y=3000000,
                    width=1000000,
                    height=1000000,
                ),
                transform=Transform(),
                fill=SolidFill(color="#0D9488"),
                auto_shape_type="rect",
            )
            for i in range(3)
        ]

        scene = SlideScene(
            canvas=Canvas(),
            shapes=shapes,
            theme=ThemeColors(),
            metadata=SlideMetadata(),
        )

        detector = ComponentDetector()
        result = detector.detect(scene)

        assert 0.0 <= result.confidence <= 1.0
        for comp in result.components:
            assert 0.0 <= comp.confidence <= 1.0


class TestTemplateStore:
    """Tests for the template store."""

    def test_save_and_get_template(self):
        """Test saving and retrieving a template."""
        from backend.templates.store import Template, TemplateStore

        store = TemplateStore()
        store.clear()

        template = Template(
            id="test_template_1",
            name="Test Template",
            description="A test template",
            archetype="funnel",
            tags=["test"],
            components=[],
        )

        template_id = store.save(template)
        assert template_id == "test_template_1"

        retrieved = store.get(template_id)
        assert retrieved is not None
        assert retrieved.name == "Test Template"

    def test_list_templates(self):
        """Test listing templates."""
        from backend.templates.store import Template, TemplateStore

        store = TemplateStore()
        store.clear()

        # Add some templates
        for i in range(3):
            template = Template(
                id=f"test_{i}",
                name=f"Template {i}",
                archetype="funnel" if i < 2 else "timeline",
                tags=[],
                components=[],
            )
            store.save(template)

        all_templates = store.list_all()
        assert len(all_templates) == 3

        funnel_templates = store.list_by_archetype("funnel")
        assert len(funnel_templates) == 2

    def test_search_templates(self):
        """Test searching templates."""
        from backend.templates.store import Template, TemplateStore

        store = TemplateStore()
        store.clear()

        template = Template(
            id="sales_funnel",
            name="Sales Funnel",
            description="A sales conversion funnel",
            archetype="funnel",
            tags=["sales", "marketing"],
            components=[],
        )
        store.save(template)

        # Search by name
        results = store.search(query="sales")
        assert len(results) == 1

        # Search by tag
        results = store.search(tags=["marketing"])
        assert len(results) == 1

    def test_delete_template(self):
        """Test deleting a template."""
        from backend.templates.store import Template, TemplateStore

        store = TemplateStore()
        store.clear()

        template = Template(
            id="delete_me",
            name="Delete Me",
            archetype="funnel",
            components=[],
        )
        store.save(template)

        assert store.get("delete_me") is not None
        assert store.delete("delete_me") is True
        assert store.get("delete_me") is None

    def test_file_persistence(self):
        """Test saving and loading templates from disk."""
        from backend.templates.store import Template, TemplateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "templates"

            # Create store and save template
            store1 = TemplateStore(storage_path)
            template = Template(
                id="persistent_template",
                name="Persistent Template",
                archetype="funnel",
                components=[],
            )
            store1.save(template)

            # Create new store from same path
            store2 = TemplateStore(storage_path)

            retrieved = store2.get("persistent_template")
            assert retrieved is not None
            assert retrieved.name == "Persistent Template"


class TestTemplateIngestion:
    """Tests for template ingestion."""

    def test_ingest_scene(self):
        """Test ingesting a scene as a template."""
        from backend.components import init_components, registry
        from backend.templates.ingestion import TemplateIngester

        # Clear registry before re-initializing to avoid "already registered" errors
        registry.clear()
        init_components()

        # Create a simple funnel scene
        shapes = [
            Shape(
                id=f"funnel_{i}",
                type="autoShape",
                bbox=BoundingBox(
                    x=2000000,
                    y=1000000 + i * 800000,
                    width=6000000 - i * 1000000,
                    height=600000,
                ),
                transform=Transform(),
                fill=SolidFill(color="#0D9488"),
                auto_shape_type="trapezoid",
                text=TextContent(
                    runs=[TextRun(text=f"Stage {i + 1}")],
                    alignment="center",
                ),
            )
            for i in range(4)
        ]

        scene = SlideScene(
            canvas=Canvas(),
            shapes=shapes,
            theme=ThemeColors(),
            metadata=SlideMetadata(archetype="funnel"),
        )

        ingester = TemplateIngester()
        template = ingester.ingest_scene(
            scene=scene,
            name="My Funnel Template",
            description="A test funnel",
            tags=["test"],
        )

        assert template.name == "My Funnel Template"
        assert template.archetype == "funnel"
        assert len(template.components) == 4


class TestBuiltinTemplates:
    """Tests for built-in template library."""

    def test_load_builtin_templates(self):
        """Test loading built-in templates."""
        from backend.templates.library import load_builtin_templates
        from backend.templates.store import TemplateStore

        store = TemplateStore()
        store.clear()

        count = load_builtin_templates(store)

        assert count > 0
        assert store.count() > 0

        # Check that known templates exist
        assert store.get("builtin_funnel_basic") is not None
        assert store.get("builtin_timeline_basic") is not None
        assert store.get("builtin_pyramid_basic") is not None

    def test_builtin_funnel_template(self):
        """Test the built-in funnel template structure."""
        from backend.templates.library import create_basic_funnel_template

        template = create_basic_funnel_template()

        assert template.id == "builtin_funnel_basic"
        assert template.archetype == "funnel"
        assert len(template.components) == 4
        assert "funnel" in template.tags

    def test_builtin_timeline_template(self):
        """Test the built-in timeline template structure."""
        from backend.templates.library import create_basic_timeline_template

        template = create_basic_timeline_template()

        assert template.id == "builtin_timeline_basic"
        assert template.archetype == "timeline"
        assert len(template.components) == 4


class TestShapeClusterer:
    """Tests for the shape clustering algorithm."""

    def test_single_cluster_close_shapes(self):
        """Test that close shapes are grouped into one cluster."""
        from backend.components.llm_detector import ShapeClusterer

        # Create shapes that are close together
        shapes = [
            Shape(
                id=f"shape_{i}",
                type="autoShape",
                bbox=BoundingBox(
                    x=1000000 + i * 500000,  # Close spacing
                    y=2000000,
                    width=400000,
                    height=400000,
                ),
                transform=Transform(),
                fill=SolidFill(color="#0D9488"),
            )
            for i in range(3)
        ]

        clusterer = ShapeClusterer()
        clusters = clusterer.cluster(shapes, 12192000, 6858000)

        # Should be one cluster
        assert len(clusters) == 1
        assert len(clusters[0].shapes) == 3

    def test_multiple_clusters_distant_shapes(self):
        """Test that distant shapes form separate clusters."""
        from backend.components.llm_detector import ShapeClusterer

        # Create two groups of shapes far apart
        shapes = []

        # Group 1: top-left
        for i in range(3):
            shapes.append(
                Shape(
                    id=f"group1_{i}",
                    type="autoShape",
                    bbox=BoundingBox(
                        x=500000 + i * 400000,
                        y=500000,
                        width=300000,
                        height=300000,
                    ),
                    transform=Transform(),
                    fill=SolidFill(color="#0D9488"),
                )
            )

        # Group 2: bottom-right (far away)
        for i in range(3):
            shapes.append(
                Shape(
                    id=f"group2_{i}",
                    type="autoShape",
                    bbox=BoundingBox(
                        x=8000000 + i * 400000,
                        y=5000000,
                        width=300000,
                        height=300000,
                    ),
                    transform=Transform(),
                    fill=SolidFill(color="#3B82F6"),
                )
            )

        clusterer = ShapeClusterer()
        clusters = clusterer.cluster(shapes, 12192000, 6858000)

        # Should be two clusters
        assert len(clusters) == 2
        assert all(len(c.shapes) == 3 for c in clusters)

    def test_cluster_bounds_calculation(self):
        """Test that cluster bounds are calculated correctly."""
        from backend.components.llm_detector import ShapeClusterer

        shapes = [
            Shape(
                id="shape_1",
                type="autoShape",
                bbox=BoundingBox(x=100, y=200, width=50, height=50),
                transform=Transform(),
                fill=SolidFill(color="#0D9488"),
            ),
            Shape(
                id="shape_2",
                type="autoShape",
                bbox=BoundingBox(x=200, y=300, width=60, height=70),
                transform=Transform(),
                fill=SolidFill(color="#0D9488"),
            ),
        ]

        clusterer = ShapeClusterer(distance_threshold_ratio=1.0)  # Large threshold
        clusters = clusterer.cluster(shapes, 1000, 1000)

        assert len(clusters) == 1
        bounds = clusters[0].bounds
        assert bounds["x"] == 100
        assert bounds["y"] == 200
        assert bounds["width"] == 160  # 200 + 60 - 100 = 160
        assert bounds["height"] == 170  # 300 + 70 - 200 = 170


class TestLLMPatternDetector:
    """Tests for the LLM-enhanced pattern detector."""

    def test_detect_single_pattern_heuristic(self):
        """Test detecting a single pattern with heuristics (no LLM)."""
        from backend.components.llm_detector import LLMPatternDetector

        # Create a funnel pattern
        shapes = [
            Shape(
                id=f"funnel_{i}",
                type="autoShape",
                bbox=BoundingBox(
                    x=2000000,
                    y=1000000 + i * 800000,
                    width=6000000 - i * 1000000,
                    height=600000,
                ),
                transform=Transform(),
                fill=SolidFill(color="#0D9488"),
                auto_shape_type="trapezoid",
            )
            for i in range(4)
        ]

        scene = SlideScene(
            canvas=Canvas(),
            shapes=shapes,
            theme=ThemeColors(),
            metadata=SlideMetadata(),
        )

        detector = LLMPatternDetector(use_llm=False)
        result = detector.detect(scene)

        assert len(result.patterns) == 1
        assert result.patterns[0].archetype == "funnel"
        assert result.primary_archetype == "funnel"

    def test_detect_multiple_patterns_heuristic(self):
        """Test detecting multiple patterns on one slide."""
        from backend.components.llm_detector import LLMPatternDetector

        shapes = []

        # Pattern 1: Funnel (top-left)
        for i in range(3):
            shapes.append(
                Shape(
                    id=f"funnel_{i}",
                    type="autoShape",
                    bbox=BoundingBox(
                        x=500000,
                        y=500000 + i * 600000,
                        width=4000000 - i * 800000,
                        height=500000,
                    ),
                    transform=Transform(),
                    fill=SolidFill(color="#0D9488"),
                    auto_shape_type="trapezoid",
                )
            )

        # Pattern 2: Timeline (bottom-right, far from funnel)
        for i in range(4):
            shapes.append(
                Shape(
                    id=f"timeline_{i}",
                    type="autoShape",
                    bbox=BoundingBox(
                        x=7000000 + i * 1200000,
                        y=5000000,
                        width=500000,
                        height=500000,
                    ),
                    transform=Transform(),
                    fill=SolidFill(color="#3B82F6"),
                    auto_shape_type="ellipse",
                )
            )

        scene = SlideScene(
            canvas=Canvas(),
            shapes=shapes,
            theme=ThemeColors(),
            metadata=SlideMetadata(),
        )

        detector = LLMPatternDetector(use_llm=False)
        result = detector.detect(scene)

        # Should detect two patterns
        assert len(result.patterns) == 2
        archetypes = result.archetypes
        assert "funnel" in archetypes
        assert "timeline" in archetypes

    def test_detect_grid_pattern(self):
        """Test detecting a grid/matrix pattern."""
        from backend.components.llm_detector import LLMPatternDetector

        # Create 2x2 grid
        shapes = []
        for row in range(2):
            for col in range(2):
                shapes.append(
                    Shape(
                        id=f"cell_{row}_{col}",
                        type="autoShape",
                        bbox=BoundingBox(
                            x=1000000 + col * 2000000,
                            y=1000000 + row * 1500000,
                            width=1800000,
                            height=1300000,
                        ),
                        transform=Transform(),
                        fill=SolidFill(color="#0D9488"),
                        auto_shape_type="rect",
                    )
                )

        scene = SlideScene(
            canvas=Canvas(),
            shapes=shapes,
            theme=ThemeColors(),
            metadata=SlideMetadata(),
        )

        detector = LLMPatternDetector(use_llm=False)
        result = detector.detect(scene)

        assert len(result.patterns) == 1
        assert result.patterns[0].archetype == "matrix"

    def test_pattern_group_has_components(self):
        """Test that detected patterns include component information."""
        from backend.components.llm_detector import LLMPatternDetector

        shapes = [
            Shape(
                id=f"proc_{i}",
                type="autoShape",
                bbox=BoundingBox(
                    x=500000 + i * 2000000,
                    y=2000000,
                    width=1500000,
                    height=800000,
                ),
                transform=Transform(),
                fill=SolidFill(color="#0D9488"),
                auto_shape_type="rect",
                text=TextContent(
                    runs=[TextRun(text=f"Step {i + 1}")],
                    alignment="center",
                ),
            )
            for i in range(4)
        ]

        scene = SlideScene(
            canvas=Canvas(),
            shapes=shapes,
            theme=ThemeColors(),
            metadata=SlideMetadata(),
        )

        detector = LLMPatternDetector(use_llm=False)
        result = detector.detect(scene)

        assert len(result.patterns) == 1
        pattern = result.patterns[0]
        assert len(pattern.components) == 4
        assert pattern.components[0]["component_type"] == "process_step"
        assert pattern.components[0]["index"] == 0

    def test_empty_scene(self):
        """Test detection on empty scene."""
        from backend.components.llm_detector import LLMPatternDetector

        scene = SlideScene(
            canvas=Canvas(),
            shapes=[],
            theme=ThemeColors(),
            metadata=SlideMetadata(),
        )

        detector = LLMPatternDetector(use_llm=False)
        result = detector.detect(scene)

        assert len(result.patterns) == 0
        assert len(result.unmatched_shapes) == 0

    def test_unmatched_shapes_reported(self):
        """Test that shapes that don't match patterns are reported."""
        from backend.components.llm_detector import LLMPatternDetector

        # Single isolated shape - won't form a pattern
        shapes = [
            Shape(
                id="lonely_shape",
                type="autoShape",
                bbox=BoundingBox(x=5000000, y=3000000, width=800000, height=600000),
                transform=Transform(),
                fill=SolidFill(color="#0D9488"),
            )
        ]

        scene = SlideScene(
            canvas=Canvas(),
            shapes=shapes,
            theme=ThemeColors(),
            metadata=SlideMetadata(),
        )

        detector = LLMPatternDetector(use_llm=False)
        result = detector.detect(scene)

        # Pattern detection requires at least 2 shapes
        assert len(result.patterns) == 0
        assert len(result.unmatched_shapes) == 1
        assert result.unmatched_shapes[0].id == "lonely_shape"
