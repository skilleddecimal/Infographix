# InfographAI Archetypes

from .base import BaseArchetype
from ..engine.data_models import (
    DiagramInput,
    BlockData,
    ConnectorData,
    LayerData,
    ColorPalette,
)

from .marketecture import (
    MarketectureArchetype,
    MarketectureConfig,
    create_simple_marketecture,
)

from .process_flow import (
    ProcessFlowArchetype,
    ProcessFlowConfig,
    FlowDirection,
    create_simple_process_flow,
)

from .comparison import (
    ComparisonArchetype,
    ComparisonConfig,
    create_simple_comparison,
)

from .timeline import (
    TimelineArchetype,
    TimelineConfig,
    TimelineDirection,
    create_simple_timeline,
)

from .pyramid import (
    PyramidArchetype,
    PyramidConfig,
    PyramidDirection,
    create_simple_pyramid,
)

from .funnel import (
    FunnelArchetype,
    FunnelConfig,
    create_simple_funnel,
)

from .hub_spoke import (
    HubSpokeArchetype,
    HubSpokeConfig,
    create_simple_hub_spoke,
)

from .venn import (
    VennArchetype,
    VennConfig,
    create_simple_venn,
)

from .matrix import (
    MatrixArchetype,
    MatrixConfig,
    MatrixSize,
    create_simple_matrix,
)

from .cycle import (
    CycleArchetype,
    CycleConfig,
    create_simple_cycle,
)

from .target import (
    TargetArchetype,
    TargetConfig,
    create_simple_target,
)

from .staircase import (
    StaircaseArchetype,
    StaircaseConfig,
    StaircaseDirection,
    create_simple_staircase,
)

from .chevron import (
    ChevronArchetype,
    ChevronConfig,
    create_simple_chevron,
)

from .icon_grid import (
    IconGridArchetype,
    IconGridConfig,
    IconGridStyle,
    create_simple_icon_grid,
)

from .bullet_list import (
    BulletListArchetype,
    BulletListConfig,
    BulletStyle,
    create_simple_bullet_list,
)

from .card_grid import (
    CardGridArchetype,
    CardGridConfig,
    create_simple_card_grid,
)

from .org_chart import (
    OrgChartArchetype,
    OrgChartConfig,
    OrgChartStyle,
    create_simple_org_chart,
)

from .pipeline import (
    PipelineArchetype,
    PipelineConfig,
    create_simple_pipeline,
)

from .swot import (
    SWOTArchetype,
    SWOTConfig,
    create_simple_swot,
)

from .before_after import (
    BeforeAfterArchetype,
    BeforeAfterConfig,
    create_simple_before_after,
)

from .roadmap import (
    RoadmapArchetype,
    RoadmapConfig,
    create_simple_roadmap,
)

from .progress_bar import (
    ProgressBarArchetype,
    ProgressBarConfig,
    create_simple_progress_bars,
)

from .gauge import (
    GaugeArchetype,
    GaugeConfig,
    create_simple_gauge,
    create_multi_gauge,
)

from .pictogram import (
    PictogramArchetype,
    PictogramConfig,
    create_simple_pictogram,
)

from .versus import (
    VersusArchetype,
    VersusConfig,
    create_simple_versus,
)

from .tree_diagram import (
    TreeDiagramArchetype,
    TreeDiagramConfig,
    create_simple_tree,
)

__all__ = [
    # Base
    'BaseArchetype',
    'DiagramInput',
    'BlockData',
    'ConnectorData',
    'LayerData',
    'ColorPalette',
    # Marketecture
    'MarketectureArchetype',
    'MarketectureConfig',
    'create_simple_marketecture',
    # Process Flow
    'ProcessFlowArchetype',
    'ProcessFlowConfig',
    'FlowDirection',
    'create_simple_process_flow',
    # Comparison
    'ComparisonArchetype',
    'ComparisonConfig',
    'create_simple_comparison',
    # Timeline
    'TimelineArchetype',
    'TimelineConfig',
    'TimelineDirection',
    'create_simple_timeline',
    # Pyramid
    'PyramidArchetype',
    'PyramidConfig',
    'PyramidDirection',
    'create_simple_pyramid',
    # Funnel
    'FunnelArchetype',
    'FunnelConfig',
    'create_simple_funnel',
    # Hub & Spoke
    'HubSpokeArchetype',
    'HubSpokeConfig',
    'create_simple_hub_spoke',
    # Venn
    'VennArchetype',
    'VennConfig',
    'create_simple_venn',
    # Matrix
    'MatrixArchetype',
    'MatrixConfig',
    'MatrixSize',
    'create_simple_matrix',
    # Cycle
    'CycleArchetype',
    'CycleConfig',
    'create_simple_cycle',
    # Target
    'TargetArchetype',
    'TargetConfig',
    'create_simple_target',
    # Staircase
    'StaircaseArchetype',
    'StaircaseConfig',
    'StaircaseDirection',
    'create_simple_staircase',
    # Chevron
    'ChevronArchetype',
    'ChevronConfig',
    'create_simple_chevron',
    # Icon Grid
    'IconGridArchetype',
    'IconGridConfig',
    'IconGridStyle',
    'create_simple_icon_grid',
    # Bullet List
    'BulletListArchetype',
    'BulletListConfig',
    'BulletStyle',
    'create_simple_bullet_list',
    # Card Grid
    'CardGridArchetype',
    'CardGridConfig',
    'create_simple_card_grid',
    # Org Chart
    'OrgChartArchetype',
    'OrgChartConfig',
    'OrgChartStyle',
    'create_simple_org_chart',
    # Pipeline
    'PipelineArchetype',
    'PipelineConfig',
    'create_simple_pipeline',
    # SWOT
    'SWOTArchetype',
    'SWOTConfig',
    'create_simple_swot',
    # Before/After
    'BeforeAfterArchetype',
    'BeforeAfterConfig',
    'create_simple_before_after',
    # Roadmap
    'RoadmapArchetype',
    'RoadmapConfig',
    'create_simple_roadmap',
    # Progress Bar
    'ProgressBarArchetype',
    'ProgressBarConfig',
    'create_simple_progress_bars',
    # Gauge
    'GaugeArchetype',
    'GaugeConfig',
    'create_simple_gauge',
    'create_multi_gauge',
    # Pictogram
    'PictogramArchetype',
    'PictogramConfig',
    'create_simple_pictogram',
    # Versus
    'VersusArchetype',
    'VersusConfig',
    'create_simple_versus',
    # Tree Diagram
    'TreeDiagramArchetype',
    'TreeDiagramConfig',
    'create_simple_tree',
]
