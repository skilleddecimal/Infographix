"""Timeline node component implementation."""

from typing import ClassVar

from backend.components.base import BaseComponent
from backend.components.parameters import TimelineNodeParams
from backend.dsl.schema import BoundingBox, Shape, TextContent, TextRun


class TimelineNodeComponent(BaseComponent[TimelineNodeParams]):
    """A node/milestone on a timeline diagram.

    Timeline nodes are typically arranged horizontally and may include
    dates, milestones, or events with connecting lines.
    """

    name: ClassVar[str] = "timeline_node"
    description: ClassVar[str] = "A milestone node on a timeline"
    archetype: ClassVar[str] = "timeline"
    param_class: ClassVar = TimelineNodeParams

    # Shape type mappings
    NODE_SHAPES = {
        "circle": "ellipse",
        "diamond": "diamond",
        "square": "rect",
        "hexagon": "hexagon",
    }

    def generate(
        self,
        params: TimelineNodeParams,
        bbox: BoundingBox,
        instance_id: str,
    ) -> list[Shape]:
        """Generate shapes for a timeline node.

        Args:
            params: Timeline node parameters.
            bbox: Bounding box for this node.
            instance_id: Unique identifier.

        Returns:
            List of shapes forming the timeline node.
        """
        shapes = []

        # Resolve color
        fill_color = self.resolve_color(
            params.color.color_token,
            params.color.color_override,
        )

        # Calculate node position based on total nodes
        node_width = bbox.width // params.total_nodes
        node_x = bbox.x + params.node_index * node_width

        # Create the main node shape (centered in its slot)
        node_size = min(node_width * 2 // 3, bbox.height * 2 // 3)
        node_bbox = BoundingBox(
            x=node_x + (node_width - node_size) // 2,
            y=bbox.y + (bbox.height - node_size) // 2,
            width=node_size,
            height=node_size,
        )

        # Create icon/node shape
        auto_shape_type = self.NODE_SHAPES.get(params.node_shape, "ellipse")

        # Create node text
        node_text = None
        if params.icon.icon:
            # If icon is specified, show it in the node
            node_text = TextContent(
                runs=[TextRun(text=params.icon.icon, font_size=1600, color="#FFFFFF")],
                alignment="center",
                vertical_alignment="middle",
            )

        node_shape = self.create_shape(
            shape_id=f"{instance_id}_node",
            shape_type="autoShape",
            bbox=node_bbox,
            fill_color=fill_color,
            auto_shape_type=auto_shape_type,
            text_content=node_text,
            z_index=params.node_index + 10,
        )
        shapes.append(node_shape)

        # Add date label if provided
        if params.date_label:
            label_height = 200000
            label_y = (
                node_bbox.y - label_height - 50000
                if params.position == "above"
                else node_bbox.y + node_bbox.height + 50000
            )

            label_bbox = BoundingBox(
                x=node_x,
                y=label_y,
                width=node_width,
                height=label_height,
            )

            label_text = TextContent(
                runs=[
                    TextRun(
                        text=params.date_label,
                        font_size=int(1000 * params.text.font_scale),
                        bold=True,
                        color=self.theme.dark1,
                    )
                ],
                alignment="center",
            )

            label_shape = self.create_shape(
                shape_id=f"{instance_id}_date",
                shape_type="text",
                bbox=label_bbox,
                fill_color="none",
                text_content=label_text,
                z_index=params.node_index + 11,
            )
            shapes.append(label_shape)

        # Add title/description below or above the node
        if params.text.title:
            content_height = 400000
            content_y = (
                node_bbox.y + node_bbox.height + 100000
                if params.position in ["above", "alternate"]
                else node_bbox.y - content_height - 100000
            )

            # Alternate position for alternate layout
            if params.position == "alternate" and params.node_index % 2 == 1:
                content_y = node_bbox.y - content_height - 100000

            content_bbox = BoundingBox(
                x=node_x,
                y=content_y,
                width=node_width,
                height=content_height,
            )

            runs = [
                TextRun(
                    text=params.text.title,
                    font_size=int(1400 * params.text.font_scale),
                    bold=True,
                    color=self.theme.dark1,
                )
            ]
            if params.text.description:
                runs.append(
                    TextRun(
                        text=f"\n{params.text.description}",
                        font_size=int(1000 * params.text.font_scale),
                        color=self.theme.dark2,
                    )
                )

            content_text = TextContent(
                runs=runs,
                alignment="center",
            )

            content_shape = self.create_shape(
                shape_id=f"{instance_id}_content",
                shape_type="text",
                bbox=content_bbox,
                fill_color="none",
                text_content=content_text,
                z_index=params.node_index + 12,
            )
            shapes.append(content_shape)

        # Add connector line to next node (if not the last)
        if params.connector_style.value != "none" and params.node_index < params.total_nodes - 1:
            connector_shape = self._create_connector(
                params=params,
                node_bbox=node_bbox,
                node_width=node_width,
                instance_id=instance_id,
                fill_color=fill_color,
            )
            if connector_shape:
                shapes.append(connector_shape)

        return shapes

    def _create_connector(
        self,
        params: TimelineNodeParams,
        node_bbox: BoundingBox,
        node_width: int,
        instance_id: str,
        fill_color: str,
    ) -> Shape | None:
        """Create a connector line to the next node."""
        connector_y = node_bbox.y + node_bbox.height // 2
        connector_start_x = node_bbox.x + node_bbox.width
        connector_end_x = node_bbox.x + node_width

        connector_height = 20000  # Thin line

        connector_bbox = BoundingBox(
            x=connector_start_x,
            y=connector_y - connector_height // 2,
            width=connector_end_x - connector_start_x,
            height=connector_height,
        )

        return self.create_shape(
            shape_id=f"{instance_id}_connector",
            shape_type="autoShape",
            bbox=connector_bbox,
            fill_color=fill_color,
            auto_shape_type="rect",
            z_index=params.node_index,
        )
