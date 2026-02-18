"""
org_chart.py — Organizational Chart Archetype.

Hierarchical tree structure for organizations:
- CEO/Manager at top
- Direct reports below
- Multiple levels supported
- Great for org structures, reporting lines

Example prompts:
- "Company organizational structure"
- "Team hierarchy"
- "Reporting structure"
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
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
# ORG CHART CONFIGURATION
# =============================================================================

class OrgChartStyle(Enum):
    """Style of org chart."""
    TOP_DOWN = "top_down"         # Root at top, children below
    LEFT_RIGHT = "left_right"     # Root at left, children to right


@dataclass
class OrgChartConfig:
    """Configuration options for org chart layout."""
    style: OrgChartStyle = OrgChartStyle.TOP_DOWN
    node_width: float = 1.8                   # Width of each node
    node_height: float = 0.6                  # Height of each node
    level_spacing: float = 0.8                # Vertical spacing between levels
    sibling_spacing: float = 0.3              # Horizontal spacing between siblings
    corner_radius: float = 0.06               # Node corner radius


# =============================================================================
# ORG CHART ARCHETYPE
# =============================================================================

class OrgChartArchetype(BaseArchetype):
    """
    Organizational Chart diagram archetype.

    Creates hierarchical layouts where:
    - Root node at top (or left)
    - Children arranged below (or to right)
    - Lines connect parent to children
    - Great for org structures, team hierarchies
    """

    name = "org_chart"
    display_name = "Org Chart"
    description = "Hierarchical organizational chart"
    example_prompts = [
        "Company org structure",
        "Team reporting hierarchy",
        "Department structure",
    ]

    def __init__(
        self,
        palette: Optional[ColorPalette] = None,
        config: Optional[OrgChartConfig] = None
    ):
        super().__init__(palette)
        self.config = config or OrgChartConfig()

    def generate_layout(self, input_data: DiagramInput) -> PositionedLayout:
        """Generate an org chart layout from input data."""
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

        # Build tree structure from blocks
        tree = self._build_tree(input_data.blocks)

        # Create org chart elements
        elements, connectors = self._create_org_chart(
            tree,
            content_top,
            content_height
        )
        layout.elements.extend(elements)
        layout.connectors.extend(connectors)

        return layout

    def _build_tree(self, blocks: List[BlockData]) -> Dict[str, Any]:
        """
        Build a tree structure from blocks.

        Blocks can specify parent via layer_id field.
        First block without parent becomes root.
        """
        if not blocks:
            return {}

        # Create node lookup
        nodes = {b.id: {"block": b, "children": []} for b in blocks}

        # Find root (first block without parent or first block)
        root_id = None
        for block in blocks:
            if not block.layer_id or block.layer_id not in nodes:
                root_id = block.id
                break

        if root_id is None:
            root_id = blocks[0].id

        # Build parent-child relationships
        for block in blocks:
            if block.layer_id and block.layer_id in nodes and block.id != root_id:
                nodes[block.layer_id]["children"].append(nodes[block.id])

        return nodes[root_id]

    def _calculate_tree_width(self, node: Dict) -> float:
        """Calculate width of tree rooted at node."""
        if not node.get("children"):
            return self.config.node_width

        children_width = sum(
            self._calculate_tree_width(child) for child in node["children"]
        ) + (len(node["children"]) - 1) * self.config.sibling_spacing

        return max(self.config.node_width, children_width)

    def _create_org_chart(
        self,
        tree: Dict,
        content_top: float,
        content_height: float
    ) -> Tuple[List[PositionedElement], List[PositionedConnector]]:
        """Create the org chart elements and connectors."""
        elements = []
        connectors = []

        if not tree:
            return elements, connectors

        # Calculate tree dimensions
        tree_width = self._calculate_tree_width(tree)
        num_levels = self._get_tree_depth(tree)

        # Scale node dimensions if needed
        max_width = CONTENT_WIDTH
        if tree_width > max_width:
            scale = max_width / tree_width
            self.config.node_width *= scale
            self.config.sibling_spacing *= scale

        # Calculate starting position (center horizontally)
        start_x = CONTENT_LEFT + (CONTENT_WIDTH - tree_width) / 2

        # Position nodes level by level
        self._position_nodes(
            tree,
            start_x,
            content_top,
            tree_width,
            elements,
            connectors,
            0,  # Level
            0   # Node index
        )

        return elements, connectors

    def _get_tree_depth(self, node: Dict) -> int:
        """Get the depth of the tree."""
        if not node.get("children"):
            return 1
        return 1 + max(self._get_tree_depth(child) for child in node["children"])

    def _position_nodes(
        self,
        node: Dict,
        start_x: float,
        y: float,
        available_width: float,
        elements: List[PositionedElement],
        connectors: List[PositionedConnector],
        level: int,
        node_idx: int
    ) -> Tuple[float, float]:
        """
        Position a node and its children recursively.
        Returns (center_x, bottom_y) of this node.
        """
        block = node["block"]
        children = node.get("children", [])

        # Calculate this node's width based on children
        if children:
            children_widths = [self._calculate_tree_width(child) for child in children]
            total_children_width = sum(children_widths) + (len(children) - 1) * self.config.sibling_spacing
            node_center_x = start_x + total_children_width / 2
        else:
            node_center_x = start_x + self.config.node_width / 2

        # Create node element
        node_x = node_center_x - self.config.node_width / 2
        fill_color = block.color or self.palette.get_color_for_index(level)

        fit_result = fit_text_to_width(
            block.label,
            self.config.node_width - 0.15,
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

        node_bottom_y = y + self.config.node_height

        # Position children
        if children:
            child_y = node_bottom_y + self.config.level_spacing
            current_x = start_x

            child_centers = []
            for i, child in enumerate(children):
                child_width = self._calculate_tree_width(child)

                child_center, child_bottom = self._position_nodes(
                    child,
                    current_x,
                    child_y,
                    child_width,
                    elements,
                    connectors,
                    level + 1,
                    i
                )
                child_centers.append(child_center)

                current_x += child_width + self.config.sibling_spacing

            # Create connectors from parent to children
            parent_bottom_x = node_center_x
            parent_bottom_y = node_bottom_y

            for i, child in enumerate(children):
                child_block = child["block"]
                child_top_x = child_centers[i]
                child_top_y = child_y

                connector = PositionedConnector(
                    id=f"conn_{block.id}_{child_block.id}",
                    from_element_id=block.id,
                    to_element_id=child_block.id,
                    start_x=parent_bottom_x,
                    start_y=parent_bottom_y,
                    end_x=child_top_x,
                    end_y=child_top_y,
                    style=ConnectorStyle.PLAIN,
                    color=self.palette.connector,
                    stroke_width_pt=1.5
                )
                connectors.append(connector)

        return node_center_x, node_bottom_y

    def validate_input(self, input_data: DiagramInput) -> List[str]:
        """Validate input for org chart layout."""
        errors = super().validate_input(input_data)

        if len(input_data.blocks) < 1:
            errors.append("Org chart requires at least 1 node")

        if len(input_data.blocks) > 15:
            errors.append("Too many nodes for org chart (max 15)")

        return errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_org_chart(
    title: str,
    root: str,
    children: List[str],
    subtitle: Optional[str] = None
) -> PositionedLayout:
    """
    Quick helper to create a simple two-level org chart.

    Args:
        title: Diagram title
        root: Label for the root node
        children: Labels for direct reports
        subtitle: Optional subtitle

    Returns:
        PositionedLayout ready for rendering

    Example:
        layout = create_simple_org_chart(
            title="Executive Team",
            root="CEO",
            children=["CTO", "CFO", "COO", "CMO"]
        )
    """
    blocks = [
        BlockData(id="root", label=root)
    ]
    blocks.extend([
        BlockData(id=f"child_{i}", label=child, layer_id="root")
        for i, child in enumerate(children)
    ])

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=blocks
    )

    archetype = OrgChartArchetype()
    return archetype.generate_layout(input_data)
