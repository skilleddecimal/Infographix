"""
layout_engine.py — Layout orchestrator.

The LayoutEngine coordinates the entire layout generation process:
1. Receives parsed diagram input
2. Selects appropriate archetype
3. Invokes archetype to generate PositionedLayout
4. Validates and returns the layout

This is the main entry point for layout generation.

ARCHITECTURE NOTE:
The engine supports two systems:
1. Legacy system: Individual Python archetype classes (backward compatible)
2. Universal system: Data-driven JSON rules with UniversalArchetype (new, preferred)

The universal system is enabled by default. Set use_universal=False to use legacy.

NOTE: Uses lazy imports to avoid circular dependency with archetypes module.
"""

from typing import Dict, Type, Optional, List, Any
from dataclasses import dataclass
import logging

from .positioned import PositionedLayout, ConnectorStyle
from .data_models import (
    ColorPalette,
    BlockData,
    ConnectorData,
    LayerData,
    DiagramInput,
)
from .archetype_registry import (
    ArchetypeType,
    ArchetypeCategory,
    ArchetypeMetadata,
    ARCHETYPE_METADATA,
    get_archetype_metadata,
    get_implemented_archetype_types,
    search_archetypes,
    generate_llm_archetype_descriptions,
)

logger = logging.getLogger(__name__)


def _get_archetype_class(archetype_type: ArchetypeType):
    """
    Lazily import and return archetype class to avoid circular imports.
    """
    if archetype_type == ArchetypeType.MARKETECTURE:
        from ..archetypes.marketecture import MarketectureArchetype
        return MarketectureArchetype
    elif archetype_type == ArchetypeType.PROCESS_FLOW:
        from ..archetypes.process_flow import ProcessFlowArchetype
        return ProcessFlowArchetype
    elif archetype_type == ArchetypeType.COMPARISON:
        from ..archetypes.comparison import ComparisonArchetype
        return ComparisonArchetype
    elif archetype_type == ArchetypeType.TIMELINE:
        from ..archetypes.timeline import TimelineArchetype
        return TimelineArchetype
    elif archetype_type == ArchetypeType.PYRAMID:
        from ..archetypes.pyramid import PyramidArchetype
        return PyramidArchetype
    elif archetype_type == ArchetypeType.FUNNEL:
        from ..archetypes.funnel import FunnelArchetype
        return FunnelArchetype
    elif archetype_type == ArchetypeType.HUB_SPOKE:
        from ..archetypes.hub_spoke import HubSpokeArchetype
        return HubSpokeArchetype
    elif archetype_type == ArchetypeType.VENN_DIAGRAM:
        from ..archetypes.venn import VennArchetype
        return VennArchetype
    elif archetype_type == ArchetypeType.MATRIX_2X2:
        from ..archetypes.matrix import MatrixArchetype
        return MatrixArchetype
    elif archetype_type == ArchetypeType.CIRCULAR_CYCLE:
        from ..archetypes.cycle import CycleArchetype
        return CycleArchetype
    elif archetype_type == ArchetypeType.TARGET:
        from ..archetypes.target import TargetArchetype
        return TargetArchetype
    elif archetype_type == ArchetypeType.STAIRCASE:
        from ..archetypes.staircase import StaircaseArchetype
        return StaircaseArchetype
    elif archetype_type == ArchetypeType.CHEVRON_PROCESS:
        from ..archetypes.chevron import ChevronArchetype
        return ChevronArchetype
    elif archetype_type == ArchetypeType.ICON_GRID:
        from ..archetypes.icon_grid import IconGridArchetype
        return IconGridArchetype
    elif archetype_type == ArchetypeType.BULLET_LIST:
        from ..archetypes.bullet_list import BulletListArchetype
        return BulletListArchetype
    elif archetype_type == ArchetypeType.CARD_GRID:
        from ..archetypes.card_grid import CardGridArchetype
        return CardGridArchetype
    elif archetype_type == ArchetypeType.ORG_CHART:
        from ..archetypes.org_chart import OrgChartArchetype
        return OrgChartArchetype
    elif archetype_type == ArchetypeType.PIPELINE:
        from ..archetypes.pipeline import PipelineArchetype
        return PipelineArchetype
    elif archetype_type == ArchetypeType.SWOT:
        from ..archetypes.swot import SWOTArchetype
        return SWOTArchetype
    elif archetype_type == ArchetypeType.BEFORE_AFTER:
        from ..archetypes.before_after import BeforeAfterArchetype
        return BeforeAfterArchetype
    elif archetype_type == ArchetypeType.ROADMAP:
        from ..archetypes.roadmap import RoadmapArchetype
        return RoadmapArchetype
    elif archetype_type == ArchetypeType.PROGRESS_BAR:
        from ..archetypes.progress_bar import ProgressBarArchetype
        return ProgressBarArchetype
    elif archetype_type == ArchetypeType.GAUGE:
        from ..archetypes.gauge import GaugeArchetype
        return GaugeArchetype
    elif archetype_type == ArchetypeType.PICTOGRAM:
        from ..archetypes.pictogram import PictogramArchetype
        return PictogramArchetype
    elif archetype_type == ArchetypeType.VERSUS:
        from ..archetypes.versus import VersusArchetype
        return VersusArchetype
    elif archetype_type == ArchetypeType.TREE_DIAGRAM:
        from ..archetypes.tree_diagram import TreeDiagramArchetype
        return TreeDiagramArchetype
    elif archetype_type == ArchetypeType.CANVAS:
        from ..archetypes.canvas import CanvasArchetype
        return CanvasArchetype
    else:
        raise ValueError(f"Archetype '{archetype_type.value}' is not yet implemented")


def get_archetype(archetype_type: ArchetypeType, palette: Optional[ColorPalette] = None):
    """
    Get an archetype instance by type.

    Args:
        archetype_type: Type of archetype to create
        palette: Optional color palette

    Returns:
        Archetype instance

    Raises:
        ValueError: If archetype type is not implemented
    """
    archetype_class = _get_archetype_class(archetype_type)
    return archetype_class(palette=palette)


def list_available_archetypes(include_unimplemented: bool = False) -> List[Dict]:
    """
    List all available archetypes with their metadata.

    Args:
        include_unimplemented: If True, includes all archetypes even if not yet implemented
    """
    result = []

    if include_unimplemented:
        # Return all archetypes from the registry
        for archetype_type, meta in ARCHETYPE_METADATA.items():
            implemented = archetype_type in get_implemented_archetype_types()
            result.append({
                "type": archetype_type.value,
                "name": archetype_type.value,
                "display_name": meta.display_name,
                "description": meta.description,
                "category": meta.category.value,
                "when_to_use": meta.when_to_use,
                "example_prompts": meta.example_prompts,
                "keywords": meta.keywords,
                "implemented": implemented,
            })
    else:
        # Only implemented archetypes
        for archetype_type in get_implemented_archetype_types():
            try:
                archetype_class = _get_archetype_class(archetype_type)
                meta = get_archetype_metadata(archetype_type)
                result.append({
                    "type": archetype_type.value,
                    "name": archetype_class.name,
                    "display_name": meta.display_name if meta else archetype_class.display_name,
                    "description": meta.description if meta else archetype_class.description,
                    "category": meta.category.value if meta else "other",
                    "example_prompts": meta.example_prompts if meta else archetype_class.example_prompts,
                    "implemented": True,
                })
            except ValueError:
                pass

    return result


# =============================================================================
# LAYOUT ENGINE
# =============================================================================

@dataclass
class LayoutResult:
    """Result of layout generation."""
    layout: PositionedLayout
    archetype_used: str
    warnings: List[str]
    success: bool
    error_message: Optional[str] = None
    system_used: str = "legacy"  # "legacy" or "universal"


class LayoutEngine:
    """
    Main layout orchestrator.

    Supports two generation modes:
    - Universal (default): Uses data-driven JSON rules via UniversalArchetype
    - Legacy: Uses individual Python archetype classes

    The universal system provides:
    - Overlay support for all archetypes (arrows, callouts, annotations)
    - Learnable archetypes from PPTX templates
    - Multi-diagram composition
    - Graceful fallback to canvas mode for unknown types
    """

    def __init__(
        self,
        default_palette: Optional[ColorPalette] = None,
        use_universal: bool = True,
    ):
        """
        Initialize the layout engine.

        Args:
            default_palette: Default color palette to use
            use_universal: If True, use the universal archetype system.
                          If False, use legacy Python archetype classes.
        """
        self.default_palette = default_palette or ColorPalette()
        self.use_universal = use_universal
        self._resolver = None  # Lazy loaded

    @property
    def resolver(self):
        """Lazily load the archetype resolver for universal system."""
        if self._resolver is None:
            from .archetype_resolver import get_resolver
            self._resolver = get_resolver()
        return self._resolver

    def generate_layout(
        self,
        input_data: DiagramInput,
        archetype_type: Optional[ArchetypeType] = None,
        archetype_id: Optional[str] = None,
        overlays: Optional[List[Any]] = None,
        use_universal: Optional[bool] = None,
    ) -> LayoutResult:
        """
        Generate a positioned layout from diagram input.

        Args:
            input_data: The diagram input data
            archetype_type: Legacy ArchetypeType enum (for backward compatibility)
            archetype_id: String archetype ID (preferred, for universal system)
            overlays: List of OverlaySpec objects to apply
            use_universal: Override instance-level use_universal setting

        Returns:
            LayoutResult with the generated layout
        """
        # Determine which system to use
        should_use_universal = use_universal if use_universal is not None else self.use_universal

        # Convert archetype_type to archetype_id if needed
        if archetype_id is None and archetype_type is not None:
            archetype_id = archetype_type.value

        # Auto-select archetype if not specified
        if archetype_id is None and archetype_type is None:
            archetype_type = self._select_archetype(input_data)
            archetype_id = archetype_type.value

        palette = input_data.palette or self.default_palette

        # Try universal system first if enabled
        if should_use_universal:
            result = self._generate_with_universal(
                input_data, archetype_id, palette, overlays
            )
            if result.success:
                return result
            # Fall back to legacy on failure if we have an archetype_type
            logger.warning(
                f"Universal system failed for '{archetype_id}': {result.error_message}. "
                f"Falling back to legacy system."
            )

        # Use legacy system
        if archetype_type is None:
            # Convert archetype_id to ArchetypeType
            for at in ArchetypeType:
                if at.value == archetype_id:
                    archetype_type = at
                    break
            if archetype_type is None:
                # No legacy archetype available, try universal as last resort
                if not should_use_universal:
                    return self._generate_with_universal(
                        input_data, archetype_id, palette, overlays
                    )
                return LayoutResult(
                    layout=self._empty_layout(input_data.title),
                    archetype_used=archetype_id or "unknown",
                    warnings=[],
                    success=False,
                    error_message=f"Unknown archetype: {archetype_id}",
                    system_used="none"
                )

        return self._generate_with_legacy(input_data, archetype_type, palette)

    def _generate_with_universal(
        self,
        input_data: DiagramInput,
        archetype_id: str,
        palette: ColorPalette,
        overlays: Optional[List[Any]] = None,
    ) -> LayoutResult:
        """Generate layout using the universal archetype system."""
        try:
            # Resolve archetype rules
            rules = self.resolver.resolve(archetype_id)

            # Create universal archetype instance
            from .universal_archetype import UniversalArchetype
            archetype = UniversalArchetype(rules, palette)

            # Generate layout with optional overlays
            layout = archetype.generate_layout(input_data, overlays=overlays)

            # Validate output layout
            layout_warnings = layout.validate()

            return LayoutResult(
                layout=layout,
                archetype_used=rules.archetype_id,
                warnings=layout_warnings,
                success=True,
                system_used="universal"
            )

        except Exception as e:
            logger.error(f"Universal archetype generation failed: {e}")
            return LayoutResult(
                layout=self._empty_layout(input_data.title),
                archetype_used=archetype_id,
                warnings=[],
                success=False,
                error_message=f"Universal system error: {str(e)}",
                system_used="universal"
            )

    def _generate_with_legacy(
        self,
        input_data: DiagramInput,
        archetype_type: ArchetypeType,
        palette: ColorPalette,
    ) -> LayoutResult:
        """Generate layout using legacy Python archetype classes."""
        # Get archetype instance
        try:
            archetype = get_archetype(archetype_type, palette)
        except ValueError as e:
            return LayoutResult(
                layout=self._empty_layout(input_data.title),
                archetype_used="none",
                warnings=[],
                success=False,
                error_message=str(e),
                system_used="legacy"
            )

        # Validate input
        validation_errors = archetype.validate_input(input_data)
        if validation_errors:
            return LayoutResult(
                layout=self._empty_layout(input_data.title),
                archetype_used=archetype.name,
                warnings=validation_errors,
                success=False,
                error_message=f"Validation failed: {validation_errors[0]}",
                system_used="legacy"
            )

        # Generate layout
        try:
            layout = archetype.generate_layout(input_data)
        except Exception as e:
            return LayoutResult(
                layout=self._empty_layout(input_data.title),
                archetype_used=archetype.name,
                warnings=[],
                success=False,
                error_message=f"Layout generation failed: {str(e)}",
                system_used="legacy"
            )

        # Validate output layout
        layout_warnings = layout.validate()

        return LayoutResult(
            layout=layout,
            archetype_used=archetype.name,
            warnings=layout_warnings,
            success=True,
            system_used="legacy"
        )

    def _select_archetype(self, input_data: DiagramInput) -> ArchetypeType:
        """Auto-select the best archetype based on input characteristics."""
        # Check for explicit archetype hint in metadata
        if "archetype" in input_data.metadata:
            hint = input_data.metadata["archetype"].lower()
            for at in ArchetypeType:
                if at.value == hint:
                    return at

        # If layers are defined, use marketecture
        if input_data.layers:
            return ArchetypeType.MARKETECTURE

        # Default to marketecture for now
        return ArchetypeType.MARKETECTURE

    def _empty_layout(self, title: str) -> PositionedLayout:
        """Create an empty layout for error cases."""
        from .units import SLIDE_WIDTH_INCHES, SLIDE_HEIGHT_INCHES
        return PositionedLayout(
            slide_width_inches=SLIDE_WIDTH_INCHES,
            slide_height_inches=SLIDE_HEIGHT_INCHES,
            background_color=self.default_palette.background,
            elements=[],
            connectors=[]
        )

    def list_archetypes(self, include_learned: bool = True) -> List[Dict[str, Any]]:
        """
        List all available archetypes from both systems.

        Args:
            include_learned: Include learned archetypes from training

        Returns:
            List of archetype info dicts
        """
        archetypes = []

        # Get universal system archetypes
        if self.use_universal:
            try:
                universal_archetypes = self.resolver.list_available(include_canvas=True)
                for arch in universal_archetypes:
                    arch["system"] = "universal"
                    archetypes.append(arch)
            except Exception as e:
                logger.warning(f"Failed to list universal archetypes: {e}")

        # Get legacy archetypes (mark duplicates)
        universal_ids = {a["id"] for a in archetypes}
        for arch_type in get_implemented_archetype_types():
            if arch_type.value not in universal_ids:
                meta = get_archetype_metadata(arch_type)
                if meta:
                    archetypes.append({
                        "id": arch_type.value,
                        "name": meta.display_name,
                        "description": meta.description,
                        "category": meta.category.value,
                        "source": "legacy",
                        "system": "legacy",
                        "confidence": 1.0,
                    })

        return archetypes

    def generate_with_overlays(
        self,
        input_data: DiagramInput,
        archetype_id: str,
        overlays: List[Any],
    ) -> LayoutResult:
        """
        Generate layout with overlays (arrows, callouts, annotations).

        This always uses the universal system since legacy archetypes
        don't support overlays.

        Args:
            input_data: The diagram input data
            archetype_id: String archetype ID
            overlays: List of OverlaySpec objects

        Returns:
            LayoutResult with overlays applied
        """
        return self.generate_layout(
            input_data,
            archetype_id=archetype_id,
            overlays=overlays,
            use_universal=True,  # Force universal for overlay support
        )

    def generate_composition(
        self,
        layout_id: str,
        diagrams: List[tuple],
        title: Optional[str] = None,
        shared_overlays: Optional[List[Any]] = None,
    ) -> LayoutResult:
        """
        Generate a multi-diagram composition on a single slide.

        Args:
            layout_id: Predefined layout ID ("two_column", "quad", etc.)
            diagrams: List of (archetype_id, DiagramInput) tuples
            title: Optional slide title
            shared_overlays: Overlays that span multiple regions

        Returns:
            LayoutResult with composed layout
        """
        try:
            from .multi_diagram_composer import compose_diagrams

            palette = self.default_palette
            layout = compose_diagrams(layout_id, diagrams, title=title, palette=palette)

            # Apply shared overlays if provided
            if shared_overlays:
                from .overlay_system import OverlayEngine
                overlay_engine = OverlayEngine()
                layout = overlay_engine.apply_overlays(layout, shared_overlays, palette)

            layout_warnings = layout.validate()

            return LayoutResult(
                layout=layout,
                archetype_used=f"composition:{layout_id}",
                warnings=layout_warnings,
                success=True,
                system_used="universal"
            )

        except Exception as e:
            logger.error(f"Composition generation failed: {e}")
            return LayoutResult(
                layout=self._empty_layout(title or "Composition"),
                archetype_used=f"composition:{layout_id}",
                warnings=[],
                success=False,
                error_message=f"Composition error: {str(e)}",
                system_used="universal"
            )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_layout(
    title: str,
    blocks: List[Dict],
    layers: Optional[List[Dict]] = None,
    connectors: Optional[List[Dict]] = None,
    subtitle: Optional[str] = None,
    archetype: Optional[str] = None,
    palette: Optional[ColorPalette] = None,
    overlays: Optional[List[Dict]] = None,
    use_universal: bool = True,
) -> LayoutResult:
    """
    Convenience function to create a layout from simple dicts.

    Args:
        title: Diagram title
        blocks: List of block dicts with id, label, etc.
        layers: Optional list of layer dicts for layered diagrams
        connectors: Optional list of connector dicts
        subtitle: Optional subtitle
        archetype: Archetype ID string (e.g., "funnel", "pyramid")
        palette: Optional color palette
        overlays: Optional list of overlay dicts for arrows/callouts
        use_universal: Use universal archetype system (default True)

    Returns:
        LayoutResult with generated layout
    """
    # Convert dicts to dataclasses
    block_data = [
        BlockData(
            id=b["id"],
            label=b["label"],
            layer_id=b.get("layer_id"),
            color=b.get("color"),
            description=b.get("description"),
        )
        for b in blocks
    ]

    layer_data = []
    if layers:
        for layer in layers:
            layer_data.append(LayerData(
                id=layer["id"],
                label=layer["label"],
                blocks=layer.get("blocks", []),
                is_cross_cutting=layer.get("is_cross_cutting", False),
                color=layer.get("color"),
            ))

    connector_data = []
    if connectors:
        for conn in connectors:
            style = ConnectorStyle.ARROW
            if "style" in conn:
                style = ConnectorStyle(conn["style"])
            connector_data.append(ConnectorData(
                from_id=conn["from_id"],
                to_id=conn["to_id"],
                label=conn.get("label"),
                style=style,
            ))

    input_data = DiagramInput(
        title=title,
        subtitle=subtitle,
        blocks=block_data,
        layers=layer_data,
        connectors=connector_data,
        palette=palette or ColorPalette(),
    )

    # Convert overlay dicts to OverlaySpec if provided
    overlay_specs = None
    if overlays:
        from .archetype_rules import OverlaySpec, OverlayElement, OverlayType, OverlayPosition
        overlay_specs = []
        for idx, ov in enumerate(overlays):
            overlay_specs.append(OverlaySpec(
                overlay_id=ov.get("id", f"overlay_{idx}"),
                overlay_type=OverlayType(ov.get("type", "side_arrow")),
                position=OverlayPosition(ov.get("position", "right")),
                elements=[
                    OverlayElement(
                        element_id=elem.get("id", f"overlay_elem_{i}"),
                        content=elem.get("label", ""),
                    )
                    for i, elem in enumerate(ov.get("elements", []))
                ],
            ))

    engine = LayoutEngine(default_palette=palette, use_universal=use_universal)
    return engine.generate_layout(
        input_data,
        archetype_id=archetype,
        overlays=overlay_specs,
    )


def quick_layout(
    title: str,
    items: List[str],
    archetype: str = "card_grid",
    subtitle: Optional[str] = None,
    palette: Optional[ColorPalette] = None,
) -> LayoutResult:
    """
    Quickest way to create a simple layout from a list of items.

    Args:
        title: Diagram title
        items: List of item labels
        archetype: Archetype to use (default "card_grid")
        subtitle: Optional subtitle
        palette: Optional color palette

    Returns:
        LayoutResult with generated layout
    """
    blocks = [
        {"id": f"block_{i}", "label": label}
        for i, label in enumerate(items)
    ]

    return create_layout(
        title=title,
        blocks=blocks,
        subtitle=subtitle,
        archetype=archetype,
        palette=palette,
    )


def create_funnel(
    title: str,
    stages: List[str],
    input_label: Optional[str] = None,
    output_label: Optional[str] = None,
    palette: Optional[ColorPalette] = None,
) -> LayoutResult:
    """
    Create a funnel diagram with optional side arrows.

    Args:
        title: Diagram title
        stages: List of funnel stage labels (top to bottom)
        input_label: Optional label for left-side input arrow
        output_label: Optional label for right-side output arrow
        palette: Optional color palette

    Returns:
        LayoutResult with funnel layout
    """
    blocks = [
        {"id": f"stage_{i}", "label": label}
        for i, label in enumerate(stages)
    ]

    overlays = []
    if input_label:
        overlays.append({
            "type": "side_arrow",
            "position": "left",
            "elements": [{"label": input_label}],
        })
    if output_label:
        overlays.append({
            "type": "side_arrow",
            "position": "right",
            "elements": [{"label": output_label}],
        })

    return create_layout(
        title=title,
        blocks=blocks,
        archetype="funnel",
        palette=palette,
        overlays=overlays if overlays else None,
    )


def create_pyramid(
    title: str,
    levels: List[str],
    palette: Optional[ColorPalette] = None,
) -> LayoutResult:
    """
    Create a pyramid diagram.

    Args:
        title: Diagram title
        levels: List of pyramid level labels (top to bottom)
        palette: Optional color palette

    Returns:
        LayoutResult with pyramid layout
    """
    blocks = [
        {"id": f"level_{i}", "label": label}
        for i, label in enumerate(levels)
    ]

    return create_layout(
        title=title,
        blocks=blocks,
        archetype="pyramid",
        palette=palette,
    )


def create_process_flow(
    title: str,
    steps: List[str],
    palette: Optional[ColorPalette] = None,
) -> LayoutResult:
    """
    Create a process flow diagram with arrows between steps.

    Args:
        title: Diagram title
        steps: List of step labels (in order)
        palette: Optional color palette

    Returns:
        LayoutResult with process flow layout
    """
    blocks = [
        {"id": f"step_{i}", "label": label}
        for i, label in enumerate(steps)
    ]

    return create_layout(
        title=title,
        blocks=blocks,
        archetype="process_flow",
        palette=palette,
    )


def create_comparison(
    title: str,
    items: List[Dict[str, str]],
    palette: Optional[ColorPalette] = None,
) -> LayoutResult:
    """
    Create a comparison diagram.

    Args:
        title: Diagram title
        items: List of item dicts with 'label' and optional 'description'
        palette: Optional color palette

    Returns:
        LayoutResult with comparison layout
    """
    blocks = [
        {"id": f"item_{i}", "label": item["label"], "description": item.get("description")}
        for i, item in enumerate(items)
    ]

    return create_layout(
        title=title,
        blocks=blocks,
        archetype="comparison",
        palette=palette,
    )


def create_hub_spoke(
    title: str,
    hub_label: str,
    spoke_labels: List[str],
    palette: Optional[ColorPalette] = None,
) -> LayoutResult:
    """
    Create a hub-and-spoke diagram.

    Args:
        title: Diagram title
        hub_label: Label for the central hub
        spoke_labels: Labels for the surrounding spokes
        palette: Optional color palette

    Returns:
        LayoutResult with hub-spoke layout
    """
    # Hub is first block, spokes follow
    blocks = [{"id": "hub", "label": hub_label}]
    blocks.extend([
        {"id": f"spoke_{i}", "label": label}
        for i, label in enumerate(spoke_labels)
    ])

    return create_layout(
        title=title,
        blocks=blocks,
        archetype="hub_spoke",
        palette=palette,
    )


def create_timeline(
    title: str,
    events: List[Dict[str, str]],
    palette: Optional[ColorPalette] = None,
) -> LayoutResult:
    """
    Create a timeline diagram.

    Args:
        title: Diagram title
        events: List of event dicts with 'label' and optional 'date'
        palette: Optional color palette

    Returns:
        LayoutResult with timeline layout
    """
    blocks = [
        {"id": f"event_{i}", "label": event["label"], "description": event.get("date")}
        for i, event in enumerate(events)
    ]

    return create_layout(
        title=title,
        blocks=blocks,
        archetype="timeline",
        palette=palette,
    )


def create_composition(
    layout_id: str,
    diagrams: List[Dict[str, Any]],
    title: Optional[str] = None,
    palette: Optional[ColorPalette] = None,
) -> LayoutResult:
    """
    Create a multi-diagram composition.

    Args:
        layout_id: Layout type ("two_column", "quad", etc.)
        diagrams: List of diagram definitions, each with:
                  - archetype: str
                  - title: str
                  - blocks: List[Dict]
                  - (other create_layout params)
        title: Optional slide title
        palette: Optional color palette

    Returns:
        LayoutResult with composed layout

    Example:
        create_composition(
            "two_column",
            [
                {"archetype": "funnel", "title": "Sales", "blocks": [...]},
                {"archetype": "bullet_list", "title": "Actions", "blocks": [...]},
            ],
            title="Sales Overview"
        )
    """
    # Convert diagram definitions to (archetype_id, DiagramInput) tuples
    diagram_tuples = []
    for diag in diagrams:
        blocks = [
            BlockData(
                id=b["id"],
                label=b["label"],
                layer_id=b.get("layer_id"),
                color=b.get("color"),
                description=b.get("description"),
            )
            for b in diag.get("blocks", [])
        ]

        input_data = DiagramInput(
            title=diag.get("title", ""),
            subtitle=diag.get("subtitle"),
            blocks=blocks,
            palette=palette or ColorPalette(),
        )

        diagram_tuples.append((diag.get("archetype", "card_grid"), input_data))

    engine = LayoutEngine(default_palette=palette)
    return engine.generate_composition(layout_id, diagram_tuples, title=title)


# =============================================================================
# ARCHETYPE LEARNING INTERFACE
# =============================================================================

def learn_archetype_from_pptx(
    pptx_path: str,
    archetype_name: Optional[str] = None,
    save_rules: bool = True,
) -> Dict[str, Any]:
    """
    Learn a new archetype from a PPTX template.

    Args:
        pptx_path: Path to the PPTX file to learn from
        archetype_name: Optional name for the learned archetype
        save_rules: If True, save the learned rules to JSON

    Returns:
        Dict with learning results including:
        - archetype_id: str
        - confidence: float
        - pattern_detected: str
        - rules_path: str (if saved)
    """
    from .archetype_learner import ArchetypeLearner

    learner = ArchetypeLearner()
    result = learner.learn_from_pptx(pptx_path, archetype_name=archetype_name)

    if save_rules and result.rules:
        from .archetype_resolver import get_resolver
        resolver = get_resolver()
        rules_path = resolver.save_learned(result.rules)
        return {
            "archetype_id": result.rules.archetype_id,
            "confidence": result.confidence,
            "pattern_detected": result.rules.layout_strategy.value,
            "rules_path": rules_path,
            "warnings": result.warnings,
        }

    return {
        "archetype_id": result.rules.archetype_id if result.rules else None,
        "confidence": result.confidence,
        "pattern_detected": result.rules.layout_strategy.value if result.rules else None,
        "warnings": result.warnings,
    }


def list_all_archetypes(include_learned: bool = True) -> List[Dict[str, Any]]:
    """
    List all available archetypes from both legacy and universal systems.

    Args:
        include_learned: Include learned archetypes from training

    Returns:
        List of archetype info dicts
    """
    engine = LayoutEngine()
    return engine.list_archetypes(include_learned=include_learned)
