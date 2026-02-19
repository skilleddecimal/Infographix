"""
universal_archetype.py — Single universal class that renders ANY archetype.

This replaces 28+ hardcoded archetype classes with a single class that
interprets ArchetypeRules to generate layouts. The rules can be:
- Predefined (JSON files for standard archetypes)
- Learned (from training on PPTX templates)
- Custom (user-defined)

The UniversalArchetype is the main entry point for the new flexible system.
"""

from typing import List, Dict, Any, Optional

from .positioned import (
    PositionedLayout,
    PositionedElement,
    PositionedConnector,
    PositionedText,
    ElementType,
    ConnectorStyle,
    RoutingStyle,
    TextAlignment,
)
from .archetype_rules import (
    ArchetypeRules,
    LayoutStrategy,
    OverlaySpec,
    ElementShape,
)
from .data_models import DiagramInput, ColorPalette, BlockData
from .units import (
    SLIDE_WIDTH_INCHES,
    SLIDE_HEIGHT_INCHES,
    CONTENT_LEFT,
    CONTENT_TOP,
    CONTENT_WIDTH,
    CONTENT_HEIGHT,
    MARGIN_TOP,
    TITLE_HEIGHT,
    SUBTITLE_HEIGHT,
    DEFAULT_FONT_FAMILY,
    TITLE_FONT_SIZE_PT,
    SUBTITLE_FONT_SIZE_PT,
    DEFAULT_TEXT_COLOR,
)
from .text_measure import fit_text_to_width
from .layout_strategies import (
    get_strategy,
    ContentBounds,
    ElementPosition,
    ConnectorPosition,
    StrategyResult,
)


class UniversalArchetype:
    """
    Universal archetype that can render any diagram type.

    Instead of hardcoded layout logic, this class interprets ArchetypeRules
    to determine how to lay out elements. The rules define:
    - Layout strategy (grid, stack, radial, tree, flow, freeform)
    - Element styling (shapes, colors, sizes)
    - Connector patterns
    - Constraints
    """

    def __init__(self, rules: ArchetypeRules, palette: Optional[ColorPalette] = None):
        """
        Initialize with archetype rules.

        Args:
            rules: ArchetypeRules defining layout behavior
            palette: Optional color palette override
        """
        self.rules = rules
        self.palette = palette or ColorPalette()

    def generate_layout(
        self,
        input_data: DiagramInput,
        overlays: Optional[List[OverlaySpec]] = None,
    ) -> PositionedLayout:
        """
        Generate a complete positioned layout from input data.

        Args:
            input_data: The diagram input data (blocks, connectors, layers)
            overlays: Optional overlay specifications to add to the diagram

        Returns:
            PositionedLayout ready for rendering
        """
        # Validate input
        errors = self.validate_input(input_data)
        if errors:
            return self._create_error_layout(
                title=input_data.title,
                error_message=errors[0]
            )

        # Use palette from input if provided
        palette = input_data.palette or self.palette

        # Calculate content bounds (may be adjusted if overlays are present)
        bounds = self._calculate_content_bounds(overlays)

        # Select and execute layout strategy
        strategy = get_strategy(self.rules.layout_strategy.value)
        result = strategy.compute(input_data, self.rules, bounds, palette)

        # Convert strategy result to PositionedLayout
        layout = self._build_positioned_layout(
            result=result,
            input_data=input_data,
            palette=palette,
        )

        # Apply overlays if specified
        if overlays:
            layout = self._apply_overlays(layout, overlays, palette)
        elif self.rules.default_overlays:
            layout = self._apply_overlays(layout, self.rules.default_overlays, palette)

        # Set archetype metadata
        layout.archetype = self.rules.archetype_id

        return layout

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """
        Validate input data against archetype rules.

        Returns list of error messages (empty if valid).
        """
        errors = []

        if not input_data.title:
            errors.append("Title is required")

        num_blocks = len(input_data.blocks)
        if num_blocks < self.rules.min_elements:
            errors.append(
                f"At least {self.rules.min_elements} elements required, got {num_blocks}"
            )
        if num_blocks > self.rules.max_elements:
            errors.append(
                f"Maximum {self.rules.max_elements} elements allowed, got {num_blocks}"
            )

        # Check for duplicate block IDs
        block_ids = [b.id for b in input_data.blocks]
        if len(block_ids) != len(set(block_ids)):
            errors.append("Block IDs must be unique")

        # Validate connector references
        for conn in input_data.connectors:
            if conn.from_id not in block_ids:
                errors.append(f"Connector references unknown block: {conn.from_id}")
            if conn.to_id not in block_ids:
                errors.append(f"Connector references unknown block: {conn.to_id}")

        return errors

    def _calculate_content_bounds(
        self,
        overlays: Optional[List[OverlaySpec]] = None,
    ) -> ContentBounds:
        """
        Calculate content bounds, adjusting for overlays.

        If overlays are on the sides, compress the main content area.
        """
        left = CONTENT_LEFT
        top = CONTENT_TOP
        width = CONTENT_WIDTH
        height = CONTENT_HEIGHT

        if overlays:
            for overlay in overlays:
                margin = overlay.margin_from_diagram + overlay.width

                if overlay.position.value == 'left':
                    left += margin
                    width -= margin
                elif overlay.position.value == 'right':
                    width -= margin
                elif overlay.position.value == 'top':
                    top += margin
                    height -= margin
                elif overlay.position.value == 'bottom':
                    height -= margin

        return ContentBounds(left=left, top=top, width=width, height=height)

    def _build_positioned_layout(
        self,
        result: StrategyResult,
        input_data: DiagramInput,
        palette: ColorPalette,
    ) -> PositionedLayout:
        """Convert strategy result to PositionedLayout."""
        layout = PositionedLayout(
            slide_width_inches=SLIDE_WIDTH_INCHES,
            slide_height_inches=SLIDE_HEIGHT_INCHES,
            background_color=palette.background,
            elements=[],
            connectors=[],
        )

        # Add title and subtitle
        title_elem, subtitle_elem = self._create_title_elements(
            input_data.title, input_data.subtitle, palette
        )
        if title_elem:
            layout.title = title_elem
        if subtitle_elem:
            layout.subtitle = subtitle_elem

        # Convert ElementPosition to PositionedElement
        for elem_pos in result.elements:
            positioned_elem = self._convert_element(elem_pos, palette)
            layout.elements.append(positioned_elem)

        # Convert ConnectorPosition to PositionedConnector
        for conn_pos in result.connectors:
            positioned_conn = self._convert_connector(conn_pos)
            layout.connectors.append(positioned_conn)

        return layout

    def _convert_element(
        self,
        elem_pos: ElementPosition,
        palette: ColorPalette,
    ) -> PositionedElement:
        """Convert ElementPosition to PositionedElement with text measurement."""
        # Fit text to element
        text = None
        if elem_pos.block_data.label:
            fit_result = fit_text_to_width(
                elem_pos.block_data.label,
                elem_pos.width,
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=18,
                min_font_size=10,
                bold=True,
                allow_wrap=True,
                max_lines=3,
            )

            # Determine text color (light on dark backgrounds)
            text_color = self._contrast_text_color(elem_pos.fill_color)

            text = PositionedText(
                content=elem_pos.block_data.label,
                lines=fit_result.lines,
                font_size_pt=fit_result.font_size,
                font_family=DEFAULT_FONT_FAMILY,
                bold=True,
                color=text_color,
                alignment=TextAlignment.CENTER,
            )

        # Map shape type to ElementType
        element_type = self._map_shape_to_element_type(elem_pos.shape_type)

        return PositionedElement(
            id=elem_pos.element_id,
            element_type=element_type,
            x_inches=elem_pos.x,
            y_inches=elem_pos.y,
            width_inches=elem_pos.width,
            height_inches=elem_pos.height,
            fill_color=elem_pos.fill_color,
            stroke_color=elem_pos.stroke_color,
            corner_radius_inches=elem_pos.corner_radius,
            text=text,
            z_order=elem_pos.z_order,
            shape_hint=elem_pos.shape_type,
            arrow_direction=elem_pos.arrow_direction,
            custom_path=elem_pos.custom_path,
            layer_id=elem_pos.block_data.layer_id,
        )

    def _convert_connector(
        self,
        conn_pos: ConnectorPosition,
    ) -> PositionedConnector:
        """Convert ConnectorPosition to PositionedConnector."""
        # Map style string to enum
        style_map = {
            'arrow': ConnectorStyle.ARROW,
            'plain': ConnectorStyle.PLAIN,
            'dashed': ConnectorStyle.DASHED,
            'bidirectional': ConnectorStyle.BIDIRECTIONAL,
        }
        style = style_map.get(conn_pos.style, ConnectorStyle.ARROW)

        # Map routing string to enum
        routing_map = {
            'direct': RoutingStyle.DIRECT,
            'orthogonal': RoutingStyle.ORTHOGONAL,
            'curved': RoutingStyle.CURVED,
            'stepped': RoutingStyle.STEPPED,
        }
        routing = routing_map.get(conn_pos.routing, RoutingStyle.DIRECT)

        # Handle label if present
        label_text = None
        if conn_pos.label:
            label_text = PositionedText(
                content=conn_pos.label,
                lines=[conn_pos.label],
                font_size_pt=10,
                font_family=DEFAULT_FONT_FAMILY,
                color=conn_pos.color,
            )

        return PositionedConnector(
            id=conn_pos.connector_id,
            start_x=conn_pos.start_x,
            start_y=conn_pos.start_y,
            end_x=conn_pos.end_x,
            end_y=conn_pos.end_y,
            style=style,
            color=conn_pos.color,
            stroke_width_pt=conn_pos.stroke_width,
            label=label_text,
            from_element_id=conn_pos.from_element_id,
            to_element_id=conn_pos.to_element_id,
            waypoints=conn_pos.waypoints,
            routing_style=routing,
        )

    def _map_shape_to_element_type(self, shape_type: str) -> ElementType:
        """Map shape type string to ElementType enum."""
        mapping = {
            'rectangle': ElementType.BLOCK,
            'rounded_rect': ElementType.BLOCK,
            'trapezoid': ElementType.BLOCK,
            'ellipse': ElementType.ELLIPSE,
            'circle': ElementType.ELLIPSE,
            'chevron': ElementType.BLOCK,
            'arrow': ElementType.BLOCK,
            'band': ElementType.BAND,
            'label': ElementType.LABEL,
            'text_box': ElementType.TEXT_BOX,
        }
        return mapping.get(shape_type, ElementType.BLOCK)

    def _create_title_elements(
        self,
        title: str,
        subtitle: Optional[str],
        palette: ColorPalette,
    ) -> tuple:
        """Create title and subtitle PositionedElements."""
        title_elem = None
        subtitle_elem = None

        if title:
            fit_result = fit_text_to_width(
                title,
                CONTENT_WIDTH,
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=TITLE_FONT_SIZE_PT,
                min_font_size=18,
                bold=True,
                allow_wrap=True,
                max_lines=2,
            )

            title_text = PositionedText(
                content=title,
                lines=fit_result.lines,
                font_size_pt=fit_result.font_size,
                font_family=DEFAULT_FONT_FAMILY,
                bold=True,
                color=DEFAULT_TEXT_COLOR,
                alignment=TextAlignment.CENTER,
            )

            title_elem = PositionedElement(
                id="title",
                element_type=ElementType.TITLE,
                x_inches=CONTENT_LEFT,
                y_inches=MARGIN_TOP,
                width_inches=CONTENT_WIDTH,
                height_inches=TITLE_HEIGHT,
                fill_color="transparent",
                text=title_text,
                z_order=100,
            )

        if subtitle:
            fit_result = fit_text_to_width(
                subtitle,
                CONTENT_WIDTH,
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=SUBTITLE_FONT_SIZE_PT,
                min_font_size=12,
                bold=False,
                allow_wrap=True,
                max_lines=2,
            )

            subtitle_text = PositionedText(
                content=subtitle,
                lines=fit_result.lines,
                font_size_pt=fit_result.font_size,
                font_family=DEFAULT_FONT_FAMILY,
                bold=False,
                color="#666666",
                alignment=TextAlignment.CENTER,
            )

            subtitle_elem = PositionedElement(
                id="subtitle",
                element_type=ElementType.SUBTITLE,
                x_inches=CONTENT_LEFT,
                y_inches=MARGIN_TOP + TITLE_HEIGHT,
                width_inches=CONTENT_WIDTH,
                height_inches=SUBTITLE_HEIGHT,
                fill_color="transparent",
                text=subtitle_text,
                z_order=100,
            )

        return (title_elem, subtitle_elem)

    def _contrast_text_color(self, bg_color: str) -> str:
        """Determine light or dark text color based on background."""
        bg_color = bg_color.lstrip('#')
        if len(bg_color) != 6:
            return DEFAULT_TEXT_COLOR

        try:
            r = int(bg_color[0:2], 16)
            g = int(bg_color[2:4], 16)
            b = int(bg_color[4:6], 16)
        except ValueError:
            return DEFAULT_TEXT_COLOR

        # Relative luminance
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

        return self.palette.text_light if luminance < 0.5 else self.palette.text_dark

    def _apply_overlays(
        self,
        layout: PositionedLayout,
        overlays: List[OverlaySpec],
        palette: ColorPalette,
    ) -> PositionedLayout:
        """
        Apply overlays to the layout.

        This is handled by the OverlayEngine, but we provide a basic
        implementation here for simple cases.
        """
        # Import overlay engine (created in Phase 4)
        try:
            from .overlay_system import OverlayEngine
            overlay_engine = OverlayEngine()
            return overlay_engine.apply_overlays(layout, overlays, palette)
        except ImportError:
            # Fallback: just add overlay elements directly
            for overlay in overlays:
                for elem in overlay.elements:
                    # Calculate overlay position
                    overlay_x, overlay_y = self._calculate_overlay_position(
                        layout, overlay
                    )

                    positioned = PositionedElement(
                        id=elem.element_id,
                        element_type=ElementType.BLOCK,
                        x_inches=overlay_x + elem.x,
                        y_inches=overlay_y + elem.y,
                        width_inches=elem.width,
                        height_inches=elem.height,
                        fill_color=elem.fill_color or palette.primary,
                        stroke_color=elem.stroke_color,
                        text=PositionedText(
                            content=elem.content,
                            lines=[elem.content],
                            font_size_pt=elem.font_size,
                            font_family=DEFAULT_FONT_FAMILY,
                            bold=elem.bold,
                            color=elem.text_color or DEFAULT_TEXT_COLOR,
                        ) if elem.content else None,
                        z_order=50,
                        arrow_direction=elem.arrow_direction,
                    )
                    layout.elements.append(positioned)

            return layout

    def _calculate_overlay_position(
        self,
        layout: PositionedLayout,
        overlay: OverlaySpec,
    ) -> tuple:
        """Calculate the base position for an overlay."""
        position = overlay.position.value
        margin = overlay.margin_from_diagram

        if position == 'left':
            return (CONTENT_LEFT - overlay.width - margin, CONTENT_TOP)
        elif position == 'right':
            return (CONTENT_LEFT + CONTENT_WIDTH + margin, CONTENT_TOP)
        elif position == 'top':
            return (CONTENT_LEFT, CONTENT_TOP - overlay.width - margin)
        elif position == 'bottom':
            return (CONTENT_LEFT, CONTENT_TOP + CONTENT_HEIGHT + margin)
        else:
            # Floating or anchored - use element position if specified
            return (CONTENT_LEFT, CONTENT_TOP)

    def _create_error_layout(
        self,
        title: str,
        error_message: str,
    ) -> PositionedLayout:
        """Create an error layout when validation fails."""
        layout = PositionedLayout(
            slide_width_inches=SLIDE_WIDTH_INCHES,
            slide_height_inches=SLIDE_HEIGHT_INCHES,
            background_color="#FFFFFF",
            elements=[],
            connectors=[],
        )

        # Add title
        title_elem, _ = self._create_title_elements(title, error_message, self.palette)
        if title_elem:
            layout.title = title_elem

        # Add error message element
        error_text = PositionedText(
            content=f"Error: {error_message}",
            lines=[f"Error: {error_message}"],
            font_size_pt=14,
            font_family=DEFAULT_FONT_FAMILY,
            color="#CC0000",
        )

        error_elem = PositionedElement(
            id="error",
            element_type=ElementType.TEXT_BOX,
            x_inches=CONTENT_LEFT,
            y_inches=CONTENT_TOP + 1,
            width_inches=CONTENT_WIDTH,
            height_inches=1.0,
            fill_color="#FFEEEE",
            stroke_color="#CC0000",
            text=error_text,
            z_order=10,
        )
        layout.elements.append(error_elem)

        return layout


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_universal_layout(
    archetype_id: str,
    input_data: DiagramInput,
    overlays: Optional[List[OverlaySpec]] = None,
    palette: Optional[ColorPalette] = None,
) -> PositionedLayout:
    """
    Convenience function to create a layout using the universal system.

    Args:
        archetype_id: ID of the archetype to use (e.g., "funnel", "pyramid")
        input_data: Diagram input data
        overlays: Optional overlay specifications
        palette: Optional color palette

    Returns:
        PositionedLayout ready for rendering
    """
    from .archetype_rules import get_predefined_rules

    # Get rules for archetype
    rules = get_predefined_rules(archetype_id)
    if not rules:
        # Fall back to freeform if archetype not found
        from .archetype_rules import ArchetypeRules, LayoutStrategy
        rules = ArchetypeRules(
            archetype_id=archetype_id,
            display_name=archetype_id.title(),
            description=f"Custom archetype: {archetype_id}",
            layout_strategy=LayoutStrategy.FREEFORM,
        )

    # Create and generate layout
    archetype = UniversalArchetype(rules, palette)
    return archetype.generate_layout(input_data, overlays)
