"""Cycle node component implementation."""

import math
from typing import ClassVar

from backend.components.base import BaseComponent, calculate_radial_position
from backend.components.parameters import CycleNodeParams
from backend.dsl.schema import BoundingBox, Shape, TextContent, TextRun


class CycleNodeComponent(BaseComponent[CycleNodeParams]):
    """A node in a circular/wheel diagram.

    Cycle diagrams show continuous processes or relationships
    arranged in a circular pattern.
    """

    name: ClassVar[str] = "cycle_node"
    description: ClassVar[str] = "A node in a circular cycle diagram"
    archetype: ClassVar[str] = "cycle"
    param_class: ClassVar = CycleNodeParams

    # Shape type mappings
    NODE_SHAPES = {
        "circle": "ellipse",
        "rounded_rect": "roundRect",
        "hexagon": "hexagon",
    }

    def generate(
        self,
        params: CycleNodeParams,
        bbox: BoundingBox,
        instance_id: str,
    ) -> list[Shape]:
        """Generate shapes for a cycle node.

        Args:
            params: Cycle node parameters.
            bbox: Bounding box for the entire cycle.
            instance_id: Unique identifier.

        Returns:
            List of shapes forming the cycle node.
        """
        shapes = []

        # Resolve color
        fill_color = self.resolve_color(
            params.color.color_token,
            params.color.color_override,
        )

        # Calculate node position on the circle
        center_x = bbox.x + bbox.width // 2
        center_y = bbox.y + bbox.height // 2
        radius = int(min(bbox.width, bbox.height) // 2 * params.radius_ratio)

        # Calculate node size based on number of nodes
        max_node_size = int(2 * math.pi * radius / params.total_nodes * 0.7)
        node_size = min(max_node_size, min(bbox.width, bbox.height) // 4)

        # Get position on circle
        pos_x, pos_y = calculate_radial_position(
            index=params.node_index,
            total=params.total_nodes,
            center_x=center_x,
            center_y=center_y,
            radius=radius,
            start_angle=-90.0,  # Start at top
        )

        # Create node bounding box (centered on position)
        node_bbox = BoundingBox(
            x=pos_x - node_size // 2,
            y=pos_y - node_size // 2,
            width=node_size,
            height=node_size,
        )

        # Get shape type
        auto_shape_type = self.NODE_SHAPES.get(params.node_shape, "ellipse")

        # Create text content
        text_content = None
        if params.text.title:
            text_runs = [
                TextRun(
                    text=params.text.title,
                    font_size=int(1200 * params.text.font_scale),
                    bold=True,
                    color="#FFFFFF",
                )
            ]
            text_content = TextContent(
                runs=text_runs,
                alignment="center",
                vertical_alignment="middle",
            )

        # Create the node shape
        node_shape = self.create_shape(
            shape_id=f"{instance_id}_node",
            shape_type="autoShape",
            bbox=node_bbox,
            fill_color=fill_color,
            auto_shape_type=auto_shape_type,
            text_content=text_content,
            z_index=params.node_index + 10,
        )
        shapes.append(node_shape)

        # Add connector arc to next node (if specified)
        if (
            params.connector_style.value != "none"
            and params.total_nodes > 1
        ):
            connector_shape = self._create_connector(
                params=params,
                node_bbox=node_bbox,
                center_x=center_x,
                center_y=center_y,
                radius=radius,
                instance_id=instance_id,
                fill_color=fill_color,
            )
            if connector_shape:
                shapes.append(connector_shape)

        # Add external label if description is provided
        if params.text.description:
            label_shape = self._create_label(
                params=params,
                node_bbox=node_bbox,
                center_x=center_x,
                center_y=center_y,
                instance_id=instance_id,
            )
            if label_shape:
                shapes.append(label_shape)

        return shapes

    def _create_connector(
        self,
        params: CycleNodeParams,
        node_bbox: BoundingBox,
        center_x: int,
        center_y: int,
        radius: int,
        instance_id: str,
        fill_color: str,
    ) -> Shape | None:
        """Create a connector arc to the next node."""
        # Calculate arrow position between this node and the next
        angle_step = 360.0 / params.total_nodes
        current_angle = -90.0 + params.node_index * angle_step
        next_angle = current_angle + angle_step

        # Position arrow at midpoint of arc
        mid_angle = math.radians(current_angle + angle_step / 2)
        arrow_radius = radius - node_bbox.width // 4

        arrow_x = int(center_x + arrow_radius * math.cos(mid_angle))
        arrow_y = int(center_y + arrow_radius * math.sin(mid_angle))

        arrow_size = node_bbox.width // 3
        arrow_bbox = BoundingBox(
            x=arrow_x - arrow_size // 2,
            y=arrow_y - arrow_size // 2,
            width=arrow_size,
            height=arrow_size,
        )

        # Rotate arrow to point along the circle
        # (rotation is handled by the shape renderer)

        return self.create_shape(
            shape_id=f"{instance_id}_connector",
            shape_type="autoShape",
            bbox=arrow_bbox,
            fill_color=fill_color,
            auto_shape_type="right_arrow" if params.connector_style.value == "arrow" else "rect",
            z_index=params.node_index,
        )

    def _create_label(
        self,
        params: CycleNodeParams,
        node_bbox: BoundingBox,
        center_x: int,
        center_y: int,
        instance_id: str,
    ) -> Shape | None:
        """Create an external label for the node."""
        # Calculate label position (outside the node)
        node_center_x = node_bbox.x + node_bbox.width // 2
        node_center_y = node_bbox.y + node_bbox.height // 2

        # Direction from center
        dx = node_center_x - center_x
        dy = node_center_y - center_y
        dist = math.sqrt(dx * dx + dy * dy) if dx or dy else 1

        # Normalize and extend
        label_offset = node_bbox.width
        label_x = node_center_x + int(dx / dist * label_offset)
        label_y = node_center_y + int(dy / dist * label_offset)

        label_width = node_bbox.width * 2
        label_height = node_bbox.height // 2

        label_bbox = BoundingBox(
            x=label_x - label_width // 2,
            y=label_y - label_height // 2,
            width=label_width,
            height=label_height,
        )

        label_text = TextContent(
            runs=[
                TextRun(
                    text=params.text.description,
                    font_size=int(1000 * params.text.font_scale),
                    color=self.theme.dark1,
                )
            ],
            alignment="center",
        )

        return self.create_shape(
            shape_id=f"{instance_id}_label",
            shape_type="text",
            bbox=label_bbox,
            fill_color="none",
            text_content=label_text,
            z_index=params.node_index + 20,
        )
