"""
tree_diagram.py — Tree Diagram Archetype.

Branching tree structure showing hierarchies:
- Root at top with branches below
- Shows parent-child relationships
- Good for taxonomies, categorization
- Decision trees, file structures

Example prompts:
- "Product category breakdown"
- "Decision tree"
- "Taxonomy structure"
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import math

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
    ConnectorStyle,
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
# TREE DIAGRAM CONFIGURATION
# =============================================================================

@dataclass
class TreeDiagramConfig:
    """Configuration options for tree diagram layout."""
    node_width: float = 1.5                   # Width of each node
    node_height: float = 0.5                  # Height of each node
    level_spacing: float = 0.7                # Vertical spacing between levels
    sibling_spacing: float = 0.2              # Horizontal spacing between siblings
    corner_radius: float = 0.06               # Node corner radius


# =============================================================================
# TREE DIAGRAM ARCHETYPE
# =============================================================================

class TreeDiagramArchetype(BaseArchetype):
    """
    Tree Diagram archetype.

    Creates branching tree layouts where:
    - Root node at top
    - Children branch out below
    - Lines connect parent to children
    - Great for taxonomies, hierarchies, breakdowns
    """

    name = "tree_diagram"
    display_name = "Tree Diagram"
    description = "Branching tree showing hierarchy or taxonomy"
    example_prompts = [
        "Product category tree",
        "Decision tree",
        "Classification hierarchy",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[TreeDiagramConfig] = None
    ):
        super().__init__(palette)
        self.config = config or TreeDiagramConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate a tree diagram layout from input data."""
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

        # Build and layout tree
        tree = self._build_tree(input_data.blocks)
        elements, connectors = self._create_tree_layout(
            tree,
            content_top,
            content_height
        )
        layout.elements.extend(elements)
        layout.connectors.extend(connectors)

        return layout

    def _build_tree(self, blocks: List[BlockData]) -> Dict[str, Any]:
        """Build tree structure from blocks using layer_id as parent."""
        if not blocks:
            return {}

        nodes = {b.id: {"block": b, "children": []} for b in blocks}

        # Find root
        root_id = None
        for block in blocks:
            if not block.layer_id or block.layer_id not in nodes:
                root_id = block.id
                break

        if root_id is None:
            root_id = blocks[0].id

        # Build relationships
        for block in blocks:
            if block.layer_id and block.layer_id in nodes and block.id != root_id:
                nodes[block.layer_id]["children"].append(nodes[block.id])

        return nodes[root_id]

    def _calculate_subtree_width(self, node: Dict) -> float:
        """Calculate width needed for a subtree."""
        if not node.get("children"):
            return self.config.node_width

        children_width = sum(
            self._calculate_subtree_width(child) for child in node["children"]
        ) + (len(node["children"]) - 1) * self.config.sibling_spacing

        return max(self.config.node_width, children_width)

    def _create_tree_layout(
        self,
        tree: Dict,
        content_top: float,
        content_height: float
    ) -> Tuple[List[PositionedElement], List[PositionedConnector]]:
        """Create tree diagram elements."""
        elements = []
        connectors = []

        if not tree:
            return elements, connectors

        # Calculate total width
        total_width = self._calculate_subtree_width(tree)

        # Scale if needed
        if total_width > CONTENT_WIDTH:
            scale = CONTENT_WIDTH / total_width
            self.config.node_width *= scale
            self.config.sibling_spacing *= scale

        # Start position (centered)
        start_x = CONTENT_LEFT + (CONTENT_WIDTH - total_width) / 2

        self._layout_node(
            tree,
            start_x,
            content_top,
            total_width,
            elements,
            connectors,
            0,
            0
        )

        return elements, connectors

    def _layout_node(
        self,
        node: Dict,
        start_x: float,
        y: float,
        available_width: float,
        elements: List[PositionedElement],
        connectors: List[PositionedConnector],
        level: int,
        node_idx: int
    ) -> float:
        """Layout a node and its children. Returns node center x."""
        block = node["block"]
        children = node.get("children", [])

        # Calculate center based on children
        if children:
            children_widths = [self._calculate_subtree_width(c) for c in children]
            total_children_width = sum(children_widths) + (len(children) - 1) * self.config.sibling_spacing
            node_center_x = start_x + total_children_width / 2
        else:
            node_center_x = start_x + self.config.node_width / 2

        # Create node element
        node_x = node_center_x - self.config.node_width / 2
        fill_color = block.color or self.palette.get_color_for_index(level)

        fit_result = fit_text_to_width(
            block.label,
            self.config.node_width - 0.1,
            font_family=DEFAULT_FONT_FAMILY,
            max_font_size=10,
            min_font_size=7,
            bold=True,
            allow_wrap=True,
            max_lines=2
        )

        text_color = self._contrast_text_color(fill_color)
        node_text = PositionedText(
            content=block.label,
            lines=fit_result.lines,
            font_size_pt=fit_result.font_size,
            font_family=DEFAULT_FONT_FAMILY,
            bold=True,
            color=text_color,
            alignment=TextAlignment.CENTER
        )

        node_element = PositionedElement(
            id=block.id,
            element_type=ElementType.BLOCK,
            x_inches=node_x,
            y_inches=y,
            width_inches=self.config.node_width,
            height_inches=self.config.node_height,
            fill_color=fill_color,
            stroke_color=self.palette.border,
            stroke_width_pt=1.0,
            corner_radius_inches=self.config.corner_radius,
            text=node_text,
            z_order=10 + level
        )
        elements.append(node_element)

        # Layout children
        if children:
            child_y = y + self.config.node_height + self.config.level_spacing
            current_x = start_x

            for i, child in enumerate(children):
                child_width = self._calculate_subtree_width(child)

                child_center_x = self._layout_node(
                    child,
                    current_x,
                    child_y,
                    child_width,
                    elements,
                    connectors,
                    level + 1,
                    i
                )

                # Create connector
                connector = PositionedConnector(
                    id=f"conn_{block.id}_{child['block'].id}",
                    from_element_id=block.id,
                    to_element_id=child["block"].id,
                    start_x=node_center_x,
                    start_y=y + self.config.node_height,
                    end_x=child_center_x,
                    end_y=child_y,
                    style=ConnectorStyle.PLAIN,
                    color=self.palette.connector,
                    stroke_width_pt=1.5
                )
                connectors.append(connector)

                current_x += child_width + self.config.sibling_spacing

        return node_center_x

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for tree diagram layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 2:
            errors.append("Tree diagram requires at least 2 nodes")

        if len(input_data.blocks) > 15:
            errors.append("Too many nodes for tree diagram (max 15)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_tree(
    title: str,
    root: str,
    branches: List[str],
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a simple two-level tree diagram.

    Args:
        title: Diagram title
        root: Label for the root node
        branches: Labels for child nodes
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_tree(
            title="Product Categories",
            root="Products",
            branches=["Electronics", "Clothing", "Home", "Sports"]
        )
    """
    blocks = [
        BlockData(id="root", label=root)
    ]
    blocks.extend([
        BlockData(id=f"branch_{i}", label=branch, layer_id="root")
        for i, branch in enumerate(branches)
    ])

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    archetype = TreeDiagramArchetype()
    return archetype.generate_layout(input_data)
