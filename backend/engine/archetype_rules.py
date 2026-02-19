"""
archetype_rules.py — Core data structures for the Universal Flexible Archetype System.

This module defines the data-driven rule system that replaces hardcoded archetype classes.
Archetypes are now defined as JSON rules (predefined or learned from training) that
the UniversalArchetype class interprets to generate layouts.

Key concepts:
- ArchetypeRules: Complete definition of how an archetype behaves
- ElementTemplate: How individual elements should be rendered
- LayoutConstraint: Rules that constrain element positioning
- OverlaySpec: Additional elements (arrows, callouts) that can be added to any archetype
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class LayoutStrategy(Enum):
    """Core layout strategies that cover all diagram patterns."""
    GRID = "grid"           # Rows/columns (Comparison, Matrix, Card Grid)
    STACK = "stack"         # Vertical/horizontal stacking (Funnel, Pyramid, Timeline)
    RADIAL = "radial"       # Circular arrangement (Hub-Spoke, Cycle, Target)
    TREE = "tree"           # Hierarchical (Org Chart, Tree Diagram)
    FLOW = "flow"           # Sequential with connectors (Process Flow, Pipeline, Chevron)
    FREEFORM = "freeform"   # Arbitrary positioning (Canvas, Custom)


class LayoutDirection(Enum):
    """Primary direction for layout flow."""
    HORIZONTAL = "horizontal"       # Left to right
    VERTICAL = "vertical"           # Top to bottom
    RADIAL = "radial"               # Center outward
    RADIAL_INWARD = "radial_inward" # Outside inward (target/bullseye)


class ElementShape(Enum):
    """Shape types for elements."""
    RECTANGLE = "rectangle"
    ROUNDED_RECT = "rounded_rect"
    TRAPEZOID = "trapezoid"         # For funnel stages
    TRIANGLE = "triangle"           # For pyramid segments
    ELLIPSE = "ellipse"
    CIRCLE = "circle"
    CHEVRON = "chevron"             # Arrow-like shape
    ARROW = "arrow"                 # Full arrow shape
    PENTAGON = "pentagon"
    HEXAGON = "hexagon"
    DIAMOND = "diamond"
    PARALLELOGRAM = "parallelogram"
    CUSTOM = "custom"               # Uses custom_path


class PositionRule(Enum):
    """Rules for how elements are positioned."""
    STACKED_CENTERED = "stacked_centered"   # Vertical stack, centered horizontally
    STACKED_LEFT = "stacked_left"           # Vertical stack, left-aligned
    GRID_FILL = "grid_fill"                 # Fill grid cells
    RADIAL_EVEN = "radial_even"             # Evenly spaced around center
    RADIAL_WEIGHTED = "radial_weighted"     # Weighted by importance
    TREE_BALANCED = "tree_balanced"         # Balanced tree layout
    TREE_LEFT = "tree_left"                 # Left-aligned tree
    FLOW_LINEAR = "flow_linear"             # Linear flow with connectors
    FLOW_WRAPPED = "flow_wrapped"           # Flow that wraps to next line
    FREEFORM = "freeform"                   # LLM-specified positions


class SizeRule(Enum):
    """Rules for how element sizes are determined."""
    UNIFORM = "uniform"             # All elements same size
    PROGRESSIVE = "progressive"     # Size changes progressively (funnel, pyramid)
    PROPORTIONAL = "proportional"   # Size based on value/weight
    TEXT_FIT = "text_fit"           # Size adapts to text content
    FIXED = "fixed"                 # Fixed size from params


class ColorRule(Enum):
    """Rules for how colors are applied."""
    PALETTE_SEQUENCE = "palette_sequence"   # Cycle through palette colors
    GRADIENT = "gradient"                   # Gradient from start to end color
    EMPHASIS_BASED = "emphasis_based"       # Color based on emphasis level
    LAYER_BASED = "layer_based"             # Color based on layer membership
    UNIFORM = "uniform"                     # Single color for all
    CUSTOM = "custom"                       # Element-specific colors


class ConnectorPattern(Enum):
    """Patterns for automatic connector generation."""
    SEQUENTIAL = "sequential"       # Connect n to n+1
    HUB_TO_SPOKES = "hub_to_spokes" # Connect center to all satellites
    FULL_MESH = "full_mesh"         # Connect everything to everything
    HIERARCHICAL = "hierarchical"   # Parent to children
    CYCLE = "cycle"                 # Circular: n to n+1, last to first
    NONE = "none"                   # No automatic connectors


class OverlayPosition(Enum):
    """Positions for overlay elements."""
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    FLOATING = "floating"           # Arbitrary position
    ANCHORED = "anchored"           # Anchored to specific element


class OverlayType(Enum):
    """Types of overlay elements."""
    SIDE_ARROW = "side_arrow"       # Arrow pointing to/from side
    CALLOUT = "callout"             # Callout box with pointer
    ANNOTATION = "annotation"       # Text annotation
    BANNER = "banner"               # Horizontal/vertical banner
    BRACKET = "bracket"             # Bracket grouping elements
    LABEL = "label"                 # Simple text label
    CONNECTOR = "connector"         # Additional connector


# =============================================================================
# ELEMENT TEMPLATE
# =============================================================================

@dataclass
class SizeParams:
    """Parameters for size rules."""
    # For PROGRESSIVE
    width_progression: float = 0.85     # Each element is this ratio of previous
    height_progression: float = 1.0     # Height progression ratio

    # For FIXED
    fixed_width: float = 2.0            # Fixed width in inches
    fixed_height: float = 1.0           # Fixed height in inches

    # For PROPORTIONAL
    min_size: float = 0.5               # Minimum element size
    max_size: float = 3.0               # Maximum element size

    # For TEXT_FIT
    min_font_size: int = 10
    max_font_size: int = 24
    padding_h: float = 0.15             # Horizontal padding
    padding_v: float = 0.08             # Vertical padding


@dataclass
class ColorParams:
    """Parameters for color rules."""
    # For GRADIENT
    start_color: Optional[str] = None   # Starting color (hex)
    end_color: Optional[str] = None     # Ending color (hex)

    # For EMPHASIS_BASED
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None

    # For UNIFORM
    uniform_color: Optional[str] = None

    # Opacity
    fill_opacity: float = 1.0
    stroke_opacity: float = 1.0


@dataclass
class ElementTemplate:
    """
    Template defining how elements should be rendered.

    This is the blueprint for all elements in an archetype.
    Individual elements can override specific properties.
    """
    # Shape
    element_type: ElementShape = ElementShape.ROUNDED_RECT
    corner_radius: float = 0.08         # Corner radius in inches

    # Positioning
    position_rule: PositionRule = PositionRule.STACKED_CENTERED

    # Sizing
    size_rule: SizeRule = SizeRule.TEXT_FIT
    size_params: SizeParams = field(default_factory=SizeParams)

    # Colors
    color_rule: ColorRule = ColorRule.PALETTE_SEQUENCE
    color_params: ColorParams = field(default_factory=ColorParams)

    # Stroke
    stroke_width: float = 1.0           # Stroke width in points
    stroke_color: Optional[str] = None  # None = auto from palette

    # Text
    text_alignment: str = "center"      # "left", "center", "right"
    text_vertical_alignment: str = "center"  # "top", "center", "bottom"
    bold_label: bool = True
    font_family: str = "Calibri"

    # Custom path for CUSTOM shape type
    custom_path: Optional[List[Any]] = None

    # Additional styling
    shadow: bool = False
    glow: bool = False


# =============================================================================
# LAYOUT CONSTRAINTS
# =============================================================================

@dataclass
class LayoutConstraint:
    """
    A constraint that the layout must satisfy.

    Constraints are checked after layout computation and can trigger adjustments.
    """
    constraint_type: str                # "min_spacing", "no_overlap", "within_bounds", etc.
    params: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1                   # Higher = more important

    # Common constraint types and their params:
    # - "min_spacing": {"horizontal": 0.25, "vertical": 0.2}
    # - "no_overlap": {}
    # - "within_bounds": {"margin": 0.1}
    # - "aspect_ratio": {"ratio": 1.5, "tolerance": 0.1}
    # - "alignment": {"type": "center", "axis": "horizontal"}
    # - "max_elements_per_row": {"count": 4}
    # - "equal_width": {"tolerance": 0.05}


# =============================================================================
# CONNECTOR TEMPLATE
# =============================================================================

@dataclass
class ConnectorTemplate:
    """Template for automatic connector generation."""
    pattern: ConnectorPattern = ConnectorPattern.NONE
    style: str = "arrow"                # "arrow", "plain", "dashed", "bidirectional"
    color: Optional[str] = None         # None = use palette connector color
    stroke_width: float = 1.5
    routing: str = "direct"             # "direct", "orthogonal", "curved"
    corner_radius: float = 0.05         # For orthogonal routing

    # For hub-spoke pattern
    hub_element_index: int = 0          # Which element is the hub

    # Label template
    show_labels: bool = False
    label_position: str = "middle"      # "start", "middle", "end"


# =============================================================================
# OVERLAY SPECIFICATIONS
# =============================================================================

@dataclass
class OverlayElement:
    """A single element within an overlay."""
    element_id: str
    element_type: str = "text"          # "text", "arrow", "shape", "icon"
    content: str = ""                   # Text content or icon ID

    # Positioning (relative to overlay container)
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 0.5

    # Styling
    fill_color: Optional[str] = None
    stroke_color: Optional[str] = None
    text_color: Optional[str] = None
    font_size: int = 12
    bold: bool = False

    # For arrows
    arrow_direction: Optional[str] = None  # "up", "down", "left", "right"


@dataclass
class OverlaySpec:
    """
    Specification for an overlay that can be added to any archetype.

    Overlays are additional visual elements (arrows, callouts, annotations)
    that enhance the base diagram. They work universally with all archetypes.
    """
    overlay_id: str
    overlay_type: OverlayType = OverlayType.ANNOTATION
    position: OverlayPosition = OverlayPosition.RIGHT

    # Elements within the overlay
    elements: List[OverlayElement] = field(default_factory=list)

    # Sizing
    width: float = 1.5                  # Overlay width in inches
    height: Optional[float] = None      # None = auto-fit to elements

    # Spacing
    margin_from_diagram: float = 0.2    # Gap between overlay and main diagram

    # Anchoring (for ANCHORED position)
    anchor_to: str = "diagram"          # "diagram" or specific element ID
    anchor_point: str = "center"        # "top", "center", "bottom" (for side overlays)

    # Background
    has_background: bool = False
    background_color: Optional[str] = None

    # Connection to diagram (for callouts)
    show_pointer: bool = False
    pointer_target: Optional[str] = None  # Element ID to point to


# =============================================================================
# ARCHETYPE RULES
# =============================================================================

@dataclass
class ArchetypeRules:
    """
    Complete rule definition for an archetype.

    This replaces hardcoded archetype classes. The UniversalArchetype class
    interprets these rules to generate layouts.
    """
    # Identity
    archetype_id: str                   # "funnel", "pyramid", "learned_001", etc.
    display_name: str
    description: str

    # Strategy
    layout_strategy: LayoutStrategy = LayoutStrategy.STACK
    primary_direction: LayoutDirection = LayoutDirection.VERTICAL

    # Element template
    element_template: ElementTemplate = field(default_factory=ElementTemplate)

    # Connectors
    connector_template: ConnectorTemplate = field(default_factory=ConnectorTemplate)

    # Layout constraints
    constraints: List[LayoutConstraint] = field(default_factory=list)

    # Overlay support
    supports_overlays: bool = True
    default_overlays: List[OverlaySpec] = field(default_factory=list)

    # Nesting support
    supports_nested: bool = False
    max_nesting_depth: int = 1

    # Grid-specific params (for GRID strategy)
    grid_params: Dict[str, Any] = field(default_factory=lambda: {
        "columns": "auto",              # "auto" or int
        "rows": "auto",
        "gutter_h": 0.25,
        "gutter_v": 0.2,
        "cell_aspect_ratio": 1.5,
    })

    # Stack-specific params (for STACK strategy)
    stack_params: Dict[str, Any] = field(default_factory=lambda: {
        "alignment": "center",          # "left", "center", "right"
        "gutter": 0.1,
        "top_width_ratio": 0.9,         # For funnel/pyramid
        "bottom_width_ratio": 0.25,
    })

    # Radial-specific params (for RADIAL strategy)
    radial_params: Dict[str, Any] = field(default_factory=lambda: {
        "center_element": True,         # Whether to show center element
        "radius_ratio": 0.35,           # Radius as ratio of content area
        "start_angle": 270,             # Starting angle in degrees (270 = top)
        "rotation": "clockwise",        # "clockwise" or "counterclockwise"
    })

    # Tree-specific params (for TREE strategy)
    tree_params: Dict[str, Any] = field(default_factory=lambda: {
        "orientation": "top_down",      # "top_down", "bottom_up", "left_right", "right_left"
        "sibling_spacing": 0.3,
        "level_spacing": 0.5,
    })

    # Flow-specific params (for FLOW strategy)
    flow_params: Dict[str, Any] = field(default_factory=lambda: {
        "wrap_after": 6,                # Wrap to next row after N elements
        "connector_gap": 0.1,           # Gap between element and connector
    })

    # Validation
    min_elements: int = 1
    max_elements: int = 50

    # Learning metadata
    learned_from: List[str] = field(default_factory=list)  # Training source files
    confidence_score: float = 1.0       # For learned archetypes

    # Additional metadata
    category: str = "other"             # "list", "process", "hierarchy", etc.
    keywords: List[str] = field(default_factory=list)
    example_prompts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        import dataclasses

        def convert(obj):
            if dataclasses.is_dataclass(obj):
                return {k: convert(v) for k, v in dataclasses.asdict(obj).items()}
            elif isinstance(obj, Enum):
                return obj.value
            elif isinstance(obj, list):
                return [convert(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            return obj

        return convert(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArchetypeRules':
        """Create from dictionary (JSON deserialization)."""
        # Convert string values back to enums
        if 'layout_strategy' in data and isinstance(data['layout_strategy'], str):
            data['layout_strategy'] = LayoutStrategy(data['layout_strategy'])
        if 'primary_direction' in data and isinstance(data['primary_direction'], str):
            data['primary_direction'] = LayoutDirection(data['primary_direction'])

        # Convert nested dataclasses
        if 'element_template' in data and isinstance(data['element_template'], dict):
            et_data = data['element_template']
            if 'element_type' in et_data and isinstance(et_data['element_type'], str):
                et_data['element_type'] = ElementShape(et_data['element_type'])
            if 'position_rule' in et_data and isinstance(et_data['position_rule'], str):
                et_data['position_rule'] = PositionRule(et_data['position_rule'])
            if 'size_rule' in et_data and isinstance(et_data['size_rule'], str):
                et_data['size_rule'] = SizeRule(et_data['size_rule'])
            if 'color_rule' in et_data and isinstance(et_data['color_rule'], str):
                et_data['color_rule'] = ColorRule(et_data['color_rule'])
            if 'size_params' in et_data and isinstance(et_data['size_params'], dict):
                et_data['size_params'] = SizeParams(**et_data['size_params'])
            if 'color_params' in et_data and isinstance(et_data['color_params'], dict):
                et_data['color_params'] = ColorParams(**et_data['color_params'])
            data['element_template'] = ElementTemplate(**et_data)

        if 'connector_template' in data and isinstance(data['connector_template'], dict):
            ct_data = data['connector_template']
            if 'pattern' in ct_data and isinstance(ct_data['pattern'], str):
                ct_data['pattern'] = ConnectorPattern(ct_data['pattern'])
            data['connector_template'] = ConnectorTemplate(**ct_data)

        if 'constraints' in data and isinstance(data['constraints'], list):
            data['constraints'] = [
                LayoutConstraint(**c) if isinstance(c, dict) else c
                for c in data['constraints']
            ]

        if 'default_overlays' in data and isinstance(data['default_overlays'], list):
            overlays = []
            for o in data['default_overlays']:
                if isinstance(o, dict):
                    if 'overlay_type' in o and isinstance(o['overlay_type'], str):
                        o['overlay_type'] = OverlayType(o['overlay_type'])
                    if 'position' in o and isinstance(o['position'], str):
                        o['position'] = OverlayPosition(o['position'])
                    if 'elements' in o and isinstance(o['elements'], list):
                        o['elements'] = [
                            OverlayElement(**e) if isinstance(e, dict) else e
                            for e in o['elements']
                        ]
                    overlays.append(OverlaySpec(**o))
                else:
                    overlays.append(o)
            data['default_overlays'] = overlays

        return cls(**data)


# =============================================================================
# COMPOSITION CONTEXT
# =============================================================================

@dataclass
class DiagramRegion:
    """A region within a composition for a single diagram."""
    region_id: str
    x: float                            # Left edge in inches
    y: float                            # Top edge in inches
    width: float                        # Width in inches
    height: float                       # Height in inches

    # Diagram to render in this region
    archetype_id: Optional[str] = None
    diagram_data: Optional[Any] = None  # DiagramInput for this region

    # Regional settings
    background_color: Optional[str] = None
    has_border: bool = False
    border_color: str = "#CCCCCC"
    padding: float = 0.1


@dataclass
class CompositionLayout:
    """
    Layout for multi-diagram compositions.

    Allows multiple diagrams on a single slide with shared overlays.
    """
    regions: List[DiagramRegion] = field(default_factory=list)
    shared_overlays: List[OverlaySpec] = field(default_factory=list)

    # Global settings
    background_color: str = "#FFFFFF"
    title: Optional[str] = None
    subtitle: Optional[str] = None


# =============================================================================
# LEARNED ARCHETYPE RESULT
# =============================================================================

@dataclass
class LearnedArchetypeResult:
    """Result from the archetype learning process."""
    rules: ArchetypeRules
    source_file: str
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)

    # Quality metrics
    confidence_score: float = 0.0
    detected_pattern: str = "unknown"
    element_count: int = 0

    # Warnings/notes
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


# =============================================================================
# PREDEFINED RULE TEMPLATES
# =============================================================================

def create_funnel_rules() -> ArchetypeRules:
    """Create predefined rules for funnel archetype."""
    return ArchetypeRules(
        archetype_id="funnel",
        display_name="Funnel",
        description="Narrowing stages showing filtering or conversion",
        layout_strategy=LayoutStrategy.STACK,
        primary_direction=LayoutDirection.VERTICAL,
        element_template=ElementTemplate(
            element_type=ElementShape.TRAPEZOID,
            position_rule=PositionRule.STACKED_CENTERED,
            size_rule=SizeRule.PROGRESSIVE,
            size_params=SizeParams(width_progression=0.85),
            color_rule=ColorRule.PALETTE_SEQUENCE,
            corner_radius=0.06,
        ),
        stack_params={
            "alignment": "center",
            "gutter": 0.06,
            "top_width_ratio": 0.9,
            "bottom_width_ratio": 0.25,
        },
        constraints=[
            LayoutConstraint(
                constraint_type="min_spacing",
                params={"vertical": 0.05}
            ),
        ],
        min_elements=2,
        max_elements=8,
        category="process",
        keywords=["funnel", "conversion", "sales", "leads", "pipeline", "filtering"],
        example_prompts=[
            "Sales funnel from leads to customers",
            "Marketing funnel TOFU MOFU BOFU",
            "Recruitment pipeline",
        ],
    )


def create_pyramid_rules() -> ArchetypeRules:
    """Create predefined rules for pyramid archetype."""
    return ArchetypeRules(
        archetype_id="pyramid",
        display_name="Pyramid",
        description="Triangular hierarchy with wide base narrowing to top",
        layout_strategy=LayoutStrategy.STACK,
        primary_direction=LayoutDirection.VERTICAL,
        element_template=ElementTemplate(
            element_type=ElementShape.TRAPEZOID,
            position_rule=PositionRule.STACKED_CENTERED,
            size_rule=SizeRule.PROGRESSIVE,
            size_params=SizeParams(width_progression=1.4),  # Gets wider going down
            color_rule=ColorRule.PALETTE_SEQUENCE,
        ),
        stack_params={
            "alignment": "center",
            "gutter": 0.0,
            "top_width_ratio": 0.25,
            "bottom_width_ratio": 0.9,
            "direction": "top_narrow",
        },
        min_elements=3,
        max_elements=7,
        category="hierarchy",
        keywords=["pyramid", "hierarchy", "levels", "needs", "tiers"],
        example_prompts=[
            "Maslow's hierarchy of needs",
            "Data-Information-Knowledge-Wisdom pyramid",
        ],
    )


def create_process_flow_rules() -> ArchetypeRules:
    """Create predefined rules for process flow archetype."""
    return ArchetypeRules(
        archetype_id="process_flow",
        display_name="Process Flow",
        description="Sequential steps connected by arrows",
        layout_strategy=LayoutStrategy.FLOW,
        primary_direction=LayoutDirection.HORIZONTAL,
        element_template=ElementTemplate(
            element_type=ElementShape.ROUNDED_RECT,
            position_rule=PositionRule.FLOW_LINEAR,
            size_rule=SizeRule.UNIFORM,
            color_rule=ColorRule.PALETTE_SEQUENCE,
        ),
        connector_template=ConnectorTemplate(
            pattern=ConnectorPattern.SEQUENTIAL,
            style="arrow",
            routing="direct",
        ),
        flow_params={
            "wrap_after": 6,
            "connector_gap": 0.1,
        },
        min_elements=2,
        max_elements=10,
        category="process",
        keywords=["process", "flow", "steps", "workflow", "pipeline"],
        example_prompts=[
            "Customer onboarding process",
            "CI/CD pipeline steps",
        ],
    )


def create_hub_spoke_rules() -> ArchetypeRules:
    """Create predefined rules for hub-spoke archetype."""
    return ArchetypeRules(
        archetype_id="hub_spoke",
        display_name="Hub & Spoke",
        description="Central hub with radiating connections",
        layout_strategy=LayoutStrategy.RADIAL,
        primary_direction=LayoutDirection.RADIAL,
        element_template=ElementTemplate(
            element_type=ElementShape.ROUNDED_RECT,
            position_rule=PositionRule.RADIAL_EVEN,
            size_rule=SizeRule.UNIFORM,
            color_rule=ColorRule.EMPHASIS_BASED,
        ),
        connector_template=ConnectorTemplate(
            pattern=ConnectorPattern.HUB_TO_SPOKES,
            style="arrow",
            routing="direct",
            hub_element_index=0,
        ),
        radial_params={
            "center_element": True,
            "radius_ratio": 0.35,
            "start_angle": 270,
        },
        min_elements=3,
        max_elements=10,
        category="relationship",
        keywords=["hub", "spoke", "central", "radial", "connected"],
        example_prompts=[
            "Core product with features",
            "Central team with stakeholders",
        ],
    )


def create_comparison_rules() -> ArchetypeRules:
    """Create predefined rules for comparison archetype."""
    return ArchetypeRules(
        archetype_id="comparison",
        display_name="Side-by-Side Comparison",
        description="Columns comparing multiple options",
        layout_strategy=LayoutStrategy.GRID,
        primary_direction=LayoutDirection.HORIZONTAL,
        element_template=ElementTemplate(
            element_type=ElementShape.ROUNDED_RECT,
            position_rule=PositionRule.GRID_FILL,
            size_rule=SizeRule.UNIFORM,
            color_rule=ColorRule.PALETTE_SEQUENCE,
        ),
        grid_params={
            "columns": "auto",
            "rows": "auto",
            "gutter_h": 0.25,
            "gutter_v": 0.2,
        },
        min_elements=2,
        max_elements=6,
        category="comparison",
        keywords=["compare", "comparison", "versus", "options"],
        example_prompts=[
            "Compare AWS vs Azure vs GCP",
            "Basic vs Pro vs Enterprise plans",
        ],
    )


# Registry of predefined rules
PREDEFINED_ARCHETYPE_RULES: Dict[str, ArchetypeRules] = {
    "funnel": create_funnel_rules(),
    "pyramid": create_pyramid_rules(),
    "process_flow": create_process_flow_rules(),
    "hub_spoke": create_hub_spoke_rules(),
    "comparison": create_comparison_rules(),
    # More will be added as we migrate existing archetypes
}


def get_predefined_rules(archetype_id: str) -> Optional[ArchetypeRules]:
    """Get predefined rules for an archetype."""
    return PREDEFINED_ARCHETYPE_RULES.get(archetype_id)


def list_predefined_archetypes() -> List[str]:
    """List all predefined archetype IDs."""
    return list(PREDEFINED_ARCHETYPE_RULES.keys())
