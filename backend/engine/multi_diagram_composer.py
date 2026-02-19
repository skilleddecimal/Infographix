"""
multi_diagram_composer.py — Framework for composing multiple diagrams on one slide.

The MultiDiagramComposer allows multiple diagrams to be rendered on a single slide,
each in its own region. This enables complex layouts like:
- Funnel on left, outcomes list on right
- Before/after comparisons with different diagram types
- Dashboard-style layouts with multiple visualizations

Key features:
- Define regions (areas) where diagrams will be rendered
- Each region gets its own diagram with independent archetype
- Shared overlays can span multiple regions
- Automatic spacing and alignment between regions
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from .positioned import (
    PositionedLayout,
    PositionedElement,
    PositionedConnector,
    ElementType,
)
from .archetype_rules import (
    ArchetypeRules,
    OverlaySpec,
    CompositionLayout,
    DiagramRegion,
)
from .data_models import DiagramInput, ColorPalette
from .units import (
    SLIDE_WIDTH_INCHES,
    SLIDE_HEIGHT_INCHES,
    CONTENT_LEFT,
    CONTENT_TOP,
    CONTENT_WIDTH,
    CONTENT_HEIGHT,
    MARGIN_TOP,
    MARGIN_LEFT,
    MARGIN_RIGHT,
    TITLE_HEIGHT,
    GUTTER_H,
    GUTTER_V,
)
from .universal_archetype import UniversalArchetype
from .archetype_resolver import get_resolver
from .overlay_system import OverlayEngine


# =============================================================================
# REGION LAYOUTS (Predefined Compositions)
# =============================================================================

@dataclass
class RegionLayout:
    """Predefined region layout pattern."""
    layout_id: str
    name: str
    description: str
    regions: List[DiagramRegion]


def create_two_column_layout() -> RegionLayout:
    """Create a two-column layout (50/50 split)."""
    half_width = (CONTENT_WIDTH - GUTTER_H) / 2

    return RegionLayout(
        layout_id="two_column",
        name="Two Columns",
        description="Side-by-side layout with two equal columns",
        regions=[
            DiagramRegion(
                region_id="left",
                x=CONTENT_LEFT,
                y=CONTENT_TOP,
                width=half_width,
                height=CONTENT_HEIGHT,
            ),
            DiagramRegion(
                region_id="right",
                x=CONTENT_LEFT + half_width + GUTTER_H,
                y=CONTENT_TOP,
                width=half_width,
                height=CONTENT_HEIGHT,
            ),
        ],
    )


def create_three_column_layout() -> RegionLayout:
    """Create a three-column layout."""
    third_width = (CONTENT_WIDTH - 2 * GUTTER_H) / 3

    return RegionLayout(
        layout_id="three_column",
        name="Three Columns",
        description="Three equal columns",
        regions=[
            DiagramRegion(
                region_id="left",
                x=CONTENT_LEFT,
                y=CONTENT_TOP,
                width=third_width,
                height=CONTENT_HEIGHT,
            ),
            DiagramRegion(
                region_id="center",
                x=CONTENT_LEFT + third_width + GUTTER_H,
                y=CONTENT_TOP,
                width=third_width,
                height=CONTENT_HEIGHT,
            ),
            DiagramRegion(
                region_id="right",
                x=CONTENT_LEFT + 2 * (third_width + GUTTER_H),
                y=CONTENT_TOP,
                width=third_width,
                height=CONTENT_HEIGHT,
            ),
        ],
    )


def create_two_row_layout() -> RegionLayout:
    """Create a two-row layout (50/50 split)."""
    half_height = (CONTENT_HEIGHT - GUTTER_V) / 2

    return RegionLayout(
        layout_id="two_row",
        name="Two Rows",
        description="Stacked layout with two equal rows",
        regions=[
            DiagramRegion(
                region_id="top",
                x=CONTENT_LEFT,
                y=CONTENT_TOP,
                width=CONTENT_WIDTH,
                height=half_height,
            ),
            DiagramRegion(
                region_id="bottom",
                x=CONTENT_LEFT,
                y=CONTENT_TOP + half_height + GUTTER_V,
                width=CONTENT_WIDTH,
                height=half_height,
            ),
        ],
    )


def create_main_sidebar_layout() -> RegionLayout:
    """Create a main area with sidebar layout (70/30 split)."""
    main_width = CONTENT_WIDTH * 0.7 - GUTTER_H / 2
    sidebar_width = CONTENT_WIDTH * 0.3 - GUTTER_H / 2

    return RegionLayout(
        layout_id="main_sidebar",
        name="Main + Sidebar",
        description="Large main area with narrow sidebar",
        regions=[
            DiagramRegion(
                region_id="main",
                x=CONTENT_LEFT,
                y=CONTENT_TOP,
                width=main_width,
                height=CONTENT_HEIGHT,
            ),
            DiagramRegion(
                region_id="sidebar",
                x=CONTENT_LEFT + main_width + GUTTER_H,
                y=CONTENT_TOP,
                width=sidebar_width,
                height=CONTENT_HEIGHT,
            ),
        ],
    )


def create_quad_layout() -> RegionLayout:
    """Create a 2x2 quadrant layout."""
    half_width = (CONTENT_WIDTH - GUTTER_H) / 2
    half_height = (CONTENT_HEIGHT - GUTTER_V) / 2

    return RegionLayout(
        layout_id="quad",
        name="Four Quadrants",
        description="2x2 grid with four equal quadrants",
        regions=[
            DiagramRegion(
                region_id="top_left",
                x=CONTENT_LEFT,
                y=CONTENT_TOP,
                width=half_width,
                height=half_height,
            ),
            DiagramRegion(
                region_id="top_right",
                x=CONTENT_LEFT + half_width + GUTTER_H,
                y=CONTENT_TOP,
                width=half_width,
                height=half_height,
            ),
            DiagramRegion(
                region_id="bottom_left",
                x=CONTENT_LEFT,
                y=CONTENT_TOP + half_height + GUTTER_V,
                width=half_width,
                height=half_height,
            ),
            DiagramRegion(
                region_id="bottom_right",
                x=CONTENT_LEFT + half_width + GUTTER_H,
                y=CONTENT_TOP + half_height + GUTTER_V,
                width=half_width,
                height=half_height,
            ),
        ],
    )


# Registry of predefined layouts
REGION_LAYOUTS: Dict[str, RegionLayout] = {
    "two_column": create_two_column_layout(),
    "three_column": create_three_column_layout(),
    "two_row": create_two_row_layout(),
    "main_sidebar": create_main_sidebar_layout(),
    "quad": create_quad_layout(),
}


# =============================================================================
# MULTI-DIAGRAM COMPOSER
# =============================================================================

class MultiDiagramComposer:
    """
    Composes multiple diagrams on a single slide.

    Usage:
        composer = MultiDiagramComposer()

        # Create composition with predefined layout
        composition = composer.create_composition("two_column")

        # Assign diagrams to regions
        composition.regions[0].archetype_id = "funnel"
        composition.regions[0].diagram_data = funnel_input
        composition.regions[1].archetype_id = "bullet_list"
        composition.regions[1].diagram_data = list_input

        # Generate combined layout
        layout = composer.compose(composition, palette)
    """

    def __init__(self):
        """Initialize the composer."""
        self.resolver = get_resolver()
        self.overlay_engine = OverlayEngine()

    def create_composition(
        self,
        layout_id: str = "two_column",
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
    ) -> CompositionLayout:
        """
        Create a composition from a predefined layout.

        Args:
            layout_id: ID of the predefined layout (e.g., "two_column", "quad")
            title: Optional slide title
            subtitle: Optional slide subtitle

        Returns:
            CompositionLayout with empty regions ready for diagram assignment
        """
        if layout_id not in REGION_LAYOUTS:
            raise ValueError(
                f"Unknown layout '{layout_id}'. Available: {list(REGION_LAYOUTS.keys())}"
            )

        layout = REGION_LAYOUTS[layout_id]

        # Deep copy regions to allow modification
        regions = [
            DiagramRegion(
                region_id=r.region_id,
                x=r.x,
                y=r.y,
                width=r.width,
                height=r.height,
            )
            for r in layout.regions
        ]

        return CompositionLayout(
            regions=regions,
            title=title,
            subtitle=subtitle,
        )

    def create_custom_composition(
        self,
        regions: List[Dict[str, Any]],
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
    ) -> CompositionLayout:
        """
        Create a composition with custom regions.

        Args:
            regions: List of region definitions, each with:
                     - region_id: str
                     - x, y, width, height: floats in inches
                     - archetype_id: optional str
            title: Optional slide title
            subtitle: Optional slide subtitle

        Returns:
            CompositionLayout with custom regions
        """
        diagram_regions = []
        for r in regions:
            region = DiagramRegion(
                region_id=r["region_id"],
                x=r["x"],
                y=r["y"],
                width=r["width"],
                height=r["height"],
                archetype_id=r.get("archetype_id"),
                background_color=r.get("background_color"),
                has_border=r.get("has_border", False),
                padding=r.get("padding", 0.1),
            )
            diagram_regions.append(region)

        return CompositionLayout(
            regions=diagram_regions,
            title=title,
            subtitle=subtitle,
        )

    def compose(
        self,
        composition: CompositionLayout,
        palette: Optional[ColorPalette] = None,
    ) -> PositionedLayout:
        """
        Compose multiple diagrams into a single layout.

        Args:
            composition: CompositionLayout with regions and diagram assignments
            palette: Optional color palette

        Returns:
            Combined PositionedLayout with all diagrams
        """
        palette = palette or ColorPalette()

        # Create base layout
        layout = PositionedLayout(
            slide_width_inches=SLIDE_WIDTH_INCHES,
            slide_height_inches=SLIDE_HEIGHT_INCHES,
            background_color=composition.background_color,
            elements=[],
            connectors=[],
        )

        # Add title/subtitle if present
        if composition.title:
            from .text_measure import fit_text_to_width
            from .positioned import PositionedText, TextAlignment

            fit = fit_text_to_width(
                composition.title,
                CONTENT_WIDTH,
                max_font_size=28,
                min_font_size=18,
                bold=True,
            )

            title_elem = PositionedElement(
                id="composition_title",
                element_type=ElementType.TITLE,
                x_inches=CONTENT_LEFT,
                y_inches=MARGIN_TOP,
                width_inches=CONTENT_WIDTH,
                height_inches=TITLE_HEIGHT,
                fill_color="transparent",
                text=PositionedText(
                    content=composition.title,
                    lines=fit.lines,
                    font_size_pt=fit.font_size,
                    font_family="Calibri",
                    bold=True,
                    color="#333333",
                    alignment=TextAlignment.CENTER,
                ),
                z_order=100,
            )
            layout.title = title_elem

        # Render each region
        for region in composition.regions:
            region_layout = self._render_region(region, palette)

            # Offset elements to region position
            for elem in region_layout.elements:
                # Skip title/subtitle from individual diagrams
                if elem.element_type in (ElementType.TITLE, ElementType.SUBTITLE):
                    continue

                # Adjust position to be relative to region
                # The region layout was generated with CONTENT bounds,
                # so we need to remap to region bounds
                elem.x_inches = self._remap_x(
                    elem.x_inches, region, region_layout
                )
                elem.y_inches = self._remap_y(
                    elem.y_inches, region, region_layout
                )
                elem.width_inches *= region.width / CONTENT_WIDTH
                elem.height_inches *= region.height / CONTENT_HEIGHT

                # Add region prefix to ID to avoid conflicts
                elem.id = f"{region.region_id}_{elem.id}"

                layout.elements.append(elem)

            # Offset connectors
            for conn in region_layout.connectors:
                conn.start_x = self._remap_x(conn.start_x, region, region_layout)
                conn.start_y = self._remap_y(conn.start_y, region, region_layout)
                conn.end_x = self._remap_x(conn.end_x, region, region_layout)
                conn.end_y = self._remap_y(conn.end_y, region, region_layout)
                conn.id = f"{region.region_id}_{conn.id}"

                layout.connectors.append(conn)

            # Add region background if specified
            if region.background_color:
                bg_elem = PositionedElement(
                    id=f"{region.region_id}_bg",
                    element_type=ElementType.BLOCK,
                    x_inches=region.x,
                    y_inches=region.y,
                    width_inches=region.width,
                    height_inches=region.height,
                    fill_color=region.background_color,
                    stroke_color=region.border_color if region.has_border else None,
                    corner_radius_inches=0.05,
                    z_order=-10,  # Behind everything
                )
                layout.elements.append(bg_elem)

        # Apply shared overlays
        if composition.shared_overlays:
            layout = self.overlay_engine.apply_overlays(
                layout, composition.shared_overlays, palette
            )

        return layout

    def _render_region(
        self,
        region: DiagramRegion,
        palette: ColorPalette,
    ) -> PositionedLayout:
        """Render a single region's diagram."""
        if not region.archetype_id or not region.diagram_data:
            # Return empty layout for unassigned regions
            return PositionedLayout(
                slide_width_inches=SLIDE_WIDTH_INCHES,
                slide_height_inches=SLIDE_HEIGHT_INCHES,
                elements=[],
                connectors=[],
            )

        # Get archetype rules
        rules = self.resolver.resolve(region.archetype_id)

        # Create archetype and generate layout
        archetype = UniversalArchetype(rules, palette)
        return archetype.generate_layout(region.diagram_data)

    def _remap_x(
        self,
        x: float,
        region: DiagramRegion,
        region_layout: PositionedLayout,
    ) -> float:
        """Remap x coordinate from content bounds to region bounds."""
        # Calculate relative position in content area
        relative = (x - CONTENT_LEFT) / CONTENT_WIDTH
        # Map to region
        return region.x + relative * region.width

    def _remap_y(
        self,
        y: float,
        region: DiagramRegion,
        region_layout: PositionedLayout,
    ) -> float:
        """Remap y coordinate from content bounds to region bounds."""
        # Calculate relative position in content area
        relative = (y - CONTENT_TOP) / CONTENT_HEIGHT
        # Map to region
        return region.y + relative * region.height

    def list_layouts(self) -> List[Dict[str, Any]]:
        """List available predefined layouts."""
        return [
            {
                "id": layout.layout_id,
                "name": layout.name,
                "description": layout.description,
                "region_count": len(layout.regions),
            }
            for layout in REGION_LAYOUTS.values()
        ]


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def compose_diagrams(
    layout_id: str,
    diagrams: List[Tuple[str, DiagramInput]],
    title: Optional[str] = None,
    palette: Optional[ColorPalette] = None,
) -> PositionedLayout:
    """
    Quick way to compose multiple diagrams.

    Args:
        layout_id: Predefined layout ID (e.g., "two_column")
        diagrams: List of (archetype_id, DiagramInput) tuples
        title: Optional slide title
        palette: Optional color palette

    Returns:
        Combined PositionedLayout

    Example:
        layout = compose_diagrams(
            "two_column",
            [
                ("funnel", funnel_data),
                ("bullet_list", list_data),
            ],
            title="Sales Pipeline Overview"
        )
    """
    composer = MultiDiagramComposer()
    composition = composer.create_composition(layout_id, title=title)

    # Assign diagrams to regions
    for i, (archetype_id, diagram_data) in enumerate(diagrams):
        if i < len(composition.regions):
            composition.regions[i].archetype_id = archetype_id
            composition.regions[i].diagram_data = diagram_data

    return composer.compose(composition, palette)
