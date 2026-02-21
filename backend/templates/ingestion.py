"""Template ingestion pipeline - import PPTX files as templates."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO

from backend.components.detector import ComponentDetector, DetectedComponent
from backend.dsl.schema import SlideScene
from backend.templates.store import (
    Template,
    TemplateComponent,
    TemplateStore,
    TemplateVariation,
)


class TemplateIngester:
    """Ingests PPTX files and converts them to reusable templates.

    The ingestion process:
    1. Parse PPTX to DSL scene graph
    2. Detect component patterns
    3. Extract parameters and variation ranges
    4. Store as template definition
    """

    def __init__(
        self,
        store: TemplateStore | None = None,
        detector: ComponentDetector | None = None,
    ) -> None:
        """Initialize the ingester.

        Args:
            store: Template store for saving results.
            detector: Component detector for pattern recognition.
        """
        self.store = store or TemplateStore()
        self.detector = detector or ComponentDetector()

    def ingest_scene(
        self,
        scene: SlideScene,
        name: str,
        description: str = "",
        tags: list[str] | None = None,
        source_file: str | None = None,
    ) -> Template:
        """Ingest a DSL scene as a template.

        Args:
            scene: SlideScene to convert to template.
            name: Template name.
            description: Template description.
            tags: Optional tags for categorization.
            source_file: Original source file name.

        Returns:
            Created Template.
        """
        # Detect components in the scene
        detection_result = self.detector.detect(scene)

        # Convert detected components to template components
        template_components = []
        for detected in detection_result.components:
            template_comp = self._convert_to_template_component(
                detected=detected,
                canvas_width=scene.canvas.width,
                canvas_height=scene.canvas.height,
            )
            template_components.append(template_comp)

        # Determine archetype
        archetype = detection_result.archetype or self._infer_archetype_from_metadata(
            scene
        )

        # Extract global variations (colors, fonts, etc.)
        global_variations = self._extract_global_variations(scene)

        # Create template
        template = Template(
            id=f"tpl_{uuid.uuid4().hex[:8]}",
            name=name,
            description=description,
            archetype=archetype or "custom",
            tags=tags or [],
            canvas_width=scene.canvas.width,
            canvas_height=scene.canvas.height,
            components=template_components,
            global_variations=global_variations,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            source_file=source_file,
            original_scene=scene,
        )

        return template

    def ingest_and_save(
        self,
        scene: SlideScene,
        name: str,
        description: str = "",
        tags: list[str] | None = None,
        source_file: str | None = None,
    ) -> str:
        """Ingest a scene and save to the store.

        Args:
            scene: SlideScene to convert.
            name: Template name.
            description: Template description.
            tags: Optional tags.
            source_file: Original source file.

        Returns:
            Template ID.
        """
        template = self.ingest_scene(
            scene=scene,
            name=name,
            description=description,
            tags=tags,
            source_file=source_file,
        )
        return self.store.save(template)

    def _convert_to_template_component(
        self,
        detected: DetectedComponent,
        canvas_width: int,
        canvas_height: int,
    ) -> TemplateComponent:
        """Convert a detected component to a template component.

        Args:
            detected: Detected component from the detector.
            canvas_width: Canvas width for relative positioning.
            canvas_height: Canvas height for relative positioning.

        Returns:
            TemplateComponent with relative positioning.
        """
        # Calculate relative bounding box
        bbox_relative = {
            "x": detected.bbox["x"] / canvas_width,
            "y": detected.bbox["y"] / canvas_height,
            "width": detected.bbox["width"] / canvas_width,
            "height": detected.bbox["height"] / canvas_height,
        }

        # Extract variations based on component type
        variations = self._extract_component_variations(
            component_type=detected.component_type,
            params=detected.params,
        )

        return TemplateComponent(
            component_type=detected.component_type,
            params=detected.params,
            variations=variations,
            bbox_relative=bbox_relative,
        )

    def _extract_component_variations(
        self,
        component_type: str,
        params: dict[str, Any],
    ) -> list[TemplateVariation]:
        """Extract variation ranges for a component.

        Args:
            component_type: Type of component.
            params: Component parameters.

        Returns:
            List of variation definitions.
        """
        variations = []

        # Common variations for all components
        variations.append(
            TemplateVariation(
                parameter="color.color_token",
                type="enum",
                values=["accent1", "accent2", "accent3", "accent4", "accent5", "accent6"],
                description="Color theme token",
            )
        )

        # Component-specific variations
        if component_type == "funnel_layer":
            variations.append(
                TemplateVariation(
                    parameter="taper_ratio",
                    type="range",
                    values=[0.6, 0.95],
                    description="Funnel taper ratio",
                )
            )
            variations.append(
                TemplateVariation(
                    parameter="accent_style",
                    type="enum",
                    values=["none", "ring", "arc", "glow"],
                    description="Accent decoration style",
                )
            )

        elif component_type == "timeline_node":
            variations.append(
                TemplateVariation(
                    parameter="node_shape",
                    type="enum",
                    values=["circle", "diamond", "square", "hexagon"],
                    description="Node shape",
                )
            )
            variations.append(
                TemplateVariation(
                    parameter="position",
                    type="enum",
                    values=["above", "below", "alternate"],
                    description="Content position",
                )
            )

        elif component_type == "pyramid_tier":
            variations.append(
                TemplateVariation(
                    parameter="tier_shape",
                    type="enum",
                    values=["trapezoid", "rectangle", "chevron"],
                    description="Tier shape",
                )
            )

        elif component_type == "process_step":
            variations.append(
                TemplateVariation(
                    parameter="step_shape",
                    type="enum",
                    values=["rectangle", "chevron", "circle", "hexagon"],
                    description="Step shape",
                )
            )
            variations.append(
                TemplateVariation(
                    parameter="connector_style",
                    type="enum",
                    values=["arrow", "line", "none"],
                    description="Connector style",
                )
            )

        elif component_type == "cycle_node":
            variations.append(
                TemplateVariation(
                    parameter="radius_ratio",
                    type="range",
                    values=[0.5, 0.9],
                    description="Circle radius ratio",
                )
            )

        elif component_type == "hub_spoke_node":
            variations.append(
                TemplateVariation(
                    parameter="node_shape",
                    type="enum",
                    values=["circle", "rounded_rect", "hexagon"],
                    description="Node shape",
                )
            )

        return variations

    def _extract_global_variations(self, scene: SlideScene) -> list[TemplateVariation]:
        """Extract global variation ranges from a scene.

        Args:
            scene: The scene to analyze.

        Returns:
            List of global variations.
        """
        variations = []

        # Theme color variations
        variations.append(
            TemplateVariation(
                parameter="theme.accent1",
                type="list",
                values=[
                    "#0D9488",  # Teal (default)
                    "#3B82F6",  # Blue
                    "#8B5CF6",  # Purple
                    "#F59E0B",  # Amber
                    "#EF4444",  # Red
                    "#10B981",  # Emerald
                ],
                description="Primary accent color",
            )
        )

        # Font scale variations
        variations.append(
            TemplateVariation(
                parameter="text.font_scale",
                type="range",
                values=[0.8, 1.2],
                description="Global font size multiplier",
            )
        )

        return variations

    def _infer_archetype_from_metadata(self, scene: SlideScene) -> str | None:
        """Infer archetype from scene metadata.

        Args:
            scene: The scene to analyze.

        Returns:
            Inferred archetype or None.
        """
        if scene.metadata.archetype:
            return scene.metadata.archetype

        # Try to infer from tags
        tag_to_archetype = {
            "funnel": "funnel",
            "sales": "funnel",
            "marketing": "funnel",
            "timeline": "timeline",
            "roadmap": "timeline",
            "history": "timeline",
            "pyramid": "pyramid",
            "hierarchy": "pyramid",
            "process": "process",
            "workflow": "process",
            "steps": "process",
            "cycle": "cycle",
            "wheel": "cycle",
            "loop": "cycle",
            "hub": "hub_spoke",
            "spoke": "hub_spoke",
            "radial": "hub_spoke",
        }

        for tag in scene.metadata.tags:
            tag_lower = tag.lower()
            if tag_lower in tag_to_archetype:
                return tag_to_archetype[tag_lower]

        return None


class TemplateGenerator:
    """Generates slides from templates with variations."""

    def __init__(self, store: TemplateStore | None = None) -> None:
        """Initialize the generator.

        Args:
            store: Template store to read templates from.
        """
        self.store = store or TemplateStore()

    def generate_from_template(
        self,
        template_id: str,
        content: dict[str, Any] | None = None,
        variations: dict[str, Any] | None = None,
    ) -> SlideScene:
        """Generate a slide from a template.

        Args:
            template_id: Template to use.
            content: Content to fill in (titles, descriptions, etc.).
            variations: Variation values to apply.

        Returns:
            Generated SlideScene.

        Raises:
            KeyError: If template not found.
        """
        from backend.components import init_components, registry
        from backend.dsl.schema import Canvas, SlideMetadata, ThemeColors

        # Ensure components are registered
        init_components()

        template = self.store.get_or_raise(template_id)

        # Create canvas
        canvas = Canvas(
            width=template.canvas_width,
            height=template.canvas_height,
        )

        # Apply theme variations
        theme = ThemeColors()
        if variations and "theme.accent1" in variations:
            theme = ThemeColors(accent1=variations["theme.accent1"])

        # Generate shapes from components
        all_shapes = []
        content_list = content.get("items", []) if content else []

        for i, comp in enumerate(template.components):
            # Calculate absolute bounding box
            from backend.dsl.schema import BoundingBox

            bbox = BoundingBox(
                x=int(comp.bbox_relative["x"] * template.canvas_width),
                y=int(comp.bbox_relative["y"] * template.canvas_height),
                width=int(comp.bbox_relative["width"] * template.canvas_width),
                height=int(comp.bbox_relative["height"] * template.canvas_height),
            )

            # Merge params with content and variations
            params = dict(comp.params)

            # Apply content if available
            if i < len(content_list):
                item_content = content_list[i]
                if "title" in item_content:
                    if "text" not in params:
                        params["text"] = {}
                    params["text"]["title"] = item_content["title"]
                if "description" in item_content:
                    if "text" not in params:
                        params["text"] = {}
                    params["text"]["description"] = item_content["description"]

            # Apply variations
            if variations:
                for var in comp.variations:
                    if var.parameter in variations:
                        self._apply_variation(params, var.parameter, variations[var.parameter])

            # Create component instance
            try:
                instance = registry.create_instance(
                    component_name=comp.component_type,
                    params=params,
                    bbox=bbox,
                    instance_id=f"gen_{i}_{uuid.uuid4().hex[:4]}",
                    theme=theme,
                )
                all_shapes.extend(instance.shapes)
            except Exception as e:
                # Skip failed components but log error
                print(f"Error generating component {comp.component_type}: {e}")

        # Create scene
        return SlideScene(
            canvas=canvas,
            shapes=all_shapes,
            theme=theme,
            metadata=SlideMetadata(
                archetype=template.archetype,
                tags=template.tags,
            ),
        )

    def _apply_variation(
        self,
        params: dict[str, Any],
        path: str,
        value: Any,
    ) -> None:
        """Apply a variation value to nested params.

        Args:
            params: Parameters dictionary to modify.
            path: Dot-separated path (e.g., 'color.color_token').
            value: Value to set.
        """
        parts = path.split(".")
        current = params

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value
