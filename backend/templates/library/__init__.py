"""Built-in template library."""

from pathlib import Path
from typing import Any

from backend.templates.store import Template, TemplateComponent, TemplateStore, TemplateVariation


def get_library_path() -> Path:
    """Get path to the library directory."""
    return Path(__file__).parent


def load_builtin_templates(store: TemplateStore) -> int:
    """Load all built-in templates into a store.

    Args:
        store: Template store to populate.

    Returns:
        Number of templates loaded.
    """
    templates = [
        create_basic_funnel_template(),
        create_basic_timeline_template(),
        create_basic_pyramid_template(),
        create_basic_process_template(),
        create_basic_cycle_template(),
        create_basic_hub_spoke_template(),
    ]

    for template in templates:
        store.save(template)

    return len(templates)


def create_basic_funnel_template() -> Template:
    """Create a basic 4-stage funnel template."""
    components = []

    # 4 funnel layers
    for i in range(4):
        y_ratio = 0.15 + i * 0.2  # Start at 15%, increment by 20%
        height_ratio = 0.18
        width_ratio = 0.8 - i * 0.15  # Decreasing width

        components.append(
            TemplateComponent(
                component_type="funnel_layer",
                params={
                    "layer_index": i,
                    "total_layers": 4,
                    "taper_ratio": 0.85,
                    "color": {"color_token": f"accent{(i % 6) + 1}"},
                    "text": {"title": "", "alignment": "center"},
                },
                variations=[
                    TemplateVariation(
                        parameter="color.color_token",
                        type="enum",
                        values=["accent1", "accent2", "accent3", "accent4"],
                    ),
                ],
                bbox_relative={
                    "x": (1.0 - width_ratio) / 2,
                    "y": y_ratio,
                    "width": width_ratio,
                    "height": height_ratio,
                },
            )
        )

    return Template(
        id="builtin_funnel_basic",
        name="Basic 4-Stage Funnel",
        description="A simple funnel with 4 stages, great for sales or marketing funnels.",
        archetype="funnel",
        tags=["funnel", "sales", "marketing", "conversion"],
        components=components,
        global_variations=[
            TemplateVariation(
                parameter="theme.accent1",
                type="list",
                values=["#0D9488", "#3B82F6", "#8B5CF6", "#F59E0B"],
            ),
        ],
    )


def create_basic_timeline_template() -> Template:
    """Create a basic horizontal timeline template."""
    components = []

    # 4 timeline nodes
    for i in range(4):
        x_ratio = 0.1 + i * 0.25  # Spread horizontally
        width_ratio = 0.15
        y_ratio = 0.35
        height_ratio = 0.3

        components.append(
            TemplateComponent(
                component_type="timeline_node",
                params={
                    "node_index": i,
                    "total_nodes": 4,
                    "position": "alternate",
                    "node_shape": "circle",
                    "color": {"color_token": "accent1"},
                    "text": {"title": "", "alignment": "center"},
                },
                variations=[
                    TemplateVariation(
                        parameter="node_shape",
                        type="enum",
                        values=["circle", "diamond", "square"],
                    ),
                ],
                bbox_relative={
                    "x": x_ratio,
                    "y": y_ratio,
                    "width": width_ratio,
                    "height": height_ratio,
                },
            )
        )

    return Template(
        id="builtin_timeline_basic",
        name="Horizontal Timeline",
        description="A 4-point horizontal timeline for roadmaps and project milestones.",
        archetype="timeline",
        tags=["timeline", "roadmap", "milestones", "history"],
        components=components,
    )


def create_basic_pyramid_template() -> Template:
    """Create a basic 3-tier pyramid template."""
    components = []

    # 3 pyramid tiers
    for i in range(3):
        y_ratio = 0.2 + i * 0.25
        height_ratio = 0.22
        width_ratio = 0.3 + i * 0.2  # Increasing width

        components.append(
            TemplateComponent(
                component_type="pyramid_tier",
                params={
                    "tier_index": i,
                    "total_tiers": 3,
                    "tier_shape": "trapezoid",
                    "color": {"color_token": f"accent{i + 1}"},
                    "text": {"title": "", "alignment": "center"},
                },
                variations=[
                    TemplateVariation(
                        parameter="tier_shape",
                        type="enum",
                        values=["trapezoid", "rectangle"],
                    ),
                ],
                bbox_relative={
                    "x": (1.0 - width_ratio) / 2,
                    "y": y_ratio,
                    "width": width_ratio,
                    "height": height_ratio,
                },
            )
        )

    return Template(
        id="builtin_pyramid_basic",
        name="3-Tier Pyramid",
        description="A classic pyramid with 3 levels for hierarchies and priorities.",
        archetype="pyramid",
        tags=["pyramid", "hierarchy", "priorities", "levels"],
        components=components,
    )


def create_basic_process_template() -> Template:
    """Create a basic 5-step process template."""
    components = []

    # 5 process steps
    for i in range(5):
        x_ratio = 0.05 + i * 0.18
        width_ratio = 0.15
        y_ratio = 0.35
        height_ratio = 0.3

        components.append(
            TemplateComponent(
                component_type="process_step",
                params={
                    "step_index": i,
                    "total_steps": 5,
                    "step_number": i + 1,
                    "step_shape": "rectangle",
                    "connector_style": "arrow",
                    "show_number": True,
                    "color": {"color_token": "accent1"},
                    "text": {"title": "", "alignment": "center"},
                },
                variations=[
                    TemplateVariation(
                        parameter="step_shape",
                        type="enum",
                        values=["rectangle", "chevron", "circle"],
                    ),
                ],
                bbox_relative={
                    "x": x_ratio,
                    "y": y_ratio,
                    "width": width_ratio,
                    "height": height_ratio,
                },
            )
        )

    return Template(
        id="builtin_process_basic",
        name="5-Step Process",
        description="A linear process flow with 5 numbered steps.",
        archetype="process",
        tags=["process", "workflow", "steps", "flow"],
        components=components,
    )


def create_basic_cycle_template() -> Template:
    """Create a basic 4-node cycle template."""
    components = []

    # 4 cycle nodes
    for i in range(4):
        # Position will be calculated by the component
        components.append(
            TemplateComponent(
                component_type="cycle_node",
                params={
                    "node_index": i,
                    "total_nodes": 4,
                    "radius_ratio": 0.7,
                    "node_shape": "circle",
                    "connector_style": "arrow",
                    "color": {"color_token": "accent1"},
                    "text": {"title": "", "alignment": "center"},
                },
                variations=[
                    TemplateVariation(
                        parameter="node_shape",
                        type="enum",
                        values=["circle", "rounded_rect", "hexagon"],
                    ),
                ],
                bbox_relative={
                    "x": 0.1,
                    "y": 0.1,
                    "width": 0.8,
                    "height": 0.8,
                },
            )
        )

    return Template(
        id="builtin_cycle_basic",
        name="4-Node Cycle",
        description="A circular diagram with 4 interconnected nodes.",
        archetype="cycle",
        tags=["cycle", "wheel", "loop", "continuous"],
        components=components,
    )


def create_basic_hub_spoke_template() -> Template:
    """Create a basic hub and spoke template."""
    components = []

    # Hub (center)
    components.append(
        TemplateComponent(
            component_type="hub_spoke_node",
            params={
                "is_hub": True,
                "spoke_index": 0,
                "total_spokes": 4,
                "node_shape": "circle",
                "color": {"color_token": "accent1"},
                "text": {"title": "", "alignment": "center"},
            },
            variations=[],
            bbox_relative={
                "x": 0.1,
                "y": 0.1,
                "width": 0.8,
                "height": 0.8,
            },
        )
    )

    # 4 spokes
    for i in range(4):
        components.append(
            TemplateComponent(
                component_type="hub_spoke_node",
                params={
                    "is_hub": False,
                    "spoke_index": i + 1,
                    "total_spokes": 4,
                    "node_shape": "circle",
                    "connector_style": "line",
                    "color": {"color_token": "accent2"},
                    "text": {"title": "", "alignment": "center"},
                },
                variations=[
                    TemplateVariation(
                        parameter="node_shape",
                        type="enum",
                        values=["circle", "rounded_rect", "hexagon"],
                    ),
                ],
                bbox_relative={
                    "x": 0.1,
                    "y": 0.1,
                    "width": 0.8,
                    "height": 0.8,
                },
            )
        )

    return Template(
        id="builtin_hub_spoke_basic",
        name="Hub and Spoke",
        description="A central hub with 4 connected spoke elements.",
        archetype="hub_spoke",
        tags=["hub", "spoke", "radial", "central"],
        components=components,
    )
