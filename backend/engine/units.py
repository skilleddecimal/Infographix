"""
units.py — EMU conversions and layout constants.

This is the foundation module. ALL positioning math uses these constants and functions.
Never hardcode EMU values anywhere else in the codebase.

EMU = English Metric Units (914400 EMUs per inch)
"""

from pptx.util import Inches, Pt, Emu

# =============================================================================
# SLIDE DIMENSIONS (16:9 widescreen)
# =============================================================================

SLIDE_WIDTH_INCHES = 13.333
SLIDE_HEIGHT_INCHES = 7.5
SLIDE_WIDTH_EMU = Inches(SLIDE_WIDTH_INCHES)
SLIDE_HEIGHT_EMU = Inches(SLIDE_HEIGHT_INCHES)

# =============================================================================
# UNIT CONVERSIONS
# =============================================================================

EMU_PER_INCH = 914400
EMU_PER_PT = 12700


def inches_to_emu(inches: float) -> int:
    """Convert inches to EMUs. Use this for all position/size calculations."""
    return int(inches * EMU_PER_INCH)


def emu_to_inches(emu: int) -> float:
    """Convert EMUs to inches."""
    return emu / EMU_PER_INCH


def pt_to_emu(pt: float) -> int:
    """Convert points to EMUs (for font sizes, line widths)."""
    return int(pt * EMU_PER_PT)


def emu_to_pt(emu: int) -> float:
    """Convert EMUs to points."""
    return emu / EMU_PER_PT


# =============================================================================
# LAYOUT CONSTANTS (all in inches for readability)
# =============================================================================

# Margins
MARGIN_TOP = 0.8
MARGIN_BOTTOM = 0.5
MARGIN_LEFT = 0.6
MARGIN_RIGHT = 0.6

# Title area
TITLE_HEIGHT = 0.9
SUBTITLE_HEIGHT = 0.4

# Gutters (spacing between elements)
GUTTER_H = 0.25  # Horizontal gutter between blocks
GUTTER_V = 0.2   # Vertical gutter between rows/layers

# Block size constraints
MIN_BLOCK_WIDTH = 1.5
MAX_BLOCK_WIDTH = 3.5
MIN_BLOCK_HEIGHT = 0.7
MAX_BLOCK_HEIGHT = 1.8

# Cross-cutting layer bands
CROSS_CUT_HEIGHT = 0.6

# Connectors
CONNECTOR_MARGIN = 0.1  # Gap between connector endpoint and shape edge
CONNECTOR_STROKE_WIDTH_PT = 1.5

# Text padding inside shapes
TEXT_PADDING_H = 0.15  # Horizontal padding
TEXT_PADDING_V = 0.08  # Vertical padding

# Corner radius for rounded rectangles
DEFAULT_CORNER_RADIUS = 0.08

# =============================================================================
# DERIVED CONTENT AREA
# =============================================================================

CONTENT_LEFT = MARGIN_LEFT
CONTENT_TOP = MARGIN_TOP + TITLE_HEIGHT
CONTENT_WIDTH = SLIDE_WIDTH_INCHES - MARGIN_LEFT - MARGIN_RIGHT
CONTENT_HEIGHT = SLIDE_HEIGHT_INCHES - MARGIN_TOP - TITLE_HEIGHT - MARGIN_BOTTOM

# =============================================================================
# FONT DEFAULTS
# =============================================================================

DEFAULT_FONT_FAMILY = "Calibri"
FALLBACK_FONT_FAMILY = "DejaVu Sans"

TITLE_FONT_SIZE_PT = 28
SUBTITLE_FONT_SIZE_PT = 16
BLOCK_LABEL_FONT_SIZE_PT = 14
BLOCK_LABEL_MIN_FONT_SIZE_PT = 10
BLOCK_LABEL_MAX_FONT_SIZE_PT = 24

# =============================================================================
# COLOR DEFAULTS
# =============================================================================

DEFAULT_BACKGROUND_COLOR = "#FFFFFF"
DEFAULT_TEXT_COLOR = "#333333"
DEFAULT_PRIMARY_COLOR = "#0073E6"
DEFAULT_SECONDARY_COLOR = "#00A3E0"
DEFAULT_ACCENT_COLOR = "#6CC24A"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color string to RGB tuple (0-255)."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB tuple to hex color string."""
    return f"#{r:02x}{g:02x}{b:02x}"
