"""Base component class for infographic building blocks."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from backend.dsl.schema import BoundingBox, Shape, SolidFill, ThemeColors, Transform
from backend.components.parameters import BaseParameters

P = TypeVar("P", bound=BaseParameters)


class ComponentMetadata(BaseModel):
    """Metadata about a component instance."""

    model_config = ConfigDict(frozen=True)

    component_type: str = Field(description="Component type name")
    instance_id: str = Field(description="Unique instance identifier")
    source_template: str | None = Field(
        default=None,
        description="Template this was derived from",
    )
    variation_seed: int | None = Field(
        default=None,
        description="Random seed for reproducible variations",
    )


class ComponentInstance(BaseModel, Generic[P]):
    """A concrete instance of a component with parameters."""

    model_config = ConfigDict(frozen=True)

    metadata: ComponentMetadata
    params: P
    shapes: list[Shape] = Field(default_factory=list)
    bbox: BoundingBox | None = Field(default=None)


class BaseComponent(ABC, Generic[P]):
    """Abstract base class for all infographic components.

    Components are reusable building blocks that can be parameterized
    and instantiated to create shapes in the DSL scene graph.
    """

    # Class-level metadata
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    archetype: ClassVar[str] = ""  # funnel, timeline, pyramid, etc.
    param_class: ClassVar[type[BaseParameters]]

    def __init__(self, theme: ThemeColors | None = None) -> None:
        """Initialize the component.

        Args:
            theme: Theme colors for color token resolution.
        """
        self.theme = theme or ThemeColors()

    @abstractmethod
    def generate(
        self,
        params: P,
        bbox: BoundingBox,
        instance_id: str,
    ) -> list[Shape]:
        """Generate shapes for this component.

        Args:
            params: Component parameters.
            bbox: Bounding box for the component.
            instance_id: Unique identifier for this instance.

        Returns:
            List of shapes forming this component.
        """
        pass

    def create_instance(
        self,
        params: P,
        bbox: BoundingBox,
        instance_id: str,
        template_name: str | None = None,
    ) -> ComponentInstance[P]:
        """Create a complete component instance.

        Args:
            params: Component parameters.
            bbox: Bounding box for the component.
            instance_id: Unique identifier.
            template_name: Optional source template name.

        Returns:
            ComponentInstance with metadata, params, and shapes.
        """
        shapes = self.generate(params, bbox, instance_id)

        metadata = ComponentMetadata(
            component_type=self.name,
            instance_id=instance_id,
            source_template=template_name,
        )

        return ComponentInstance(
            metadata=metadata,
            params=params,
            shapes=shapes,
            bbox=bbox,
        )

    def resolve_color(self, color_token: str, override: str | None = None) -> str:
        """Resolve a color token to a hex color.

        Args:
            color_token: Token like 'accent1', 'primary', etc.
            override: Direct hex color override.

        Returns:
            Hex color string.
        """
        if override:
            return override

        token_map = {
            "accent1": self.theme.accent1,
            "accent2": self.theme.accent2,
            "accent3": self.theme.accent3,
            "accent4": self.theme.accent4,
            "accent5": self.theme.accent5,
            "accent6": self.theme.accent6,
            "primary": self.theme.accent1,
            "secondary": self.theme.accent2,
            "dark1": self.theme.dark1,
            "dark2": self.theme.dark2,
            "light1": self.theme.light1,
            "light2": self.theme.light2,
        }

        return token_map.get(color_token, self.theme.accent1)

    def create_shape(
        self,
        shape_id: str,
        shape_type: str,
        bbox: BoundingBox,
        fill_color: str,
        auto_shape_type: str = "rect",
        text_content: Any = None,
        z_index: int = 0,
    ) -> Shape:
        """Helper to create a shape with common defaults.

        Args:
            shape_id: Unique shape identifier.
            shape_type: DSL shape type.
            bbox: Bounding box.
            fill_color: Fill color hex.
            auto_shape_type: Auto shape type name.
            text_content: Optional text content.
            z_index: Z-order index.

        Returns:
            Shape instance.
        """
        return Shape(
            id=shape_id,
            type=shape_type,
            bbox=bbox,
            transform=Transform(),
            fill=SolidFill(color=fill_color),
            auto_shape_type=auto_shape_type,
            text=text_content,
            z_index=z_index,
        )

    @classmethod
    def get_default_params(cls) -> P:
        """Get default parameters for this component."""
        return cls.param_class()

    @classmethod
    def validate_params(cls, params: dict[str, Any]) -> P:
        """Validate parameters dictionary.

        Args:
            params: Raw parameter dictionary.

        Returns:
            Validated parameter instance.
        """
        return cls.param_class(**params)


def calculate_tier_width(
    tier_index: int,
    total_tiers: int,
    max_width: int,
    min_ratio: float = 0.25,
    direction: str = "increasing",
) -> int:
    """Calculate width for a tiered component (funnel, pyramid).

    Args:
        tier_index: Current tier index (0-based).
        total_tiers: Total number of tiers.
        max_width: Maximum width in EMUs.
        min_ratio: Minimum width as ratio of max.
        direction: 'increasing' (pyramid) or 'decreasing' (funnel).

    Returns:
        Width in EMUs.
    """
    if total_tiers <= 1:
        return max_width

    if direction == "increasing":
        # Top is narrow, bottom is wide (pyramid)
        ratio = min_ratio + (1.0 - min_ratio) * (tier_index / (total_tiers - 1))
    else:
        # Top is wide, bottom is narrow (funnel)
        ratio = 1.0 - (1.0 - min_ratio) * (tier_index / (total_tiers - 1))

    return int(max_width * ratio)


def calculate_radial_position(
    index: int,
    total: int,
    center_x: int,
    center_y: int,
    radius: int,
    start_angle: float = -90.0,
) -> tuple[int, int]:
    """Calculate position on a circle.

    Args:
        index: Item index.
        total: Total items.
        center_x: Circle center X.
        center_y: Circle center Y.
        radius: Circle radius.
        start_angle: Starting angle in degrees (default: top).

    Returns:
        Tuple of (x, y) position.
    """
    import math

    angle_step = 360.0 / total
    angle = math.radians(start_angle + index * angle_step)

    x = int(center_x + radius * math.cos(angle))
    y = int(center_y + radius * math.sin(angle))

    return x, y
