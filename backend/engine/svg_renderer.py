"""
svg_renderer.py — SVG file generation from PositionedLayout.

This renderer consumes PositionedLayout and produces SVG strings/files.
It NEVER computes positions — that's the layout engine's job.
It only converts inches to pixels and creates SVG elements.

Used for:
1. Real-time preview in the frontend
2. Export to SVG format
3. Embedding in web pages
"""

import math
from pathlib import Path
from typing import Optional, Union, List
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element, SubElement

from .positioned import (
    PositionedLayout,
    PositionedElement,
    PositionedConnector,
    PositionedText,
    ElementType,
    ConnectorStyle,
    TextAlignment,
)


# =============================================================================
# CONSTANTS
# =============================================================================

# Standard screen DPI for conversion
DPI = 96

# SVG namespace
SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"


# =============================================================================
# CONVERSION HELPERS
# =============================================================================

def inches_to_px(inches: float) -> float:
    """Convert inches to pixels at 96 DPI."""
    return inches * DPI


def pt_to_px(pt: float) -> float:
    """Convert points to pixels."""
    return pt * (DPI / 72)


def format_px(value: float) -> str:
    """Format pixel value for SVG (2 decimal places)."""
    return f"{value:.2f}"


def escape_xml(text: str) -> str:
    """Escape special XML characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


# =============================================================================
# SVG RENDERER
# =============================================================================

class SVGRenderer:
    """
    Renders PositionedLayout to SVG format.

    The renderer is stateless — each render() call creates a new SVG.
    """

    def __init__(self, include_fonts: bool = True):
        """
        Initialize renderer.

        Args:
            include_fonts: Whether to include @font-face declarations
        """
        self.include_fonts = include_fonts

    def render(
        self,
        layout: PositionedLayout,
        output: Optional[Union[str, Path]] = None
    ) -> str:
        """
        Render a PositionedLayout to SVG format.

        Args:
            layout: The positioned layout to render
            output: Optional output path for file

        Returns:
            SVG content as string
        """
        # Calculate dimensions in pixels
        width_px = inches_to_px(layout.slide_width_inches)
        height_px = inches_to_px(layout.slide_height_inches)

        # Create root SVG element
        svg = Element('svg')
        svg.set('xmlns', SVG_NS)
        svg.set('xmlns:xlink', XLINK_NS)
        svg.set('width', format_px(width_px))
        svg.set('height', format_px(height_px))
        svg.set('viewBox', f"0 0 {format_px(width_px)} {format_px(height_px)}")

        # Add defs section for gradients, filters, markers
        defs = SubElement(svg, 'defs')
        self._add_defs(defs, layout)

        # Add style section
        if self.include_fonts:
            self._add_styles(svg)

        # Background
        bg = SubElement(svg, 'rect')
        bg.set('x', '0')
        bg.set('y', '0')
        bg.set('width', format_px(width_px))
        bg.set('height', format_px(height_px))
        bg.set('fill', layout.background_color)

        # Create groups for layering
        bands_group = SubElement(svg, 'g')
        bands_group.set('id', 'bands')

        blocks_group = SubElement(svg, 'g')
        blocks_group.set('id', 'blocks')

        connectors_group = SubElement(svg, 'g')
        connectors_group.set('id', 'connectors')

        text_group = SubElement(svg, 'g')
        text_group.set('id', 'text-overlays')

        # Render title and subtitle
        if layout.title:
            self._render_element(text_group, layout.title)
        if layout.subtitle:
            self._render_element(text_group, layout.subtitle)

        # Render elements sorted by z-order
        for element in layout.elements_sorted_by_z_order():
            if element.element_type == ElementType.BAND:
                self._render_element(bands_group, element)
            else:
                self._render_element(blocks_group, element)

        # Render connectors
        for connector in layout.connectors:
            self._render_connector(connectors_group, connector)

        # Generate SVG string
        ET.indent(svg, space="  ")
        svg_str = ET.tostring(svg, encoding='unicode')

        # Add XML declaration
        svg_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + svg_str

        # Write to file if output specified
        if output:
            output_path = Path(output)
            output_path.write_text(svg_str, encoding='utf-8')

        return svg_str

    def render_to_file(self, layout: PositionedLayout, filepath: Union[str, Path]) -> None:
        """
        Render layout directly to a file.

        Args:
            layout: The positioned layout to render
            filepath: Output file path
        """
        self.render(layout, output=filepath)

    # =========================================================================
    # DEFS SECTION (markers, filters)
    # =========================================================================

    def _add_defs(self, defs: Element, layout: PositionedLayout) -> None:
        """Add SVG defs (markers, filters, etc.)."""
        # Arrow marker for connectors
        marker = SubElement(defs, 'marker')
        marker.set('id', 'arrowhead')
        marker.set('markerWidth', '10')
        marker.set('markerHeight', '7')
        marker.set('refX', '9')
        marker.set('refY', '3.5')
        marker.set('orient', 'auto')
        marker.set('markerUnits', 'strokeWidth')

        arrow_path = SubElement(marker, 'polygon')
        arrow_path.set('points', '0 0, 10 3.5, 0 7')
        arrow_path.set('fill', 'context-stroke')

        # Reverse arrow marker for bidirectional
        marker_start = SubElement(defs, 'marker')
        marker_start.set('id', 'arrowhead-start')
        marker_start.set('markerWidth', '10')
        marker_start.set('markerHeight', '7')
        marker_start.set('refX', '1')
        marker_start.set('refY', '3.5')
        marker_start.set('orient', 'auto-start-reverse')
        marker_start.set('markerUnits', 'strokeWidth')

        arrow_path_start = SubElement(marker_start, 'polygon')
        arrow_path_start.set('points', '10 0, 0 3.5, 10 7')
        arrow_path_start.set('fill', 'context-stroke')

        # Drop shadow filter
        shadow = SubElement(defs, 'filter')
        shadow.set('id', 'drop-shadow')
        shadow.set('x', '-20%')
        shadow.set('y', '-20%')
        shadow.set('width', '140%')
        shadow.set('height', '140%')

        fe_offset = SubElement(shadow, 'feDropShadow')
        fe_offset.set('dx', '2')
        fe_offset.set('dy', '2')
        fe_offset.set('stdDeviation', '3')
        fe_offset.set('flood-color', '#000000')
        fe_offset.set('flood-opacity', '0.15')

    def _add_styles(self, svg: Element) -> None:
        """Add CSS styles for fonts and common properties."""
        style = SubElement(svg, 'style')
        style.text = """
            @import url('https://fonts.googleapis.com/css2?family=Calibri:wght@400;700&display=swap');

            text {
                font-family: 'Calibri', 'Segoe UI', 'DejaVu Sans', Arial, sans-serif;
            }
            .block-text {
                dominant-baseline: middle;
                text-anchor: middle;
            }
            .title-text {
                font-weight: 700;
            }
        """

    # =========================================================================
    # ELEMENT RENDERING
    # =========================================================================

    def _render_element(self, parent: Element, element: PositionedElement) -> None:
        """Render a single positioned element."""
        # Skip transparent fill elements without text (spacers)
        if element.fill_color == "transparent" and element.text is None:
            return

        # Convert to pixels
        x_px = inches_to_px(element.x_inches)
        y_px = inches_to_px(element.y_inches)
        width_px = inches_to_px(element.width_inches)
        height_px = inches_to_px(element.height_inches)

        # Choose rendering method based on element type
        if element.element_type == ElementType.TITLE:
            self._render_title(parent, element, x_px, y_px, width_px, height_px)
        elif element.element_type == ElementType.SUBTITLE:
            self._render_subtitle(parent, element, x_px, y_px, width_px, height_px)
        elif element.element_type == ElementType.BAND:
            self._render_band(parent, element, x_px, y_px, width_px, height_px)
        elif element.element_type == ElementType.LABEL:
            self._render_label(parent, element, x_px, y_px, width_px, height_px)
        elif element.element_type == ElementType.ELLIPSE:
            self._render_ellipse(parent, element, x_px, y_px, width_px, height_px)
        elif element.element_type == ElementType.TEXT_BOX:
            self._render_text_box(parent, element, x_px, y_px, width_px, height_px)
        else:
            self._render_block(parent, element, x_px, y_px, width_px, height_px)

    def _render_block(
        self,
        parent: Element,
        element: PositionedElement,
        x: float,
        y: float,
        width: float,
        height: float
    ) -> None:
        """Render a standard block (rounded rectangle)."""
        # Create group for block
        g = SubElement(parent, 'g')
        g.set('id', f'block-{element.id}')
        g.set('class', 'block')

        # Calculate corner radius
        corner_px = inches_to_px(element.corner_radius_inches)

        # Create rounded rectangle
        rect = SubElement(g, 'rect')
        rect.set('x', format_px(x))
        rect.set('y', format_px(y))
        rect.set('width', format_px(width))
        rect.set('height', format_px(height))
        rect.set('rx', format_px(corner_px))
        rect.set('ry', format_px(corner_px))

        # Fill
        if element.fill_color and element.fill_color != "transparent":
            rect.set('fill', element.fill_color)
        else:
            rect.set('fill', 'none')

        # Stroke
        if element.stroke_color:
            rect.set('stroke', element.stroke_color)
            rect.set('stroke-width', format_px(pt_to_px(element.stroke_width_pt)))
        else:
            rect.set('stroke', 'none')

        # Opacity
        if element.opacity < 1.0:
            rect.set('opacity', str(element.opacity))

        # Add text if present
        if element.text:
            self._render_text(g, element.text, x, y, width, height)

    def _render_band(
        self,
        parent: Element,
        element: PositionedElement,
        x: float,
        y: float,
        width: float,
        height: float
    ) -> None:
        """Render a full-width band (rectangle)."""
        g = SubElement(parent, 'g')
        g.set('id', f'band-{element.id}')
        g.set('class', 'band')

        rect = SubElement(g, 'rect')
        rect.set('x', format_px(x))
        rect.set('y', format_px(y))
        rect.set('width', format_px(width))
        rect.set('height', format_px(height))

        # Fill with opacity
        if element.fill_color and element.fill_color != "transparent":
            rect.set('fill', element.fill_color)
            if element.opacity < 1.0:
                rect.set('opacity', str(element.opacity))
        else:
            rect.set('fill', 'none')

        rect.set('stroke', 'none')

        # Add text
        if element.text:
            self._render_text(g, element.text, x, y, width, height)

    def _render_ellipse(
        self,
        parent: Element,
        element: PositionedElement,
        x: float,
        y: float,
        width: float,
        height: float
    ) -> None:
        """Render an ellipse/circle shape."""
        g = SubElement(parent, 'g')
        g.set('id', f'ellipse-{element.id}')
        g.set('class', 'ellipse')

        # Calculate center and radii
        cx = x + width / 2
        cy = y + height / 2
        rx = width / 2
        ry = height / 2

        # Create ellipse
        ellipse = SubElement(g, 'ellipse')
        ellipse.set('cx', format_px(cx))
        ellipse.set('cy', format_px(cy))
        ellipse.set('rx', format_px(rx))
        ellipse.set('ry', format_px(ry))

        # Fill
        if element.fill_color and element.fill_color != "transparent":
            ellipse.set('fill', element.fill_color)
        else:
            ellipse.set('fill', 'none')

        # Stroke
        if element.stroke_color:
            ellipse.set('stroke', element.stroke_color)
            ellipse.set('stroke-width', format_px(pt_to_px(element.stroke_width_pt)))
        else:
            ellipse.set('stroke', 'none')

        # Opacity
        if element.opacity < 1.0:
            ellipse.set('opacity', str(element.opacity))

        # Add text if present
        if element.text:
            self._render_text(g, element.text, x, y, width, height)

    def _render_text_box(
        self,
        parent: Element,
        element: PositionedElement,
        x: float,
        y: float,
        width: float,
        height: float
    ) -> None:
        """Render a text-only element (no shape border)."""
        g = SubElement(parent, 'g')
        g.set('id', f'text-box-{element.id}')
        g.set('class', 'text-box')

        # Add text if present
        if element.text:
            self._render_text(g, element.text, x, y, width, height)

    def _render_title(
        self,
        parent: Element,
        element: PositionedElement,
        x: float,
        y: float,
        width: float,
        height: float
    ) -> None:
        """Render title text."""
        if not element.text:
            return

        self._render_text(
            parent,
            element.text,
            x, y, width, height,
            extra_class='title-text'
        )

    def _render_subtitle(
        self,
        parent: Element,
        element: PositionedElement,
        x: float,
        y: float,
        width: float,
        height: float
    ) -> None:
        """Render subtitle text."""
        if not element.text:
            return

        self._render_text(
            parent,
            element.text,
            x, y, width, height
        )

    def _render_label(
        self,
        parent: Element,
        element: PositionedElement,
        x: float,
        y: float,
        width: float,
        height: float
    ) -> None:
        """Render a text label."""
        if not element.text:
            return

        self._render_text(parent, element.text, x, y, width, height)

    # =========================================================================
    # TEXT RENDERING
    # =========================================================================

    def _render_text(
        self,
        parent: Element,
        text: PositionedText,
        x: float,
        y: float,
        width: float,
        height: float,
        extra_class: str = ''
    ) -> None:
        """
        Render pre-measured text.

        Uses pre-computed font sizes and line breaks from PositionedText.
        """
        if not text.lines:
            return

        # Calculate text anchor based on alignment
        text_anchor = {
            TextAlignment.LEFT: 'start',
            TextAlignment.CENTER: 'middle',
            TextAlignment.RIGHT: 'end',
        }.get(text.alignment, 'middle')

        # Calculate x position based on alignment
        if text.alignment == TextAlignment.LEFT:
            text_x = x + 5  # Small padding
        elif text.alignment == TextAlignment.RIGHT:
            text_x = x + width - 5
        else:
            text_x = x + width / 2

        # Calculate font size in pixels
        font_size_px = pt_to_px(text.font_size_pt)

        # Calculate line height
        line_height = font_size_px * 1.2

        # Calculate total text height
        total_text_height = line_height * len(text.lines)

        # Calculate starting y (vertically centered)
        start_y = y + (height - total_text_height) / 2 + font_size_px * 0.8

        # Create text element
        text_elem = SubElement(parent, 'text')
        text_elem.set('x', format_px(text_x))
        text_elem.set('text-anchor', text_anchor)
        text_elem.set('fill', text.color if text.color != "transparent" else '#333333')
        text_elem.set('font-size', f'{font_size_px:.1f}px')
        text_elem.set('font-family', f"'{text.font_family}', 'Segoe UI', Arial, sans-serif")

        classes = ['block-text']
        if extra_class:
            classes.append(extra_class)
        text_elem.set('class', ' '.join(classes))

        if text.bold:
            text_elem.set('font-weight', 'bold')
        if text.italic:
            text_elem.set('font-style', 'italic')

        # Add tspans for each line
        for i, line in enumerate(text.lines):
            tspan = SubElement(text_elem, 'tspan')
            tspan.set('x', format_px(text_x))
            tspan.set('y', format_px(start_y + i * line_height))
            tspan.text = line

    # =========================================================================
    # CONNECTOR RENDERING
    # =========================================================================

    def _render_connector(self, parent: Element, connector: PositionedConnector) -> None:
        """Render a connector line."""
        g = SubElement(parent, 'g')
        g.set('id', f'connector-{connector.id}')
        g.set('class', 'connector')

        # Convert to pixels
        start_x = inches_to_px(connector.start_x)
        start_y = inches_to_px(connector.start_y)
        end_x = inches_to_px(connector.end_x)
        end_y = inches_to_px(connector.end_y)

        # Create line
        line = SubElement(g, 'line')
        line.set('x1', format_px(start_x))
        line.set('y1', format_px(start_y))
        line.set('x2', format_px(end_x))
        line.set('y2', format_px(end_y))
        line.set('stroke', connector.color)
        line.set('stroke-width', format_px(pt_to_px(connector.stroke_width_pt)))

        # Apply style-specific attributes
        if connector.style == ConnectorStyle.DASHED:
            line.set('stroke-dasharray', '8,4')
            line.set('marker-end', 'url(#arrowhead)')

        elif connector.style == ConnectorStyle.ARROW:
            line.set('marker-end', 'url(#arrowhead)')

        elif connector.style == ConnectorStyle.BIDIRECTIONAL:
            line.set('marker-start', 'url(#arrowhead-start)')
            line.set('marker-end', 'url(#arrowhead)')

        # PLAIN style has no markers

        # Add label if present
        if connector.label:
            self._render_connector_label(g, connector)

    def _render_connector_label(self, parent: Element, connector: PositionedConnector) -> None:
        """Add a text label at connector midpoint."""
        if not connector.label:
            return

        # Calculate midpoint in pixels
        mid_x = inches_to_px(connector.midpoint_x)
        mid_y = inches_to_px(connector.midpoint_y)

        # Create background rect for label
        label_width = 60
        label_height = 20

        bg = SubElement(parent, 'rect')
        bg.set('x', format_px(mid_x - label_width / 2))
        bg.set('y', format_px(mid_y - label_height / 2))
        bg.set('width', format_px(label_width))
        bg.set('height', format_px(label_height))
        bg.set('fill', 'white')
        bg.set('stroke', 'none')

        # Render the label text
        self._render_text(
            parent,
            connector.label,
            mid_x - label_width / 2,
            mid_y - label_height / 2,
            label_width,
            label_height
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def render_to_svg(layout: PositionedLayout, output_path: Optional[str] = None) -> str:
    """
    Convenience function to render a layout to SVG.

    Args:
        layout: PositionedLayout to render
        output_path: Optional file path to save to

    Returns:
        SVG content as string
    """
    renderer = SVGRenderer()
    return renderer.render(layout, output=output_path)


def render_to_svg_string(layout: PositionedLayout, include_fonts: bool = False) -> str:
    """
    Render layout to SVG string (for API responses/embedding).

    Args:
        layout: PositionedLayout to render
        include_fonts: Whether to include font imports (False for inline use)

    Returns:
        SVG content as string
    """
    renderer = SVGRenderer(include_fonts=include_fonts)
    return renderer.render(layout)


def render_to_data_uri(layout: PositionedLayout) -> str:
    """
    Render layout to SVG data URI (for img src or CSS background).

    Args:
        layout: PositionedLayout to render

    Returns:
        Data URI string (data:image/svg+xml;base64,...)
    """
    import base64

    renderer = SVGRenderer(include_fonts=False)
    svg_str = renderer.render(layout)

    # Encode as base64
    svg_bytes = svg_str.encode('utf-8')
    b64 = base64.b64encode(svg_bytes).decode('ascii')

    return f"data:image/svg+xml;base64,{b64}"
