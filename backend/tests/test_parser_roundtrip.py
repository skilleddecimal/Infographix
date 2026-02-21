"""Round-trip validation tests for PPTX parser.

Tests that templates can be parsed completely and that the extracted
DSL contains all expected elements for reconstruction.
"""

import os
from pathlib import Path
from typing import Generator

import pytest

from backend.dsl.schema import (
    PathCommandType,
    ShapeType,
    SlideScene,
)
from backend.parser import PPTXReader


# Get templates directory relative to this test file
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def get_all_template_files() -> list[Path]:
    """Get all PPTX template files."""
    if not TEMPLATES_DIR.exists():
        return []

    templates = []
    for category_dir in TEMPLATES_DIR.iterdir():
        if category_dir.is_dir():
            for pptx_file in category_dir.glob("*.pptx"):
                templates.append(pptx_file)

    return sorted(templates)


def get_template_by_category(category: str) -> list[Path]:
    """Get templates for a specific category."""
    category_dir = TEMPLATES_DIR / category
    if not category_dir.exists():
        return []
    return sorted(category_dir.glob("*.pptx"))


class TestPPTXReaderBasic:
    """Basic tests for PPTXReader."""

    @pytest.fixture
    def reader(self) -> PPTXReader:
        """Create a PPTXReader instance."""
        return PPTXReader()

    def test_reader_initialization(self, reader: PPTXReader) -> None:
        """Test that reader initializes correctly with all parsers."""
        assert reader.shape_extractor is not None
        assert reader.style_extractor is not None
        assert reader.theme_parser is not None
        assert hasattr(reader.shape_extractor, "path_parser")
        assert hasattr(reader.shape_extractor, "transform_parser")


@pytest.mark.skipif(
    not TEMPLATES_DIR.exists() or not get_all_template_files(),
    reason="No templates available for testing",
)
class TestTemplateRoundtrip:
    """Round-trip tests for all templates."""

    @pytest.fixture
    def reader(self) -> PPTXReader:
        """Create a PPTXReader instance."""
        return PPTXReader()

    @pytest.mark.parametrize(
        "template_path",
        get_all_template_files(),
        ids=lambda p: f"{p.parent.name}/{p.name}",
    )
    def test_template_parses_without_error(
        self, reader: PPTXReader, template_path: Path
    ) -> None:
        """Test that each template parses without raising exceptions."""
        scenes = reader.read(template_path)

        assert len(scenes) >= 1
        for scene in scenes:
            assert isinstance(scene, SlideScene)
            assert scene.canvas is not None
            assert scene.theme is not None

    @pytest.mark.parametrize(
        "template_path",
        get_all_template_files(),
        ids=lambda p: f"{p.parent.name}/{p.name}",
    )
    def test_template_shapes_have_required_properties(
        self, reader: PPTXReader, template_path: Path
    ) -> None:
        """Test that extracted shapes have all required properties."""
        scenes = reader.read(template_path)

        for scene in scenes:
            for shape in scene.shapes:
                # Required properties
                assert shape.id is not None
                assert shape.type is not None
                assert shape.bbox is not None
                assert shape.transform is not None

                # Bounding box must be valid
                assert shape.bbox.width >= 0
                assert shape.bbox.height >= 0

                # Transform must have valid values
                assert shape.transform.scale_x > 0
                assert shape.transform.scale_y > 0


@pytest.mark.skipif(
    not TEMPLATES_DIR.exists() or not get_template_by_category("funnel"),
    reason="No funnel templates available",
)
class TestFunnelTemplates:
    """Tests specific to funnel templates which typically have freeform shapes."""

    @pytest.fixture
    def reader(self) -> PPTXReader:
        """Create a PPTXReader instance."""
        return PPTXReader()

    @pytest.mark.parametrize(
        "template_path",
        get_template_by_category("funnel"),
        ids=lambda p: p.name,
    )
    def test_funnel_has_shapes(
        self, reader: PPTXReader, template_path: Path
    ) -> None:
        """Test that funnel templates have shapes."""
        scenes = reader.read(template_path)

        assert len(scenes) >= 1
        # Funnels should have multiple shapes
        total_shapes = sum(len(scene.shapes) for scene in scenes)
        assert total_shapes > 0, f"Funnel template {template_path.name} has no shapes"

    def test_freeform_path_extraction(self, reader: PPTXReader) -> None:
        """Test that freeform shapes have path commands extracted."""
        funnel_templates = get_template_by_category("funnel")
        if not funnel_templates:
            pytest.skip("No funnel templates")

        # Check first funnel template
        scenes = reader.read(funnel_templates[0])

        freeform_shapes = []
        for scene in scenes:
            for shape in scene.shapes:
                if shape.type == ShapeType.FREEFORM:
                    freeform_shapes.append(shape)
                # Also check groups
                if shape.children:
                    for child in shape.children:
                        if child.type == ShapeType.FREEFORM:
                            freeform_shapes.append(child)

        # Funnels often have freeform shapes - if found, verify paths
        for shape in freeform_shapes:
            if shape.path:
                # Verify path command structure
                for cmd in shape.path:
                    assert cmd.type in PathCommandType
                    if cmd.type in (PathCommandType.MOVE_TO, PathCommandType.LINE_TO):
                        assert cmd.x is not None
                        assert cmd.y is not None


@pytest.mark.skipif(
    not TEMPLATES_DIR.exists() or not get_template_by_category("pyramid"),
    reason="No pyramid templates available",
)
class TestPyramidTemplates:
    """Tests specific to pyramid templates."""

    @pytest.fixture
    def reader(self) -> PPTXReader:
        """Create a PPTXReader instance."""
        return PPTXReader()

    @pytest.mark.parametrize(
        "template_path",
        get_template_by_category("pyramid"),
        ids=lambda p: p.name,
    )
    def test_pyramid_shapes_have_fills(
        self, reader: PPTXReader, template_path: Path
    ) -> None:
        """Test that pyramid shapes have fill styles extracted."""
        scenes = reader.read(template_path)

        shapes_with_fill = 0
        for scene in scenes:
            for shape in scene.shapes:
                if shape.fill and shape.fill.type != "none":
                    shapes_with_fill += 1

        # Pyramids should have filled shapes
        assert shapes_with_fill > 0


@pytest.mark.skipif(
    not TEMPLATES_DIR.exists() or not get_all_template_files(),
    reason="No templates available",
)
class TestTransformExtraction:
    """Tests for transform extraction across templates."""

    @pytest.fixture
    def reader(self) -> PPTXReader:
        """Create a PPTXReader instance."""
        return PPTXReader()

    def test_rotation_values_valid(self, reader: PPTXReader) -> None:
        """Test that rotation values are within valid range."""
        templates = get_all_template_files()[:10]  # Test first 10

        for template_path in templates:
            scenes = reader.read(template_path)

            for scene in scenes:
                for shape in scene.shapes:
                    rotation = shape.transform.rotation
                    assert -360 <= rotation <= 360, (
                        f"Invalid rotation {rotation} in {template_path.name}"
                    )

    def test_flip_values_are_boolean(self, reader: PPTXReader) -> None:
        """Test that flip values are boolean."""
        templates = get_all_template_files()[:10]

        for template_path in templates:
            scenes = reader.read(template_path)

            for scene in scenes:
                for shape in scene.shapes:
                    assert isinstance(shape.transform.flip_h, bool)
                    assert isinstance(shape.transform.flip_v, bool)


@pytest.mark.skipif(
    not TEMPLATES_DIR.exists() or not get_all_template_files(),
    reason="No templates available",
)
class TestThemeExtraction:
    """Tests for theme color extraction."""

    @pytest.fixture
    def reader(self) -> PPTXReader:
        """Create a PPTXReader instance."""
        return PPTXReader()

    def test_theme_colors_are_hex(self, reader: PPTXReader) -> None:
        """Test that theme colors are valid hex strings."""
        templates = get_all_template_files()[:5]  # Test first 5

        for template_path in templates:
            scenes = reader.read(template_path)

            for scene in scenes:
                theme = scene.theme
                # Check all color fields
                for color in [
                    theme.dark1,
                    theme.light1,
                    theme.accent1,
                    theme.accent2,
                    theme.hyperlink,
                ]:
                    assert color.startswith("#"), f"Invalid color format: {color}"
                    assert len(color) == 7, f"Invalid color length: {color}"


@pytest.mark.skipif(
    not TEMPLATES_DIR.exists() or not get_all_template_files(),
    reason="No templates available",
)
class TestEffectsExtraction:
    """Tests for visual effects extraction."""

    @pytest.fixture
    def reader(self) -> PPTXReader:
        """Create a PPTXReader instance."""
        return PPTXReader()

    def test_effects_object_always_present(self, reader: PPTXReader) -> None:
        """Test that shapes always have an Effects object."""
        templates = get_all_template_files()[:10]

        for template_path in templates:
            scenes = reader.read(template_path)

            for scene in scenes:
                for shape in scene.shapes:
                    assert shape.effects is not None
                    # Effects properties should be None or valid objects
                    if shape.effects.shadow is not None:
                        assert shape.effects.shadow.blur_radius >= 0
                    if shape.effects.glow is not None:
                        assert shape.effects.glow.radius >= 0
                    if shape.effects.soft_edges is not None:
                        assert shape.effects.soft_edges >= 0


@pytest.mark.skipif(
    not TEMPLATES_DIR.exists() or not get_all_template_files(),
    reason="No templates available",
)
class TestTextAlignment:
    """Tests for text alignment extraction."""

    @pytest.fixture
    def reader(self) -> PPTXReader:
        """Create a PPTXReader instance."""
        return PPTXReader()

    def test_text_alignment_valid_values(self, reader: PPTXReader) -> None:
        """Test that text alignment is one of valid values."""
        templates = get_all_template_files()[:10]
        valid_alignments = {"left", "center", "right", "justify"}

        for template_path in templates:
            scenes = reader.read(template_path)

            for scene in scenes:
                for shape in scene.shapes:
                    if shape.text is not None:
                        assert shape.text.alignment in valid_alignments, (
                            f"Invalid alignment: {shape.text.alignment}"
                        )


class TestParserModuleExports:
    """Tests for parser module exports."""

    def test_all_parsers_exported(self) -> None:
        """Test that all parser classes are exported from the module."""
        from backend.parser import (
            PathParser,
            PPTXReader,
            ShapeExtractor,
            StyleExtractor,
            ThemeParser,
            TransformParser,
        )

        # Verify classes exist
        assert PathParser is not None
        assert PPTXReader is not None
        assert ShapeExtractor is not None
        assert StyleExtractor is not None
        assert ThemeParser is not None
        assert TransformParser is not None

    def test_parser_integration(self) -> None:
        """Test that all parsers work together."""
        from backend.parser import PPTXReader

        reader = PPTXReader()

        # Verify internal parsers are initialized
        assert reader.shape_extractor.path_parser is not None
        assert reader.shape_extractor.transform_parser is not None
        assert reader.shape_extractor.style_extractor is not None
        assert reader.theme_parser is not None
