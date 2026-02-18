"""
comparison.py — Comparison / Side-by-Side Archetype.

Side-by-side comparison diagrams:
- 2-4 columns comparing items/options
- Optional row headers for comparison criteria
- Highlights for recommended option
- Support for feature matrices

Example prompts:
- "Compare AWS, Azure, and GCP cloud platforms"
- "Feature comparison between Basic, Pro, and Enterprise plans"
- "Before/After comparison of the architecture"
"""

from typing import List, Dict, Optional, Tuple
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
    PositionedConnector,
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
    DEFAULT_FONT_FAMILY,
    DEFAULT_TEXT_COLOR,
)
from ..engine.text_measure import fit_text_to_width


# =============================================================================
# COMPARISON CONFIGURATION
# =============================================================================

@dataclass
class ComparisonConfig:
    """Configuration options for comparison layout."""
    column_gutter: float = GUTTER_H * 1.5   # Gap between columns
    row_gutter: float = GUTTER_V            # Gap between rows
    header_height: float = 0.8              # Height for column headers
    row_height: float = 0.6                 # Height for comparison rows
    min_column_width: float = 2.0           # Minimum column width
    show_column_headers: bool = True        # Show column header row
    highlight_recommended: bool = True      # Highlight recommended option
    recommended_keyword: str = "recommended" # Keyword to identify recommended


# =============================================================================
# COMPARISON ARCHETYPE
# =============================================================================

class ComparisonArchetype(BaseArchetype):
    """
    Comparison diagram archetype.

    Creates side-by-side comparison layouts where:
    - Columns represent items being compared (products, options, etc.)
    - Rows represent comparison criteria or features
    - Optional highlighting for recommended option
    - Support for 2-4 columns
    """

    name = "comparison"
    display_name = "Comparison / Side-by-Side"
    description = "Side-by-side columns comparing items, features, or options"
    example_prompts = [
        "Compare AWS, Azure, and GCP cloud platforms",
        "Feature comparison: Basic vs Pro vs Enterprise",
        "Before and After architecture comparison",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[ComparisonConfig] = None
    ):
        super().__init__(palette)
        self.config = config or ComparisonConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """
        Generate a comparison layout from input data.

        Layout strategy:
        1. Determine number of columns from layers or blocks
        2. Create column headers
        3. Distribute items into columns
        4. Apply highlighting to recommended column
        """
        # Validate input
        errors = self.validate_input(input_data)
        if errors:
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

        # Adjust content area
        content_top = CONTENT_TOP
        if subtitle_elem:
            content_top += 0.3

        content_height = CONTENT_HEIGHT - (content_top - CONTENT_TOP)

        # Organize into columns
        columns = self._organize_columns(input_data)

        if not columns:
            return layout

        # Create column elements
        elements = self._create_comparison_layout(
            columns,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _organize_columns(self, input_data: DiagramInput) -> List[Dict]:
        """
        Organize blocks into comparison columns.

        If layers are defined, each layer becomes a column.
        Otherwise, blocks are distributed evenly across columns.

        Returns list of column dicts with 'header' and 'items' keys.
        """
        columns = []

        if input_data.layers:
            # Use layers as columns
            layer_lookup = {layer.id: layer for layer in input_data.layers}
            layer_blocks: Dict[str, List[BlockData]] = {}

            for block in input_data.blocks:
                if block.layer_id:
                    if block.layer_id not in layer_blocks:
                        layer_blocks[block.layer_id] = []
                    layer_blocks[block.layer_id].append(block)

            for layer in input_data.layers:
                is_recommended = self._is_recommended(layer.label)
                columns.append({
                    'header': layer.label,
                    'items': layer_blocks.get(layer.id, []),
                    'recommended': is_recommended,
                    'color': layer.color,
                })
        else:
            # No layers - treat each block as a column header
            for i, block in enumerate(input_data.blocks):
                is_recommended = self._is_recommended(block.label)
                columns.append({
                    'header': block.label,
                    'items': [],
                    'recommended': is_recommended,
                    'color': block.color,
                })

        return columns

    def _is_recommended(self, label: str) -> bool:
        """Check if a label indicates the recommended option."""
        if not self.config.highlight_recommended:
            return False
        lower_label = label.lower()
        return self.config.recommended_keyword.lower() in lower_label

    def _create_comparison_layout(
        self,
        columns: List[Dict],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """
        Create positioned elements for comparison columns.
        """
        elements = []

        num_columns = len(columns)
        if num_columns == 0:
            return elements

        # Calculate column dimensions
        total_gutter = self.config.column_gutter * (num_columns - 1)
        available_width = CONTENT_WIDTH - total_gutter
        column_width = available_width / num_columns
        column_width = max(self.config.min_column_width, column_width)

        # Center columns if they don't fill width
        actual_total_width = column_width * num_columns + total_gutter
        start_x = CONTENT_LEFT + (CONTENT_WIDTH - actual_total_width) / 2

        # Find max items per column (for row layout)
        max_items = max(len(col['items']) for col in columns) if columns else 0

        # Calculate row heights
        header_height = self.config.header_height if self.config.show_column_headers else 0
        available_for_rows = content_height - header_height - self.config.row_gutter

        if max_items > 0:
            row_height = min(
                self.config.row_height,
                (available_for_rows - self.config.row_gutter * (max_items - 1)) / max_items
            )
        else:
            row_height = self.config.row_height

        # Create column elements
        for col_idx, column in enumerate(columns):
            x = start_x + col_idx * (column_width + self.config.column_gutter)
            y = content_top

            # Determine column color
            if column['recommended']:
                fill_color = self.palette.primary
                header_bg = self.palette.primary
            else:
                fill_color = self.palette.get_color_for_index(col_idx)
                header_bg = fill_color

            # Create header
            if self.config.show_column_headers:
                header_elem = self._create_column_header(
                    column['header'],
                    x,
                    y,
                    column_width,
                    header_height,
                    header_bg,
                    col_idx,
                    column['recommended']
                )
                elements.append(header_elem)
                y += header_height + self.config.row_gutter

            # Create item blocks
            for item_idx, block in enumerate(column['items']):
                item_elem = self._create_item_block(
                    block,
                    x,
                    y,
                    column_width,
                    row_height,
                    col_idx,
                    item_idx
                )
                elements.append(item_elem)
                y += row_height + self.config.row_gutter

        return elements

    def _create_column_header(
        self,
        label: str,
        x: float,
        y: float,
        width: float,
        height: float,
        bg_color: str,
        col_idx: int,
        recommended: bool
    ) -> PositionedElement:
        """
        Create a column header element.
        """
        # Fit label text
        fit_result = fit_text_to_width(
            label,
            width - 0.2,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=16,
            min_font_size=11,
            bold=True,
            allow_wrap=True,
            max_lines=2
        )

        text_color = self._contrast_text_color(bg_color)

        header_text = PositionedText(
            content=label,
            lines=fit_result.lines,
            font_size_pt=fit_result.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            color=text_color,
            alignment=TextAlignment.CENTER
        )

        return PositionedElement(
            id=f"header_{col_idx}",
            element_type=ElementType.BLOCK,
            x_inches=x,
            y_inches=y,
            width_inches=width,
            height_inches=height,
            fill_color=bg_color,
            text=header_text,
            z_order=20 if recommended else 10
        )

    def _create_item_block(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        height: float,
        col_idx: int,
        item_idx: int
    ) -> PositionedElement:
        """
        Create an item block within a column.
        """
        # Use lighter shade for item blocks
        fill_color = block.color or self.palette.background

        fit_result = fit_text_to_width(
            block.label,
            width - 0.2,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=12,
            min_font_size=9,
            bold=False,
            allow_wrap=True,
            max_lines=2
        )

        text_color = self._contrast_text_color(fill_color)

        item_text = PositionedText(
            content=block.label,
            lines=fit_result.lines,
            font_size_pt=fit_result.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=False,
            color=text_color,
            alignment=TextAlignment.CENTER
        )

        return PositionedElement(
            id=block.id,
            element_type=ElementType.BLOCK,
            x_inches=x,
            y_inches=y,
            width_inches=width,
            height_inches=height,
            fill_color=fill_color,
            stroke_color=self.palette.border,
            stroke_width_pt=1.0,
            text=item_text,
            z_order=5
        )

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """
        Validate input for comparison layout.
        """
        errors = super().validate_input(input_data)

        # Comparison-specific validation
        num_columns = len(input_data.layers) if input_data.layers else len(input_data.blocks)

        if num_columns > 6:
            errors.append("Too many columns for comparison (max 6)")

        if num_columns < 2 and not input_data.layers:
            errors.append("Comparison requires at least 2 items")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_comparison(
    title: str,
    columns: Dict[str, List[str]],
    subtitle: Optional[str] = None,
    recommended: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a comparison diagram.

    Args:
        title: Diagram title
        columns: Dict mapping column header to list of feature/item labels
        subtitle: Optional subtitle
        recommended: Name of recommended column (will be highlighted)

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_comparison(
            title="Cloud Platform Comparison",
            columns={
                "AWS": ["EC2", "S3", "Lambda"],
                "Azure": ["VMs", "Blob Storage", "Functions"],
                "GCP": ["Compute Engine", "Cloud Storage", "Cloud Functions"]
            },
            recommended="AWS"
        )
    """
    # Build input data
    blocks = []
    layers = []
    block_id = 0

    for col_name, items in columns.items():
        layer_id = f"col_{col_name.lower().replace(' ', '_')}"

        # Mark as recommended in label if specified
        label = col_name
        if recommended and col_name == recommended:
            label = f"{col_name} (Recommended)"

        layers.append(LayerData(
            id=layer_id,
            label=label,
            blocks=[],
            is_cross_cutting=False
        ))

        for item in items:
            bid = f"item_{block_id}"
            blocks.append(BlockData(
                id=bid,
                label=item,
                layer_id=layer_id
            ))
            layers[-1].blocks.append(bid)
            block_id += 1

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks,
        layers=layers
    )

    archetype = ComparisonArchetype()
    return archetype.generate_layout(input_data)
