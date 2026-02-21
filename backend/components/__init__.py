"""Component library module - reusable infographic components."""

from backend.components.base import BaseComponent, ComponentInstance, ComponentMetadata
from backend.components.registry import (
    ComponentRegistry,
    registry,
    register_component,
    get_component,
    create_component_instance,
)
from backend.components.detector import ComponentDetector, DetectedComponent, DetectionResult
from backend.components.llm_detector import (
    LLMPatternDetector,
    MultiPatternResult,
    PatternGroup,
    ShapeCluster,
    ShapeClusterer,
)
from backend.components.parameters import (
    BaseParameters,
    FunnelLayerParams,
    TimelineNodeParams,
    PyramidTierParams,
    ProcessStepParams,
    CycleNodeParams,
    HubSpokeNodeParams,
)

__all__ = [
    # Base classes
    "BaseComponent",
    "ComponentInstance",
    "ComponentMetadata",
    # Registry
    "ComponentRegistry",
    "registry",
    "register_component",
    "get_component",
    "create_component_instance",
    # Detector (basic)
    "ComponentDetector",
    "DetectedComponent",
    "DetectionResult",
    # Detector (LLM-enhanced with multi-pattern support)
    "LLMPatternDetector",
    "MultiPatternResult",
    "PatternGroup",
    "ShapeCluster",
    "ShapeClusterer",
    # Parameters
    "BaseParameters",
    "FunnelLayerParams",
    "TimelineNodeParams",
    "PyramidTierParams",
    "ProcessStepParams",
    "CycleNodeParams",
    "HubSpokeNodeParams",
]


def init_components() -> None:
    """Initialize the component system by registering all built-in components."""
    from backend.components.templates import register_all_components

    register_all_components()
