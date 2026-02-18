"""
layout_engine.py — Layout orchestrator.

The LayoutEngine coordinates the entire layout generation process:
1. Receives parsed diagram input
2. Selects appropriate archetype
3. Invokes archetype to generate PositionedLayout
4. Validates and returns the layout

This is the main entry point for layout generation.

NOTE: Uses lazy imports to avoid circular dependency with archetypes module.
"""

from typing import Dict, Type, Optional, List, Any
from dataclasses import dataclass

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


class LayoutEngine:
    """
    Main layout orchestrator.
    """

    def __init__(self, default_palette: Optional[ColorPalette] = None):
        self.default_palette = default_palette or ColorPalette()

    def generate_layout(
        self,
        input_data: DiagramInput,
        archetype_type: Optional[ArchetypeType] = None
    ) -> LayoutResult:
        """Generate a positioned layout from diagram input."""
        # Auto-select archetype if not specified
        if archetype_type is None:
            archetype_type = self._select_archetype(input_data)

        # Get archetype instance
        try:
            palette = input_data.palette or self.default_palette
            archetype = get_archetype(archetype_type, palette)
        except ValueError as e:
            return LayoutResult(
                layout=self._empty_layout(input_data.title),
                archetype_used="none",
                warnings=[],
                success=False,
                error_message=str(e)
            )

        # Validate input
        validation_errors = archetype.validate_input(input_data)
        if validation_errors:
            return LayoutResult(
                layout=self._empty_layout(input_data.title),
                archetype_used=archetype.name,
                warnings=validation_errors,
                success=False,
                error_message=f"Validation failed: {validation_errors[0]}"
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
                error_message=f"Layout generation failed: {str(e)}"
            )

        # Validate output layout
        layout_warnings = layout.validate()

        return LayoutResult(
            layout=layout,
            archetype_used=archetype.name,
            warnings=layout_warnings,
            success=True
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
    palette: Optional[ColorPalette] = None
) -> LayoutResult:
    """
    Convenience function to create a layout from simple dicts.
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

    # Determine archetype type
    archetype_type = None
    if archetype:
        for at in ArchetypeType:
            if at.value == archetype:
                archetype_type = at
                break

    engine = LayoutEngine(default_palette=palette)
    return engine.generate_layout(input_data, archetype_type)


def quick_layout(
    title: str,
    items: List[str],
    rows: Optional[int] = None,
    subtitle: Optional[str] = None
) -> LayoutResult:
    """Quickest way to create a simple grid layout."""
    blocks = [
        {"id": f"block_{i}", "label": label}
        for i, label in enumerate(items)
    ]

    return create_layout(
        title=title,
        blocks=blocks,
        subtitle=subtitle
    )
