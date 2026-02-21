"""Component registry for managing infographic component types."""

from typing import Any, Type

from backend.components.base import BaseComponent, ComponentInstance
from backend.components.parameters import BaseParameters
from backend.dsl.schema import BoundingBox, ThemeColors


class ComponentRegistry:
    """Registry for managing and instantiating component types.

    This registry provides a central place to register component classes
    and create instances of them. Components are registered by name and
    can be looked up and instantiated dynamically.
    """

    _instance: "ComponentRegistry | None" = None
    _components: dict[str, Type[BaseComponent]]

    def __new__(cls) -> "ComponentRegistry":
        """Singleton pattern for global registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._components = {}
        return cls._instance

    def register(self, component_class: Type[BaseComponent]) -> Type[BaseComponent]:
        """Register a component class.

        Can be used as a decorator:
            @registry.register
            class MyComponent(BaseComponent):
                ...

        Args:
            component_class: The component class to register.

        Returns:
            The same class (for decorator use).

        Raises:
            ValueError: If component has no name or is already registered.
        """
        name = component_class.name
        if not name:
            raise ValueError(f"Component {component_class} has no name")

        if name in self._components:
            raise ValueError(f"Component '{name}' is already registered")

        self._components[name] = component_class
        return component_class

    def unregister(self, name: str) -> None:
        """Unregister a component by name.

        Args:
            name: Component name to unregister.
        """
        self._components.pop(name, None)

    def get(self, name: str) -> Type[BaseComponent] | None:
        """Get a component class by name.

        Args:
            name: Component name.

        Returns:
            Component class or None if not found.
        """
        return self._components.get(name)

    def get_or_raise(self, name: str) -> Type[BaseComponent]:
        """Get a component class by name, raising if not found.

        Args:
            name: Component name.

        Returns:
            Component class.

        Raises:
            KeyError: If component not found.
        """
        component = self._components.get(name)
        if component is None:
            raise KeyError(f"Component '{name}' not found in registry")
        return component

    def list_components(self) -> list[str]:
        """List all registered component names.

        Returns:
            List of component names.
        """
        return list(self._components.keys())

    def list_by_archetype(self, archetype: str) -> list[str]:
        """List components for a specific archetype.

        Args:
            archetype: Archetype name (funnel, timeline, etc.).

        Returns:
            List of component names.
        """
        return [
            name
            for name, cls in self._components.items()
            if cls.archetype == archetype
        ]

    def create_instance(
        self,
        component_name: str,
        params: dict[str, Any],
        bbox: BoundingBox,
        instance_id: str,
        theme: ThemeColors | None = None,
        template_name: str | None = None,
    ) -> ComponentInstance:
        """Create a component instance.

        Args:
            component_name: Name of the component to instantiate.
            params: Parameter dictionary.
            bbox: Bounding box for the component.
            instance_id: Unique instance identifier.
            theme: Optional theme colors.
            template_name: Optional source template name.

        Returns:
            ComponentInstance with generated shapes.

        Raises:
            KeyError: If component not found.
            ValidationError: If parameters invalid.
        """
        component_class = self.get_or_raise(component_name)
        component = component_class(theme=theme)

        validated_params = component_class.validate_params(params)
        return component.create_instance(
            params=validated_params,
            bbox=bbox,
            instance_id=instance_id,
            template_name=template_name,
        )

    def get_param_schema(self, component_name: str) -> Type[BaseParameters] | None:
        """Get the parameter schema for a component.

        Args:
            component_name: Component name.

        Returns:
            Parameter class or None.
        """
        component = self.get(component_name)
        if component:
            return component.param_class
        return None

    def get_component_info(self, component_name: str) -> dict[str, Any] | None:
        """Get information about a component.

        Args:
            component_name: Component name.

        Returns:
            Dictionary with component info or None.
        """
        component = self.get(component_name)
        if component is None:
            return None

        param_schema = component.param_class.model_json_schema()

        return {
            "name": component.name,
            "description": component.description,
            "archetype": component.archetype,
            "parameters": param_schema,
        }

    def clear(self) -> None:
        """Clear all registered components. Use for testing."""
        self._components.clear()


# Global registry instance
registry = ComponentRegistry()


def register_component(cls: Type[BaseComponent]) -> Type[BaseComponent]:
    """Decorator to register a component class.

    Usage:
        @register_component
        class FunnelLayerComponent(BaseComponent):
            name = "funnel_layer"
            ...
    """
    return registry.register(cls)


def get_component(name: str) -> Type[BaseComponent] | None:
    """Get a component class by name."""
    return registry.get(name)


def create_component_instance(
    component_name: str,
    params: dict[str, Any],
    bbox: BoundingBox,
    instance_id: str,
    theme: ThemeColors | None = None,
) -> ComponentInstance:
    """Convenience function to create a component instance."""
    return registry.create_instance(
        component_name=component_name,
        params=params,
        bbox=bbox,
        instance_id=instance_id,
        theme=theme,
    )
