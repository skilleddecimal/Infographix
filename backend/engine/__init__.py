# InfographAI Layout Engine

from .units import (
    SLIDE_WIDTH_INCHES,
    SLIDE_HEIGHT_INCHES,
    inches_to_emu,
    emu_to_inches,
)

from .data_models import (
    ColorPalette,
    BlockData,
    ConnectorData,
    LayerData,
    DiagramInput,
)

from .positioned import (
    PositionedLayout,
    PositionedElement,
    PositionedConnector,
    PositionedText,
    ElementType,
    ConnectorStyle,
    TextAlignment,
    MultiSlidePresentation,
)

from .text_measure import (
    fit_text_to_width,
    measure_text,
    TextFitResult,
)

from .grid_layout import (
    compute_grid,
    compute_centered_block,
    compute_centered_row,
    GridLayout,
    GridCell,
)

from .layout_engine import (
    LayoutEngine,
    LayoutResult,
    ArchetypeType,
    create_layout,
    quick_layout,
    # New universal system convenience functions
    create_funnel,
    create_pyramid,
    create_process_flow,
    create_comparison,
    create_hub_spoke,
    create_timeline,
    create_composition,
    learn_archetype_from_pptx,
    list_all_archetypes,
)

# Universal Archetype System
from .archetype_rules import (
    ArchetypeRules,
    ElementTemplate,
    ConnectorTemplate,
    LayoutConstraint,
    OverlaySpec,
    OverlayElement,
    CompositionLayout,
    DiagramRegion,
    # Enums
    LayoutStrategy,
    LayoutDirection,
    ElementShape,
    PositionRule,
    SizeRule,
    ColorRule,
    ConnectorPattern,
    OverlayType,
    OverlayPosition,
)

from .universal_archetype import UniversalArchetype

from .archetype_resolver import (
    ArchetypeResolver,
    get_resolver,
    resolve_archetype,
    list_archetypes,
)

from .archetype_learner import (
    ArchetypeLearner,
    LearnedArchetypeResult,
)

from .multi_diagram_composer import (
    MultiDiagramComposer,
    RegionLayout,
    compose_diagrams,
    REGION_LAYOUTS,
)

from .overlay_system import OverlayEngine

from .pptx_renderer import (
    PPTXRenderer,
    render_to_pptx,
    render_to_bytes,
    render_styled,
    render_presentation_to_pptx,
    render_presentation_to_bytes,
    create_presentation_from_layouts,
    # Visual effect types
    ShapeType,
    ShadowEffect,
    GradientEffect,
    VisualStyle,
    # Style presets
    STYLE_FLAT,
    STYLE_SUBTLE_3D,
    STYLE_PROFESSIONAL,
    STYLE_EXECUTIVE,
    STYLE_PYRAMID_LEVEL,
    SHADOW_SUBTLE,
    SHADOW_MEDIUM,
    SHADOW_STRONG,
    GRADIENT_SUBTLE_3D,
    GRADIENT_GLASS,
    # Utility
    apply_visual_effects_to_shape,
    lighten_color,
    darken_color,
)

from .design_learner import (
    StyleDatabase,
    PPTAnalyzer,
    ImageAnalyzer,
    DesignStyle,
    ColorPaletteExtended,
    ShapeStyle,
    TypographyStyle,
    LayoutStyle,
    ShadowStyle,
    GradientStyle,
    GradientStop,
)

from .svg_renderer import (
    SVGRenderer,
    render_to_svg,
    render_to_svg_string,
    render_to_data_uri,
)

from .brand_engine import (
    extract_colors_from_logo,
    create_palette_from_extracted_colors,
    generate_palette_from_primary,
    generate_monochromatic_palette,
    generate_complementary_palette,
    get_brand_preset,
    list_brand_presets,
    validate_palette_contrast,
    BRAND_PRESETS,
)

from .llm_reasoning import (
    InfographBrief,
    EntityBrief,
    LayerBrief,
    ConnectionBrief,
    SlideBrief,
    analyze_prompt,
    analyze_prompt_sync,
    validate_brief,
    enhance_brief,
    brief_to_dict,
    dict_to_brief,
)

from .template_library import (
    DiagramTemplate,
    TemplateCategory,
    get_template,
    list_templates,
    get_categories,
    get_popular_tags,
    create_brief_from_template,
    TEMPLATE_LIBRARY,
)

__all__ = [
    # Units
    'SLIDE_WIDTH_INCHES',
    'SLIDE_HEIGHT_INCHES',
    'inches_to_emu',
    'emu_to_inches',
    # Data models
    'ColorPalette',
    'BlockData',
    'ConnectorData',
    'LayerData',
    'DiagramInput',
    # Positioned
    'PositionedLayout',
    'PositionedElement',
    'PositionedConnector',
    'PositionedText',
    'ElementType',
    'ConnectorStyle',
    'TextAlignment',
    'MultiSlidePresentation',
    # Text measurement
    'fit_text_to_width',
    'measure_text',
    'TextFitResult',
    # Grid layout
    'compute_grid',
    'compute_centered_block',
    'compute_centered_row',
    'GridLayout',
    'GridCell',
    # Layout engine
    'LayoutEngine',
    'LayoutResult',
    'ArchetypeType',
    'create_layout',
    'quick_layout',
    'create_funnel',
    'create_pyramid',
    'create_process_flow',
    'create_comparison',
    'create_hub_spoke',
    'create_timeline',
    'create_composition',
    'learn_archetype_from_pptx',
    'list_all_archetypes',
    # Universal Archetype System
    'ArchetypeRules',
    'ElementTemplate',
    'ConnectorTemplate',
    'LayoutConstraint',
    'OverlaySpec',
    'OverlayElement',
    'CompositionLayout',
    'DiagramRegion',
    'LayoutStrategy',
    'LayoutDirection',
    'ElementShape',
    'PositionRule',
    'SizeRule',
    'ColorRule',
    'ConnectorPattern',
    'OverlayType',
    'OverlayPosition',
    'UniversalArchetype',
    'ArchetypeResolver',
    'get_resolver',
    'resolve_archetype',
    'list_archetypes',
    'ArchetypeLearner',
    'LearnedArchetypeResult',
    'MultiDiagramComposer',
    'RegionLayout',
    'compose_diagrams',
    'REGION_LAYOUTS',
    'OverlayEngine',
    # PPTX renderer
    'PPTXRenderer',
    'render_to_pptx',
    'render_to_bytes',
    'render_styled',
    'render_presentation_to_pptx',
    'render_presentation_to_bytes',
    'create_presentation_from_layouts',
    # Visual effects
    'ShapeType',
    'ShadowEffect',
    'GradientEffect',
    'VisualStyle',
    'STYLE_FLAT',
    'STYLE_SUBTLE_3D',
    'STYLE_PROFESSIONAL',
    'STYLE_EXECUTIVE',
    'STYLE_PYRAMID_LEVEL',
    'SHADOW_SUBTLE',
    'SHADOW_MEDIUM',
    'SHADOW_STRONG',
    'GRADIENT_SUBTLE_3D',
    'GRADIENT_GLASS',
    'apply_visual_effects_to_shape',
    'lighten_color',
    'darken_color',
    # Design learner
    'StyleDatabase',
    'PPTAnalyzer',
    'ImageAnalyzer',
    'DesignStyle',
    'ColorPaletteExtended',
    'ShapeStyle',
    'TypographyStyle',
    'LayoutStyle',
    'ShadowStyle',
    'GradientStyle',
    'GradientStop',
    # SVG renderer
    'SVGRenderer',
    'render_to_svg',
    'render_to_svg_string',
    'render_to_data_uri',
    # Brand engine
    'extract_colors_from_logo',
    'create_palette_from_extracted_colors',
    'generate_palette_from_primary',
    'generate_monochromatic_palette',
    'generate_complementary_palette',
    'get_brand_preset',
    'list_brand_presets',
    'validate_palette_contrast',
    'BRAND_PRESETS',
    # LLM reasoning
    'InfographBrief',
    'EntityBrief',
    'LayerBrief',
    'ConnectionBrief',
    'SlideBrief',
    'analyze_prompt',
    'analyze_prompt_sync',
    'validate_brief',
    'enhance_brief',
    'brief_to_dict',
    'dict_to_brief',
    # Template library
    'DiagramTemplate',
    'TemplateCategory',
    'get_template',
    'list_templates',
    'get_categories',
    'get_popular_tags',
    'create_brief_from_template',
    'TEMPLATE_LIBRARY',
]
