"""
archetype_registry.py — Comprehensive archetype type definitions and metadata.

This module defines ALL available infographic archetypes with rich metadata
to help the LLM select the appropriate archetype for user prompts.

Categories:
- LIST: Non-sequential items (bullet lists, icon grids, cards)
- PROCESS: Sequential steps (flows, funnels, pipelines)
- CYCLE: Circular/repeating patterns
- HIERARCHY: Levels/ranks (pyramids, org charts, trees)
- RELATIONSHIP: Connections between concepts (Venn, hub-spoke, network)
- MATRIX: 2D categorization (quadrants, SWOT, feature tables)
- TIMELINE: Chronological events
- COMPARISON: Side-by-side comparisons
- ARCHITECTURE: System/tech diagrams
- DATA: Statistical/quantitative visualizations
- GEOGRAPHIC: Location-based diagrams
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Any


# =============================================================================
# ARCHETYPE TYPE ENUM
# =============================================================================

class ArchetypeCategory(Enum):
    """High-level categories for archetypes."""
    LIST = "list"
    PROCESS = "process"
    CYCLE = "cycle"
    HIERARCHY = "hierarchy"
    RELATIONSHIP = "relationship"
    MATRIX = "matrix"
    TIMELINE = "timeline"
    COMPARISON = "comparison"
    ARCHITECTURE = "architecture"
    DATA = "data"
    GEOGRAPHIC = "geographic"


class ArchetypeType(Enum):
    """
    All available infographic archetype types.

    Each archetype has a unique string value that serves as its identifier.
    The naming convention is: category_specific_variant
    """

    # =========================================================================
    # LIST ARCHETYPES (non-sequential items)
    # =========================================================================
    BULLET_LIST = "bullet_list"
    NUMBERED_LIST = "numbered_list"
    ICON_GRID = "icon_grid"
    CARD_GRID = "card_grid"
    CHEVRON_LIST = "chevron_list"
    STACKED_LIST = "stacked_list"
    GROUPED_LIST = "grouped_list"

    # =========================================================================
    # PROCESS ARCHETYPES (sequential steps)
    # =========================================================================
    PROCESS_FLOW = "process_flow"           # Linear horizontal/vertical flow
    CHEVRON_PROCESS = "chevron_process"     # Chevron arrow steps
    CURVED_FLOW = "curved_flow"             # S-curve or snake pattern
    BRANCHING_FLOW = "branching_flow"       # Decision tree with branches
    SWIMLANE = "swimlane"                   # Parallel lanes by responsibility
    FUNNEL = "funnel"                       # Narrowing stages
    PIPELINE = "pipeline"                   # Horizontal pipeline stages

    # =========================================================================
    # CYCLE ARCHETYPES (circular/repeating)
    # =========================================================================
    CIRCULAR_CYCLE = "circular_cycle"       # Items around a circle with arrows
    SEGMENTED_CYCLE = "segmented_cycle"     # Pie-like segments with flow
    GEAR_CYCLE = "gear_cycle"               # Interlocking gears
    CONTINUOUS_LOOP = "continuous_loop"     # Infinity or Mobius pattern

    # =========================================================================
    # HIERARCHY ARCHETYPES (levels/ranks)
    # =========================================================================
    PYRAMID = "pyramid"                     # Triangular levels (wide base)
    INVERTED_PYRAMID = "inverted_pyramid"   # Narrow base to wide top
    ORG_CHART = "org_chart"                 # Organizational tree
    TREE_DIAGRAM = "tree_diagram"           # Branching tree structure
    NESTED_BOXES = "nested_boxes"           # Boxes within boxes
    STAIRCASE = "staircase"                 # Ascending/descending steps

    # =========================================================================
    # RELATIONSHIP ARCHETYPES (connections between concepts)
    # =========================================================================
    VENN_DIAGRAM = "venn_diagram"           # 2-5 overlapping circles
    HUB_SPOKE = "hub_spoke"                 # Central hub with radiating spokes
    NETWORK = "network"                     # Nodes with interconnecting lines
    BRIDGE = "bridge"                       # Two sides connected
    INTERLOCKING = "interlocking"           # Puzzle pieces or linked rings
    CONVERGENCE = "convergence"             # Multiple items flowing to one
    DIVERGENCE = "divergence"               # One item splitting to many
    TARGET = "target"                       # Concentric rings (bullseye)

    # =========================================================================
    # MATRIX ARCHETYPES (2D categorization)
    # =========================================================================
    MATRIX_2X2 = "matrix_2x2"               # Four quadrants
    MATRIX_3X3 = "matrix_3x3"               # Nine cells
    FEATURE_MATRIX = "feature_matrix"       # Rows = items, columns = features
    SWOT = "swot"                           # Strengths/Weaknesses/Opp/Threats

    # =========================================================================
    # TIMELINE ARCHETYPES (chronological)
    # =========================================================================
    TIMELINE = "timeline"                   # Horizontal/vertical timeline
    ROADMAP = "roadmap"                     # Future milestones/phases
    GANTT = "gantt"                         # Project schedule bars
    MILESTONE = "milestone"                 # Key events with markers

    # =========================================================================
    # COMPARISON ARCHETYPES (side-by-side)
    # =========================================================================
    COMPARISON = "comparison"               # Side-by-side columns
    BEFORE_AFTER = "before_after"           # Two-state comparison
    VERSUS = "versus"                       # Head-to-head (VS)
    PROS_CONS = "pros_cons"                 # Two-column advantages/disadvantages
    SCALE = "scale"                         # Items along a spectrum

    # =========================================================================
    # ARCHITECTURE ARCHETYPES (system diagrams)
    # =========================================================================
    MARKETECTURE = "marketecture"           # Horizontal tech stack layers
    TECH_STACK = "tech_stack"               # Vertical technology layers
    BLOCK_DIAGRAM = "block_diagram"         # Components with connections
    CONTAINER_DIAGRAM = "container_diagram" # Nested systems (C4 style)

    # =========================================================================
    # DATA ARCHETYPES (statistical/quantitative)
    # =========================================================================
    BAR_CHART = "bar_chart"                 # Horizontal/vertical bars
    PIE_CHART = "pie_chart"                 # Proportional slices
    DONUT_CHART = "donut_chart"             # Pie with center hole
    PICTOGRAM = "pictogram"                 # Icons representing quantities
    GAUGE = "gauge"                         # Speedometer-style meter
    PROGRESS_BAR = "progress_bar"           # Completion percentage
    KPI_DASHBOARD = "kpi_dashboard"         # Multiple metrics display

    # =========================================================================
    # GEOGRAPHIC ARCHETYPES (location-based)
    # =========================================================================
    WORLD_MAP = "world_map"                 # World map with highlights
    REGION_MAP = "region_map"               # Country/region map
    PIN_MAP = "pin_map"                     # Markers on locations
    FLOW_MAP = "flow_map"                   # Arrows showing movement


# =============================================================================
# ARCHETYPE METADATA
# =============================================================================

@dataclass
class ArchetypeMetadata:
    """Rich metadata for each archetype to help LLM selection."""
    archetype_type: ArchetypeType
    category: ArchetypeCategory
    display_name: str
    description: str
    when_to_use: str
    example_prompts: List[str]
    keywords: List[str]
    min_items: int = 1
    max_items: int = 20
    supports_layers: bool = False
    supports_connectors: bool = False


# Complete metadata registry
ARCHETYPE_METADATA: Dict[ArchetypeType, ArchetypeMetadata] = {

    # =========================================================================
    # LIST ARCHETYPES
    # =========================================================================

    ArchetypeType.BULLET_LIST: ArchetypeMetadata(
        archetype_type=ArchetypeType.BULLET_LIST,
        category=ArchetypeCategory.LIST,
        display_name="Bullet List",
        description="Enhanced bullet points with icons and visual styling",
        when_to_use="When presenting a list of items, features, or key points without sequence",
        example_prompts=[
            "List the key features of our product",
            "5 benefits of cloud computing",
            "Main takeaways from the meeting",
        ],
        keywords=["list", "bullet", "points", "features", "items", "key"],
        min_items=2,
        max_items=10,
    ),

    ArchetypeType.ICON_GRID: ArchetypeMetadata(
        archetype_type=ArchetypeType.ICON_GRID,
        category=ArchetypeCategory.LIST,
        display_name="Icon Grid",
        description="Grid of icons with labels, great for feature showcases",
        when_to_use="When displaying multiple items/features with equal importance",
        example_prompts=[
            "Show our 6 core services with icons",
            "Product features grid",
            "Team capabilities overview",
        ],
        keywords=["grid", "icons", "services", "features", "capabilities", "offerings"],
        min_items=3,
        max_items=12,
    ),

    ArchetypeType.CARD_GRID: ArchetypeMetadata(
        archetype_type=ArchetypeType.CARD_GRID,
        category=ArchetypeCategory.LIST,
        display_name="Card Grid",
        description="Cards arranged in rows/columns with titles and descriptions",
        when_to_use="When each item needs more detail than just a label",
        example_prompts=[
            "Team member profiles",
            "Product lineup cards",
            "Service packages overview",
        ],
        keywords=["cards", "profiles", "packages", "lineup", "team"],
        min_items=2,
        max_items=9,
    ),

    ArchetypeType.CHEVRON_LIST: ArchetypeMetadata(
        archetype_type=ArchetypeType.CHEVRON_LIST,
        category=ArchetypeCategory.LIST,
        display_name="Chevron List",
        description="Horizontal chevron shapes showing progression or categories",
        when_to_use="When showing categories or themes with visual flow",
        example_prompts=[
            "Our core values",
            "Strategic pillars",
            "Product categories",
        ],
        keywords=["chevron", "pillars", "values", "categories", "themes"],
        min_items=3,
        max_items=7,
    ),

    ArchetypeType.STACKED_LIST: ArchetypeMetadata(
        archetype_type=ArchetypeType.STACKED_LIST,
        category=ArchetypeCategory.LIST,
        display_name="Stacked List",
        description="Vertically stacked blocks with labels",
        when_to_use="When showing a vertical arrangement of items or layers",
        example_prompts=[
            "Priority levels",
            "Subscription tiers",
            "Skill levels",
        ],
        keywords=["stacked", "tiers", "levels", "layers", "vertical"],
        min_items=2,
        max_items=8,
    ),

    ArchetypeType.GROUPED_LIST: ArchetypeMetadata(
        archetype_type=ArchetypeType.GROUPED_LIST,
        category=ArchetypeCategory.LIST,
        display_name="Grouped List",
        description="Items organized into labeled categories or groups",
        when_to_use="When items belong to distinct categories",
        example_prompts=[
            "Features grouped by category",
            "Team organized by department",
            "Products by product line",
        ],
        keywords=["grouped", "categories", "organized", "departments", "sections"],
        min_items=4,
        max_items=20,
        supports_layers=True,
    ),

    # =========================================================================
    # PROCESS ARCHETYPES
    # =========================================================================

    ArchetypeType.PROCESS_FLOW: ArchetypeMetadata(
        archetype_type=ArchetypeType.PROCESS_FLOW,
        category=ArchetypeCategory.PROCESS,
        display_name="Process Flow",
        description="Sequential steps connected by arrows showing workflow",
        when_to_use="When showing a sequence of steps, stages, or actions",
        example_prompts=[
            "Customer onboarding process",
            "CI/CD pipeline steps",
            "Order fulfillment workflow",
        ],
        keywords=["process", "flow", "steps", "workflow", "pipeline", "stages", "sequence"],
        min_items=2,
        max_items=10,
        supports_connectors=True,
    ),

    ArchetypeType.CHEVRON_PROCESS: ArchetypeMetadata(
        archetype_type=ArchetypeType.CHEVRON_PROCESS,
        category=ArchetypeCategory.PROCESS,
        display_name="Chevron Process",
        description="Chevron arrows in sequence showing process stages",
        when_to_use="When showing a linear process with visual momentum",
        example_prompts=[
            "Sales process stages",
            "Project phases",
            "Customer journey stages",
        ],
        keywords=["chevron", "stages", "phases", "journey", "progression"],
        min_items=3,
        max_items=7,
    ),

    ArchetypeType.FUNNEL: ArchetypeMetadata(
        archetype_type=ArchetypeType.FUNNEL,
        category=ArchetypeCategory.PROCESS,
        display_name="Funnel",
        description="Narrowing stages showing filtering or conversion",
        when_to_use="When showing decreasing quantities through stages (sales, conversion)",
        example_prompts=[
            "Sales funnel from leads to customers",
            "Conversion funnel",
            "Recruitment pipeline",
            "Marketing funnel TOFU MOFU BOFU",
        ],
        keywords=["funnel", "conversion", "sales", "leads", "pipeline", "filtering", "narrowing"],
        min_items=3,
        max_items=7,
    ),

    ArchetypeType.PIPELINE: ArchetypeMetadata(
        archetype_type=ArchetypeType.PIPELINE,
        category=ArchetypeCategory.PROCESS,
        display_name="Pipeline",
        description="Horizontal pipeline showing stages or throughput",
        when_to_use="When showing a continuous process or data flow",
        example_prompts=[
            "Data pipeline architecture",
            "Development pipeline",
            "Content production pipeline",
        ],
        keywords=["pipeline", "data", "throughput", "stream", "continuous"],
        min_items=3,
        max_items=8,
    ),

    ArchetypeType.SWIMLANE: ArchetypeMetadata(
        archetype_type=ArchetypeType.SWIMLANE,
        category=ArchetypeCategory.PROCESS,
        display_name="Swimlane",
        description="Parallel horizontal lanes showing responsibilities across roles",
        when_to_use="When showing a process across multiple actors/departments",
        example_prompts=[
            "Approval workflow across departments",
            "Cross-functional process",
            "Handoff process between teams",
        ],
        keywords=["swimlane", "lanes", "departments", "cross-functional", "handoff", "responsibilities"],
        min_items=4,
        max_items=20,
        supports_layers=True,
        supports_connectors=True,
    ),

    ArchetypeType.BRANCHING_FLOW: ArchetypeMetadata(
        archetype_type=ArchetypeType.BRANCHING_FLOW,
        category=ArchetypeCategory.PROCESS,
        display_name="Branching Flow / Decision Tree",
        description="Process with decision points and multiple paths",
        when_to_use="When showing decisions that lead to different outcomes",
        example_prompts=[
            "Troubleshooting decision tree",
            "Customer support routing",
            "If-then logic flow",
        ],
        keywords=["decision", "branching", "tree", "if-then", "routing", "paths"],
        min_items=3,
        max_items=15,
        supports_connectors=True,
    ),

    # =========================================================================
    # CYCLE ARCHETYPES
    # =========================================================================

    ArchetypeType.CIRCULAR_CYCLE: ArchetypeMetadata(
        archetype_type=ArchetypeType.CIRCULAR_CYCLE,
        category=ArchetypeCategory.CYCLE,
        display_name="Circular Cycle",
        description="Items arranged in a circle with arrows showing continuous flow",
        when_to_use="When showing a repeating or continuous process",
        example_prompts=[
            "PDCA cycle (Plan-Do-Check-Act)",
            "Agile sprint cycle",
            "Customer lifecycle",
            "Continuous improvement loop",
        ],
        keywords=["cycle", "circular", "loop", "continuous", "repeating", "iterative"],
        min_items=3,
        max_items=8,
    ),

    ArchetypeType.SEGMENTED_CYCLE: ArchetypeMetadata(
        archetype_type=ArchetypeType.SEGMENTED_CYCLE,
        category=ArchetypeCategory.CYCLE,
        display_name="Segmented Cycle",
        description="Pie-like segments with directional flow",
        when_to_use="When showing phases that make up a complete cycle",
        example_prompts=[
            "Product development lifecycle",
            "Annual business cycle",
            "Project management phases",
        ],
        keywords=["segments", "phases", "lifecycle", "annual", "seasons"],
        min_items=3,
        max_items=8,
    ),

    ArchetypeType.GEAR_CYCLE: ArchetypeMetadata(
        archetype_type=ArchetypeType.GEAR_CYCLE,
        category=ArchetypeCategory.CYCLE,
        display_name="Interlocking Gears",
        description="Gears that interlock showing interdependent processes",
        when_to_use="When showing how processes or teams work together",
        example_prompts=[
            "How departments work together",
            "Interdependent systems",
            "Collaboration between teams",
        ],
        keywords=["gears", "interlock", "collaboration", "interdependent", "working together"],
        min_items=2,
        max_items=5,
    ),

    # =========================================================================
    # HIERARCHY ARCHETYPES
    # =========================================================================

    ArchetypeType.PYRAMID: ArchetypeMetadata(
        archetype_type=ArchetypeType.PYRAMID,
        category=ArchetypeCategory.HIERARCHY,
        display_name="Pyramid",
        description="Triangular hierarchy with wide base narrowing to top",
        when_to_use="When showing hierarchical levels, needs hierarchy, or importance levels",
        example_prompts=[
            "Maslow's hierarchy of needs",
            "Organizational hierarchy",
            "Data-Information-Knowledge-Wisdom pyramid",
            "Management levels",
        ],
        keywords=["pyramid", "hierarchy", "levels", "needs", "tiers", "foundation"],
        min_items=3,
        max_items=7,
    ),

    ArchetypeType.INVERTED_PYRAMID: ArchetypeMetadata(
        archetype_type=ArchetypeType.INVERTED_PYRAMID,
        category=ArchetypeCategory.HIERARCHY,
        display_name="Inverted Pyramid",
        description="Wide at top, narrow at bottom - opposite of traditional pyramid",
        when_to_use="When showing filtering, prioritization, or servant leadership",
        example_prompts=[
            "Servant leadership model",
            "Customer-first organization",
            "Filtering from many to few",
        ],
        keywords=["inverted", "servant", "customer-first", "filtering"],
        min_items=3,
        max_items=6,
    ),

    ArchetypeType.ORG_CHART: ArchetypeMetadata(
        archetype_type=ArchetypeType.ORG_CHART,
        category=ArchetypeCategory.HIERARCHY,
        display_name="Organization Chart",
        description="Traditional org chart showing reporting structure",
        when_to_use="When showing organizational structure and reporting lines",
        example_prompts=[
            "Company organization chart",
            "Team structure",
            "Reporting hierarchy",
            "Department structure",
        ],
        keywords=["org chart", "organization", "reporting", "structure", "hierarchy", "team"],
        min_items=2,
        max_items=30,
        supports_connectors=True,
    ),

    ArchetypeType.TREE_DIAGRAM: ArchetypeMetadata(
        archetype_type=ArchetypeType.TREE_DIAGRAM,
        category=ArchetypeCategory.HIERARCHY,
        display_name="Tree Diagram",
        description="Branching tree structure for categories or decomposition",
        when_to_use="When breaking down a concept into sub-categories",
        example_prompts=[
            "Product category tree",
            "Work breakdown structure",
            "Taxonomy of concepts",
        ],
        keywords=["tree", "breakdown", "categories", "taxonomy", "decomposition"],
        min_items=3,
        max_items=25,
        supports_connectors=True,
    ),

    ArchetypeType.STAIRCASE: ArchetypeMetadata(
        archetype_type=ArchetypeType.STAIRCASE,
        category=ArchetypeCategory.HIERARCHY,
        display_name="Staircase / Steps",
        description="Ascending or descending steps showing progression",
        when_to_use="When showing growth, maturity levels, or progression",
        example_prompts=[
            "Maturity model levels",
            "Career progression ladder",
            "Skill development stages",
            "Growth stages",
        ],
        keywords=["stairs", "steps", "ladder", "progression", "maturity", "growth", "levels"],
        min_items=3,
        max_items=7,
    ),

    ArchetypeType.NESTED_BOXES: ArchetypeMetadata(
        archetype_type=ArchetypeType.NESTED_BOXES,
        category=ArchetypeCategory.HIERARCHY,
        display_name="Nested Boxes",
        description="Boxes within boxes showing containment or layers",
        when_to_use="When showing containment, scope, or layered architecture",
        example_prompts=[
            "System layers",
            "Scope containment",
            "Nested categories",
        ],
        keywords=["nested", "containment", "layers", "scope", "within"],
        min_items=2,
        max_items=5,
    ),

    # =========================================================================
    # RELATIONSHIP ARCHETYPES
    # =========================================================================

    ArchetypeType.VENN_DIAGRAM: ArchetypeMetadata(
        archetype_type=ArchetypeType.VENN_DIAGRAM,
        category=ArchetypeCategory.RELATIONSHIP,
        display_name="Venn Diagram",
        description="Overlapping circles showing relationships and intersections",
        when_to_use="When showing overlap, intersection, or shared attributes",
        example_prompts=[
            "Skills overlap between teams",
            "Product feature intersection",
            "Audience segment overlap",
            "Venn diagram of responsibilities",
        ],
        keywords=["venn", "overlap", "intersection", "shared", "common", "circles"],
        min_items=2,
        max_items=4,
    ),

    ArchetypeType.HUB_SPOKE: ArchetypeMetadata(
        archetype_type=ArchetypeType.HUB_SPOKE,
        category=ArchetypeCategory.RELATIONSHIP,
        display_name="Hub & Spoke",
        description="Central hub with radiating connections to surrounding items",
        when_to_use="When showing a central concept connected to related items",
        example_prompts=[
            "Core product with features",
            "Central team with stakeholders",
            "Main service with integrations",
            "Hub and spoke model",
        ],
        keywords=["hub", "spoke", "central", "radial", "connected", "surrounding"],
        min_items=3,
        max_items=10,
        supports_connectors=True,
    ),

    ArchetypeType.NETWORK: ArchetypeMetadata(
        archetype_type=ArchetypeType.NETWORK,
        category=ArchetypeCategory.RELATIONSHIP,
        display_name="Network / Web",
        description="Nodes with interconnecting lines showing relationships",
        when_to_use="When showing complex relationships between many items",
        example_prompts=[
            "Partner ecosystem",
            "Knowledge network",
            "Interconnected systems",
        ],
        keywords=["network", "web", "interconnected", "ecosystem", "mesh"],
        min_items=3,
        max_items=15,
        supports_connectors=True,
    ),

    ArchetypeType.CONVERGENCE: ArchetypeMetadata(
        archetype_type=ArchetypeType.CONVERGENCE,
        category=ArchetypeCategory.RELATIONSHIP,
        display_name="Convergence",
        description="Multiple items flowing into a single point",
        when_to_use="When showing multiple inputs combining into one output",
        example_prompts=[
            "Data sources feeding into analytics",
            "Teams contributing to a goal",
            "Inputs combining to create output",
        ],
        keywords=["convergence", "combine", "merge", "inputs", "feeding into"],
        min_items=3,
        max_items=8,
        supports_connectors=True,
    ),

    ArchetypeType.DIVERGENCE: ArchetypeMetadata(
        archetype_type=ArchetypeType.DIVERGENCE,
        category=ArchetypeCategory.RELATIONSHIP,
        display_name="Divergence",
        description="Single item splitting into multiple outputs",
        when_to_use="When showing one source distributing to many destinations",
        example_prompts=[
            "Content distributed across channels",
            "Single source multiple outputs",
            "Branching from one to many",
        ],
        keywords=["divergence", "split", "distribute", "branch", "one to many"],
        min_items=3,
        max_items=8,
        supports_connectors=True,
    ),

    ArchetypeType.TARGET: ArchetypeMetadata(
        archetype_type=ArchetypeType.TARGET,
        category=ArchetypeCategory.RELATIONSHIP,
        display_name="Target / Bullseye",
        description="Concentric circles showing layers from outside to center",
        when_to_use="When showing layers of priority, focus, or containment",
        example_prompts=[
            "Target customer segments",
            "Priority circles",
            "Core vs peripheral features",
            "Bullseye framework",
        ],
        keywords=["target", "bullseye", "concentric", "core", "focus", "priority"],
        min_items=2,
        max_items=5,
    ),

    ArchetypeType.BRIDGE: ArchetypeMetadata(
        archetype_type=ArchetypeType.BRIDGE,
        category=ArchetypeCategory.RELATIONSHIP,
        display_name="Bridge",
        description="Two sides connected by a bridging element",
        when_to_use="When showing how something connects two separate entities",
        example_prompts=[
            "Integration bridging two systems",
            "Translation layer between teams",
            "Connecting old and new",
        ],
        keywords=["bridge", "connect", "link", "between", "integration"],
        min_items=3,
        max_items=5,
        supports_connectors=True,
    ),

    # =========================================================================
    # MATRIX ARCHETYPES
    # =========================================================================

    ArchetypeType.MATRIX_2X2: ArchetypeMetadata(
        archetype_type=ArchetypeType.MATRIX_2X2,
        category=ArchetypeCategory.MATRIX,
        display_name="2x2 Matrix",
        description="Four quadrants for categorizing items on two dimensions",
        when_to_use="When categorizing items by two criteria (e.g., urgency vs importance)",
        example_prompts=[
            "Eisenhower matrix (urgent/important)",
            "Risk vs impact matrix",
            "Effort vs value quadrant",
            "BCG growth-share matrix",
        ],
        keywords=["matrix", "quadrant", "2x2", "urgent", "important", "prioritization"],
        min_items=4,
        max_items=4,
    ),

    ArchetypeType.MATRIX_3X3: ArchetypeMetadata(
        archetype_type=ArchetypeType.MATRIX_3X3,
        category=ArchetypeCategory.MATRIX,
        display_name="3x3 Matrix",
        description="Nine cells for more granular categorization",
        when_to_use="When needing more granularity than 2x2",
        example_prompts=[
            "GE-McKinsey matrix",
            "Skill proficiency matrix",
            "Priority matrix with medium option",
        ],
        keywords=["matrix", "3x3", "nine", "granular"],
        min_items=9,
        max_items=9,
    ),

    ArchetypeType.FEATURE_MATRIX: ArchetypeMetadata(
        archetype_type=ArchetypeType.FEATURE_MATRIX,
        category=ArchetypeCategory.MATRIX,
        display_name="Feature Matrix",
        description="Table with items in rows and features/attributes in columns",
        when_to_use="When comparing multiple items across multiple criteria",
        example_prompts=[
            "Product comparison table",
            "Vendor evaluation matrix",
            "Feature comparison chart",
        ],
        keywords=["feature", "comparison", "table", "evaluation", "criteria"],
        min_items=4,
        max_items=30,
    ),

    ArchetypeType.SWOT: ArchetypeMetadata(
        archetype_type=ArchetypeType.SWOT,
        category=ArchetypeCategory.MATRIX,
        display_name="SWOT Analysis",
        description="Strengths, Weaknesses, Opportunities, Threats quadrants",
        when_to_use="When doing strategic analysis",
        example_prompts=[
            "SWOT analysis of our company",
            "Strategic assessment",
            "Strengths and weaknesses analysis",
        ],
        keywords=["swot", "strengths", "weaknesses", "opportunities", "threats", "strategic"],
        min_items=4,
        max_items=20,
    ),

    # =========================================================================
    # TIMELINE ARCHETYPES
    # =========================================================================

    ArchetypeType.TIMELINE: ArchetypeMetadata(
        archetype_type=ArchetypeType.TIMELINE,
        category=ArchetypeCategory.TIMELINE,
        display_name="Timeline",
        description="Chronological events along a horizontal or vertical axis",
        when_to_use="When showing events in chronological order",
        example_prompts=[
            "Company history timeline",
            "Project milestones",
            "Product evolution history",
        ],
        keywords=["timeline", "history", "chronological", "events", "milestones", "dates"],
        min_items=2,
        max_items=10,
    ),

    ArchetypeType.ROADMAP: ArchetypeMetadata(
        archetype_type=ArchetypeType.ROADMAP,
        category=ArchetypeCategory.TIMELINE,
        display_name="Roadmap",
        description="Future-focused timeline showing planned phases or features",
        when_to_use="When showing future plans, phases, or releases",
        example_prompts=[
            "Product roadmap Q1-Q4",
            "Strategic initiatives roadmap",
            "Technology roadmap",
        ],
        keywords=["roadmap", "future", "planned", "phases", "releases", "quarters"],
        min_items=2,
        max_items=12,
    ),

    ArchetypeType.GANTT: ArchetypeMetadata(
        archetype_type=ArchetypeType.GANTT,
        category=ArchetypeCategory.TIMELINE,
        display_name="Gantt Chart",
        description="Project schedule with task bars showing duration and overlap",
        when_to_use="When showing project schedules with task durations",
        example_prompts=[
            "Project schedule Gantt chart",
            "Implementation timeline with tasks",
            "Sprint planning timeline",
        ],
        keywords=["gantt", "schedule", "tasks", "duration", "project", "planning"],
        min_items=3,
        max_items=15,
    ),

    # =========================================================================
    # COMPARISON ARCHETYPES
    # =========================================================================

    ArchetypeType.COMPARISON: ArchetypeMetadata(
        archetype_type=ArchetypeType.COMPARISON,
        category=ArchetypeCategory.COMPARISON,
        display_name="Side-by-Side Comparison",
        description="Columns comparing multiple options or items",
        when_to_use="When comparing multiple options, products, or choices",
        example_prompts=[
            "Compare AWS vs Azure vs GCP",
            "Basic vs Pro vs Enterprise plans",
            "Option A vs Option B comparison",
        ],
        keywords=["compare", "comparison", "versus", "vs", "options", "side by side"],
        min_items=2,
        max_items=6,
        supports_layers=True,
    ),

    ArchetypeType.BEFORE_AFTER: ArchetypeMetadata(
        archetype_type=ArchetypeType.BEFORE_AFTER,
        category=ArchetypeCategory.COMPARISON,
        display_name="Before / After",
        description="Two-state comparison showing transformation",
        when_to_use="When showing a transformation or change over time",
        example_prompts=[
            "Before and after implementation",
            "Current state vs future state",
            "Legacy vs modern architecture",
        ],
        keywords=["before", "after", "transformation", "change", "current", "future"],
        min_items=2,
        max_items=2,
    ),

    ArchetypeType.VERSUS: ArchetypeMetadata(
        archetype_type=ArchetypeType.VERSUS,
        category=ArchetypeCategory.COMPARISON,
        display_name="Versus (VS)",
        description="Head-to-head comparison of two options",
        when_to_use="When showing a direct head-to-head comparison",
        example_prompts=[
            "React vs Vue comparison",
            "Buy vs build analysis",
            "Monolith vs microservices",
        ],
        keywords=["versus", "vs", "head to head", "either or"],
        min_items=2,
        max_items=2,
    ),

    ArchetypeType.PROS_CONS: ArchetypeMetadata(
        archetype_type=ArchetypeType.PROS_CONS,
        category=ArchetypeCategory.COMPARISON,
        display_name="Pros & Cons",
        description="Two columns showing advantages and disadvantages",
        when_to_use="When evaluating a single option's benefits and drawbacks",
        example_prompts=[
            "Pros and cons of remote work",
            "Advantages and disadvantages",
            "Benefits vs drawbacks",
        ],
        keywords=["pros", "cons", "advantages", "disadvantages", "benefits", "drawbacks"],
        min_items=2,
        max_items=20,
    ),

    ArchetypeType.SCALE: ArchetypeMetadata(
        archetype_type=ArchetypeType.SCALE,
        category=ArchetypeCategory.COMPARISON,
        display_name="Scale / Spectrum",
        description="Items positioned along a continuum or scale",
        when_to_use="When showing items along a range or spectrum",
        example_prompts=[
            "Risk spectrum from low to high",
            "Technology adoption curve",
            "Skill level scale",
        ],
        keywords=["scale", "spectrum", "range", "continuum", "gradient"],
        min_items=2,
        max_items=7,
    ),

    # =========================================================================
    # ARCHITECTURE ARCHETYPES
    # =========================================================================

    ArchetypeType.MARKETECTURE: ArchetypeMetadata(
        archetype_type=ArchetypeType.MARKETECTURE,
        category=ArchetypeCategory.ARCHITECTURE,
        display_name="Marketecture",
        description="Horizontal layers showing technology stack or platform components",
        when_to_use="When showing a technology platform, stack, or system architecture",
        example_prompts=[
            "Platform architecture overview",
            "Technology stack layers",
            "System architecture with components",
            "Marketecture diagram",
        ],
        keywords=["marketecture", "architecture", "platform", "stack", "layers", "components"],
        min_items=3,
        max_items=30,
        supports_layers=True,
    ),

    ArchetypeType.TECH_STACK: ArchetypeMetadata(
        archetype_type=ArchetypeType.TECH_STACK,
        category=ArchetypeCategory.ARCHITECTURE,
        display_name="Tech Stack",
        description="Vertical technology stack showing layers from bottom to top",
        when_to_use="When showing a vertical technology stack (infrastructure to UI)",
        example_prompts=[
            "Our technology stack",
            "Full stack architecture",
            "Frontend to backend stack",
        ],
        keywords=["stack", "technology", "frontend", "backend", "infrastructure"],
        min_items=2,
        max_items=8,
    ),

    ArchetypeType.BLOCK_DIAGRAM: ArchetypeMetadata(
        archetype_type=ArchetypeType.BLOCK_DIAGRAM,
        category=ArchetypeCategory.ARCHITECTURE,
        display_name="Block Diagram",
        description="System components as blocks with connecting lines",
        when_to_use="When showing system components and their connections",
        example_prompts=[
            "System block diagram",
            "Component architecture",
            "Integration diagram",
        ],
        keywords=["block", "diagram", "components", "system", "integration"],
        min_items=2,
        max_items=15,
        supports_connectors=True,
    ),

    ArchetypeType.CONTAINER_DIAGRAM: ArchetypeMetadata(
        archetype_type=ArchetypeType.CONTAINER_DIAGRAM,
        category=ArchetypeCategory.ARCHITECTURE,
        display_name="Container Diagram",
        description="Nested containers showing system boundaries (C4 style)",
        when_to_use="When showing system boundaries and contained components",
        example_prompts=[
            "C4 container diagram",
            "System context with boundaries",
            "Microservices boundaries",
        ],
        keywords=["container", "c4", "boundaries", "microservices", "context"],
        min_items=2,
        max_items=12,
        supports_layers=True,
    ),

    # =========================================================================
    # DATA ARCHETYPES
    # =========================================================================

    ArchetypeType.BAR_CHART: ArchetypeMetadata(
        archetype_type=ArchetypeType.BAR_CHART,
        category=ArchetypeCategory.DATA,
        display_name="Bar Chart",
        description="Horizontal or vertical bars showing quantities",
        when_to_use="When comparing quantities across categories",
        example_prompts=[
            "Sales by region bar chart",
            "Performance metrics comparison",
            "Category breakdown",
        ],
        keywords=["bar", "chart", "comparison", "quantities", "metrics"],
        min_items=2,
        max_items=12,
    ),

    ArchetypeType.PIE_CHART: ArchetypeMetadata(
        archetype_type=ArchetypeType.PIE_CHART,
        category=ArchetypeCategory.DATA,
        display_name="Pie Chart",
        description="Circular chart divided into proportional slices",
        when_to_use="When showing parts of a whole (percentages)",
        example_prompts=[
            "Market share breakdown",
            "Budget allocation pie chart",
            "Revenue by segment",
        ],
        keywords=["pie", "chart", "percentage", "share", "breakdown", "proportion"],
        min_items=2,
        max_items=8,
    ),

    ArchetypeType.DONUT_CHART: ArchetypeMetadata(
        archetype_type=ArchetypeType.DONUT_CHART,
        category=ArchetypeCategory.DATA,
        display_name="Donut Chart",
        description="Pie chart with center hole, often showing total",
        when_to_use="When showing parts of whole with emphasis on total",
        example_prompts=[
            "Progress donut chart",
            "Composition with total in center",
            "Allocation donut",
        ],
        keywords=["donut", "ring", "progress", "composition", "total"],
        min_items=2,
        max_items=8,
    ),

    ArchetypeType.PICTOGRAM: ArchetypeMetadata(
        archetype_type=ArchetypeType.PICTOGRAM,
        category=ArchetypeCategory.DATA,
        display_name="Pictogram / Icon Chart",
        description="Icons or symbols representing quantities",
        when_to_use="When making statistics more visual and memorable",
        example_prompts=[
            "User statistics with icons",
            "Infographic statistics",
            "Visual data representation",
        ],
        keywords=["pictogram", "icons", "statistics", "visual", "infographic"],
        min_items=1,
        max_items=10,
    ),

    ArchetypeType.GAUGE: ArchetypeMetadata(
        archetype_type=ArchetypeType.GAUGE,
        category=ArchetypeCategory.DATA,
        display_name="Gauge / Meter",
        description="Speedometer-style gauge showing a single metric",
        when_to_use="When showing progress toward a goal or current status",
        example_prompts=[
            "Performance gauge",
            "Goal progress meter",
            "Health score indicator",
        ],
        keywords=["gauge", "meter", "speedometer", "indicator", "score", "progress"],
        min_items=1,
        max_items=1,
    ),

    ArchetypeType.PROGRESS_BAR: ArchetypeMetadata(
        archetype_type=ArchetypeType.PROGRESS_BAR,
        category=ArchetypeCategory.DATA,
        display_name="Progress Bar",
        description="Horizontal bar showing completion percentage",
        when_to_use="When showing progress toward completion",
        example_prompts=[
            "Project completion status",
            "Progress toward goal",
            "Milestone progress bars",
        ],
        keywords=["progress", "bar", "completion", "percentage", "status"],
        min_items=1,
        max_items=10,
    ),

    ArchetypeType.KPI_DASHBOARD: ArchetypeMetadata(
        archetype_type=ArchetypeType.KPI_DASHBOARD,
        category=ArchetypeCategory.DATA,
        display_name="KPI Dashboard",
        description="Multiple metrics displayed together",
        when_to_use="When showing multiple key metrics at once",
        example_prompts=[
            "Executive KPI dashboard",
            "Performance metrics overview",
            "Key metrics summary",
        ],
        keywords=["kpi", "dashboard", "metrics", "key", "performance", "indicators"],
        min_items=3,
        max_items=12,
    ),

    # =========================================================================
    # GEOGRAPHIC ARCHETYPES
    # =========================================================================

    ArchetypeType.WORLD_MAP: ArchetypeMetadata(
        archetype_type=ArchetypeType.WORLD_MAP,
        category=ArchetypeCategory.GEOGRAPHIC,
        display_name="World Map",
        description="World map with highlighted regions or markers",
        when_to_use="When showing global presence or geographic distribution",
        example_prompts=[
            "Global office locations",
            "Worldwide customer distribution",
            "International expansion map",
        ],
        keywords=["world", "map", "global", "international", "locations", "geographic"],
        min_items=1,
        max_items=50,
    ),

    ArchetypeType.REGION_MAP: ArchetypeMetadata(
        archetype_type=ArchetypeType.REGION_MAP,
        category=ArchetypeCategory.GEOGRAPHIC,
        display_name="Region Map",
        description="Country or region map with highlighted areas",
        when_to_use="When showing regional distribution or presence",
        example_prompts=[
            "US regional sales map",
            "European market presence",
            "State-by-state breakdown",
        ],
        keywords=["region", "map", "country", "state", "area", "territory"],
        min_items=1,
        max_items=50,
    ),

    ArchetypeType.PIN_MAP: ArchetypeMetadata(
        archetype_type=ArchetypeType.PIN_MAP,
        category=ArchetypeCategory.GEOGRAPHIC,
        display_name="Pin Map",
        description="Map with location markers/pins",
        when_to_use="When showing specific location points",
        example_prompts=[
            "Store locations map",
            "Event venues on map",
            "Partner locations pinned",
        ],
        keywords=["pin", "marker", "locations", "points", "places"],
        min_items=1,
        max_items=30,
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_archetype_metadata(archetype_type: ArchetypeType) -> Optional[ArchetypeMetadata]:
    """Get metadata for a specific archetype type."""
    return ARCHETYPE_METADATA.get(archetype_type)


def get_archetypes_by_category(category: ArchetypeCategory) -> List[ArchetypeMetadata]:
    """Get all archetypes in a specific category."""
    return [
        meta for meta in ARCHETYPE_METADATA.values()
        if meta.category == category
    ]


def get_all_archetype_types() -> List[ArchetypeType]:
    """Get all defined archetype types."""
    return list(ArchetypeType)


def get_implemented_archetype_types() -> List[ArchetypeType]:
    """Get only implemented archetype types (have a corresponding class)."""
    # This will be updated as archetypes are implemented
    return [
        # Architecture
        ArchetypeType.MARKETECTURE,
        # Process
        ArchetypeType.PROCESS_FLOW,
        ArchetypeType.FUNNEL,
        # Comparison
        ArchetypeType.COMPARISON,
        # Timeline
        ArchetypeType.TIMELINE,
        # Hierarchy
        ArchetypeType.PYRAMID,
        # Relationship
        ArchetypeType.HUB_SPOKE,
        ArchetypeType.VENN_DIAGRAM,
        ArchetypeType.TARGET,
        # Cycle
        ArchetypeType.CIRCULAR_CYCLE,
        # Matrix
        ArchetypeType.MATRIX_2X2,
        # Hierarchy
        ArchetypeType.STAIRCASE,
        ArchetypeType.ORG_CHART,
        # Process
        ArchetypeType.CHEVRON_PROCESS,
        ArchetypeType.PIPELINE,
        # List
        ArchetypeType.ICON_GRID,
        ArchetypeType.BULLET_LIST,
        ArchetypeType.CARD_GRID,
        # Matrix
        ArchetypeType.SWOT,
        # Comparison
        ArchetypeType.BEFORE_AFTER,
        # Timeline
        ArchetypeType.ROADMAP,
        # Data
        ArchetypeType.PROGRESS_BAR,
        ArchetypeType.GAUGE,
        ArchetypeType.PICTOGRAM,
        # Comparison
        ArchetypeType.VERSUS,
        # Hierarchy
        ArchetypeType.TREE_DIAGRAM,
    ]


def search_archetypes(keywords: List[str]) -> List[ArchetypeMetadata]:
    """
    Search archetypes by keywords.
    Returns archetypes sorted by relevance (number of keyword matches).
    """
    results = []
    for meta in ARCHETYPE_METADATA.values():
        # Count keyword matches
        score = 0
        search_text = " ".join([
            meta.display_name.lower(),
            meta.description.lower(),
            meta.when_to_use.lower(),
            " ".join(meta.keywords),
            " ".join(meta.example_prompts).lower(),
        ])
        for keyword in keywords:
            if keyword.lower() in search_text:
                score += 1
        if score > 0:
            results.append((score, meta))

    # Sort by score descending
    results.sort(key=lambda x: x[0], reverse=True)
    return [meta for score, meta in results]


def generate_llm_archetype_descriptions() -> str:
    """
    Generate a formatted string describing all archetypes for the LLM system prompt.
    """
    lines = ["## Available Diagram Types (Archetypes)\n"]

    current_category = None
    for archetype_type in ArchetypeType:
        meta = ARCHETYPE_METADATA.get(archetype_type)
        if not meta:
            continue

        # Add category header
        if meta.category != current_category:
            current_category = meta.category
            lines.append(f"\n### {current_category.value.upper()}\n")

        # Add archetype entry
        lines.append(f"- **{archetype_type.value}**: {meta.description}")
        lines.append(f"  - Use when: {meta.when_to_use}")
        lines.append(f"  - Keywords: {', '.join(meta.keywords[:5])}")

    return "\n".join(lines)
