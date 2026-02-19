"""
overlay_system.py — Universal overlay system for adding annotations to diagrams.

Overlays are additional visual elements (arrows, callouts, annotations, banners)
that can be added to ANY archetype. This system works universally with all
archetypes, whether predefined or learned.

Key features:
- Side overlays (left, right, top, bottom arrows and labels)
- Callouts with pointers
- Annotations and labels
- Brackets for grouping
- Automatic diagram compression when overlays need space
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .positioned import (
    PositionedLayout,
    PositionedElement,
    PositionedConnector,
    PositionedText,
    ElementType,
    ConnectorStyle,
    TextAlignment,
)
from .archetype_rules import (
    OverlaySpec,
    OverlayElement,
    OverlayType,
    OverlayPosition,
)
from .data_models import ColorPalette
from .units import (
    CONTENT_LEFT,
    CONTENT_TOP,
    CONTENT_WIDTH,
    CONTENT_HEIGHT,
    DEFAULT_FONT_FAMILY,
)
from .text_measure import fit_text_to_width


@dataclass
class OverlayBounds:
    """Bounds for an overlay region."""
    x: float
    y: float
    width: float
    height: float


class OverlayEngine:
    """
    Engine for applying overlays to layouts.

    The overlay engine:
    1. Calculates space needed for overlays
    2. Compresses the main diagram if needed
    3. Positions overlay elements
    4. Adds overlay connectors (for callouts, pointers)
    """

    def apply_overlays(
        self,
        layout: PositionedLayout,
        overlays: List[OverlaySpec],
        palette: ColorPalette,
    ) -> PositionedLayout:
        """
        Apply overlays to a positioned layout.

        Args:
            layout: The base positioned layout
            overlays: List of overlay specifications
            palette: Color palette for overlay elements

        Returns:
            Modified layout with overlays applied
        """
        if not overlays:
            return layout

        # Calculate compression needed for side overlays
        compression = self._calculate_compression(overlays)

        # Compress main diagram elements if needed
        if compression:
            layout = self._compress_diagram(layout, compression)

        # Add each overlay
        for overlay in overlays:
            layout = self._apply_single_overlay(layout, overlay, palette, compression)

        return layout

    def _calculate_compression(
        self,
        overlays: List[OverlaySpec],
    ) -> Dict[str, float]:
        """Calculate how much to compress the diagram for overlays."""
        compression = {
            'left': 0.0,
            'right': 0.0,
            'top': 0.0,
            'bottom': 0.0,
        }

        for overlay in overlays:
            position = overlay.position.value
            if position in compression:
                space_needed = overlay.width + overlay.margin_from_diagram
                compression[position] = max(compression[position], space_needed)

        return compression

    def _compress_diagram(
        self,
        layout: PositionedLayout,
        compression: Dict[str, float],
    ) -> PositionedLayout:
        """Compress diagram elements to make room for overlays."""
        left_compression = compression.get('left', 0.0)
        right_compression = compression.get('right', 0.0)
        top_compression = compression.get('top', 0.0)
        bottom_compression = compression.get('bottom', 0.0)

        # Calculate scale factors
        original_width = CONTENT_WIDTH
        original_height = CONTENT_HEIGHT
        new_width = original_width - left_compression - right_compression
        new_height = original_height - top_compression - bottom_compression

        scale_x = new_width / original_width
        scale_y = new_height / original_height

        # New content origin
        new_left = CONTENT_LEFT + left_compression
        new_top = CONTENT_TOP + top_compression

        # Scale and translate all elements
        for elem in layout.elements:
            # Skip title and subtitle
            if elem.element_type in (ElementType.TITLE, ElementType.SUBTITLE):
                continue

            # Calculate relative position
            rel_x = (elem.x_inches - CONTENT_LEFT) / original_width
            rel_y = (elem.y_inches - CONTENT_TOP) / original_height
            rel_w = elem.width_inches / original_width
            rel_h = elem.height_inches / original_height

            # Apply scaling
            elem.x_inches = new_left + rel_x * new_width
            elem.y_inches = new_top + rel_y * new_height
            elem.width_inches = rel_w * new_width
            elem.height_inches = rel_h * new_height

        # Scale connectors
        for conn in layout.connectors:
            # Start point
            rel_sx = (conn.start_x - CONTENT_LEFT) / original_width
            rel_sy = (conn.start_y - CONTENT_TOP) / original_height
            conn.start_x = new_left + rel_sx * new_width
            conn.start_y = new_top + rel_sy * new_height

            # End point
            rel_ex = (conn.end_x - CONTENT_LEFT) / original_width
            rel_ey = (conn.end_y - CONTENT_TOP) / original_height
            conn.end_x = new_left + rel_ex * new_width
            conn.end_y = new_top + rel_ey * new_height

            # Waypoints
            new_waypoints = []
            for wx, wy in conn.waypoints:
                rel_wx = (wx - CONTENT_LEFT) / original_width
                rel_wy = (wy - CONTENT_TOP) / original_height
                new_waypoints.append((
                    new_left + rel_wx * new_width,
                    new_top + rel_wy * new_height,
                ))
            conn.waypoints = new_waypoints

        return layout

    def _apply_single_overlay(
        self,
        layout: PositionedLayout,
        overlay: OverlaySpec,
        palette: ColorPalette,
        compression: Dict[str, float],
    ) -> PositionedLayout:
        """Apply a single overlay to the layout."""
        # Calculate overlay region
        bounds = self._calculate_overlay_bounds(layout, overlay, compression)

        # Create elements based on overlay type
        if overlay.overlay_type == OverlayType.SIDE_ARROW:
            elements = self._create_side_arrow(overlay, bounds, palette)
        elif overlay.overlay_type == OverlayType.CALLOUT:
            elements, connectors = self._create_callout(overlay, bounds, palette, layout)
            layout.connectors.extend(connectors)
        elif overlay.overlay_type == OverlayType.ANNOTATION:
            elements = self._create_annotation(overlay, bounds, palette)
        elif overlay.overlay_type == OverlayType.BANNER:
            elements = self._create_banner(overlay, bounds, palette)
        elif overlay.overlay_type == OverlayType.BRACKET:
            elements = self._create_bracket(overlay, bounds, palette, layout)
        elif overlay.overlay_type == OverlayType.LABEL:
            elements = self._create_label(overlay, bounds, palette)
        else:
            # Generic: just add the overlay elements
            elements = self._create_generic_overlay(overlay, bounds, palette)

        layout.elements.extend(elements)
        return layout

    def _calculate_overlay_bounds(
        self,
        layout: PositionedLayout,
        overlay: OverlaySpec,
        compression: Dict[str, float],
    ) -> OverlayBounds:
        """Calculate the bounds for an overlay region."""
        position = overlay.position.value
        margin = overlay.margin_from_diagram

        # Find diagram bounds (after compression)
        left_comp = compression.get('left', 0.0)
        right_comp = compression.get('right', 0.0)
        top_comp = compression.get('top', 0.0)
        bottom_comp = compression.get('bottom', 0.0)

        diagram_left = CONTENT_LEFT + left_comp
        diagram_top = CONTENT_TOP + top_comp
        diagram_right = CONTENT_LEFT + CONTENT_WIDTH - right_comp
        diagram_bottom = CONTENT_TOP + CONTENT_HEIGHT - bottom_comp

        # Calculate overlay position
        if position == 'left':
            x = CONTENT_LEFT
            y = diagram_top
            width = left_comp - margin
            height = diagram_bottom - diagram_top
        elif position == 'right':
            x = diagram_right + margin
            y = diagram_top
            width = right_comp - margin
            height = diagram_bottom - diagram_top
        elif position == 'top':
            x = diagram_left
            y = CONTENT_TOP
            width = diagram_right - diagram_left
            height = top_comp - margin
        elif position == 'bottom':
            x = diagram_left
            y = diagram_bottom + margin
            width = diagram_right - diagram_left
            height = bottom_comp - margin
        else:
            # Floating or anchored
            if overlay.anchor_to != "diagram":
                # Find anchor element
                anchor_elem = layout.get_element_by_id(overlay.anchor_to)
                if anchor_elem:
                    x = anchor_elem.right_edge + margin
                    y = anchor_elem.y_inches
                    width = overlay.width
                    height = overlay.height or anchor_elem.height_inches
                else:
                    x = diagram_left
                    y = diagram_top
                    width = overlay.width
                    height = overlay.height or 1.0
            else:
                x = diagram_left
                y = diagram_top
                width = overlay.width
                height = overlay.height or 1.0

        return OverlayBounds(x=x, y=y, width=width, height=height)

    def _create_side_arrow(
        self,
        overlay: OverlaySpec,
        bounds: OverlayBounds,
        palette: ColorPalette,
    ) -> List[PositionedElement]:
        """Create side arrow overlay (e.g., "Inputs" arrow on left side)."""
        elements = []
        position = overlay.position.value

        # Determine arrow direction based on position
        arrow_direction = {
            'left': 'right',  # Arrow pointing into diagram
            'right': 'left',
            'top': 'down',
            'bottom': 'up',
        }.get(position, 'right')

        # Create arrow element
        arrow_height = min(bounds.height * 0.6, 1.5)
        arrow_width = bounds.width * 0.8

        # Center in bounds
        if position in ('left', 'right'):
            arrow_x = bounds.x + (bounds.width - arrow_width) / 2
            arrow_y = bounds.y + (bounds.height - arrow_height) / 2
        else:
            arrow_x = bounds.x + (bounds.width - arrow_height) / 2
            arrow_y = bounds.y + (bounds.height - arrow_width) / 2
            # Swap width/height for vertical arrows
            arrow_width, arrow_height = arrow_height, arrow_width

        arrow_elem = PositionedElement(
            id=f"{overlay.overlay_id}_arrow",
            element_type=ElementType.BLOCK,
            x_inches=arrow_x,
            y_inches=arrow_y,
            width_inches=arrow_width,
            height_inches=arrow_height,
            fill_color=palette.primary,
            stroke_color=None,
            shape_hint='arrow',
            arrow_direction=arrow_direction,
            z_order=50,
        )
        elements.append(arrow_elem)

        # Add label from overlay elements
        for i, elem_spec in enumerate(overlay.elements):
            if elem_spec.content:
                # Position label based on overlay position
                if position == 'left':
                    label_x = bounds.x
                    label_y = arrow_y + arrow_height + 0.1
                elif position == 'right':
                    label_x = bounds.x
                    label_y = arrow_y + arrow_height + 0.1
                else:
                    label_x = arrow_x + arrow_width + 0.1
                    label_y = bounds.y

                fit_result = fit_text_to_width(
                    elem_spec.content,
                    bounds.width,
                    font_family=DEFAULT_FONT_FAMILY,
                    max_font_size=elem_spec.font_size,
                    min_font_size=10,
                    bold=elem_spec.bold,
                )

                label_text = PositionedText(
                    content=elem_spec.content,
                    lines=fit_result.lines,
                    font_size_pt=fit_result.font_size,
                    font_family=DEFAULT_FONT_FAMILY,
                    bold=elem_spec.bold,
                    color=elem_spec.text_color or palette.text_dark,
                    alignment=TextAlignment.CENTER,
                )

                label_elem = PositionedElement(
                    id=f"{overlay.overlay_id}_label_{i}",
                    element_type=ElementType.LABEL,
                    x_inches=label_x,
                    y_inches=label_y,
                    width_inches=bounds.width,
                    height_inches=0.4,
                    fill_color="transparent",
                    text=label_text,
                    z_order=51,
                )
                elements.append(label_elem)

        return elements

    def _create_callout(
        self,
        overlay: OverlaySpec,
        bounds: OverlayBounds,
        palette: ColorPalette,
        layout: PositionedLayout,
    ) -> Tuple[List[PositionedElement], List[PositionedConnector]]:
        """Create callout overlay with pointer to target element."""
        elements = []
        connectors = []

        # Create callout box
        callout_elem = PositionedElement(
            id=f"{overlay.overlay_id}_box",
            element_type=ElementType.BLOCK,
            x_inches=bounds.x,
            y_inches=bounds.y,
            width_inches=bounds.width,
            height_inches=bounds.height or 1.0,
            fill_color=overlay.background_color or "#FFFFCC",
            stroke_color=palette.border,
            corner_radius_inches=0.1,
            z_order=55,
        )

        # Add text content
        content_parts = []
        for elem_spec in overlay.elements:
            if elem_spec.content:
                content_parts.append(elem_spec.content)

        if content_parts:
            full_content = "\n".join(content_parts)
            fit_result = fit_text_to_width(
                full_content,
                bounds.width - 0.2,
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=12,
                min_font_size=9,
            )

            callout_elem.text = PositionedText(
                content=full_content,
                lines=fit_result.lines,
                font_size_pt=fit_result.font_size,
                font_family=DEFAULT_FONT_FAMILY,
                color=palette.text_dark,
            )

        elements.append(callout_elem)

        # Create pointer connector if target specified
        if overlay.show_pointer and overlay.pointer_target:
            target_elem = layout.get_element_by_id(overlay.pointer_target)
            if target_elem:
                # Calculate connection points
                callout_cx = bounds.x + bounds.width / 2
                callout_cy = bounds.y + (bounds.height or 1.0) / 2
                target_cx = target_elem.center_x
                target_cy = target_elem.center_y

                connector = PositionedConnector(
                    id=f"{overlay.overlay_id}_pointer",
                    start_x=callout_cx,
                    start_y=callout_cy,
                    end_x=target_cx,
                    end_y=target_cy,
                    style=ConnectorStyle.PLAIN,
                    color=palette.border,
                    stroke_width_pt=1.0,
                )
                connectors.append(connector)

        return elements, connectors

    def _create_annotation(
        self,
        overlay: OverlaySpec,
        bounds: OverlayBounds,
        palette: ColorPalette,
    ) -> List[PositionedElement]:
        """Create text annotation overlay."""
        elements = []

        for i, elem_spec in enumerate(overlay.elements):
            if elem_spec.content:
                fit_result = fit_text_to_width(
                    elem_spec.content,
                    bounds.width,
                    font_family=DEFAULT_FONT_FAMILY,
                    max_font_size=elem_spec.font_size,
                    min_font_size=9,
                    bold=elem_spec.bold,
                )

                text = PositionedText(
                    content=elem_spec.content,
                    lines=fit_result.lines,
                    font_size_pt=fit_result.font_size,
                    font_family=DEFAULT_FONT_FAMILY,
                    bold=elem_spec.bold,
                    color=elem_spec.text_color or palette.text_dark,
                )

                elem = PositionedElement(
                    id=f"{overlay.overlay_id}_annotation_{i}",
                    element_type=ElementType.TEXT_BOX,
                    x_inches=bounds.x + elem_spec.x,
                    y_inches=bounds.y + elem_spec.y,
                    width_inches=elem_spec.width or bounds.width,
                    height_inches=elem_spec.height or 0.5,
                    fill_color="transparent",
                    text=text,
                    z_order=50,
                )
                elements.append(elem)

        return elements

    def _create_banner(
        self,
        overlay: OverlaySpec,
        bounds: OverlayBounds,
        palette: ColorPalette,
    ) -> List[PositionedElement]:
        """Create horizontal/vertical banner overlay."""
        elements = []

        banner_elem = PositionedElement(
            id=f"{overlay.overlay_id}_banner",
            element_type=ElementType.BAND,
            x_inches=bounds.x,
            y_inches=bounds.y,
            width_inches=bounds.width,
            height_inches=bounds.height or 0.6,
            fill_color=overlay.background_color or palette.secondary,
            corner_radius_inches=0.05,
            z_order=45,
        )

        # Add text
        content_parts = [e.content for e in overlay.elements if e.content]
        if content_parts:
            fit_result = fit_text_to_width(
                content_parts[0],
                bounds.width - 0.2,
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=14,
                min_font_size=10,
                bold=True,
            )

            # Contrast text color
            bg_color = overlay.background_color or palette.secondary
            text_color = self._get_contrast_color(bg_color, palette)

            banner_elem.text = PositionedText(
                content=content_parts[0],
                lines=fit_result.lines,
                font_size_pt=fit_result.font_size,
                font_family=DEFAULT_FONT_FAMILY,
                bold=True,
                color=text_color,
                alignment=TextAlignment.CENTER,
            )

        elements.append(banner_elem)
        return elements

    def _create_bracket(
        self,
        overlay: OverlaySpec,
        bounds: OverlayBounds,
        palette: ColorPalette,
        layout: PositionedLayout,
    ) -> List[PositionedElement]:
        """Create bracket overlay to group elements."""
        elements = []
        position = overlay.position.value

        # Create bracket shape using lines
        # This is simplified - a real implementation might use custom paths
        bracket_color = palette.border

        if position in ('left', 'right'):
            # Vertical bracket
            bracket_width = 0.15
            bracket_height = bounds.height

            x = bounds.x if position == 'left' else bounds.x + bounds.width - bracket_width

            bracket = PositionedElement(
                id=f"{overlay.overlay_id}_bracket",
                element_type=ElementType.BLOCK,
                x_inches=x,
                y_inches=bounds.y,
                width_inches=bracket_width,
                height_inches=bracket_height,
                fill_color="transparent",
                stroke_color=bracket_color,
                stroke_width_pt=2.0,
                shape_hint='bracket_vertical',
                z_order=48,
            )
        else:
            # Horizontal bracket
            bracket_width = bounds.width
            bracket_height = 0.15

            y = bounds.y if position == 'top' else bounds.y + bounds.height - bracket_height

            bracket = PositionedElement(
                id=f"{overlay.overlay_id}_bracket",
                element_type=ElementType.BLOCK,
                x_inches=bounds.x,
                y_inches=y,
                width_inches=bracket_width,
                height_inches=bracket_height,
                fill_color="transparent",
                stroke_color=bracket_color,
                stroke_width_pt=2.0,
                shape_hint='bracket_horizontal',
                z_order=48,
            )

        elements.append(bracket)
        return elements

    def _create_label(
        self,
        overlay: OverlaySpec,
        bounds: OverlayBounds,
        palette: ColorPalette,
    ) -> List[PositionedElement]:
        """Create simple label overlay."""
        elements = []

        for i, elem_spec in enumerate(overlay.elements):
            if elem_spec.content:
                fit_result = fit_text_to_width(
                    elem_spec.content,
                    bounds.width,
                    font_family=DEFAULT_FONT_FAMILY,
                    max_font_size=elem_spec.font_size,
                    min_font_size=10,
                    bold=elem_spec.bold,
                )

                text = PositionedText(
                    content=elem_spec.content,
                    lines=fit_result.lines,
                    font_size_pt=fit_result.font_size,
                    font_family=DEFAULT_FONT_FAMILY,
                    bold=elem_spec.bold,
                    color=elem_spec.text_color or palette.text_dark,
                )

                elem = PositionedElement(
                    id=f"{overlay.overlay_id}_label_{i}",
                    element_type=ElementType.LABEL,
                    x_inches=bounds.x + elem_spec.x,
                    y_inches=bounds.y + elem_spec.y,
                    width_inches=elem_spec.width or bounds.width,
                    height_inches=elem_spec.height or 0.4,
                    fill_color="transparent",
                    text=text,
                    z_order=50,
                )
                elements.append(elem)

        return elements

    def _create_generic_overlay(
        self,
        overlay: OverlaySpec,
        bounds: OverlayBounds,
        palette: ColorPalette,
    ) -> List[PositionedElement]:
        """Create generic overlay from element specifications."""
        elements = []

        for i, elem_spec in enumerate(overlay.elements):
            fill_color = elem_spec.fill_color or palette.secondary
            stroke_color = elem_spec.stroke_color

            text = None
            if elem_spec.content:
                fit_result = fit_text_to_width(
                    elem_spec.content,
                    elem_spec.width,
                    font_family=DEFAULT_FONT_FAMILY,
                    max_font_size=elem_spec.font_size,
                    min_font_size=9,
                    bold=elem_spec.bold,
                )

                text = PositionedText(
                    content=elem_spec.content,
                    lines=fit_result.lines,
                    font_size_pt=fit_result.font_size,
                    font_family=DEFAULT_FONT_FAMILY,
                    bold=elem_spec.bold,
                    color=elem_spec.text_color or self._get_contrast_color(fill_color, palette),
                )

            elem = PositionedElement(
                id=elem_spec.element_id,
                element_type=ElementType.BLOCK,
                x_inches=bounds.x + elem_spec.x,
                y_inches=bounds.y + elem_spec.y,
                width_inches=elem_spec.width,
                height_inches=elem_spec.height,
                fill_color=fill_color,
                stroke_color=stroke_color,
                text=text,
                arrow_direction=elem_spec.arrow_direction,
                z_order=50,
            )
            elements.append(elem)

        return elements

    def _get_contrast_color(
        self,
        bg_color: str,
        palette: ColorPalette,
    ) -> str:
        """Get contrasting text color for background."""
        bg = bg_color.lstrip('#')
        if len(bg) != 6:
            return palette.text_dark

        try:
            r = int(bg[0:2], 16)
            g = int(bg[2:4], 16)
            b = int(bg[4:6], 16)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return palette.text_light if luminance < 0.5 else palette.text_dark
        except ValueError:
            return palette.text_dark
