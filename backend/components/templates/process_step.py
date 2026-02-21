"""Process step component implementation."""

from typing import ClassVar

from backend.components.base import BaseComponent
from backend.components.parameters import ProcessStepParams
from backend.dsl.schema import BoundingBox, Shape, TextContent, TextRun


class ProcessStepComponent(BaseComponent[ProcessStepParams]):
    """A step in a process flow diagram.

    Process steps are typically arranged horizontally with arrows
    or connectors showing the flow between steps.
    """

    name: ClassVar[str] = "process_step"
    description: ClassVar[str] = "A step in a process flow diagram"
    archetype: ClassVar[str] = "process"
    param_class: ClassVar = ProcessStepParams

    # Shape type mappings
    STEP_SHAPES = {
        "rectangle": "rect",
        "chevron": "chevron",
        "circle": "ellipse",
        "hexagon": "hexagon",
    }

    def generate(
        self,
        params: ProcessStepParams,
        bbox: BoundingBox,
        instance_id: str,
    ) -> list[Shape]:
        """Generate shapes for a process step.

        Args:
            params: Process step parameters.
            bbox: Bounding box for this step.
            instance_id: Unique identifier.

        Returns:
            List of shapes forming the process step.
        """
        shapes = []

        # Resolve color
        fill_color = self.resolve_color(
            params.color.color_token,
            params.color.color_override,
        )

        # Calculate step dimensions
        gap = 100000  # Gap between steps for connectors
        step_width = (bbox.width - gap * (params.total_steps - 1)) // params.total_steps
        step_x = bbox.x + params.step_index * (step_width + gap)

        # Create step bounding box
        step_bbox = BoundingBox(
            x=step_x,
            y=bbox.y,
            width=step_width,
            height=bbox.height,
        )

        # Get shape type
        auto_shape_type = self.STEP_SHAPES.get(params.step_shape, "rect")

        # Create text content
        text_runs = []

        # Add step number if enabled
        if params.show_number:
            step_num = params.step_number or (params.step_index + 1)
            text_runs.append(
                TextRun(
                    text=f"{step_num}. ",
                    font_size=int(1600 * params.text.font_scale),
                    bold=True,
                    color="#FFFFFF",
                )
            )

        # Add title
        if params.text.title:
            text_runs.append(
                TextRun(
                    text=params.text.title,
                    font_size=int(1400 * params.text.font_scale),
                    bold=True,
                    color="#FFFFFF",
                )
            )

        # Add description
        if params.text.description:
            text_runs.append(
                TextRun(
                    text=f"\n{params.text.description}",
                    font_size=int(1000 * params.text.font_scale),
                    color="#FFFFFF",
                )
            )

        text_content = None
        if text_runs:
            text_content = TextContent(
                runs=text_runs,
                alignment=params.text.alignment.value,
                vertical_alignment="middle",
            )

        # Create the main step shape
        step_shape = self.create_shape(
            shape_id=f"{instance_id}_step",
            shape_type="autoShape",
            bbox=step_bbox,
            fill_color=fill_color,
            auto_shape_type=auto_shape_type,
            text_content=text_content,
            z_index=params.step_index + 10,
        )
        shapes.append(step_shape)

        # Add icon if specified
        if params.icon.icon:
            icon_shape = self._create_icon(
                params=params,
                step_bbox=step_bbox,
                instance_id=instance_id,
            )
            if icon_shape:
                shapes.append(icon_shape)

        # Add connector to next step (if not the last)
        if (
            params.connector_style.value != "none"
            and params.step_index < params.total_steps - 1
        ):
            connector_shape = self._create_connector(
                params=params,
                step_bbox=step_bbox,
                gap=gap,
                instance_id=instance_id,
                fill_color=fill_color,
            )
            if connector_shape:
                shapes.append(connector_shape)

        return shapes

    def _create_icon(
        self,
        params: ProcessStepParams,
        step_bbox: BoundingBox,
        instance_id: str,
    ) -> Shape | None:
        """Create an icon shape above the step."""
        icon_size = min(step_bbox.width // 3, 150000)

        # Position icon above the step
        icon_bbox = BoundingBox(
            x=step_bbox.x + (step_bbox.width - icon_size) // 2,
            y=step_bbox.y - icon_size - 50000,
            width=icon_size,
            height=icon_size,
        )

        icon_color = params.icon.icon_color or self.theme.accent1
        icon_text = TextContent(
            runs=[
                TextRun(
                    text=params.icon.icon,
                    font_size=int(1200 * params.icon.icon_size),
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
            fill_color=self.theme.light1,
            auto_shape_type="ellipse",
            text_content=icon_text,
            z_index=params.step_index + 100,
        )

    def _create_connector(
        self,
        params: ProcessStepParams,
        step_bbox: BoundingBox,
        gap: int,
        instance_id: str,
        fill_color: str,
    ) -> Shape | None:
        """Create a connector arrow to the next step."""
        connector_style = params.connector_style.value

        # Position connector in the gap
        connector_x = step_bbox.x + step_bbox.width
        connector_y = step_bbox.y + step_bbox.height // 2

        connector_width = gap
        connector_height = gap // 2

        connector_bbox = BoundingBox(
            x=connector_x,
            y=connector_y - connector_height // 2,
            width=connector_width,
            height=connector_height,
        )

        # Choose shape based on connector style
        if connector_style == "arrow":
            shape_type = "right_arrow"
        elif connector_style == "line":
            shape_type = "rect"
            connector_bbox = BoundingBox(
                x=connector_x,
                y=connector_y - 10000,
                width=connector_width,
                height=20000,
            )
        else:
            shape_type = "rect"

        return self.create_shape(
            shape_id=f"{instance_id}_connector",
            shape_type="autoShape",
            bbox=connector_bbox,
            fill_color=fill_color,
            auto_shape_type=shape_type,
            z_index=params.step_index,
        )
