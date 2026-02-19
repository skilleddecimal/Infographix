"""
tree_strategy.py — Hierarchical tree layout strategy.

Used for: Org Chart, Tree Diagram, Hierarchy
Pattern: Elements arranged in a tree structure with parent-child relationships.
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict

from .base_strategy import (
    BaseLayoutStrategy,
    StrategyResult,
    ElementPosition,
    ConnectorPosition,
    ContentBounds,
)
from ..archetype_rules import ArchetypeRules, ConnectorPattern
from ..data_models import DiagramInput, BlockData, ColorPalette


class TreeStrategy(BaseLayoutStrategy):
    """
    Tree layout strategy for hierarchical structures.

    Key features:
    - Automatic tree structure detection from layers or metadata
    - Configurable orientation (top-down, bottom-up, left-right, right-left)
    - Level-based positioning
    - Balanced and compact layouts
    """

    def compute(
        self,
        input_data: DiagramInput,
        rules: ArchetypeRules,
        bounds: ContentBounds,
        palette: ColorPalette,
    ) -> StrategyResult:
        """Compute positions for tree layout."""
        blocks = input_data.blocks
        if not blocks:
            return StrategyResult(warnings=["No blocks to layout"])

        template = rules.element_template
        tree_params = rules.tree_params

        # Get configuration
        orientation = tree_params.get('orientation', 'top_down')
        sibling_spacing = tree_params.get('sibling_spacing', 0.3)
        level_spacing = tree_params.get('level_spacing', 0.5)

        # Build tree structure from layers or metadata
        tree = self._build_tree_structure(blocks, input_data.layers)

        # Calculate positions based on tree structure
        elements = self._compute_tree_positions(
            tree=tree,
            blocks=blocks,
            bounds=bounds,
            template=template,
            palette=palette,
            orientation=orientation,
            sibling_spacing=sibling_spacing,
            level_spacing=level_spacing,
        )

        # Generate hierarchical connectors
        connectors = []
        if rules.connector_template.pattern == ConnectorPattern.HIERARCHICAL:
            connectors = self._create_tree_connectors(
                elements=elements,
                tree=tree,
                connector_template=rules.connector_template,
                palette=palette,
                orientation=orientation,
            )

        result = StrategyResult(
            elements=elements,
            connectors=connectors,
            used_bounds=bounds,
        )

        # Apply constraints
        if rules.constraints:
            result = self.apply_constraints(result, rules.constraints, bounds)

        return result

    def _build_tree_structure(
        self,
        blocks: List[BlockData],
        layers: List,
    ) -> Dict[str, Any]:
        """
        Build tree structure from blocks and layers.

        Returns a dict with:
        - 'root': ID of root node (or None if forest)
        - 'children': Dict mapping parent_id -> list of child IDs
        - 'levels': Dict mapping block_id -> level number
        """
        children = defaultdict(list)
        parent_of = {}
        levels = {}

        # Try to infer structure from layers
        if layers:
            # Layers define hierarchy: earlier layers are higher (parents)
            for level_idx, layer in enumerate(layers):
                for block_id in layer.blocks:
                    levels[block_id] = level_idx
                    # Connect to blocks in previous layer as potential parents
                    if level_idx > 0 and layers[level_idx - 1].blocks:
                        # Simple heuristic: connect to nearest parent
                        parent_id = layers[level_idx - 1].blocks[0]
                        parent_of[block_id] = parent_id
                        children[parent_id].append(block_id)

        # Try to infer from metadata
        for block in blocks:
            parent_id = block.metadata.get('parent_id')
            if parent_id:
                parent_of[block.id] = parent_id
                children[parent_id].append(block.id)

            level = block.metadata.get('level')
            if level is not None:
                levels[block.id] = level

        # Find root(s) - blocks without parents
        all_children = set()
        for child_list in children.values():
            all_children.update(child_list)

        roots = [b.id for b in blocks if b.id not in all_children]

        # Assign levels if not already set
        if roots and not levels:
            self._assign_levels_bfs(roots, children, levels)

        return {
            'roots': roots,
            'children': dict(children),
            'parent_of': parent_of,
            'levels': levels,
        }

    def _assign_levels_bfs(
        self,
        roots: List[str],
        children: Dict[str, List[str]],
        levels: Dict[str, int],
    ) -> None:
        """Assign levels using BFS from roots."""
        from collections import deque

        queue = deque()
        for root_id in roots:
            queue.append((root_id, 0))

        while queue:
            node_id, level = queue.popleft()
            if node_id not in levels:
                levels[node_id] = level
                for child_id in children.get(node_id, []):
                    queue.append((child_id, level + 1))

    def _compute_tree_positions(
        self,
        tree: Dict[str, Any],
        blocks: List[BlockData],
        bounds: ContentBounds,
        template,
        palette: ColorPalette,
        orientation: str,
        sibling_spacing: float,
        level_spacing: float,
    ) -> List[ElementPosition]:
        """Compute positions for tree nodes."""
        elements = []

        levels = tree['levels']
        children = tree['children']
        roots = tree['roots']

        if not levels:
            # Fallback: arrange linearly if no hierarchy detected
            return self._fallback_linear_layout(
                blocks, bounds, template, palette
            )

        # Group blocks by level
        blocks_by_level = defaultdict(list)
        block_dict = {b.id: b for b in blocks}

        for block_id, level in levels.items():
            if block_id in block_dict:
                blocks_by_level[level].append(block_dict[block_id])

        # Determine number of levels
        max_level = max(levels.values()) if levels else 0
        num_levels = max_level + 1

        # Calculate element sizes
        if orientation in ('top_down', 'bottom_up'):
            # Vertical tree
            available_height = bounds.height - level_spacing * (num_levels - 1)
            element_height = min(1.0, available_height / num_levels)
            element_width = 2.0
        else:
            # Horizontal tree
            available_width = bounds.width - level_spacing * (num_levels - 1)
            element_width = min(2.0, available_width / num_levels)
            element_height = 1.0

        # Position elements level by level
        for level_num in range(num_levels):
            level_blocks = blocks_by_level[level_num]
            num_at_level = len(level_blocks)

            if num_at_level == 0:
                continue

            if orientation in ('top_down', 'bottom_up'):
                # Vertical: spread horizontally at each level
                total_width = num_at_level * element_width + (num_at_level - 1) * sibling_spacing
                start_x = bounds.center_x - total_width / 2

                if orientation == 'top_down':
                    y = bounds.top + level_num * (element_height + level_spacing)
                else:
                    y = bounds.bottom - element_height - level_num * (element_height + level_spacing)

                for i, block in enumerate(level_blocks):
                    x = start_x + i * (element_width + sibling_spacing)

                    fill_color = self.compute_element_color(
                        block, template, level_num, num_levels, palette
                    )

                    elements.append(ElementPosition(
                        element_id=block.id,
                        block_data=block,
                        x=x,
                        y=y,
                        width=element_width,
                        height=element_height,
                        fill_color=fill_color,
                        stroke_color=template.stroke_color,
                        shape_type=template.element_type.value,
                        corner_radius=template.corner_radius,
                        z_order=10,
                    ))
            else:
                # Horizontal: spread vertically at each level
                total_height = num_at_level * element_height + (num_at_level - 1) * sibling_spacing
                start_y = bounds.center_y - total_height / 2

                if orientation == 'left_right':
                    x = bounds.left + level_num * (element_width + level_spacing)
                else:
                    x = bounds.right - element_width - level_num * (element_width + level_spacing)

                for i, block in enumerate(level_blocks):
                    y = start_y + i * (element_height + sibling_spacing)

                    fill_color = self.compute_element_color(
                        block, template, level_num, num_levels, palette
                    )

                    elements.append(ElementPosition(
                        element_id=block.id,
                        block_data=block,
                        x=x,
                        y=y,
                        width=element_width,
                        height=element_height,
                        fill_color=fill_color,
                        stroke_color=template.stroke_color,
                        shape_type=template.element_type.value,
                        corner_radius=template.corner_radius,
                        z_order=10,
                    ))

        return elements

    def _fallback_linear_layout(
        self,
        blocks: List[BlockData],
        bounds: ContentBounds,
        template,
        palette: ColorPalette,
    ) -> List[ElementPosition]:
        """Fallback to simple linear layout if no hierarchy detected."""
        elements = []
        num_blocks = len(blocks)

        element_width = 2.0
        element_height = 1.0
        spacing = 0.5

        total_height = num_blocks * element_height + (num_blocks - 1) * spacing
        start_y = bounds.top + (bounds.height - total_height) / 2
        x = bounds.center_x - element_width / 2

        for i, block in enumerate(blocks):
            y = start_y + i * (element_height + spacing)

            fill_color = self.compute_element_color(
                block, template, i, num_blocks, palette
            )

            elements.append(ElementPosition(
                element_id=block.id,
                block_data=block,
                x=x,
                y=y,
                width=element_width,
                height=element_height,
                fill_color=fill_color,
                stroke_color=template.stroke_color,
                shape_type=template.element_type.value,
                corner_radius=template.corner_radius,
                z_order=10,
            ))

        return elements

    def _create_tree_connectors(
        self,
        elements: List[ElementPosition],
        tree: Dict[str, Any],
        connector_template,
        palette: ColorPalette,
        orientation: str,
    ) -> List[ConnectorPosition]:
        """Create hierarchical connectors between parent and children."""
        connectors = []
        children = tree['children']

        # Build lookup
        element_dict = {e.element_id: e for e in elements}

        connector_idx = 0
        for parent_id, child_ids in children.items():
            parent = element_dict.get(parent_id)
            if not parent:
                continue

            for child_id in child_ids:
                child = element_dict.get(child_id)
                if not child:
                    continue

                # Determine connection points based on orientation
                if orientation == 'top_down':
                    start_x, start_y = parent.center_x, parent.bottom_edge
                    end_x, end_y = child.center_x, child.y
                elif orientation == 'bottom_up':
                    start_x, start_y = parent.center_x, parent.y
                    end_x, end_y = child.center_x, child.bottom_edge
                elif orientation == 'left_right':
                    start_x, start_y = parent.right_edge, parent.center_y
                    end_x, end_y = child.x, child.center_y
                else:  # right_left
                    start_x, start_y = parent.x, parent.center_y
                    end_x, end_y = child.right_edge, child.center_y

                connectors.append(ConnectorPosition(
                    connector_id=f"conn_tree_{connector_idx}",
                    from_element_id=parent_id,
                    to_element_id=child_id,
                    start_x=start_x,
                    start_y=start_y,
                    end_x=end_x,
                    end_y=end_y,
                    style=connector_template.style,
                    color=connector_template.color or palette.connector,
                    stroke_width=connector_template.stroke_width,
                    routing=connector_template.routing,
                ))
                connector_idx += 1

        return connectors
