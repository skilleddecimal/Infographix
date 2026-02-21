"""Component templates - concrete implementations of infographic components."""

from backend.components.templates.funnel_layer import FunnelLayerComponent
from backend.components.templates.timeline_node import TimelineNodeComponent
from backend.components.templates.pyramid_tier import PyramidTierComponent
from backend.components.templates.process_step import ProcessStepComponent
from backend.components.templates.cycle_node import CycleNodeComponent
from backend.components.templates.hub_spoke import HubSpokeNodeComponent

__all__ = [
    "FunnelLayerComponent",
    "TimelineNodeComponent",
    "PyramidTierComponent",
    "ProcessStepComponent",
    "CycleNodeComponent",
    "HubSpokeNodeComponent",
]


def register_all_components() -> None:
    """Register all built-in component templates with the registry."""
    from backend.components.registry import registry

    registry.register(FunnelLayerComponent)
    registry.register(TimelineNodeComponent)
    registry.register(PyramidTierComponent)
    registry.register(ProcessStepComponent)
    registry.register(CycleNodeComponent)
    registry.register(HubSpokeNodeComponent)
