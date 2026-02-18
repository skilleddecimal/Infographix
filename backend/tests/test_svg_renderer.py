"""
test_svg_renderer.py — Tests for SVG renderer functionality.

Tests:
- SVG generation from PositionedLayout
- Element rendering (blocks, bands, titles)
- Connector rendering with arrow markers
- Text rendering
- Data URI generation
"""

import pytest
import sys
import re
from pathlib import Path
from xml.etree import ElementTree as ET

# Add paths for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir.parent))

from backend.engine.svg_renderer import (
    SVGRenderer,
    render_to_svg,
    render_to_svg_string,
    render_to_data_uri,
    inches_to_px,
    pt_to_px,
)
from backend.engine.positioned import (
    PositionedLayout,
    PositionedElement,
    PositionedConnector,
    PositionedText,
    ElementType,
    ConnectorStyle,
    TextAlignment,
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_simple_layout() -> PositionedLayout:
    """Create a simple test layout with one block."""
    text = PositionedText(
        content="Test Block",
        lines=["Test Block"],
        font_size_pt=14,
        font_family="Calibri",
    )

    block = PositionedElement(
        id="block1",
        element_type=ElementType.BLOCK,
        x_inches=1.0,
        y_inches=1.0,
        width_inches=2.0,
        height_inches=1.0,
        fill_color="#0073E6",
        stroke_color="#005BB5",
        stroke_width_pt=1.5,
        corner_radius_inches=0.08,
        text=text,
    )

    return PositionedLayout(
        slide_width_inches=13.333,
        slide_height_inches=7.5,
        background_color="#FFFFFF",
        elements=[block],
    )


def create_layout_with_connectors() -> PositionedLayout:
    """Create a layout with blocks and connectors."""
    block1 = PositionedElement(
        id="block1",
        element_type=ElementType.BLOCK,
        x_inches=1.0,
        y_inches=1.0,
        width_inches=2.0,
        height_inches=1.0,
        fill_color="#0073E6",
    )

    block2 = PositionedElement(
        id="block2",
        element_type=ElementType.BLOCK,
        x_inches=5.0,
        y_inches=1.0,
        width_inches=2.0,
        height_inches=1.0,
        fill_color="#00A3E0",
    )

    connector = PositionedConnector(
        id="conn1",
        start_x=3.0,
        start_y=1.5,
        end_x=5.0,
        end_y=1.5,
        style=ConnectorStyle.ARROW,
        color="#666666",
        stroke_width_pt=1.5,
        from_element_id="block1",
        to_element_id="block2",
    )

    return PositionedLayout(
        slide_width_inches=13.333,
        slide_height_inches=7.5,
        elements=[block1, block2],
        connectors=[connector],
    )


def parse_svg(svg_str: str) -> ET.Element:
    """Parse SVG string to ElementTree element."""
    # Remove XML declaration for parsing
    svg_str = re.sub(r'<\?xml[^?]*\?>\s*', '', svg_str)
    return ET.fromstring(svg_str)


# =============================================================================
# BASIC RENDERING TESTS
# =============================================================================

class TestSVGRendererBasic:
    """Test basic SVG rendering functionality."""

    def test_render_returns_string(self):
        """Test that render returns an SVG string."""
        layout = create_simple_layout()
        renderer = SVGRenderer()
        svg = renderer.render(layout)

        assert isinstance(svg, str)
        assert svg.startswith('<?xml')
        assert '<svg' in svg
        assert '</svg>' in svg

    def test_render_has_correct_dimensions(self):
        """Test that SVG has correct width and height."""
        layout = create_simple_layout()
        renderer = SVGRenderer()
        svg = renderer.render(layout)
        root = parse_svg(svg)

        width = float(root.get('width').replace('px', ''))
        height = float(root.get('height').replace('px', ''))

        expected_width = inches_to_px(13.333)
        expected_height = inches_to_px(7.5)

        assert abs(width - expected_width) < 1
        assert abs(height - expected_height) < 1

    def test_render_has_viewbox(self):
        """Test that SVG has a viewBox."""
        layout = create_simple_layout()
        renderer = SVGRenderer()
        svg = renderer.render(layout)
        root = parse_svg(svg)

        viewbox = root.get('viewBox')
        assert viewbox is not None
        assert viewbox.startswith('0 0')

    def test_render_has_background_rect(self):
        """Test that SVG has a background rectangle."""
        layout = create_simple_layout()
        renderer = SVGRenderer()
        svg = renderer.render(layout)
        root = parse_svg(svg)

        # Find background rect (first rect child)
        rects = root.findall('.//{http://www.w3.org/2000/svg}rect')
        assert len(rects) >= 1

        bg_rect = rects[0]
        assert bg_rect.get('fill') == '#FFFFFF'


# =============================================================================
# ELEMENT RENDERING TESTS
# =============================================================================

class TestElementRendering:
    """Test element rendering (blocks, bands, etc.)."""

    def test_render_block(self):
        """Test rendering a block element."""
        layout = create_simple_layout()
        renderer = SVGRenderer()
        svg = renderer.render(layout)
        root = parse_svg(svg)

        # Find block group
        blocks_group = root.find('.//{http://www.w3.org/2000/svg}g[@id="blocks"]')
        assert blocks_group is not None

        # Find block rect
        rects = blocks_group.findall('.//{http://www.w3.org/2000/svg}rect')
        assert len(rects) >= 1

    def test_render_block_with_correct_fill(self):
        """Test that block has correct fill color."""
        layout = create_simple_layout()
        renderer = SVGRenderer()
        svg = renderer.render(layout)

        # Check for the blue fill color
        assert '#0073E6' in svg

    def test_render_block_with_rounded_corners(self):
        """Test that block has rounded corners (rx/ry)."""
        layout = create_simple_layout()
        renderer = SVGRenderer()
        svg = renderer.render(layout)
        root = parse_svg(svg)

        blocks_group = root.find('.//{http://www.w3.org/2000/svg}g[@id="blocks"]')
        rect = blocks_group.find('.//{http://www.w3.org/2000/svg}rect')

        rx = rect.get('rx')
        ry = rect.get('ry')

        assert rx is not None
        assert ry is not None
        assert float(rx) > 0

    def test_render_band(self):
        """Test rendering a band element."""
        band = PositionedElement(
            id="band1",
            element_type=ElementType.BAND,
            x_inches=0.0,
            y_inches=2.0,
            width_inches=13.333,
            height_inches=0.6,
            fill_color="#E3F2FD",
            opacity=0.8,
        )

        layout = PositionedLayout(
            slide_width_inches=13.333,
            slide_height_inches=7.5,
            elements=[band],
        )

        renderer = SVGRenderer()
        svg = renderer.render(layout)

        # Band should be in bands group
        assert 'band-band1' in svg


# =============================================================================
# CONNECTOR RENDERING TESTS
# =============================================================================

class TestConnectorRendering:
    """Test connector rendering."""

    def test_render_connector(self):
        """Test rendering a connector."""
        layout = create_layout_with_connectors()
        renderer = SVGRenderer()
        svg = renderer.render(layout)

        # Connector should have a line element
        assert '<line' in svg

    def test_render_connector_with_arrow(self):
        """Test connector has arrow marker."""
        layout = create_layout_with_connectors()
        renderer = SVGRenderer()
        svg = renderer.render(layout)

        # Should have arrow marker defined
        assert 'arrowhead' in svg
        assert 'marker-end' in svg

    def test_render_dashed_connector(self):
        """Test dashed connector style."""
        connector = PositionedConnector(
            id="conn1",
            start_x=1.0,
            start_y=1.0,
            end_x=3.0,
            end_y=1.0,
            style=ConnectorStyle.DASHED,
            color="#666666",
        )

        layout = PositionedLayout(
            slide_width_inches=13.333,
            slide_height_inches=7.5,
            connectors=[connector],
        )

        renderer = SVGRenderer()
        svg = renderer.render(layout)

        assert 'stroke-dasharray' in svg

    def test_render_bidirectional_connector(self):
        """Test bidirectional connector has arrows at both ends."""
        connector = PositionedConnector(
            id="conn1",
            start_x=1.0,
            start_y=1.0,
            end_x=3.0,
            end_y=1.0,
            style=ConnectorStyle.BIDIRECTIONAL,
            color="#666666",
        )

        layout = PositionedLayout(
            slide_width_inches=13.333,
            slide_height_inches=7.5,
            connectors=[connector],
        )

        renderer = SVGRenderer()
        svg = renderer.render(layout)

        assert 'marker-start' in svg
        assert 'marker-end' in svg


# =============================================================================
# TEXT RENDERING TESTS
# =============================================================================

class TestTextRendering:
    """Test text rendering."""

    def test_render_text_in_block(self):
        """Test that block text is rendered."""
        layout = create_simple_layout()
        renderer = SVGRenderer()
        svg = renderer.render(layout)

        assert 'Test Block' in svg
        assert '<text' in svg

    def test_render_multiline_text(self):
        """Test multiline text rendering."""
        text = PositionedText(
            content="Line 1\nLine 2",
            lines=["Line 1", "Line 2"],
            font_size_pt=14,
            font_family="Calibri",
        )

        block = PositionedElement(
            id="block1",
            element_type=ElementType.BLOCK,
            x_inches=1.0,
            y_inches=1.0,
            width_inches=2.0,
            height_inches=1.5,
            fill_color="#0073E6",
            text=text,
        )

        layout = PositionedLayout(
            slide_width_inches=13.333,
            slide_height_inches=7.5,
            elements=[block],
        )

        renderer = SVGRenderer()
        svg = renderer.render(layout)

        assert 'Line 1' in svg
        assert 'Line 2' in svg
        assert '<tspan' in svg  # Should use tspan for multiline

    def test_render_title(self):
        """Test title rendering."""
        title_text = PositionedText(
            content="Test Title",
            lines=["Test Title"],
            font_size_pt=28,
            font_family="Calibri",
            bold=True,
        )

        title = PositionedElement(
            id="title",
            element_type=ElementType.TITLE,
            x_inches=0.6,
            y_inches=0.5,
            width_inches=12.0,
            height_inches=0.9,
            fill_color="transparent",
            text=title_text,
        )

        layout = PositionedLayout(
            slide_width_inches=13.333,
            slide_height_inches=7.5,
            title=title,
        )

        renderer = SVGRenderer()
        svg = renderer.render(layout)

        assert 'Test Title' in svg
        assert 'font-weight' in svg and 'bold' in svg


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================

class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_render_to_svg(self):
        """Test render_to_svg function."""
        layout = create_simple_layout()
        svg = render_to_svg(layout)

        assert isinstance(svg, str)
        assert '<svg' in svg

    def test_render_to_svg_string(self):
        """Test render_to_svg_string function."""
        layout = create_simple_layout()
        svg = render_to_svg_string(layout, include_fonts=False)

        assert isinstance(svg, str)
        assert '<svg' in svg

    def test_render_to_data_uri(self):
        """Test render_to_data_uri function."""
        layout = create_simple_layout()
        data_uri = render_to_data_uri(layout)

        assert data_uri.startswith('data:image/svg+xml;base64,')
        # Should be decodable
        import base64
        b64_content = data_uri.split(',')[1]
        decoded = base64.b64decode(b64_content)
        assert b'<svg' in decoded


# =============================================================================
# UNIT CONVERSION TESTS
# =============================================================================

class TestUnitConversion:
    """Test unit conversion functions."""

    def test_inches_to_px(self):
        """Test inches to pixels conversion (96 DPI)."""
        assert inches_to_px(1.0) == 96.0
        assert inches_to_px(0.5) == 48.0
        assert inches_to_px(2.0) == 192.0

    def test_pt_to_px(self):
        """Test points to pixels conversion."""
        # 72 points = 1 inch = 96 pixels
        # So 1 point = 96/72 = 1.333... pixels
        result = pt_to_px(72)
        assert abs(result - 96.0) < 0.1

        result = pt_to_px(12)
        assert abs(result - 16.0) < 0.1


# =============================================================================
# FILE OUTPUT TESTS
# =============================================================================

class TestFileOutput:
    """Test file output functionality."""

    def test_render_to_file(self, tmp_path):
        """Test rendering directly to a file."""
        layout = create_simple_layout()
        renderer = SVGRenderer()

        output_file = tmp_path / "test_output.svg"
        renderer.render_to_file(layout, output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert '<svg' in content
        assert 'Test Block' in content


# =============================================================================
# RUN TESTS
# =============================================================================

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SVG Renderer Tests")
    print("=" * 60 + "\n")

    try:
        import pytest
        sys.exit(pytest.main([__file__, "-v"]))
    except ImportError:
        # Basic test runner
        test_classes = [
            TestSVGRendererBasic,
            TestElementRendering,
            TestConnectorRendering,
            TestTextRendering,
            TestConvenienceFunctions,
            TestUnitConversion,
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
