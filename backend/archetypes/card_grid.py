"""
card_grid.py — Card Grid Archetype.

Grid of cards with titles and descriptions:
- Feature cards with header and description
- Team member cards
- Service offerings
- Product highlights

Example prompts:
- "Our services overview"
- "Team members"
- "Product features with descriptions"
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

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
)
from ..engine.text_measure import fit_text_to_width


# =============================================================================
# CARD GRID CONFIGURATION
# =============================================================================

@dataclass
class CardGridConfig:
    """Configuration options for card grid layout."""
    max_columns: int = 3                      # Maximum columns
    min_columns: int = 2                      # Minimum columns
    card_padding: float = 0.15                # Padding inside cards
    header_height_ratio: float = 0.25         # Header takes this % of card height
    show_header_bar: bool = True              # Show colored header bar
    corner_radius: float = 0.08               # Card corner radius


# =============================================================================
# CARD GRID ARCHETYPE
# =============================================================================

class CardGridArchetype(BaseArchetype):
    """
    Card Grid diagram archetype.

    Creates grid layouts where:
    - Each card has a header and optional description
    - Cards arranged in uniform grid
    - Great for features, services, team members
    - Professional, clean appearance
    """

    name = "card_grid"
    display_name = "Card Grid"
    description = "Grid of cards with headers and descriptions"
    example_prompts = [
        "Our service offerings",
        "Team member profiles",
        "Product features overview",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[CardGridConfig] = None
    ):
        super().__init__(palette)
        self.config = config or CardGridConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a card grid layout from input data."""
        errors = self.validate_input(input_data)
        if errors:
            return self.create_empty_layout(
                title=input_data.title,
                subtitle=f"Layout error: {errors[0]}"
            )

        if input_data.palette:
            self.palette = input_data.palette

        layout = PositionedLayout(
            slide_width_inches=SLIDE_WIDTH_INCHES,
            slide_height_inches=SLIDE_HEIGHT_INCHES,
            background_color=self.palette.background,
            elements=[],
            connectors=[]
        )

        title_elem, subtitle_elem = self.create_title_element(
            input_data.title,
            input_data.subtitle
        )
        if title_elem:
            layout.title = title_elem
        if subtitle_elem:
            layout.subtitle = subtitle_elem

        content_top = CONTENT_TOP
        if subtitle_elem:
            content_top += 0.3

        content_height = CONTENT_HEIGHT - (content_top - CONTENT_TOP)

        # Create card elements
        elements = self._create_card_grid(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _calculate_grid_dimensions(self, num_items: int) -> Tuple[int, int]:
        """Calculate optimal rows and columns for the grid."""
        import math

        if num_items <= self.config.max_columns:
            return 1, num_items

        # Find best column count
        for cols in range(self.config.max_columns, self.config.min_columns - 1, -1):
            rows = math.ceil(num_items / cols)
            if rows * cols >= num_items and rows <= 3:  # Max 3 rows
                return rows, cols

        # Fallback
        cols = self.config.max_columns
        rows = math.ceil(num_items / cols)
        return rows, cols

    def _create_card_grid(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create the card grid elements."""
        elements = []
        num_items = len(blocks)

        if num_items == 0:
            return elements

        rows, cols = self._calculate_grid_dimensions(num_items)

        # Calculate card dimensions
        card_width = (CONTENT_WIDTH - (cols - 1) * GUTTER_H) / cols
        card_height = (content_height - (rows - 1) * GUTTER_V) / rows

        # Limit card height
        max_card_height = 2.0
        if card_height > max_card_height:
            card_height = max_card_height
            # Recenter vertically
            total_height = rows * card_height + (rows - 1) * GUTTER_V
            content_top = content_top + (content_height - total_height) / 2

        # Create cards
        for i, block in enumerate(blocks):
            row = i // cols
            col = i % cols

            x = CONTENT_LEFT + col * (card_width + GUTTER_H)
            y = content_top + row * (card_height + GUTTER_V)

            card_elements = self._create_card(
                block,
                x,
                y,
                card_width,
                card_height,
                i
            )
            elements.extend(card_elements)

        return elements

    def _create_card(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        height: float,
        card_idx: int
    ) -> List[PositionedElement]:
        """Create a single card with header and description."""
        elements = []

        fill_color = block.color or self.palette.get_color_for_index(card_idx)
        padding = self.config.card_padding

        # Card background (white/light)
        card_bg = PositionedElement(
            id=f"{block.id}_bg",
            element_type=ElementType.BLOCK,
            x_inches=x,
            y_inches=y,
            width_inches=width,
            height_inches=height,
            fill_color="#FFFFFF",
            stroke_color=self.palette.border,
            stroke_width_pt=0.75,
            corner_radius_inches=self.config.corner_radius,
            z_order=5 + card_idx
        )
        elements.append(card_bg)

        # Header bar (colored top section)
        if self.config.show_header_bar:
            header_height = height * self.config.header_height_ratio

            header_bar = PositionedElement(
                id=f"{block.id}_header",
                element_type=ElementType.BLOCK,
                x_inches=x,
                y_inches=y,
                width_inches=width,
                height_inches=header_height,
                fill_color=fill_color,
                stroke_color=None,
                stroke_width_pt=0,
                corner_radius_inches=self.config.corner_radius,
                z_order=6 + card_idx
            )
            elements.append(header_bar)

            # Header text
            fit_result = fit_text_to_width(
                block.label,
                width - padding * 2,
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=11,
                min_font_size=8,
                bold=True,
                allow_wrap=True,
                max_lines=2
            )

            text_color = self._contrast_text_color(fill_color)
            header_text = PositionedText(
                content=block.label,
                lines=fit_result.lines,
                font_size_pt=fit_result.font_size,
                font_family=DEFAULT_FONT_FAMILY,
                bold=True,
                color=text_color,
                alignment=TextAlignment.CENTER
            )

            header_text_elem = PositionedElement(
                id=f"{block.id}_header_text",
                element_type=ElementType.TEXT_BOX,
                x_inches=x + padding,
                y_inches=y + padding * 0.5,
                width_inches=width - padding * 2,
                height_inches=header_height - padding,
                fill_color=None,
                stroke_color=None,
                stroke_width_pt=0,
                text=header_text,
                z_order=7 + card_idx
            )
            elements.append(header_text_elem)

            # Description (if provided)
            if block.description:
                desc_y = y + header_height + padding
                desc_height = height - header_height - padding * 2

                fit_desc = fit_text_to_width(
                    block.description,
                    width - padding * 2,
                    font_family=DEFAULT_FONT_FAMILY,
                    max_font_size=10,
                    min_font_size=8,
                    bold=False,
                    allow_wrap=True,
                    max_lines=4
                )

                desc_text = PositionedText(
                    content=block.description,
                    lines=fit_desc.lines,
                    font_size_pt=fit_desc.font_size,
                    font_family=DEFAULT_FONT_FAMILY,
                    bold=False,
                    color=self.palette.text_dark,
                    alignment=TextAlignment.LEFT
                )

                desc_elem = PositionedElement(
                    id=f"{block.id}_desc",
                    element_type=ElementType.TEXT_BOX,
                    x_inches=x + padding,
                    y_inches=desc_y,
                    width_inches=width - padding * 2,
                    height_inches=desc_height,
                    fill_color=None,
                    stroke_color=None,
                    stroke_width_pt=0,
                    text=desc_text,
                    z_order=8 + card_idx
                )
                elements.append(desc_elem)

        else:
            # No header bar - just centered text
            fit_result = fit_text_to_width(
                block.label,
                width - padding * 2,
                font_family=DEFAULT_FONT_FAMILY,
                max_font_size=12,
                min_font_size=9,
                bold=True,
                allow_wrap=True,
                max_lines=3
            )

            label_text = PositionedText(
                content=block.label,
                lines=fit_result.lines,
                font_size_pt=fit_result.font_size,
                font_family=DEFAULT_FONT_FAMILY,
                bold=True,
                color=self.palette.text_dark,
                alignment=TextAlignment.CENTER
            )

            text_elem = PositionedElement(
                id=f"{block.id}_text",
                element_type=ElementType.TEXT_BOX,
                x_inches=x + padding,
                y_inches=y + padding,
                width_inches=width - padding * 2,
                height_inches=height - padding * 2,
                fill_color=None,
                stroke_color=None,
                stroke_width_pt=0,
                text=label_text,
                z_order=7 + card_idx
            )
            elements.append(text_elem)

        return elements

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for card grid layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 2:
            errors.append("Card grid requires at least 2 items")

        if len(input_data.blocks) > 9:
            errors.append("Too many items for card grid (max 9)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_card_grid(
    title: str,
    cards: List[Dict[str, str]],
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a card grid diagram.

    Args:
        title: Diagram title
        cards: List of dicts with 'label' and optional 'description'
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_card_grid(
            title="Our Services",
            cards=[
                {"label": "Consulting", "description": "Expert guidance"},
                {"label": "Development", "description": "Custom solutions"},
                {"label": "Support", "description": "24/7 assistance"},
            ]
        )
    """
    blocks = [
        BlockData(
            id=f"card_{i}",
            label=card.get("label", ""),
            description=card.get("description")
        )
        for i, card in enumerate(cards)
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    archetype = CardGridArchetype()
    return archetype.generate_layout(input_data)
