"""
bullet_list.py — Bullet List Archetype.

Simple vertical list with bullet points:
- Clean, scannable format
- Great for key points, takeaways, features
- Optional numbering
- Icons or bullet markers

Example prompts:
- "Key takeaways from the meeting"
- "Main benefits of our solution"
- "Action items"
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

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
    GUTTER_V,
    DEFAULT_FONT_FAMILY,
)
from ..engine.text_measure import fit_text_to_width


# =============================================================================
# BULLET LIST CONFIGURATION
# =============================================================================

class BulletStyle(Enum):
    """Style of bullet markers."""
    CIRCLE = "circle"             # Filled circle bullets
    NUMBERED = "numbered"         # 1, 2, 3...
    ICON = "icon"                 # Icon placeholders (colored circles)
    CHECK = "check"               # Checkmarks (uses colored circles for now)
    ARROW = "arrow"               # Arrow markers


@dataclass
class BulletListConfig:
    """Configuration options for bullet list layout."""
    bullet_style: BulletStyle = BulletStyle.CIRCLE
    bullet_size: float = 0.12              # Size of bullet marker
    bullet_text_gap: float = 0.2           # Gap between bullet and text
    item_spacing: float = GUTTER_V * 0.8   # Vertical spacing between items
    indent: float = 0.3                    # Left indent for content
    two_column_threshold: int = 6          # Switch to 2 columns after this many items


# =============================================================================
# BULLET LIST ARCHETYPE
# =============================================================================

class BulletListArchetype(BaseArchetype):
    """
    Bullet List diagram archetype.

    Creates vertical list layouts where:
    - Items displayed with bullet markers
    - Clean, scannable format
    - Supports single or two-column layout
    - Great for takeaways, features, action items
    """

    name = "bullet_list"
    display_name = "Bullet List"
    description = "Vertical list with bullet points"
    example_prompts = [
        "Key takeaways",
        "Action items from meeting",
        "Main benefits",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[BulletListConfig] = None
    ):
        super().__init__(palette)
        self.config = config or BulletListConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a bullet list layout from input data."""
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

        # Create list elements
        elements = self._create_bullet_list(
            input_data.blocks,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _create_bullet_list(
        self,
        blocks: List[BlockData],
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create the bullet list elements."""
        elements = []
        num_items = len(blocks)

        if num_items == 0:
            return elements

        # Determine layout (single or double column)
        use_two_columns = num_items > self.config.two_column_threshold

        if use_two_columns:
            column_width = (CONTENT_WIDTH - 0.3) / 2  # Gap between columns
            items_per_column = (num_items + 1) // 2
        else:
            column_width = CONTENT_WIDTH
            items_per_column = num_items

        # Calculate item height
        available_height = content_height - 0.2  # Some padding
        item_height = min(
            (available_height - (items_per_column - 1) * self.config.item_spacing) / items_per_column,
            0.6  # Max item height
        )

        # Create list items
        for i, block in enumerate(blocks):
            if use_two_columns:
                col = i // items_per_column
                row = i % items_per_column
                x = CONTENT_LEFT + col * (column_width + 0.3)
            else:
                col = 0
                row = i
                x = CONTENT_LEFT

            y = content_top + row * (item_height + self.config.item_spacing)

            item_elements = self._create_list_item(
                block,
                x,
                y,
                column_width,
                item_height,
                i
            )
            elements.extend(item_elements)

        return elements

    def _create_list_item(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        height: float,
        item_idx: int
    ) -> List[PositionedElement]:
        """Create a single list item with bullet and text."""
        elements = []

        fill_color = block.color or self.palette.get_color_for_index(item_idx)

        # Bullet marker
        bullet_x = x + self.config.indent
        bullet_y = y + (height - self.config.bullet_size) / 2

        if self.config.bullet_style == BulletStyle.NUMBERED:
            # Number marker
            number_text = PositionedText(
                content=str(item_idx + 1),
                lines=[str(item_idx + 1)],
                font_size_pt=11,
                font_family=DEFAULT_FONT_FAMILY,
                bold=True,
                color=fill_color,
                alignment=TextAlignment.CENTER
            )

            bullet_element = PositionedElement(
                id=f"{block.id}_bullet",
                element_type=ElementType.TEXT_BOX,
                x_inches=bullet_x - self.config.bullet_size / 2,
                y_inches=bullet_y,
                width_inches=self.config.bullet_size * 2,
                height_inches=self.config.bullet_size,
                fill_color=None,
                stroke_color=None,
                stroke_width_pt=0,
                text=number_text,
                z_order=10 + item_idx
            )
        else:
            # Circle/icon bullet
            bullet_element = PositionedElement(
                id=f"{block.id}_bullet",
                element_type=ElementType.ELLIPSE,
                x_inches=bullet_x,
                y_inches=bullet_y,
                width_inches=self.config.bullet_size,
                height_inches=self.config.bullet_size,
                fill_color=fill_color,
                stroke_color=None,
                stroke_width_pt=0,
                z_order=10 + item_idx
            )
        elements.append(bullet_element)

        # Text
        text_x = bullet_x + self.config.bullet_size + self.config.bullet_text_gap
        text_width = width - self.config.indent - self.config.bullet_size - self.config.bullet_text_gap - 0.1

        fit_result = fit_text_to_width(
            block.label,
            text_width,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=12,
            min_font_size=9,
            bold=False,
            allow_wrap=True,
            max_lines=2
        )

        label_text = PositionedText(
            content=block.label,
            lines=fit_result.lines,
            font_size_pt=fit_result.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=False,
            color=self.palette.text_dark,
            alignment=TextAlignment.LEFT
        )

        text_element = PositionedElement(
            id=f"{block.id}_text",
            element_type=ElementType.TEXT_BOX,
            x_inches=text_x,
            y_inches=y,
            width_inches=text_width,
            height_inches=height,
            fill_color=None,
            stroke_color=None,
            stroke_width_pt=0,
            text=label_text,
            z_order=11 + item_idx
        )
        elements.append(text_element)

        return elements

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for bullet list layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 1:
            errors.append("Bullet list requires at least 1 item")

        if len(input_data.blocks) > 12:
            errors.append("Too many items for bullet list (max 12)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_bullet_list(
    title: str,
    items: List[str],
    subtitle: Optional[str] = None,
    numbered: bool = False
) -> PositionedLayout:
    """
    Quick helper to create a bullet list diagram.

    Args:
        title: Diagram title
        items: List of item labels
        subtitle: Optional subtitle
        numbered: If True, use numbered list instead of bullets

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_bullet_list(
            title="Key Takeaways",
            items=["First point", "Second point", "Third point"]
        )
    """
    blocks = [
        BlockData(id=f"item_{i}", label=item)
        for i, item in enumerate(items)
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    config = BulletListConfig(
        bullet_style=BulletStyle.NUMBERED if numbered else BulletStyle.CIRCLE
    )

    archetype = BulletListArchetype(config=config)
    return archetype.generate_layout(input_data)
