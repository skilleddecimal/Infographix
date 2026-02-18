"""
pptx_renderer.py — PowerPoint file generation from PositionedLayout.

This renderer consumes PositionedLayout and produces .pptx files.
It NEVER computes positions — that's the layout engine's job.
It only converts inches to EMU and creates the actual shapes.

CRITICAL RULES:
1. NEVER set shape.text_frame.auto_size = MSO_AUTO_SIZE.SHAPE_TO_FIT_TEXT
2. ALWAYS use pre-computed font sizes from PositionedText
3. ALWAYS disable word wrap for single-line text
4. Use explicit paragraph formatting (no defaults)
"""

from pathlib import Path
from typing import Optional, BinaryIO, Union
from io import BytesIO

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.oxml import parse_xml

from .positioned import (
    PositionedLayout,
    PositionedElement,
    PositionedConnector,
    PositionedText,
    ElementType,
    ConnectorStyle,
    TextAlignment,
)
from .units import (
    inches_to_emu,
    pt_to_emu,
    SLIDE_WIDTH_EMU,
    SLIDE_HEIGHT_EMU,
)


# =============================================================================
# COLOR HELPERS
# =============================================================================

def hex_to_rgb_color(hex_color: str) -> RGBColor:
    """Convert hex color string to pptx RGBColor."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return RGBColor(0x33, 0x33, 0x33)  # Default dark gray

    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return RGBColor(r, g, b)
    except ValueError:
        return RGBColor(0x33, 0x33, 0x33)


def get_alignment(text_align: TextAlignment) -> PP_ALIGN:
    """Convert TextAlignment to pptx PP_ALIGN."""
    mapping = {
        TextAlignment.LEFT: PP_ALIGN.LEFT,
        TextAlignment.CENTER: PP_ALIGN.CENTER,
        TextAlignment.RIGHT: PP_ALIGN.RIGHT,
    }
    return mapping.get(text_align, PP_ALIGN.CENTER)


# =============================================================================
# PPTX RENDERER
# =============================================================================

class PPTXRenderer:
    """
    Renders PositionedLayout to PowerPoint files.

    The renderer is stateless — each render() call creates a new presentation.
    """

    def __init__(self):
        """Initialize renderer."""
        pass

    def render(
        self,
        layout: PositionedLayout,
        output: Optional[Union[str, Path, BinaryIO]] = None
    ) -> bytes:
        """
        Render a PositionedLayout to PPTX format.

        Args:
            layout: The positioned layout to render
            output: Optional output path or file-like object
                    If None, returns bytes

        Returns:
            PPTX file contents as bytes
        """
        # Create presentation with correct dimensions
        prs = Presentation()
        prs.slide_width = Emu(inches_to_emu(layout.slide_width_inches))
        prs.slide_height = Emu(inches_to_emu(layout.slide_height_inches))

        # Add blank slide
        blank_layout = prs.slide_layouts[6]  # Blank layout
        slide = prs.slides.add_slide(blank_layout)

        # Set background color
        self._set_slide_background(slide, layout.background_color)

        # Render title and subtitle first (z-order highest)
        if layout.title:
            self._render_element(slide, layout.title)
        if layout.subtitle:
            self._render_element(slide, layout.subtitle)

        # Render elements sorted by z-order (lowest first = behind)
        for element in layout.elements_sorted_by_z_order():
            self._render_element(slide, element)

        # Render connectors
        for connector in layout.connectors:
            self._render_connector(slide, connector)

        # Save to output
        if output is None:
            buffer = BytesIO()
            prs.save(buffer)
            return buffer.getvalue()
        elif isinstance(output, (str, Path)):
            prs.save(str(output))
            with open(output, 'rb') as f:
                return f.read()
        else:
            prs.save(output)
            output.seek(0)
            return output.read()

    def render_to_file(self, layout: PositionedLayout, filepath: Union[str, Path]) -> None:
        """
        Render layout directly to a file.

        Args:
            layout: The positioned layout to render
            filepath: Output file path
        """
        self.render(layout, output=filepath)

    # =========================================================================
    # SLIDE BACKGROUND
    # =========================================================================

    def _set_slide_background(self, slide, color: str) -> None:
        """Set slide background color."""
        if color.lower() == "transparent" or color == "#FFFFFF":
            return  # White/transparent is default

        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = hex_to_rgb_color(color)

    # =========================================================================
    # ELEMENT RENDERING
    # =========================================================================

    def _render_element(self, slide, element: PositionedElement) -> None:
        """Render a single positioned element."""
        # Skip transparent fill elements without text (spacers)
        if element.fill_color == "transparent" and element.text is None:
            return

        # Convert to EMU
        left = Emu(inches_to_emu(element.x_inches))
        top = Emu(inches_to_emu(element.y_inches))
        width = Emu(inches_to_emu(element.width_inches))
        height = Emu(inches_to_emu(element.height_inches))

        # Choose shape type based on element type
        if element.element_type == ElementType.TITLE:
            self._render_title(slide, element, left, top, width, height)
        elif element.element_type == ElementType.SUBTITLE:
            self._render_subtitle(slide, element, left, top, width, height)
        elif element.element_type == ElementType.BAND:
            self._render_band(slide, element, left, top, width, height)
        elif element.element_type == ElementType.LABEL:
            self._render_label(slide, element, left, top, width, height)
        else:
            self._render_block(slide, element, left, top, width, height)

    def _render_block(self, slide, element: PositionedElement, left, top, width, height) -> None:
        """Render a standard block (rounded rectangle)."""
        # Create rounded rectangle
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            left, top, width, height
        )

        # Set corner radius (adjustment)
        # PowerPoint uses adjustment values 0-100000 for corner radius
        corner_pct = min(50000, int((element.corner_radius_inches / element.height_inches) * 100000))
        shape.adjustments[0] = corner_pct / 100000

        # Fill color
        if element.fill_color and element.fill_color != "transparent":
            shape.fill.solid()
            shape.fill.fore_color.rgb = hex_to_rgb_color(element.fill_color)
        else:
            shape.fill.background()  # No fill

        # Border
        if element.stroke_color:
            shape.line.color.rgb = hex_to_rgb_color(element.stroke_color)
            shape.line.width = Pt(element.stroke_width_pt)
        else:
            shape.line.fill.background()  # No border

        # Add text if present
        if element.text:
            self._apply_text(shape, element.text, element.height_inches)

    def _render_band(self, slide, element: PositionedElement, left, top, width, height) -> None:
        """Render a full-width band (rectangle)."""
        shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            left, top, width, height
        )

        # Fill with semi-transparency
        if element.fill_color and element.fill_color != "transparent":
            shape.fill.solid()
            shape.fill.fore_color.rgb = hex_to_rgb_color(element.fill_color)

            # Set transparency if specified
            if element.opacity < 1.0:
                # Transparency is inverted (0 = opaque, 100000 = transparent)
                transparency = int((1 - element.opacity) * 100000)
                shape.fill.fore_color.brightness = 0  # Reset brightness
                # Note: python-pptx doesn't directly support fill transparency
                # Would need to modify XML directly for true transparency
        else:
            shape.fill.background()

        # No border for bands
        shape.line.fill.background()

        # Add text
        if element.text:
            self._apply_text(shape, element.text, element.height_inches)

    def _render_title(self, slide, element: PositionedElement, left, top, width, height) -> None:
        """Render title text."""
        if not element.text:
            return

        # Use text box for title
        textbox = slide.shapes.add_textbox(left, top, width, height)
        self._apply_text(textbox, element.text, element.height_inches, is_title=True)

    def _render_subtitle(self, slide, element: PositionedElement, left, top, width, height) -> None:
        """Render subtitle text."""
        if not element.text:
            return

        textbox = slide.shapes.add_textbox(left, top, width, height)
        self._apply_text(textbox, element.text, element.height_inches)

    def _render_label(self, slide, element: PositionedElement, left, top, width, height) -> None:
        """Render a text label."""
        if not element.text:
            return

        textbox = slide.shapes.add_textbox(left, top, width, height)
        self._apply_text(textbox, element.text, element.height_inches)

    # =========================================================================
    # TEXT APPLICATION (CRITICAL - PREVENTS OVERFLOW)
    # =========================================================================

    def _apply_text(
        self,
        shape,
        text: PositionedText,
        container_height: float,
        is_title: bool = False
    ) -> None:
        """
        Apply pre-measured text to a shape.

        CRITICAL: Uses pre-computed font sizes and line breaks.
        Never lets PowerPoint auto-size or wrap text.
        """
        tf = shape.text_frame

        # CRITICAL: Disable auto-size — we computed the font size
        tf.auto_size = None  # Explicitly None to prevent any auto-sizing

        # Set margins (minimal)
        tf.margin_left = Emu(inches_to_emu(0.05))
        tf.margin_right = Emu(inches_to_emu(0.05))
        tf.margin_top = Emu(inches_to_emu(0.03))
        tf.margin_bottom = Emu(inches_to_emu(0.03))

        # Vertical centering
        tf.anchor = MSO_ANCHOR.MIDDLE

        # Word wrap — only if multiple lines
        tf.word_wrap = len(text.lines) > 1

        # Clear existing paragraphs and add new ones
        for i, line in enumerate(text.lines):
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()

            p.text = line
            p.alignment = get_alignment(text.alignment)

            # Apply font formatting to the run
            if p.runs:
                run = p.runs[0]
            else:
                run = p.add_run()
                run.text = line

            # CRITICAL: Use pre-computed font size
            run.font.size = Pt(text.font_size_pt)
            run.font.name = text.font_family
            run.font.bold = text.bold
            run.font.italic = text.italic

            if text.color and text.color != "transparent":
                run.font.color.rgb = hex_to_rgb_color(text.color)

            # Line spacing for multi-line text
            if len(text.lines) > 1:
                p.line_spacing = 1.15

    # =========================================================================
    # CONNECTOR RENDERING
    # =========================================================================

    def _render_connector(self, slide, connector: PositionedConnector) -> None:
        """Render a connector line using a freeform shape for precise positioning."""
        from pptx.oxml.ns import nsmap
        from pptx.oxml import parse_xml
        from lxml import etree

        start_x_emu = inches_to_emu(connector.start_x)
        start_y_emu = inches_to_emu(connector.start_y)
        end_x_emu = inches_to_emu(connector.end_x)
        end_y_emu = inches_to_emu(connector.end_y)

        # Calculate bounding box
        min_x = min(start_x_emu, end_x_emu)
        min_y = min(start_y_emu, end_y_emu)
        width = abs(end_x_emu - start_x_emu)
        height = abs(end_y_emu - start_y_emu)

        # Ensure minimum size
        if width < 1:
            width = 1
        if height < 1:
            height = 1

        # Calculate relative positions within bounding box (0-based)
        # These are relative to the top-left of the bounding box
        rel_start_x = start_x_emu - min_x
        rel_start_y = start_y_emu - min_y
        rel_end_x = end_x_emu - min_x
        rel_end_y = end_y_emu - min_y

        # Create a freeform/path shape via XML for precise line positioning
        # This gives us exact control over start and end points

        # Build the shape XML
        nsmap_a = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}

        sp_xml = f'''
        <p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
              xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
          <p:nvSpPr>
            <p:cNvPr id="0" name="Line"/>
            <p:cNvSpPr/>
            <p:nvPr/>
          </p:nvSpPr>
          <p:spPr>
            <a:xfrm>
              <a:off x="{min_x}" y="{min_y}"/>
              <a:ext cx="{width}" cy="{height}"/>
            </a:xfrm>
            <a:custGeom>
              <a:avLst/>
              <a:gdLst/>
              <a:ahLst/>
              <a:cxnLst/>
              <a:rect l="0" t="0" r="0" b="0"/>
              <a:pathLst>
                <a:path w="{width}" h="{height}">
                  <a:moveTo>
                    <a:pt x="{rel_start_x}" y="{rel_start_y}"/>
                  </a:moveTo>
                  <a:lnTo>
                    <a:pt x="{rel_end_x}" y="{rel_end_y}"/>
                  </a:lnTo>
                </a:path>
              </a:pathLst>
            </a:custGeom>
            <a:ln w="{int(connector.stroke_width_pt * 12700)}">
              <a:solidFill>
                <a:srgbClr val="{connector.color.lstrip('#')}"/>
              </a:solidFill>
            </a:ln>
          </p:spPr>
          <p:txBody>
            <a:bodyPr/>
            <a:lstStyle/>
            <a:p/>
          </p:txBody>
        </p:sp>
        '''

        # Parse and add to slide
        sp_element = etree.fromstring(sp_xml)
        slide.shapes._spTree.append(sp_element)

        # For arrow heads, we need to add them via XML as well
        if connector.style in [ConnectorStyle.ARROW, ConnectorStyle.DASHED, ConnectorStyle.BIDIRECTIONAL]:
            self._add_arrow_to_xml(sp_element, connector.style)

        # Add label if present
        if connector.label:
            self._add_connector_label(slide, connector)

    def _add_arrow_to_xml(self, sp_element, style: ConnectorStyle) -> None:
        """Add arrowhead(s) to a shape via XML."""
        try:
            nsmap_a = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
            ln = sp_element.find('.//a:ln', nsmap_a)
            if ln is not None:
                # Add end arrow
                tail_end = etree.SubElement(ln, '{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd')
                tail_end.set('type', 'triangle')
                tail_end.set('w', 'med')
                tail_end.set('len', 'med')

                # Add start arrow for bidirectional
                if style == ConnectorStyle.BIDIRECTIONAL:
                    head_end = etree.SubElement(ln, '{http://schemas.openxmlformats.org/drawingml/2006/main}headEnd')
                    head_end.set('type', 'triangle')
                    head_end.set('w', 'med')
                    head_end.set('len', 'med')

                # Add dash for dashed style
                if style == ConnectorStyle.DASHED:
                    prstDash = etree.SubElement(ln, '{http://schemas.openxmlformats.org/drawingml/2006/main}prstDash')
                    prstDash.set('val', 'dash')
        except Exception:
            pass

    def _add_end_arrow(self, shape) -> None:
        """Add arrowhead to end of connector."""
        # Access line element and add arrow
        try:
            line = shape.line
            # Set end arrow using underlying XML
            spPr = shape._element.spPr
            ln = spPr.find(qn('a:ln'))
            if ln is not None:
                tailEnd = parse_xml(
                    '<a:tailEnd xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                    'type="triangle" w="med" len="med"/>'
                )
                ln.append(tailEnd)
        except Exception:
            pass  # Arrow heads may fail in some cases

    def _add_start_arrow(self, shape) -> None:
        """Add arrowhead to start of connector."""
        try:
            spPr = shape._element.spPr
            ln = spPr.find(qn('a:ln'))
            if ln is not None:
                headEnd = parse_xml(
                    '<a:headEnd xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                    'type="triangle" w="med" len="med"/>'
                )
                ln.append(headEnd)
        except Exception:
            pass

    def _add_connector_label(self, slide, connector: PositionedConnector) -> None:
        """Add a text label at connector midpoint."""
        if not connector.label:
            return

        # Position label at midpoint
        mid_x = connector.midpoint_x
        mid_y = connector.midpoint_y

        # Small textbox for label
        label_width = 1.5
        label_height = 0.3

        left = Emu(inches_to_emu(mid_x - label_width / 2))
        top = Emu(inches_to_emu(mid_y - label_height / 2))
        width = Emu(inches_to_emu(label_width))
        height = Emu(inches_to_emu(label_height))

        textbox = slide.shapes.add_textbox(left, top, width, height)
        self._apply_text(textbox, connector.label, label_height)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def render_to_pptx(layout: PositionedLayout, output_path: Optional[str] = None) -> bytes:
    """
    Convenience function to render a layout to PPTX.

    Args:
        layout: PositionedLayout to render
        output_path: Optional file path to save to

    Returns:
        PPTX file bytes
    """
    renderer = PPTXRenderer()
    if output_path:
        renderer.render_to_file(layout, output_path)
        with open(output_path, 'rb') as f:
            return f.read()
    else:
        return renderer.render(layout)


def render_to_bytes(layout: PositionedLayout) -> bytes:
    """Render layout to PPTX bytes (for API responses)."""
    renderer = PPTXRenderer()
    return renderer.render(layout)
