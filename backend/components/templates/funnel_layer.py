"""Funnel layer component implementation."""

from typing import ClassVar

from backend.components.base import BaseComponent, calculate_tier_width
from backend.components.parameters import FunnelLayerParams
from backend.dsl.schema import BoundingBox, Shape, TextContent, TextRun


class FunnelLayerComponent(BaseComponent[FunnelLayerParams]):
    """A single layer/stage in a funnel diagram.

    Funnels typically show a narrowing progression from top to bottom,
    representing stages like awareness → interest → decision → action.
    """

    name: ClassVar[str] = "funnel_layer"
    description: ClassVar[str] = "A layer in a funnel diagram with tapering width"
    archetype: ClassVar[str] = "funnel"
    param_class: ClassVar = FunnelLayerParams

    def generate(
        self,
        params: FunnelLayerParams,
        bbox: BoundingBox,
        instance_id: str,
    ) -> list[Shape]:
        """Generate shapes for a funnel layer.

        Args:
            params: Funnel layer parameters.
            bbox: Bounding box for this layer.
            instance_id: Unique identifier.

        Returns:
            List of shapes forming the funnel layer.
        """
        shapes = []

        # Calculate actual width based on position in funnel
        layer_width = calculate_tier_width(
            tier_index=params.layer_index,
            total_tiers=params.total_layers,
            max_width=bbox.width,
            min_ratio=params.taper_ratio,
            direction="decreasing",
        )

        # Center the layer horizontally
        layer_x = bbox.x + (bbox.width - layer_width) // 2

        # Resolve color
        fill_color = self.resolve_color(
            params.color.color_token,
            params.color.color_override,
        )

        # Create text content if provided
        text_content = None
        if params.text.title:
            runs = [
                TextRun(
                    text=params.text.title,
                    font_size=int(1800 * params.text.font_scale),
                    bold=True,
                    color="#FFFFFF",
                )
            ]
            if params.text.description:
                runs.append(
                    TextRun(
                        text=f"\n{params.text.description}",
                        font_size=int(1200 * params.text.font_scale),
                        color="#FFFFFF",
                    )
                )
            text_content = TextContent(
                runs=runs,
                alignment=params.text.alignment.value,
                vertical_alignment="middle",
            )

        # Create the main shape
        layer_bbox = BoundingBox(
            x=layer_x,
            y=bbox.y,
            width=layer_width,
            height=bbox.height,
        )

        main_shape = self.create_shape(
            shape_id=f"{instance_id}_layer",
            shape_type="autoShape",
            bbox=layer_bbox,
            fill_color=fill_color,
            auto_shape_type="trapezoid",
            text_content=text_content,
            z_index=params.layer_index,
        )
        shapes.append(main_shape)

        # Add accent if specified
        if params.accent_style.value != "none":
            accent_shape = self._create_accent(
                params=params,
                layer_bbox=layer_bbox,
                instance_id=instance_id,
                fill_color=fill_color,
            )
            if accent_shape:
                shapes.append(accent_shape)

        return shapes

    def _create_accent(
        self,
        params: FunnelLayerParams,
        layer_bbox: BoundingBox,
        instance_id: str,
        fill_color: str,
    ) -> Shape | None:
        """Create an accent shape for the layer."""
        accent_style = params.accent_style.value

        if accent_style == "ring":
            # Add a ring accent on the left side
            ring_size = min(layer_bbox.height * 2 // 3, 300000)
            ring_bbox = BoundingBox(
                x=layer_bbox.x - ring_size - 50000,
                y=layer_bbox.y + (layer_bbox.height - ring_size) // 2,
                width=ring_size,
                height=ring_size,
            )
            return self.create_shape(
                shape_id=f"{instance_id}_accent",
                shape_type="autoShape",
                bbox=ring_bbox,
                fill_color=fill_color,
                auto_shape_type="donut",
                z_index=params.layer_index + 100,
            )

        elif accent_style == "arc":
            # Add an arc on the right side
            arc_width = layer_bbox.height // 2
            arc_bbox = BoundingBox(
                x=layer_bbox.x + layer_bbox.width + 50000,
                y=layer_bbox.y,
                width=arc_width,
                height=layer_bbox.height,
            )
            return self.create_shape(
                shape_id=f"{instance_id}_accent",
                shape_type="autoShape",
                bbox=arc_bbox,
                fill_color=fill_color,
                auto_shape_type="arc",
                z_index=params.layer_index + 100,
            )

        return None
