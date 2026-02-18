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
)

from .pptx_renderer import (
    PPTXRenderer,
    render_to_pptx,
    render_to_bytes,
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
    analyze_prompt,
    analyze_prompt_sync,
    validate_brief,
    enhance_brief,
    brief_to_dict,
    dict_to_brief,
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
    # PPTX renderer
    'PPTXRenderer',
    'render_to_pptx',
    'render_to_bytes',
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
    'analyze_prompt',
    'analyze_prompt_sync',
    'validate_brief',
    'enhance_brief',
    'brief_to_dict',
    'dict_to_brief',
]
