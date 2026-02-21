"""Hub and spoke node component implementation."""

import math
from typing import ClassVar

from backend.components.base import BaseComponent, calculate_radial_position
from backend.components.parameters import HubSpokeNodeParams
from backend.dsl.schema import BoundingBox, Shape, TextContent, TextRun


class HubSpokeNodeComponent(BaseComponent[HubSpokeNodeParams]):
    """A node in a hub-and-spoke diagram.

    Hub-and-spoke diagrams show a central concept (hub) with
    related items (spokes) radiating outward.
    """

    name: ClassVar[str] = "hub_spoke_node"
    description: ClassVar[str] = "A hub or spoke node in a hub-and-spoke diagram"
    archetype: ClassVar[str] = "hub_spoke"
    param_class: ClassVar = HubSpokeNodeParams

    # Shape type mappings
    NODE_SHAPES = {
        "circle": "ellipse",
        "rounded_rect": "roundRect",
        "hexagon": "hexagon",
    }

    def generate(
        self,
        params: HubSpokeNodeParams,
        bbox: BoundingBox,
        instance_id: str,
    ) -> list[Shape]:
        """Generate shapes for a hub or spoke node.

        Args:
            params: Hub/spoke node parameters.
            bbox: Bounding box for the entire diagram.
            instance_id: Unique identifier.

        Returns:
            List of shapes forming the node.
        """
        shapes = []

        # Resolve color
        fill_color = self.resolve_color(
            params.color.color_token,
            params.color.color_override,
        )

        # Calculate center of the diagram
        center_x = bbox.x + bbox.width // 2
        center_y = bbox.y + bbox.height // 2

        if params.is_hub:
            # Hub is centered and larger
            hub_size = min(bbox.width, bbox.height) // 3
            node_bbox = BoundingBox(
                x=center_x - hub_size // 2,
                y=center_y - hub_size // 2,
                width=hub_size,
                height=hub_size,
            )
        else:
            # Spoke is positioned radially
            spoke_radius = min(bbox.width, bbox.height) // 3
            spoke_size = min(bbox.width, bbox.height) // 5

            # Calculate position using angle or index
            if params.angle != 0.0:
                angle_rad = math.radians(params.angle)
                pos_x = int(center_x + spoke_radius * math.cos(angle_rad))
                pos_y = int(center_y + spoke_radius * math.sin(angle_rad))
            else:
                pos_x, pos_y = calculate_radial_position(
                    index=params.spoke_index - 1,  # Adjust for 1-based index
                    total=params.total_spokes,
                    center_x=center_x,
                    center_y=center_y,
                    radius=spoke_radius,
                    start_angle=-90.0,
                )

            node_bbox = BoundingBox(
                x=pos_x - spoke_size // 2,
                y=pos_y - spoke_size // 2,
                width=spoke_size,
                height=spoke_size,
            )

        # Get shape type
        auto_shape_type = self.NODE_SHAPES.get(params.node_shape, "ellipse")

        # Create text content
        text_content = None
        if params.text.title:
            font_size = 1600 if params.is_hub else 1200
            text_runs = [
                TextRun(
                    text=params.text.title,
                    font_size=int(font_size * params.text.font_scale),
                    bold=True,
                    color="#FFFFFF",
                )
            ]
            if params.text.description and params.is_hub:
                text_runs.append(
                    TextRun(
                        text=f"\n{params.text.description}",
                        font_size=int(1000 * params.text.font_scale),
                        color="#FFFFFF",
                    )
                )
            text_content = TextContent(
                runs=text_runs,
                alignment="center",
                vertical_alignment="middle",
            )

        # Create the node shape
        z_index = 100 if params.is_hub else params.spoke_index + 10
        node_shape = self.create_shape(
            shape_id=f"{instance_id}_node",
            shape_type="autoShape",
            bbox=node_bbox,
            fill_color=fill_color,
            auto_shape_type=auto_shape_type,
            text_content=text_content,
            z_index=z_index,
        )
        shapes.append(node_shape)

        # Add connector line from spoke to hub (if this is a spoke)
        if not params.is_hub and params.connector_style.value != "none":
            connector_shape = self._create_connector(
                params=params,
                node_bbox=node_bbox,
                center_x=center_x,
                center_y=center_y,
                instance_id=instance_id,
                fill_color=fill_color,
            )
            if connector_shape:
                shapes.append(connector_shape)

        # Add icon if specified
        if params.icon.icon:
            icon_shape = self._create_icon(
                params=params,
                node_bbox=node_bbox,
                instance_id=instance_id,
            )
            if icon_shape:
                shapes.append(icon_shape)

        return shapes

    def _create_connector(
        self,
        params: HubSpokeNodeParams,
        node_bbox: BoundingBox,
        center_x: int,
        center_y: int,
        instance_id: str,
        fill_color: str,
    ) -> Shape | None:
        """Create a connector line from spoke to hub."""
        # Calculate line from node center to diagram center
        node_center_x = node_bbox.x + node_bbox.width // 2
        node_center_y = node_bbox.y + node_bbox.height // 2

        # Line dimensions
        dx = center_x - node_center_x
        dy = center_y - node_center_y
        line_length = int(math.sqrt(dx * dx + dy * dy))

        # Shorten line so it doesn't overlap with shapes
        shorten = node_bbox.width // 2 + 20000
        if line_length > shorten * 2:
            # Calculate start and end points
            ratio = shorten / line_length if line_length > 0 else 0
            start_x = node_center_x + int(dx * ratio)
            start_y = node_center_y + int(dy * ratio)
            end_x = center_x - int(dx * ratio)
            end_y = center_y - int(dy * ratio)

            # Create a thin rectangle as connector
            min_x = min(start_x, end_x)
            min_y = min(start_y, end_y)
            max_x = max(start_x, end_x)
            max_y = max(start_y, end_y)

            connector_bbox = BoundingBox(
                x=min_x,
                y=min_y,
                width=max(max_x - min_x, 10000),
                height=max(max_y - min_y, 10000),
            )

            return self.create_shape(
                shape_id=f"{instance_id}_connector",
                shape_type="connector",
                bbox=connector_bbox,
                fill_color=fill_color,
                auto_shape_type="rect",
                z_index=params.spoke_index,
            )

        return None

    def _create_icon(
        self,
        params: HubSpokeNodeParams,
        node_bbox: BoundingBox,
        instance_id: str,
    ) -> Shape | None:
        """Create an icon shape for the node."""
        icon_size = node_bbox.width // 2

        # Center icon in the node
        icon_bbox = BoundingBox(
            x=node_bbox.x + (node_bbox.width - icon_size) // 2,
            y=node_bbox.y + (node_bbox.height - icon_size) // 2,
            width=icon_size,
            height=icon_size,
        )

        icon_color = params.icon.icon_color or "#FFFFFF"
        icon_text = TextContent(
            runs=[
                TextRun(
                    text=params.icon.icon,
                    font_size=int(1000 * params.icon.icon_size),
                    color=icon_color,
                )
            ],
            alignment="center",
            vertical_alignment="middle",
        )

        z_index = 101 if params.is_hub else params.spoke_index + 50
        return self.create_shape(
            shape_id=f"{instance_id}_icon",
            shape_type="text",
            bbox=icon_bbox,
            fill_color="none",
            text_content=icon_text,
            z_index=z_index,
        )
