"""
test_brand_engine.py — Tests for brand engine functionality.

Tests:
- Brand preset lookup
- Color extraction from images
- Palette generation from primary color
- Color utility functions
- Palette contrast validation
"""

import pytest
import sys
from pathlib import Path
from io import BytesIO

# Add paths for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir.parent))

from backend.engine.brand_engine import (
    # Brand presets
    get_brand_preset,
    list_brand_presets,
    BRAND_PRESETS,
    # Color utilities
    hex_to_rgb,
    rgb_to_hex,
    hex_to_hsl,
    hsl_to_hex,
    get_luminance,
    get_contrast_text_color,
    # Palette generation
    generate_palette_from_primary,
    generate_monochromatic_palette,
    generate_complementary_palette,
    # Color extraction
    extract_colors_from_logo,
    create_palette_from_extracted_colors,
    # Validation
    validate_palette_contrast,
)
from backend.engine.data_models import ColorPalette


# =============================================================================
# BRAND PRESET TESTS
# =============================================================================

class TestBrandPresets:
    """Test brand preset functionality."""

    def test_get_brand_preset_microsoft(self):
        """Test Microsoft brand preset lookup."""
        palette = get_brand_preset("microsoft")
        assert palette is not None
        assert palette.primary == "#0078D4"

    def test_get_brand_preset_opentext(self):
        """Test OpenText brand preset lookup."""
        palette = get_brand_preset("opentext")
        assert palette is not None
        assert palette.primary == "#1B365D"

    def test_get_brand_preset_case_insensitive(self):
        """Test that brand lookup is case insensitive."""
        palette1 = get_brand_preset("Microsoft")
        palette2 = get_brand_preset("MICROSOFT")
        palette3 = get_brand_preset("microsoft")
        assert palette1 == palette2 == palette3

    def test_get_brand_preset_unknown(self):
        """Test unknown brand returns None."""
        palette = get_brand_preset("unknown_brand_xyz")
        assert palette is None

    def test_list_brand_presets(self):
        """Test listing all brand presets."""
        presets = list_brand_presets()
        assert len(presets) >= 10
        assert "microsoft" in presets
        assert "google" in presets
        assert "opentext" in presets
        assert "aws" in presets

    def test_all_presets_have_required_colors(self):
        """Test all presets have primary, secondary, tertiary, quaternary."""
        for name in list_brand_presets():
            palette = BRAND_PRESETS[name]
            assert palette.primary.startswith("#")
            assert palette.secondary.startswith("#")
            assert palette.tertiary.startswith("#")
            assert palette.quaternary.startswith("#")
            assert len(palette.primary) == 7  # #RRGGBB format


# =============================================================================
# COLOR UTILITY TESTS
# =============================================================================

class TestColorUtilities:
    """Test color conversion utilities."""

    def test_hex_to_rgb(self):
        """Test hex to RGB conversion."""
        assert hex_to_rgb("#FF0000") == (255, 0, 0)
        assert hex_to_rgb("#00FF00") == (0, 255, 0)
        assert hex_to_rgb("#0000FF") == (0, 0, 255)
        assert hex_to_rgb("#FFFFFF") == (255, 255, 255)
        assert hex_to_rgb("#000000") == (0, 0, 0)

    def test_hex_to_rgb_lowercase(self):
        """Test hex to RGB with lowercase."""
        assert hex_to_rgb("#ff0000") == (255, 0, 0)

    def test_rgb_to_hex(self):
        """Test RGB to hex conversion."""
        assert rgb_to_hex(255, 0, 0) == "#FF0000"
        assert rgb_to_hex(0, 255, 0) == "#00FF00"
        assert rgb_to_hex(0, 0, 255) == "#0000FF"

    def test_hex_rgb_roundtrip(self):
        """Test hex -> RGB -> hex roundtrip."""
        colors = ["#0078D4", "#1B365D", "#FF9900", "#4285F4"]
        for color in colors:
            r, g, b = hex_to_rgb(color)
            result = rgb_to_hex(r, g, b)
            assert result.upper() == color.upper()

    def test_hex_to_hsl(self):
        """Test hex to HSL conversion."""
        # Red should have hue ~0
        h, s, l = hex_to_hsl("#FF0000")
        assert abs(h) < 1 or abs(h - 360) < 1  # Hue near 0 or 360
        assert s > 0.9  # High saturation
        assert abs(l - 0.5) < 0.1  # Lightness around 0.5

    def test_hsl_to_hex(self):
        """Test HSL to hex conversion."""
        # Pure red
        result = hsl_to_hex(0, 1.0, 0.5)
        assert result.upper() == "#FF0000"

    def test_get_luminance(self):
        """Test luminance calculation."""
        # White should have high luminance
        assert get_luminance("#FFFFFF") > 0.9
        # Black should have low luminance
        assert get_luminance("#000000") < 0.1

    def test_get_contrast_text_color(self):
        """Test contrast text color selection."""
        # Dark backgrounds should get white text
        assert get_contrast_text_color("#000000") == "#FFFFFF"
        assert get_contrast_text_color("#1B365D") == "#FFFFFF"
        # Light backgrounds should get dark text
        assert get_contrast_text_color("#FFFFFF") == "#333333"
        assert get_contrast_text_color("#F5F5F5") == "#333333"


# =============================================================================
# PALETTE GENERATION TESTS
# =============================================================================

class TestPaletteGeneration:
    """Test palette generation from primary colors."""

    def test_generate_palette_from_primary(self):
        """Test generating full palette from primary color."""
        palette = generate_palette_from_primary("#0078D4")

        assert palette.primary == "#0078D4"
        assert palette.secondary != palette.primary
        assert palette.tertiary != palette.primary
        assert palette.quaternary != palette.primary
        assert palette.background == "#FFFFFF"
        assert palette.text_dark == "#333333"

    def test_generate_palette_has_valid_colors(self):
        """Test all generated colors are valid hex."""
        palette = generate_palette_from_primary("#FF5500")

        colors = [
            palette.primary, palette.secondary,
            palette.tertiary, palette.quaternary,
            palette.background, palette.text_dark,
            palette.text_light, palette.border, palette.connector
        ]

        for color in colors:
            assert color.startswith("#")
            assert len(color) == 7
            # Should be valid hex
            int(color[1:], 16)

    def test_generate_monochromatic_palette(self):
        """Test monochromatic palette generation."""
        palette = generate_monochromatic_palette("#0078D4")

        # All colors should have similar hue
        h1, _, _ = hex_to_hsl(palette.primary)
        h2, _, _ = hex_to_hsl(palette.secondary)
        h3, _, _ = hex_to_hsl(palette.tertiary)

        # Hue difference should be small (within 10 degrees)
        assert abs(h1 - h2) < 10 or abs(h1 - h2) > 350
        assert abs(h1 - h3) < 10 or abs(h1 - h3) > 350

    def test_generate_complementary_palette(self):
        """Test complementary palette generation."""
        palette = generate_complementary_palette("#0078D4")

        # Secondary should be roughly opposite hue (180 degrees)
        h1, _, _ = hex_to_hsl(palette.primary)
        h2, _, _ = hex_to_hsl(palette.secondary)

        hue_diff = abs(h1 - h2)
        # Should be near 180 degrees
        assert 150 < hue_diff < 210 or hue_diff > 330


# =============================================================================
# COLOR EXTRACTION TESTS
# =============================================================================

class TestColorExtraction:
    """Test color extraction from images."""

    def _create_solid_color_image(self, color: tuple, size: int = 100) -> bytes:
        """Create a solid color test image."""
        from PIL import Image
        img = Image.new('RGB', (size, size), color)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    def _create_two_color_image(self, color1: tuple, color2: tuple) -> bytes:
        """Create an image with two colors (left/right split)."""
        from PIL import Image
        img = Image.new('RGB', (100, 100))
        for x in range(100):
            for y in range(100):
                img.putpixel((x, y), color1 if x < 50 else color2)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    def test_extract_colors_solid_image(self):
        """Test extracting colors from solid color image."""
        # Create solid red image
        image_bytes = self._create_solid_color_image((255, 0, 0))
        colors = extract_colors_from_logo(image_bytes, k=3)

        # K-means may return fewer clusters if data doesn't support k
        assert len(colors) >= 1
        # Primary color should be close to red
        r, g, b = hex_to_rgb(colors[0])
        assert r > 200  # Should be predominantly red

    def test_extract_colors_two_colors(self):
        """Test extracting colors from two-color image."""
        # Create image with red and blue
        image_bytes = self._create_two_color_image((255, 0, 0), (0, 0, 255))
        colors = extract_colors_from_logo(image_bytes, k=2)

        assert len(colors) == 2
        # Should find both red and blue

    def test_extract_colors_returns_hex(self):
        """Test that extracted colors are valid hex strings."""
        image_bytes = self._create_solid_color_image((100, 150, 200))
        colors = extract_colors_from_logo(image_bytes, k=3)

        for color in colors:
            assert color.startswith("#")
            assert len(color) == 7

    def test_create_palette_from_extracted_colors(self):
        """Test creating palette from extracted colors."""
        colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00"]
        palette = create_palette_from_extracted_colors(colors)

        assert isinstance(palette, ColorPalette)
        assert palette.primary == "#FF0000"
        assert palette.secondary == "#00FF00"
        assert palette.tertiary == "#0000FF"
        assert palette.quaternary == "#FFFF00"

    def test_create_palette_from_single_color(self):
        """Test creating palette from single color (should cycle)."""
        colors = ["#FF0000"]
        palette = create_palette_from_extracted_colors(colors)

        assert isinstance(palette, ColorPalette)
        assert palette.primary == "#FF0000"


# =============================================================================
# PALETTE VALIDATION TESTS
# =============================================================================

class TestPaletteValidation:
    """Test palette contrast validation."""

    def test_validate_good_contrast(self):
        """Test that good contrast palette passes validation."""
        palette = ColorPalette(
            primary="#0078D4",
            secondary="#00A3E0",
            tertiary="#6CC24A",
            quaternary="#FFB81C",
            background="#FFFFFF",
            text_dark="#333333",
            text_light="#FFFFFF",
        )
        warnings = validate_palette_contrast(palette)
        # Should have no warnings about text contrast
        text_warnings = [w for w in warnings if "text_dark" in w.lower()]
        assert len(text_warnings) == 0

    def test_validate_poor_contrast(self):
        """Test that poor contrast is flagged."""
        palette = ColorPalette(
            primary="#CCCCCC",
            secondary="#DDDDDD",  # Very similar to primary
            tertiary="#EEEEEE",
            quaternary="#F0F0F0",
            background="#FFFFFF",
            text_dark="#CCCCCC",  # Poor contrast with white background
            text_light="#FFFFFF",
        )
        warnings = validate_palette_contrast(palette)
        # Should have warnings
        assert len(warnings) > 0


# =============================================================================
# RUN TESTS
# =============================================================================

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Brand Engine Tests")
    print("=" * 60 + "\n")

    # Run with pytest if available, otherwise basic test runner
    try:
        import pytest
        sys.exit(pytest.main([__file__, "-v"]))
    except ImportError:
        # Basic test runner
        test_classes = [
            TestBrandPresets,
            TestColorUtilities,
            TestPaletteGeneration,
            TestColorExtraction,
            TestPaletteValidation,
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
        return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
