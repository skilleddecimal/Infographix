"""
radial_strategy.py — Circular/radial layout strategy.

Used for: Hub-Spoke, Circular Cycle, Target, Venn Diagram
Pattern: Elements arranged in a circle or radial pattern.
"""

import math
from typing import List, Dict, Any, Optional

from .base_strategy import (
    BaseLayoutStrategy,
    StrategyResult,
    ElementPosition,
    ConnectorPosition,
    ContentBounds,
)
from ..archetype_rules import (
    ArchetypeRules,
    LayoutDirection,
    ConnectorPattern,
)
from ..data_models import DiagramInput, ColorPalette


class RadialStrategy(BaseLayoutStrategy):
    """
    Radial layout strategy for circular arrangements.

    Key features:
    - Central hub element (optional)
    - Satellite elements arranged in a circle
    - Configurable start angle and direction
    - Support for concentric rings (target)
    """

    def compute(
        self,
        input_data: DiagramInput,
        rules: ArchetypeRules,
        bounds: ContentBounds,
        palette: ColorPalette,
    ) -> StrategyResult:
        """Compute positions for radial layout."""
        blocks = input_data.blocks
        if not blocks:
            return StrategyResult(warnings=["No blocks to layout"])

        template = rules.element_template
        radial_params = rules.radial_params
        direction = rules.primary_direction

        # Get configuration
        center_element = radial_params.get('center_element', True)
        radius_ratio = radial_params.get('radius_ratio', 0.35)
        start_angle = radial_params.get('start_angle', 270)  # Start from top
        rotation = radial_params.get('rotation', 'clockwise')

        if direction == LayoutDirection.RADIAL_INWARD:
            # Target/bullseye: concentric rings
            return self._compute_concentric_layout(
                blocks, bounds, template, palette, radial_params
            )
        else:
            # Standard radial: hub and spokes
            return self._compute_hub_spoke_layout(
                blocks, bounds, template, palette, radial_params,
                center_element, radius_ratio, start_angle, rotation,
                rules.connector_template,
            )

    def _compute_hub_spoke_layout(
        self,
        blocks: List,
        bounds: ContentBounds,
        template,
        palette: ColorPalette,
        radial_params: Dict,
        center_element: bool,
        radius_ratio: float,
        start_angle: int,
        rotation: str,
        connector_template,
    ) -> StrategyResult:
        """Compute hub-and-spoke layout."""
        elements: List[ElementPosition] = []
        connectors: List[ConnectorPosition] = []

        num_blocks = len(blocks)

        # Calculate center point
        center_x = bounds.center_x
        center_y = bounds.center_y

        # Calculate radius
        max_radius = min(bounds.width, bounds.height) / 2
        radius = max_radius * radius_ratio

        # Element sizes
        satellite_size = max(1.0, min(2.0, radius * 0.6))
        hub_size = satellite_size * 1.2

        if center_element and num_blocks >= 1:
            # First block is the center/hub
            hub_block = blocks[0]
            satellite_blocks = blocks[1:]

            hub_fill = self.compute_element_color(
                hub_block, template, 0, num_blocks, palette
            )

            hub_element = ElementPosition(
                element_id=hub_block.id,
                block_data=hub_block,
                x=center_x - hub_size / 2,
                y=center_y - hub_size / 2,
                width=hub_size,
                height=hub_size,
                fill_color=hub_fill,
                stroke_color=template.stroke_color,
                shape_type=template.element_type.value,
                corner_radius=template.corner_radius,
                z_order=20,  # Hub on top
            )
            elements.append(hub_element)
        else:
            satellite_blocks = blocks
            hub_element = None

        # Place satellite elements in a circle
        num_satellites = len(satellite_blocks)
        if num_satellites > 0:
            angle_step = 360 / num_satellites
            if rotation == 'counterclockwise':
                angle_step = -angle_step

            for i, block in enumerate(satellite_blocks):
                angle_deg = start_angle + i * angle_step
                angle_rad = math.radians(angle_deg)

                # Position on circle
                x = center_x + radius * math.cos(angle_rad) - satellite_size / 2
                y = center_y + radius * math.sin(angle_rad) - satellite_size / 2

                fill_color = self.compute_element_color(
                    block, template, i + 1, num_blocks, palette
                )

                element = ElementPosition(
                    element_id=block.id,
                    block_data=block,
                    x=x,
                    y=y,
                    width=satellite_size,
                    height=satellite_size,
                    fill_color=fill_color,
                    stroke_color=template.stroke_color,
                    shape_type=template.element_type.value,
                    corner_radius=template.corner_radius,
                    z_order=10,
                )
                elements.append(element)

                # Create connector from hub to satellite
                if hub_element and connector_template.pattern == ConnectorPattern.HUB_TO_SPOKES:
                    conn = self._create_hub_spoke_connector(
                        hub_element, element, i, connector_template, palette
                    )
                    connectors.append(conn)

        # Create cycle connectors if needed
        if connector_template.pattern == ConnectorPattern.CYCLE and len(elements) > 1:
            cycle_elements = elements[1:] if hub_element else elements
            connectors.extend(self._create_cycle_connectors(
                cycle_elements, connector_template, palette
            ))

        return StrategyResult(
            elements=elements,
            connectors=connectors,
            used_bounds=bounds,
        )

    def _compute_concentric_layout(
        self,
        blocks: List,
        bounds: ContentBounds,
        template,
        palette: ColorPalette,
        radial_params: Dict,
    ) -> StrategyResult:
        """Compute concentric rings (target/bullseye) layout."""
        elements: List[ElementPosition] = []
        num_rings = len(blocks)

        center_x = bounds.center_x
        center_y = bounds.center_y

        # Max radius (leave some margin)
        max_radius = min(bounds.width, bounds.height) / 2 - 0.2

        # Ring radii: evenly spaced, innermost is smallest
        for i, block in enumerate(blocks):
            # Rings are created outside-in (first block is outermost)
            ring_index = i
            radius = max_radius * (1 - ring_index / num_rings)
            inner_radius = max_radius * (1 - (ring_index + 1) / num_rings) if ring_index < num_rings - 1 else 0

            # Size is based on radius
            ring_size = radius * 2

            fill_color = self.compute_element_color(
                block, template, i, num_rings, palette
            )

            element = ElementPosition(
                element_id=block.id,
                block_data=block,
                x=center_x - radius,
                y=center_y - radius,
                width=ring_size,
                height=ring_size,
                fill_color=fill_color,
                stroke_color=template.stroke_color,
                shape_type='ellipse',  # Use ellipse for target rings
                corner_radius=0,
                z_order=num_rings - i,  # Outer rings behind inner
            )
            elements.append(element)

        return StrategyResult(
            elements=elements,
            connectors=[],
            used_bounds=bounds,
        )

    def _create_hub_spoke_connector(
        self,
        hub: ElementPosition,
        satellite: ElementPosition,
        index: int,
        connector_template,
        palette: ColorPalette,
    ) -> ConnectorPosition:
        """Create a connector from hub to satellite."""
        # Calculate edge points
        hub_cx, hub_cy = hub.center_x, hub.center_y
        sat_cx, sat_cy = satellite.center_x, satellite.center_y

        # Direction vector from hub to satellite
        dx = sat_cx - hub_cx
        dy = sat_cy - hub_cy
        dist = math.sqrt(dx**2 + dy**2)

        if dist > 0:
            dx /= dist
            dy /= dist

            # Start point: edge of hub
            hub_radius = hub.width / 2
            start_x = hub_cx + dx * hub_radius
            start_y = hub_cy + dy * hub_radius

            # End point: edge of satellite
            sat_radius = satellite.width / 2
            end_x = sat_cx - dx * sat_radius
            end_y = sat_cy - dy * sat_radius
        else:
            start_x, start_y = hub_cx, hub_cy
            end_x, end_y = sat_cx, sat_cy

        return ConnectorPosition(
            connector_id=f"conn_hub_{index}",
            from_element_id=hub.element_id,
            to_element_id=satellite.element_id,
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            style=connector_template.style,
            color=connector_template.color or palette.connector,
            stroke_width=connector_template.stroke_width,
            routing=connector_template.routing,
        )

    def _create_cycle_connectors(
        self,
        elements: List[ElementPosition],
        connector_template,
        palette: ColorPalette,
    ) -> List[ConnectorPosition]:
        """Create connectors forming a cycle (last connects to first)."""
        connectors = []

        for i in range(len(elements)):
            e1 = elements[i]
            e2 = elements[(i + 1) % len(elements)]  # Wrap around

            # Calculate tangent connection points for circular layout
            e1_cx, e1_cy = e1.center_x, e1.center_y
            e2_cx, e2_cy = e2.center_x, e2.center_y

            # Direction vector
            dx = e2_cx - e1_cx
            dy = e2_cy - e1_cy
            dist = math.sqrt(dx**2 + dy**2)

            if dist > 0:
                dx /= dist
                dy /= dist

                # Start/end at edges
                radius = e1.width / 2
                start_x = e1_cx + dx * radius
                start_y = e1_cy + dy * radius

                radius2 = e2.width / 2
                end_x = e2_cx - dx * radius2
                end_y = e2_cy - dy * radius2
            else:
                start_x, start_y = e1_cx, e1_cy
                end_x, end_y = e2_cx, e2_cy

            connectors.append(ConnectorPosition(
                connector_id=f"conn_cycle_{i}",
                from_element_id=e1.element_id,
                to_element_id=e2.element_id,
                start_x=start_x,
                start_y=start_y,
                end_x=end_x,
                end_y=end_y,
                style=connector_template.style,
                color=connector_template.color or palette.connector,
                stroke_width=connector_template.stroke_width,
                routing=connector_template.routing,
            ))

        return connectors
