"""Tests for the creativity engine."""

import pytest

from backend.creativity.operators import (
    VariationParams,
    PaletteVariation,
    TaperVariation,
    ScaleVariation,
    SpacingVariation,
    AccentStyleVariation,
    DepthVariation,
    CornerRadiusVariation,
    LabelPlacementVariation,
    OrientationVariation,
    AlignmentVariation,
)
from backend.creativity.constraints import (
    BrandConstraintChecker,
    BrandGuidelines,
)
from backend.creativity.sampling import VariationSampler, SamplingConfig
from backend.creativity.variation_engine import VariationEngine


# Test DSL fixture
@pytest.fixture
def sample_dsl():
    """Create a sample DSL for testing."""
    return {
        "archetype": "funnel",
        "canvas": {"width": 960, "height": 540},
        "theme": {
            "accent1": "#0D9488",
            "accent2": "#14B8A6",
            "accent3": "#2DD4BF",
            "accent4": "#5EEAD4",
            "accent5": "#99F6E4",
            "accent6": "#CCFBF1",
        },
        "shapes": [
            {
                "id": "shape1",
                "bbox": {"x": 180, "y": 50, "width": 600, "height": 60},
                "fill": {"type": "solid", "color": "accent1"},
                "text": {"content": "Awareness", "font_family": "Inter"},
            },
            {
                "id": "shape2",
                "bbox": {"x": 230, "y": 120, "width": 500, "height": 60},
                "fill": {"type": "solid", "color": "accent2"},
                "text": {"content": "Interest", "font_family": "Inter"},
            },
            {
                "id": "shape3",
                "bbox": {"x": 280, "y": 190, "width": 400, "height": 60},
                "fill": {"type": "solid", "color": "accent3"},
                "text": {"content": "Decision", "font_family": "Inter"},
            },
            {
                "id": "shape4",
                "bbox": {"x": 330, "y": 260, "width": 300, "height": 60},
                "fill": {"type": "solid", "color": "accent4"},
                "text": {"content": "Action", "font_family": "Inter"},
            },
        ],
    }


class TestPaletteVariation:
    """Tests for palette variation operator."""

    def test_hue_shift(self, sample_dsl):
        """Test hue shift mode."""
        op = PaletteVariation()
        params = VariationParams(
            intensity=0.5,
            seed=42,
            extra={"mode": "hue_shift"},
        )

        result = op.apply(sample_dsl, params)

        # Theme should have new colors
        assert result["theme"]["accent1"] != sample_dsl["theme"]["accent1"]

    def test_preset_palette(self, sample_dsl):
        """Test preset palette mode."""
        op = PaletteVariation()
        params = VariationParams(
            intensity=0.5,
            extra={"mode": "preset", "preset": "sunset"},
        )

        result = op.apply(sample_dsl, params)

        # Should have sunset palette colors
        assert result["theme"]["accent1"] == "#F97316"

    def test_monochromatic(self, sample_dsl):
        """Test monochromatic mode."""
        op = PaletteVariation()
        params = VariationParams(
            intensity=0.5,
            extra={"mode": "monochromatic", "base_color": "#0000FF"},
        )

        result = op.apply(sample_dsl, params)

        # All colors should be variations of blue
        for i in range(1, 7):
            color = result["theme"][f"accent{i}"]
            # Blue channel should dominate
            assert color.startswith("#")


class TestGeometryOperators:
    """Tests for geometry variation operators."""

    def test_taper_variation(self, sample_dsl):
        """Test taper variation."""
        op = TaperVariation()
        params = VariationParams(intensity=0.8, seed=42)

        result = op.apply(sample_dsl, params)

        # Widths should be modified
        original_widths = [s["bbox"]["width"] for s in sample_dsl["shapes"]]
        new_widths = [s["bbox"]["width"] for s in result["shapes"]]

        # At least some widths should change
        assert original_widths != new_widths

    def test_scale_uniform(self, sample_dsl):
        """Test uniform scaling."""
        op = ScaleVariation()
        params = VariationParams(
            intensity=0.5,
            seed=42,
            extra={"mode": "uniform"},
        )

        result = op.apply(sample_dsl, params)

        # Shapes should be scaled
        assert len(result["shapes"]) == len(sample_dsl["shapes"])

    def test_spacing_variation(self, sample_dsl):
        """Test spacing variation."""
        op = SpacingVariation()
        params = VariationParams(intensity=0.5, seed=42)

        result = op.apply(sample_dsl, params)

        # Y positions should be modified (vertical arrangement)
        original_y = [s["bbox"]["y"] for s in sample_dsl["shapes"]]
        new_y = [s["bbox"]["y"] for s in result["shapes"]]

        # At least some positions should change
        assert original_y != new_y


class TestStyleOperators:
    """Tests for style variation operators."""

    def test_accent_style(self, sample_dsl):
        """Test accent style variation."""
        op = AccentStyleVariation()
        params = VariationParams(
            intensity=0.7,
            extra={"style": "glow"},
        )

        result = op.apply(sample_dsl, params)

        # Shapes should have glow effect
        for shape in result["shapes"]:
            assert "glow" in shape.get("effects", {})

    def test_depth_variation(self, sample_dsl):
        """Test depth variation."""
        op = DepthVariation()
        params = VariationParams(
            intensity=0.8,
            extra={"preset": "elevated"},
        )

        result = op.apply(sample_dsl, params)

        # Shapes should have shadow effect
        for shape in result["shapes"]:
            assert "shadow" in shape.get("effects", {})

    def test_corner_radius(self, sample_dsl):
        """Test corner radius variation."""
        op = CornerRadiusVariation()
        params = VariationParams(
            intensity=1.0,
            extra={"preset": "pill"},
        )

        result = op.apply(sample_dsl, params)

        # Shapes should have pill corners
        for shape in result["shapes"]:
            assert shape.get("corner_radius") == "50%"


class TestLayoutOperators:
    """Tests for layout variation operators."""

    def test_label_placement(self, sample_dsl):
        """Test label placement variation."""
        op = LabelPlacementVariation()
        params = VariationParams(
            intensity=0.5,
            extra={"placement": "callout_right"},
        )

        result = op.apply(sample_dsl, params)

        # Text should have new placement
        for shape in result["shapes"]:
            text = shape.get("text", {})
            assert text.get("placement") == "callout_right"

    def test_alignment_variation(self, sample_dsl):
        """Test alignment variation."""
        op = AlignmentVariation()
        params = VariationParams(
            intensity=0.5,
            extra={"alignment": "left"},
        )

        result = op.apply(sample_dsl, params)

        # Shapes should be left-aligned
        for shape in result["shapes"]:
            assert shape["bbox"]["x"] == 50  # Left margin


class TestBrandConstraintChecker:
    """Tests for brand constraint checker."""

    def test_check_valid_dsl(self, sample_dsl):
        """Test checking valid DSL."""
        checker = BrandConstraintChecker(BrandGuidelines())
        result = checker.check(sample_dsl)

        assert result.is_valid
        assert result.error_count == 0

    def test_forbidden_colors(self, sample_dsl):
        """Test forbidden color detection."""
        guidelines = BrandGuidelines(
            forbidden_colors=["#FF0000"],
        )
        checker = BrandConstraintChecker(guidelines)

        # Add forbidden color to DSL
        sample_dsl["shapes"][0]["fill"]["color"] = "#FF0000"

        result = checker.check(sample_dsl)

        assert not result.is_valid
        assert result.error_count > 0

    def test_allowed_fonts(self, sample_dsl):
        """Test font restriction enforcement."""
        guidelines = BrandGuidelines(
            allowed_fonts=["Roboto"],
        )
        checker = BrandConstraintChecker(guidelines)

        result = checker.check(sample_dsl)

        # Inter is not in allowed fonts
        assert result.error_count > 0

    def test_enforce_constraints(self, sample_dsl):
        """Test constraint enforcement."""
        guidelines = BrandGuidelines(
            allowed_fonts=["Roboto"],
        )
        checker = BrandConstraintChecker(guidelines)

        fixed_dsl, result = checker.enforce(sample_dsl)

        # Font should be fixed
        assert fixed_dsl.get("font_family") == "Roboto"

    def test_shadow_restriction(self, sample_dsl):
        """Test shadow restriction."""
        guidelines = BrandGuidelines(allow_shadows=False)
        checker = BrandConstraintChecker(guidelines)

        # Add shadow to shape
        sample_dsl["shapes"][0]["effects"] = {"shadow": {"blur": 10}}

        result = checker.check(sample_dsl)

        assert result.error_count > 0


class TestVariationSampler:
    """Tests for variation sampler."""

    def test_random_sampling(self, sample_dsl):
        """Test random sampling."""
        operators = [
            PaletteVariation(),
            TaperVariation(),
            DepthVariation(),
        ]
        config = SamplingConfig(num_variations=5, seed=42)
        sampler = VariationSampler(operators, config)

        samples = sampler.sample_random(sample_dsl, 5)

        assert len(samples) == 5
        for op_name, params in samples:
            assert isinstance(params, VariationParams)

    def test_diverse_sampling(self, sample_dsl):
        """Test diverse sampling."""
        operators = [
            PaletteVariation(),
            TaperVariation(),
            DepthVariation(),
            AccentStyleVariation(),
        ]
        config = SamplingConfig(diversity=0.8, seed=42)
        sampler = VariationSampler(operators, config)

        samples = sampler.sample_diverse(sample_dsl, 4)

        # Should have variety of operators
        op_names = [s[0] for s in samples]
        assert len(set(op_names)) >= 2  # At least 2 different operators

    def test_combination_sampling(self, sample_dsl):
        """Test combination sampling."""
        operators = [
            PaletteVariation(),
            DepthVariation(),
            CornerRadiusVariation(),
        ]
        config = SamplingConfig(seed=42)
        sampler = VariationSampler(operators, config)

        combos = sampler.sample_combination(sample_dsl, operators_per_variation=2, count=3)

        assert len(combos) == 3
        for combo in combos:
            assert len(combo) == 2


class TestVariationEngine:
    """Tests for variation engine."""

    def test_single_variation(self, sample_dsl):
        """Test applying single variation."""
        engine = VariationEngine()
        result = engine.apply_variation(sample_dsl, "palette")

        assert result.dsl is not None
        assert "palette" in result.operators_applied
        assert result.is_valid

    def test_variation_chain(self, sample_dsl):
        """Test applying variation chain."""
        engine = VariationEngine()
        operations = [
            ("palette", VariationParams(intensity=0.5, extra={"mode": "preset", "preset": "ocean"})),
            ("depth", VariationParams(intensity=0.6, extra={"preset": "soft"})),
        ]

        result = engine.apply_chain(sample_dsl, operations)

        assert len(result.operators_applied) == 2
        assert result.is_valid

    def test_generate_variations(self, sample_dsl):
        """Test generating multiple variations."""
        engine = VariationEngine()
        results = engine.generate_variations(sample_dsl, count=3, strategy="diverse", seed=42)

        assert len(results) == 3
        for result in results:
            assert result.is_valid

    def test_preset_application(self, sample_dsl):
        """Test preset application."""
        engine = VariationEngine()
        result = engine.apply_preset(sample_dsl, "modern")

        assert result.is_valid
        assert len(result.operators_applied) >= 2

    def test_available_operators(self, sample_dsl):
        """Test getting available operators."""
        engine = VariationEngine()
        available = engine.get_available_operators(sample_dsl)

        # Taper should be available for funnel
        assert "taper" in available
        # Palette should always be available
        assert "palette" in available

    def test_brand_constraint_enforcement(self, sample_dsl):
        """Test brand constraints are enforced."""
        guidelines = BrandGuidelines(
            primary_colors=["#0D9488"],
            allow_shadows=True,
        )
        engine = VariationEngine(brand_guidelines=guidelines)

        result = engine.apply_variation(
            sample_dsl,
            "depth",
            VariationParams(intensity=0.8),
        )

        # Should still be valid after constraint enforcement
        assert result.is_valid
