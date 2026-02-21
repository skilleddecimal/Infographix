"""Pyramid tier component implementation."""

from typing import ClassVar

from backend.components.base import BaseComponent, calculate_tier_width
from backend.components.parameters import PyramidTierParams
from backend.dsl.schema import BoundingBox, Shape, TextContent, TextRun


class PyramidTierComponent(BaseComponent[PyramidTierParams]):
    """A single tier/level in a pyramid diagram.

    Pyramids show hierarchical information with the top being the smallest
    (most important/exclusive) and bottom being the widest (foundation).
    """

    name: ClassVar[str] = "pyramid_tier"
    description: ClassVar[str] = "A tier in a pyramid diagram with increasing width"
    archetype: ClassVar[str] = "pyramid"
    param_class: ClassVar = PyramidTierParams

    # Shape type mappings
    TIER_SHAPES = {
        "trapezoid": "trapezoid",
        "rectangle": "rect",
        "chevron": "chevron",
    }

    def generate(
        self,
        params: PyramidTierParams,
        bbox: BoundingBox,
        instance_id: str,
    ) -> list[Shape]:
        """Generate shapes for a pyramid tier.

        Args:
            params: Pyramid tier parameters.
            bbox: Bounding box for this tier.
            instance_id: Unique identifier.

        Returns:
            List of shapes forming the pyramid tier.
        """
        shapes = []

        # Calculate actual width based on position in pyramid
        tier_width = calculate_tier_width(
            tier_index=params.tier_index,
            total_tiers=params.total_tiers,
            max_width=bbox.width,
            min_ratio=0.25,  # Top tier is 25% of max width
            direction="increasing",
        )

        # Override with explicit width_ratio if provided
        if params.width_ratio < 1.0:
            tier_width = int(bbox.width * params.width_ratio)

        # Center the tier horizontally
        tier_x = bbox.x + (bbox.width - tier_width) // 2

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
                    font_size=int(1600 * params.text.font_scale),
                    bold=True,
                    color="#FFFFFF",
                )
            ]
            if params.text.description:
                runs.append(
                    TextRun(
                        text=f"\n{params.text.description}",
                        font_size=int(1100 * params.text.font_scale),
                        color="#FFFFFF",
                    )
                )
            text_content = TextContent(
                runs=runs,
                alignment=params.text.alignment.value,
                vertical_alignment="middle",
            )

        # Create the tier bounding box
        tier_bbox = BoundingBox(
            x=tier_x,
            y=bbox.y,
            width=tier_width,
            height=bbox.height,
        )

        # Get the shape type
        auto_shape_type = self.TIER_SHAPES.get(params.tier_shape, "trapezoid")

        # Create the main tier shape
        tier_shape = self.create_shape(
            shape_id=f"{instance_id}_tier",
            shape_type="autoShape",
            bbox=tier_bbox,
            fill_color=fill_color,
            auto_shape_type=auto_shape_type,
            text_content=text_content,
            z_index=params.tier_index,
        )
        shapes.append(tier_shape)

        # Add icon if specified
        if params.icon.icon:
            icon_shape = self._create_icon(
                params=params,
                tier_bbox=tier_bbox,
                instance_id=instance_id,
            )
            if icon_shape:
                shapes.append(icon_shape)

        # Add accent if specified
        if params.accent_style.value != "none":
            accent_shape = self._create_accent(
                params=params,
                tier_bbox=tier_bbox,
                instance_id=instance_id,
                fill_color=fill_color,
            )
            if accent_shape:
                shapes.append(accent_shape)

        return shapes

    def _create_icon(
        self,
        params: PyramidTierParams,
        tier_bbox: BoundingBox,
        instance_id: str,
    ) -> Shape | None:
        """Create an icon shape for the tier."""
        icon_size = min(tier_bbox.height * 2 // 3, 200000)

        # Position based on icon_position parameter
        position = params.icon.icon_position.value
        if position == "left":
            icon_x = tier_bbox.x + 50000
            icon_y = tier_bbox.y + (tier_bbox.height - icon_size) // 2
        elif position == "right":
            icon_x = tier_bbox.x + tier_bbox.width - icon_size - 50000
            icon_y = tier_bbox.y + (tier_bbox.height - icon_size) // 2
        elif position == "top":
            icon_x = tier_bbox.x + (tier_bbox.width - icon_size) // 2
            icon_y = tier_bbox.y + 50000
        elif position == "bottom":
            icon_x = tier_bbox.x + (tier_bbox.width - icon_size) // 2
            icon_y = tier_bbox.y + tier_bbox.height - icon_size - 50000
        else:  # center
            icon_x = tier_bbox.x + (tier_bbox.width - icon_size) // 2
            icon_y = tier_bbox.y + (tier_bbox.height - icon_size) // 2

        icon_bbox = BoundingBox(
            x=icon_x,
            y=icon_y,
            width=icon_size,
            height=icon_size,
        )

        icon_color = params.icon.icon_color or "#FFFFFF"
        icon_text = TextContent(
            runs=[
                TextRun(
                    text=params.icon.icon,
                    font_size=int(1400 * params.icon.icon_size),
                    color=icon_color,
                )
            ],
            alignment="center",
            vertical_alignment="middle",
        )

        return self.create_shape(
            shape_id=f"{instance_id}_icon",
            shape_type="autoShape",
            bbox=icon_bbox,
            fill_color="none",
            auto_shape_type="ellipse",
            text_content=icon_text,
            z_index=params.tier_index + 100,
        )

    def _create_accent(
        self,
        params: PyramidTierParams,
        tier_bbox: BoundingBox,
        instance_id: str,
        fill_color: str,
    ) -> Shape | None:
        """Create an accent shape for the tier."""
        accent_style = params.accent_style.value

        if accent_style == "glow":
            # Create a larger background shape for glow effect
            glow_padding = 20000
            glow_bbox = BoundingBox(
                x=tier_bbox.x - glow_padding,
                y=tier_bbox.y - glow_padding,
                width=tier_bbox.width + glow_padding * 2,
                height=tier_bbox.height + glow_padding * 2,
            )
            return self.create_shape(
                shape_id=f"{instance_id}_accent",
                shape_type="autoShape",
                bbox=glow_bbox,
                fill_color=fill_color,
                auto_shape_type="trapezoid",
                z_index=params.tier_index - 1,
            )

        elif accent_style == "shadow":
            # Create an offset shadow shape
            shadow_offset = 30000
            shadow_bbox = BoundingBox(
                x=tier_bbox.x + shadow_offset,
                y=tier_bbox.y + shadow_offset,
                width=tier_bbox.width,
                height=tier_bbox.height,
            )
            return self.create_shape(
                shape_id=f"{instance_id}_accent",
                shape_type="autoShape",
                bbox=shadow_bbox,
                fill_color="#333333",
                auto_shape_type="trapezoid",
                z_index=params.tier_index - 1,
            )

        return None
