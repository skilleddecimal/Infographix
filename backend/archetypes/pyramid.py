"""
pyramid.py — Pyramid / Hierarchy Archetype.

Triangular pyramid diagrams showing hierarchical levels:
- Wide base narrowing to top
- 3-7 levels typical
- Each level represents a tier of importance/hierarchy
- Optional inverted pyramid variant

Example prompts:
- "Maslow's hierarchy of needs"
- "Data-Information-Knowledge-Wisdom pyramid"
- "Organizational pyramid with leadership at top"
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

# Learned styles from template analysis
try:
    from ..engine.learned_styles import (
        generate_creative_pyramid_style,
        CreativeStyleGenerator,
    )
    LEARNED_STYLES_AVAILABLE = True
except ImportError:
    LEARNED_STYLES_AVAILABLE = False


# =============================================================================
# PYRAMID CONFIGURATION
# =============================================================================

class PyramidDirection(Enum):
    """Direction of the pyramid."""
    UPWARD = "upward"      # Wide base at bottom, narrow top (traditional)
    DOWNWARD = "downward"  # Wide at top, narrow bottom (inverted)


@dataclass
class PyramidConfig:
    """Configuration options for pyramid layout."""
    direction: PyramidDirection = PyramidDirection.UPWARD
    level_gutter: float = 0.0                # No gap - shapes touch for seamless pyramid
    base_width_ratio: float = 0.85           # Base width as ratio of content width
    top_width_ratio: float = 0.25            # Top width as ratio of content width
    min_level_height: float = 0.8            # Minimum height for each level
    max_level_height: float = 1.4            # Maximum height for each level
    show_3d_effect: bool = False             # Add 3D shading effect


# =============================================================================
# PYRAMID ARCHETYPE
# =============================================================================

class PyramidArchetype(BaseArchetype):
    """
    Pyramid diagram archetype.

    Creates triangular pyramid layouts where:
    - Levels stack from wide (base) to narrow (top)
    - Each level represents a hierarchical tier
    - Colors typically progress from darker at base to lighter at top
    - Supports traditional (upward) and inverted (downward) pyramids
    """

    name = "pyramid"
    display_name = "Pyramid / Hierarchy"
    description = "Triangular hierarchy with levels from base to apex"
    example_prompts = [
        "Maslow's hierarchy of needs pyramid",
        "Data-Information-Knowledge-Wisdom hierarchy",
        "Leadership pyramid with executives at top",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[PyramidConfig] = None
    ):
        super().__init__(palette)
        self.config = config or PyramidConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a pyramid layout from input data."""
        errors = self.validate_input(input_data)
        if errors:
            return self.create_empty_layout(
                title=input_data.title,
                subtitle=f"Layout error: {errors[0]}"
            )

        if input_data.palette:
            self.palette = input_data.palette

        # Count levels for style generation
        level_data = self._get_level_data(input_data)
        num_levels = len(level_data)

        # Generate learned style if available
        self.learned_style = None
        if LEARNED_STYLES_AVAILABLE:
            # Get brand hint from metadata if available
            brand_hint = input_data.metadata.get("brand_hint", "") if input_data.metadata else ""
            self.learned_style = generate_creative_pyramid_style(
                num_levels=num_levels,
                title=input_data.title or "",
                brand_hint=brand_hint,
            )

        layout = PositionedLayout(
            slide_width_inches=SLIDE_WIDTH_INCHES,
            slide_height_inches=SLIDE_HEIGHT_INCHES,
            background_color=self.palette.background,
            elements=[],
            connectors=[],
            archetype="pyramid"  # Set archetype for renderer style selection
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

        # Create pyramid levels - use layers if available, otherwise use blocks
        elements = self._create_pyramid_levels(
            input_data,
            content_top,
            content_height
        )
        layout.elements.extend(elements)

        return layout

    def _create_pyramid_levels(
        self,
        input_data: DiagramInput,
        content_top: float,
        content_height: float
    ) -> List[PositionedElement]:
        """Create the pyramid level elements.

        If layers are defined, creates one level per layer.
        Otherwise, creates one level per block.
        """
        elements = []

        # Build level data - either from layers or blocks
        level_data = self._get_level_data(input_data)

        if not level_data:
            return elements

        num_levels = len(level_data)

        # Calculate level heights
        total_gutter = self.config.level_gutter * (num_levels - 1)
        available_height = content_height - total_gutter
        level_height = available_height / num_levels
        level_height = max(self.config.min_level_height,
                          min(self.config.max_level_height, level_height))

        # Recalculate total height
        total_height = level_height * num_levels + total_gutter
        start_y = content_top + (content_height - total_height) / 2

        # Width progression from base to top
        base_width = CONTENT_WIDTH * self.config.base_width_ratio
        top_width = CONTENT_WIDTH * self.config.top_width_ratio
        width_step = (base_width - top_width) / (num_levels - 1) if num_levels > 1 else 0

        # Create levels - level 0 is base (bottom, widest), last level is apex (top, narrowest)
        for level_idx, level_info in enumerate(level_data):
            if self.config.direction == PyramidDirection.UPWARD:
                # Traditional pyramid: base at bottom
                # level_idx 0 = base = bottom of screen (highest y) = widest
                # level_idx n-1 = apex = top of screen (lowest y) = narrowest
                y = start_y + (num_levels - 1 - level_idx) * (level_height + self.config.level_gutter)
                level_width = base_width - (level_idx * width_step)
            else:
                # Inverted pyramid: base at top
                y = start_y + level_idx * (level_height + self.config.level_gutter)
                level_width = base_width - (level_idx * width_step)

            # Center horizontally
            x = CONTENT_LEFT + (CONTENT_WIDTH - level_width) / 2

            # Create level element
            element = self._create_level_element(
                level_info,
                x,
                y,
                level_width,
                level_height,
                level_idx,
                num_levels
            )
            elements.append(element)

        return elements

    def _get_level_data(self, input_data: DiagramInput) -> List[BlockData]:
        """Extract level data from input.

        If layers are defined, merges entity labels within each layer.
        Otherwise, treats each block as a separate level.
        """
        # If no layers defined, use blocks directly
        if not input_data.layers:
            return input_data.blocks

        # Build block lookup
        block_map = {b.id: b for b in input_data.blocks}

        # Create one level per layer
        levels = []
        for layer in input_data.layers:
            # Get all blocks in this layer
            layer_blocks = [block_map[bid] for bid in layer.blocks if bid in block_map]

            if not layer_blocks:
                # No blocks in layer, use layer label
                levels.append(BlockData(
                    id=layer.id,
                    label=layer.label,
                    description="",
                ))
            elif len(layer_blocks) == 1:
                # Single block - use its label
                levels.append(layer_blocks[0])
            else:
                # Multiple blocks - combine labels
                combined_label = " / ".join(b.label for b in layer_blocks)
                levels.append(BlockData(
                    id=layer.id,
                    label=combined_label,
                    description=layer.label,
                    color=layer_blocks[0].color,  # Use first block's color
                ))

        return levels

    def _create_level_element(
        self,
        block: BlockData,
        x: float,
        y: float,
        width: float,
        height: float,
        level_idx: int,
        total_levels: int
    ) -> PositionedElement:
        """Create a single pyramid level element."""
        # Use learned colors if available, otherwise fall back to palette
        if self.learned_style and "level_colors" in self.learned_style:
            # Learned colors are ordered base to apex
            learned_colors = self.learned_style["level_colors"]
            if level_idx < len(learned_colors):
                fill_color = block.color or learned_colors[level_idx]
            else:
                fill_color = block.color or self.palette.get_color_for_index(level_idx)
        else:
            fill_color = block.color or self.palette.get_color_for_index(level_idx)

        # Fit text
        fit_result = fit_text_to_width(
            block.label,
            width - 0.4,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=14,
            min_font_size=10,
            bold=True,
            allow_wrap=True,
            max_lines=2
        )

        # Use learned text color or compute contrast
        if self.learned_style:
            # Use the learned text color based on background luminance
            generator = CreativeStyleGenerator() if LEARNED_STYLES_AVAILABLE else None
            if generator:
                text_color = generator.get_text_color_for_background(fill_color)
            else:
                text_color = self._contrast_text_color(fill_color)
        else:
            text_color = self._contrast_text_color(fill_color)

        level_text = PositionedText(
            content=block.label,
            lines=fit_result.lines,
            font_size_pt=fit_result.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            color=text_color,
            alignment=TextAlignment.CENTER
        )

        # Determine stroke based on learned style
        if self.learned_style:
            use_stroke = self.learned_style.get("use_stroke", False)
            stroke_color = self.learned_style.get("stroke_color") if use_stroke else None
            stroke_width = self.learned_style.get("stroke_width_pt", 0) if use_stroke else 0
        else:
            stroke_color = self.palette.border
            stroke_width = 1.0

        return PositionedElement(
            id=f"level_{level_idx}",  # Standardized format for renderer to parse level index
            element_type=ElementType.BLOCK,
            x_inches=x,
            y_inches=y,
            width_inches=width,
            height_inches=height,
            fill_color=fill_color,
            stroke_color=stroke_color,
            stroke_width_pt=stroke_width,
            corner_radius_inches=0.04,
            text=level_text,
            z_order=10 + level_idx  # Higher levels on top
        )

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for pyramid layout."""
        errors = super().validate_input(input_data)

        # Count levels: use layers if defined, otherwise blocks
        num_levels = len(input_data.layers) if input_data.layers else len(input_data.blocks)

        if num_levels < 2:
            errors.append("Pyramid requires at least 2 levels")

        if num_levels > 7:
            errors.append("Too many levels for pyramid (max 7)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_pyramid(
    title: str,
    levels: List[str],
    subtitle: Optional[str] = None,
    inverted: bool = False
) -> PositionedLayout:
    """
    Quick helper to create a pyramid diagram.

    Args:
        title: Diagram title
        levels: List of level labels from base to apex
        subtitle: Optional subtitle
        inverted: If True, creates inverted pyramid (wide at top)

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_pyramid(
            title="Maslow's Hierarchy",
            levels=[
                "Physiological",
                "Safety",
                "Love/Belonging",
                "Esteem",
                "Self-Actualization"
            ]
        )
    """
    blocks = [
        BlockData(id=f"level_{i}", label=level)
        for i, level in enumerate(levels)
    ]

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    config = PyramidConfig(
        direction=PyramidDirection.DOWNWARD if inverted else PyramidDirection.UPWARD
    )

    archetype = PyramidArchetype(config=config)
    return archetype.generate_layout(input_data)
