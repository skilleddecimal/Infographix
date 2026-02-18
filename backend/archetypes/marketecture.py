"""
marketecture.py — Marketecture (Layered Architecture) Archetype.

The classic enterprise architecture diagram:
- Horizontal layers representing tiers (UI, Services, Data, etc.)
- Blocks within each layer representing components
- Optional cross-cutting layers (Security, Monitoring, etc.)
- Connectors showing relationships

Example prompts:
- "Create a 3-tier web architecture with frontend, API, and database"
- "Show our microservices architecture with gateway, services, and data layer"
- "Enterprise architecture with presentation, business logic, and persistence"
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field

from .base import (
    BaseArchetype,
    DiagramInput,
    BlockData,
    LayerData,
    ColorPalette,
)
from ..engine.positioned import (
    PositionedLayout,
    PositionedElement,
    PositionedText,
    ElementType,
    TextAlignment,
)
from ..engine.units import (
    SLIDE_WIDTH_INCHES,
    SLIDE_HEIGHT_INCHES,
    CONTENT_LEFT,
    CONTENT_TOP,
    CONTENT_WIDTH,
    CONTENT_HEIGHT,
    GUTTER_H,
    GUTTER_V,
    CROSS_CUT_HEIGHT,
    DEFAULT_FONT_FAMILY,
    DEFAULT_TEXT_COLOR,
)
from ..engine.text_measure import fit_text_to_width
from ..engine.grid_layout import (
    compute_layered_layout,
    RowConfig,
    compute_full_width_band,
)


# =============================================================================
# MARKETECTURE-SPECIFIC CONFIGURATION
# =============================================================================

@dataclass
class MarketectureConfig:
    """Configuration options for marketecture layout."""
    layer_gutter: float = GUTTER_V * 1.5      # Vertical gap between layers
    block_gutter: float = GUTTER_H            # Horizontal gap between blocks
    min_layer_height: float = 0.8             # Minimum layer height
    max_layer_height: float = 1.6             # Maximum layer height
    cross_cut_height: float = CROSS_CUT_HEIGHT
    show_layer_labels: bool = True            # Show layer name labels
    layer_label_width: float = 1.2            # Width reserved for layer labels
    connector_style: str = "arrow"            # Default connector style


# =============================================================================
# MARKETECTURE ARCHETYPE
# =============================================================================

class MarketectureArchetype(BaseArchetype):
    """
    Marketecture (Layered Architecture) diagram archetype.

    Creates horizontal layered architecture diagrams where:
    - Each layer represents a tier (UI, API, Data, etc.)
    - Blocks within layers represent components
    - Cross-cutting layers span the full width
    - Connectors show data flow or dependencies
    """

    name = "marketecture"
    display_name = "Marketecture / Layered Architecture"
    description = "Horizontal layers with blocks representing system tiers and components"
    example_prompts = [
        "Create a 3-tier web architecture with frontend, API, and database",
        "Show our microservices with API gateway, services, and data stores",
        "Enterprise system with presentation, business, and data layers",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[MarketectureConfig] = None
    ):
        super().__init__(palette)
        self.config = config or MarketectureConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """
        Generate a marketecture layout from input data.

        Layout strategy:
        1. Parse layers and blocks
        2. Determine layer arrangement (top to bottom)
        3. Position blocks within each layer
        4. Add cross-cutting layers as bands
        5. Create connectors between related blocks
        """
        # Validate input
        errors = self.validate_input(input_data)
        if errors:
            # Return empty layout with error indication
            return self.create_empty_layout(
                title=input_data.title,
                subtitle=f"Layout error: {errors[0]}"
            )

        # Use palette from input if provided
        if input_data.palette:
            self.palette = input_data.palette

        # Create base layout
        layout = PositionedLayout(
            slide_width_inches=SLIDE_WIDTH_INCHES,
            slide_height_inches=SLIDE_HEIGHT_INCHES,
            background_color=self.palette.background,
            elements=[],
            connectors=[]
        )

        # Add title and subtitle
        title_elem, subtitle_elem = self.create_title_element(
            input_data.title,
            input_data.subtitle
        )
        if title_elem:
            layout.title = title_elem
        if subtitle_elem:
            layout.subtitle = subtitle_elem

        # Adjust content top if subtitle exists
        content_top = CONTENT_TOP
        if subtitle_elem:
            content_top += 0.3  # Extra space for subtitle

        # Organize blocks by layer
        layers = self._organize_layers(input_data)

        # Calculate layer heights
        layer_heights = self._calculate_layer_heights(
            layers,
            CONTENT_HEIGHT - (content_top - CONTENT_TOP)
        )

        # Position layers and blocks
        current_y = content_top
        block_positions: Dict[str, PositionedElement] = {}

        for layer_idx, (layer_info, layer_blocks) in enumerate(layers):
            layer_height = layer_heights[layer_idx]

            if layer_info and layer_info.is_cross_cutting:
                # Cross-cutting layer (full-width band)
                elements = self._create_cross_cutting_layer(
                    layer_info,
                    current_y,
                    layer_height,
                    layer_idx
                )
            else:
                # Regular layer with blocks
                elements = self._create_regular_layer(
                    layer_info,
                    layer_blocks,
                    current_y,
                    layer_height,
                    layer_idx
                )

            for elem in elements:
                layout.elements.append(elem)
                block_positions[elem.id] = elem

            current_y += layer_height + self.config.layer_gutter

        # Create connectors
        for conn_idx, conn_data in enumerate(input_data.connectors):
            if conn_data.from_id in block_positions and conn_data.to_id in block_positions:
                connector = self.create_connector(
                    conn_data,
                    block_positions[conn_data.from_id],
                    block_positions[conn_data.to_id],
                    f"connector_{conn_idx}"
                )
                layout.connectors.append(connector)

        return layout

    def _organize_layers(
        self,
        input_data: DiagramInput
    ) -> List[tuple]:
        """
        Organize blocks into layers.

        Returns list of (LayerData or None, List[BlockData]) tuples.
        Blocks without a layer are grouped into an "auto" layer.
        """
        # Build layer lookup
        layer_lookup = {layer.id: layer for layer in input_data.layers}
        block_lookup = {block.id: block for block in input_data.blocks}

        # Group blocks by layer
        layer_blocks: Dict[str, List[BlockData]] = {}
        unassigned_blocks: List[BlockData] = []

        for block in input_data.blocks:
            if block.layer_id and block.layer_id in layer_lookup:
                if block.layer_id not in layer_blocks:
                    layer_blocks[block.layer_id] = []
                layer_blocks[block.layer_id].append(block)
            else:
                unassigned_blocks.append(block)

        # Build result in layer order
        result = []

        # Add explicit layers in order
        for layer in input_data.layers:
            blocks = layer_blocks.get(layer.id, [])
            result.append((layer, blocks))

        # Add unassigned blocks as auto layer
        if unassigned_blocks:
            result.append((None, unassigned_blocks))

        # If no layers defined, treat all blocks as single layer
        if not result:
            result.append((None, input_data.blocks))

        return result

    def _calculate_layer_heights(
        self,
        layers: List[tuple],
        available_height: float
    ) -> List[float]:
        """
        Calculate height for each layer.

        Cross-cutting layers get fixed height.
        Regular layers share remaining space proportionally to block count.
        """
        num_layers = len(layers)
        if num_layers == 0:
            return []

        # Total gutter space
        total_gutter = self.config.layer_gutter * (num_layers - 1)
        available = available_height - total_gutter

        # Identify cross-cutting vs regular layers
        cross_cut_count = sum(
            1 for layer_info, _ in layers
            if layer_info and layer_info.is_cross_cutting
        )
        regular_count = num_layers - cross_cut_count

        # Reserve space for cross-cutting layers
        cross_cut_total = cross_cut_count * self.config.cross_cut_height
        regular_available = available - cross_cut_total

        # Calculate regular layer height
        if regular_count > 0:
            regular_height = regular_available / regular_count
            regular_height = max(
                self.config.min_layer_height,
                min(self.config.max_layer_height, regular_height)
            )
        else:
            regular_height = self.config.min_layer_height

        # Assign heights
        heights = []
        for layer_info, blocks in layers:
            if layer_info and layer_info.is_cross_cutting:
                heights.append(self.config.cross_cut_height)
            else:
                heights.append(regular_height)

        return heights

    def _create_regular_layer(
        self,
        layer_info: Optional[LayerData],
        blocks: List[BlockData],
        y_position: float,
        height: float,
        layer_index: int
    ) -> List[PositionedElement]:
        """
        Create elements for a regular layer with blocks.
        """
        elements = []

        if not blocks:
            return elements

        # Calculate block positions
        num_blocks = len(blocks)
        content_left = CONTENT_LEFT

        # Reserve space for layer label if showing
        if self.config.show_layer_labels and layer_info:
            content_left += self.config.layer_label_width

        available_width = CONTENT_WIDTH
        if self.config.show_layer_labels and layer_info:
            available_width -= self.config.layer_label_width

        total_gutter = self.config.block_gutter * (num_blocks - 1) if num_blocks > 1 else 0
        block_width = (available_width - total_gutter) / num_blocks

        # Clamp block width
        block_width = min(block_width, 3.0)  # Max 3 inches wide

        # Center blocks if they don't fill the width
        actual_total_width = block_width * num_blocks + total_gutter
        start_x = content_left + (available_width - actual_total_width) / 2

        # Create block elements
        for i, block in enumerate(blocks):
            x = start_x + i * (block_width + self.config.block_gutter)

            element = self.create_block_element(
                block,
                x=x,
                y=y_position,
                width=block_width,
                height=height,
                color_index=layer_index,
                z_order=10 + layer_index
            )
            elements.append(element)

        # Add layer label if configured
        if self.config.show_layer_labels and layer_info:
            label_elem = self._create_layer_label(
                layer_info,
                CONTENT_LEFT,
                y_position,
                self.config.layer_label_width - 0.1,
                height,
                layer_index
            )
            elements.append(label_elem)

        return elements

    def _create_cross_cutting_layer(
        self,
        layer_info: LayerData,
        y_position: float,
        height: float,
        layer_index: int
    ) -> List[PositionedElement]:
        """
        Create a full-width cross-cutting layer band.
        """
        # Determine band color
        band_color = layer_info.color or self.palette.get_color_for_index(layer_index + 3)

        # Fit label text
        fit_result = fit_text_to_width(
            layer_info.label,
            CONTENT_WIDTH - 0.5,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=14,
            min_font_size=10,
            bold=True
        )

        text_color = self._contrast_text_color(band_color)

        band_text = PositionedText(
            content=layer_info.label,
            lines=fit_result.lines,
            font_size_pt=fit_result.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            color=text_color,
            alignment=TextAlignment.CENTER
        )

        band_element = PositionedElement(
            id=f"layer_{layer_info.id}",
            element_type=ElementType.BAND,
            x_inches=CONTENT_LEFT,
            y_inches=y_position,
            width_inches=CONTENT_WIDTH,
            height_inches=height,
            fill_color=band_color,
            text=band_text,
            layer_id=layer_info.id,
            z_order=5,  # Behind regular blocks
            opacity=0.9
        )

        return [band_element]

    def _create_layer_label(
        self,
        layer_info: LayerData,
        x: float,
        y: float,
        width: float,
        height: float,
        layer_index: int
    ) -> PositionedElement:
        """
        Create a layer label element.

        Labels are displayed horizontally (not rotated) with text that
        fits within the label area. Font size matches nearby blocks.
        """
        # Use a font size that's closer to block labels for visual consistency
        # Allow wrapping to 2 lines max within the available width
        fit_result = fit_text_to_width(
            layer_info.label,
            width,  # Use actual width
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=14,
            min_font_size=9,
            bold=True,
            allow_wrap=True,
            max_lines=2
        )

        label_text = PositionedText(
            content=layer_info.label,
            lines=fit_result.lines,
            font_size_pt=fit_result.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            color="#666666",
            alignment=TextAlignment.CENTER
        )

        return PositionedElement(
            id=f"label_{layer_info.id}",
            element_type=ElementType.LABEL,
            x_inches=x,
            y_inches=y,
            width_inches=width,
            height_inches=height,
            fill_color="transparent",
            text=label_text,
            layer_id=layer_info.id,
            z_order=20
        )

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """
        Validate input for marketecture layout.
        """
        errors = super().validate_input(input_data)

        # Marketecture-specific validation
        if len(input_data.blocks) > 20:
            errors.append("Too many blocks for marketecture (max 20)")

        if len(input_data.layers) > 6:
            errors.append("Too many layers for marketecture (max 6)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_marketecture(
    title: str,
    layers: Dict[str, List[str]],
    subtitle: Optional[str] = None,
    cross_cutting: Optional[List[str]] = None
) -> PositionedLayout:
    """
    Quick helper to create a marketecture diagram from simple inputs.

    Args:
        title: Diagram title
        layers: Dict mapping layer name to list of block labels
        subtitle: Optional subtitle
        cross_cutting: List of cross-cutting layer names

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_marketecture(
            title="Web Application Architecture",
            layers={
                "Frontend": ["React App", "Admin Portal"],
                "API Layer": ["REST API", "GraphQL"],
                "Data": ["PostgreSQL", "Redis", "S3"]
            },
            cross_cutting=["Security", "Monitoring"]
        )
    """
    cross_cutting = cross_cutting or []

    # Build input data
    blocks = []
    layer_data = []
    block_id = 0

    for layer_name, block_labels in layers.items():
        layer_id = f"layer_{layer_name.lower().replace(' ', '_')}"
        is_cross = layer_name in cross_cutting

        layer_data.append(LayerData(
            id=layer_id,
            label=layer_name,
            blocks=[],
            is_cross_cutting=is_cross
        ))

        for label in block_labels:
            bid = f"block_{block_id}"
            blocks.append(BlockData(
                id=bid,
                label=label,
                layer_id=layer_id
            ))
            layer_data[-1].blocks.append(bid)
            block_id += 1

    # Add standalone cross-cutting layers
    for cc_name in cross_cutting:
        if cc_name not in layers:
            layer_id = f"layer_{cc_name.lower().replace(' ', '_')}"
            layer_data.append(LayerData(
                id=layer_id,
                label=cc_name,
                blocks=[],
                is_cross_cutting=True
            ))

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks,
        layers=layer_data
    )

    archetype = MarketectureArchetype()
    return archetype.generate_layout(input_data)
