"""Tests for DSL schema models."""

import pytest
from pydantic import ValidationError

from backend.dsl.schema import (
    BoundingBox,
    Canvas,
    Effects,
    EMU_PER_INCH,
    GenerateRequest,
    GradientFill,
    GradientStop,
    NoFill,
    Shape,
    ShapeType,
    SlideScene,
    SolidFill,
    Stroke,
    TextContent,
    TextRun,
    ThemeColors,
    Transform,
)


class TestBoundingBox:
    """Tests for BoundingBox model."""

    def test_create_bounding_box(self) -> None:
        """Test creating a bounding box."""
        bbox = BoundingBox(x=100, y=200, width=300, height=400)
        assert bbox.x == 100
        assert bbox.y == 200
        assert bbox.width == 300
        assert bbox.height == 400

    def test_computed_properties(self) -> None:
        """Test computed properties."""
        bbox = BoundingBox(x=100, y=200, width=300, height=400)
        assert bbox.right == 400
        assert bbox.bottom == 600
        assert bbox.center_x == 250
        assert bbox.center_y == 400

    def test_to_inches(self) -> None:
        """Test conversion to inches."""
        bbox = BoundingBox(x=EMU_PER_INCH, y=EMU_PER_INCH * 2, width=EMU_PER_INCH, height=EMU_PER_INCH)
        inches = bbox.to_inches()
        assert inches["x"] == 1.0
        assert inches["y"] == 2.0
        assert inches["width"] == 1.0
        assert inches["height"] == 1.0

    def test_width_must_be_non_negative(self) -> None:
        """Test width validation."""
        with pytest.raises(ValidationError):
            BoundingBox(x=0, y=0, width=-100, height=100)


class TestTransform:
    """Tests for Transform model."""

    def test_default_transform(self) -> None:
        """Test default transform values."""
        transform = Transform()
        assert transform.rotation == 0.0
        assert transform.flip_h is False
        assert transform.flip_v is False
        assert transform.scale_x == 1.0
        assert transform.scale_y == 1.0

    def test_rotation_bounds(self) -> None:
        """Test rotation stays within bounds."""
        transform = Transform(rotation=180.0)
        assert transform.rotation == 180.0

        with pytest.raises(ValidationError):
            Transform(rotation=400.0)


class TestFills:
    """Tests for fill models."""

    def test_solid_fill(self) -> None:
        """Test solid fill creation."""
        fill = SolidFill(color="#0D9488")
        assert fill.type == "solid"
        assert fill.color == "#0D9488"
        assert fill.alpha == 1.0

    def test_gradient_fill(self) -> None:
        """Test gradient fill creation."""
        fill = GradientFill(
            stops=[
                GradientStop(position=0.0, color="#0D9488"),
                GradientStop(position=1.0, color="#14B8A6"),
            ]
        )
        assert fill.type == "gradient"
        assert len(fill.stops) == 2

    def test_gradient_requires_two_stops(self) -> None:
        """Test gradient requires at least 2 stops."""
        with pytest.raises(ValidationError):
            GradientFill(stops=[GradientStop(position=0.0, color="#0D9488")])

    def test_no_fill(self) -> None:
        """Test no fill creation."""
        fill = NoFill()
        assert fill.type == "none"


class TestShape:
    """Tests for Shape model."""

    def test_create_auto_shape(self) -> None:
        """Test creating an auto shape."""
        shape = Shape(
            id="shape_1",
            type=ShapeType.AUTO_SHAPE,
            bbox=BoundingBox(x=0, y=0, width=1000, height=500),
            auto_shape_type="roundRect",
            fill=SolidFill(color="#0D9488"),
        )
        assert shape.id == "shape_1"
        assert shape.type == ShapeType.AUTO_SHAPE
        assert shape.auto_shape_type == "roundRect"

    def test_shape_with_text(self) -> None:
        """Test shape with text content."""
        shape = Shape(
            id="shape_2",
            type=ShapeType.AUTO_SHAPE,
            bbox=BoundingBox(x=0, y=0, width=1000, height=500),
            text=TextContent(
                runs=[TextRun(text="Hello World", font_size=1800, bold=True)]
            ),
        )
        assert shape.text is not None
        assert len(shape.text.runs) == 1
        assert shape.text.runs[0].text == "Hello World"


class TestSlideScene:
    """Tests for SlideScene model."""

    def test_create_empty_scene(self) -> None:
        """Test creating an empty scene."""
        scene = SlideScene()
        assert scene.canvas.width == 12192000  # 16:9 default
        assert scene.canvas.height == 6858000
        assert len(scene.shapes) == 0

    def test_create_scene_with_shapes(self, sample_slide_scene: dict) -> None:
        """Test creating a scene with shapes."""
        scene = SlideScene(**sample_slide_scene)
        assert len(scene.shapes) == 1
        assert scene.shapes[0].id == "shape_1_abc123"

    def test_get_shape_by_id(self, sample_slide_scene: dict) -> None:
        """Test finding a shape by ID."""
        scene = SlideScene(**sample_slide_scene)
        shape = scene.get_shape_by_id("shape_1_abc123")
        assert shape is not None
        assert shape.name == "Rectangle 1"

        missing = scene.get_shape_by_id("nonexistent")
        assert missing is None


class TestGenerateRequest:
    """Tests for GenerateRequest model."""

    def test_valid_request(self) -> None:
        """Test valid generate request."""
        request = GenerateRequest(prompt="Create a sales funnel with 5 stages")
        assert request.prompt == "Create a sales funnel with 5 stages"
        assert request.variations == 1

    def test_prompt_required(self) -> None:
        """Test prompt is required."""
        with pytest.raises(ValidationError):
            GenerateRequest(prompt="")

    def test_variations_bounds(self) -> None:
        """Test variations within bounds."""
        request = GenerateRequest(prompt="test", variations=5)
        assert request.variations == 5

        with pytest.raises(ValidationError):
            GenerateRequest(prompt="test", variations=0)

        with pytest.raises(ValidationError):
            GenerateRequest(prompt="test", variations=20)

    def test_color_scheme_limit(self) -> None:
        """Test color scheme limited to 6 colors."""
        request = GenerateRequest(
            prompt="test",
            color_scheme=["#000000", "#111111", "#222222"],
        )
        assert len(request.color_scheme) == 3
