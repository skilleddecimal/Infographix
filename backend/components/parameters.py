"""Component parameter schemas for infographic components."""

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class AccentStyle(str, Enum):
    """Visual accent styles for components."""

    NONE = "none"
    RING = "ring"
    ARC = "arc"
    GLOW = "glow"
    SHADOW = "shadow"
    GRADIENT = "gradient"


class ConnectorStyle(str, Enum):
    """Connector line styles."""

    ARROW = "arrow"
    LINE = "line"
    DASHED = "dashed"
    DOTTED = "dotted"
    NONE = "none"


class IconPosition(str, Enum):
    """Icon placement positions."""

    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    CENTER = "center"


class TextAlignment(str, Enum):
    """Text alignment options."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


# ============================================================================
# Base Parameter Models
# ============================================================================


class BaseParameters(BaseModel):
    """Base class for all component parameters."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ColorParameters(BaseModel):
    """Color-related parameters."""

    model_config = ConfigDict(frozen=True)

    color_token: str = Field(
        default="accent1",
        description="Color token reference (accent1-6, primary, secondary)",
    )
    color_override: Optional[str] = Field(
        default=None,
        description="Direct hex color override (#RRGGBB)",
    )
    opacity: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Fill opacity",
    )


class TextParameters(BaseModel):
    """Text-related parameters."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(default="", description="Main title text")
    description: Optional[str] = Field(default=None, description="Description text")
    subtitle: Optional[str] = Field(default=None, description="Subtitle text")
    font_scale: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Font size multiplier",
    )
    alignment: TextAlignment = Field(default=TextAlignment.CENTER)


class IconParameters(BaseModel):
    """Icon-related parameters."""

    model_config = ConfigDict(frozen=True)

    icon: Optional[str] = Field(default=None, description="Icon name/ID")
    icon_position: IconPosition = Field(default=IconPosition.LEFT)
    icon_size: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Icon size multiplier",
    )
    icon_color: Optional[str] = Field(
        default=None,
        description="Icon color override",
    )


# ============================================================================
# Component-Specific Parameter Models
# ============================================================================


class FunnelLayerParams(BaseParameters):
    """Parameters for a funnel layer component."""

    layer_index: int = Field(ge=0, description="Layer position (0 = top)")
    total_layers: int = Field(ge=1, description="Total number of layers")
    taper_ratio: float = Field(
        default=0.8,
        ge=0.3,
        le=1.0,
        description="Width ratio compared to layer above",
    )
    color: ColorParameters = Field(default_factory=ColorParameters)
    text: TextParameters = Field(default_factory=TextParameters)
    icon: IconParameters = Field(default_factory=IconParameters)
    accent_style: AccentStyle = Field(default=AccentStyle.NONE)
    show_connector: bool = Field(default=True)


class TimelineNodeParams(BaseParameters):
    """Parameters for a timeline node component."""

    node_index: int = Field(ge=0, description="Position on timeline")
    total_nodes: int = Field(ge=1, description="Total number of nodes")
    date_label: Optional[str] = Field(default=None, description="Date/time label")
    position: Literal["above", "below", "alternate"] = Field(
        default="alternate",
        description="Content position relative to timeline",
    )
    color: ColorParameters = Field(default_factory=ColorParameters)
    text: TextParameters = Field(default_factory=TextParameters)
    icon: IconParameters = Field(default_factory=IconParameters)
    connector_style: ConnectorStyle = Field(default=ConnectorStyle.LINE)
    node_shape: Literal["circle", "diamond", "square", "hexagon"] = Field(
        default="circle"
    )


class PyramidTierParams(BaseParameters):
    """Parameters for a pyramid tier component."""

    tier_index: int = Field(ge=0, description="Tier position (0 = top)")
    total_tiers: int = Field(ge=1, description="Total number of tiers")
    width_ratio: float = Field(
        default=1.0,
        ge=0.2,
        le=1.0,
        description="Width as ratio of max width",
    )
    color: ColorParameters = Field(default_factory=ColorParameters)
    text: TextParameters = Field(default_factory=TextParameters)
    icon: IconParameters = Field(default_factory=IconParameters)
    accent_style: AccentStyle = Field(default=AccentStyle.NONE)
    tier_shape: Literal["trapezoid", "rectangle", "chevron"] = Field(
        default="trapezoid"
    )


class ProcessStepParams(BaseParameters):
    """Parameters for a process step component."""

    step_index: int = Field(ge=0, description="Step position")
    total_steps: int = Field(ge=1, description="Total number of steps")
    step_number: Optional[int] = Field(default=None, description="Displayed step number")
    color: ColorParameters = Field(default_factory=ColorParameters)
    text: TextParameters = Field(default_factory=TextParameters)
    icon: IconParameters = Field(default_factory=IconParameters)
    connector_style: ConnectorStyle = Field(default=ConnectorStyle.ARROW)
    step_shape: Literal["rectangle", "chevron", "circle", "hexagon"] = Field(
        default="rectangle"
    )
    show_number: bool = Field(default=True)


class CycleNodeParams(BaseParameters):
    """Parameters for a cycle/wheel node component."""

    node_index: int = Field(ge=0, description="Position in cycle")
    total_nodes: int = Field(ge=2, description="Total nodes in cycle")
    angle: float = Field(description="Angle position in degrees")
    radius_ratio: float = Field(
        default=0.7,
        ge=0.3,
        le=1.0,
        description="Radius as ratio of available space",
    )
    color: ColorParameters = Field(default_factory=ColorParameters)
    text: TextParameters = Field(default_factory=TextParameters)
    icon: IconParameters = Field(default_factory=IconParameters)
    connector_style: ConnectorStyle = Field(default=ConnectorStyle.ARROW)
    node_shape: Literal["circle", "rounded_rect", "hexagon"] = Field(default="circle")


class HubSpokeNodeParams(BaseParameters):
    """Parameters for a hub or spoke node component."""

    is_hub: bool = Field(default=False, description="True if this is the central hub")
    spoke_index: int = Field(default=0, ge=0, description="Spoke position (0 for hub)")
    total_spokes: int = Field(ge=1, description="Total number of spokes")
    angle: float = Field(default=0.0, description="Angle position in degrees")
    color: ColorParameters = Field(default_factory=ColorParameters)
    text: TextParameters = Field(default_factory=TextParameters)
    icon: IconParameters = Field(default_factory=IconParameters)
    connector_style: ConnectorStyle = Field(default=ConnectorStyle.LINE)
    node_shape: Literal["circle", "rounded_rect", "hexagon"] = Field(default="circle")


class IconBubbleParams(BaseParameters):
    """Parameters for an icon bubble component."""

    color: ColorParameters = Field(default_factory=ColorParameters)
    text: TextParameters = Field(default_factory=TextParameters)
    icon: IconParameters = Field(default_factory=IconParameters)
    bubble_shape: Literal["circle", "rounded_rect", "square"] = Field(default="circle")
    accent_style: AccentStyle = Field(default=AccentStyle.SHADOW)
    size: Literal["small", "medium", "large"] = Field(default="medium")


class ComparisonColumnParams(BaseParameters):
    """Parameters for a comparison column component."""

    column_index: int = Field(ge=0, description="Column position")
    total_columns: int = Field(ge=2, description="Total columns")
    header_text: str = Field(description="Column header")
    items: list[str] = Field(default_factory=list, description="List items")
    color: ColorParameters = Field(default_factory=ColorParameters)
    text: TextParameters = Field(default_factory=TextParameters)
    icon: IconParameters = Field(default_factory=IconParameters)
    check_style: Literal["checkmark", "x", "dot", "number"] = Field(default="checkmark")


class MatrixCellParams(BaseParameters):
    """Parameters for a matrix cell component."""

    row: int = Field(ge=0, description="Row index")
    col: int = Field(ge=0, description="Column index")
    total_rows: int = Field(ge=1)
    total_cols: int = Field(ge=1)
    color: ColorParameters = Field(default_factory=ColorParameters)
    text: TextParameters = Field(default_factory=TextParameters)
    icon: IconParameters = Field(default_factory=IconParameters)
    cell_type: Literal["content", "header_row", "header_col", "corner"] = Field(
        default="content"
    )


# ============================================================================
# Parameter Registry
# ============================================================================


COMPONENT_PARAMS: dict[str, type[BaseParameters]] = {
    "funnel_layer": FunnelLayerParams,
    "timeline_node": TimelineNodeParams,
    "pyramid_tier": PyramidTierParams,
    "process_step": ProcessStepParams,
    "cycle_node": CycleNodeParams,
    "hub_spoke_node": HubSpokeNodeParams,
    "icon_bubble": IconBubbleParams,
    "comparison_column": ComparisonColumnParams,
    "matrix_cell": MatrixCellParams,
}


def get_param_schema(component_type: str) -> type[BaseParameters] | None:
    """Get the parameter schema for a component type."""
    return COMPONENT_PARAMS.get(component_type)


def validate_params(component_type: str, params: dict[str, Any]) -> BaseParameters:
    """Validate parameters for a component type.

    Args:
        component_type: The component type name.
        params: Parameter dictionary.

    Returns:
        Validated parameter model.

    Raises:
        ValueError: If component type is unknown.
        ValidationError: If parameters are invalid.
    """
    schema = get_param_schema(component_type)
    if schema is None:
        raise ValueError(f"Unknown component type: {component_type}")
    return schema(**params)
