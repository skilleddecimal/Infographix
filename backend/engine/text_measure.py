"""
text_measure.py — Measure text BEFORE placing it in shapes.

This module solves python-pptx's #1 problem: text overflow.
We use Pillow to pre-measure text and determine:
- Optimal font size to fit within a given width
- Line wrapping for multi-line text
- Total height required

ALWAYS call fit_text_to_width() BEFORE creating any text-containing shape.
Never rely on python-pptx's auto_size — disable it explicitly.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from PIL import ImageFont

from .units import (
    TEXT_PADDING_H,
    DEFAULT_FONT_FAMILY,
    FALLBACK_FONT_FAMILY,
    BLOCK_LABEL_MIN_FONT_SIZE_PT,
    BLOCK_LABEL_MAX_FONT_SIZE_PT,
)

# =============================================================================
# FONT CONFIGURATION
# =============================================================================

# Font directory (relative to this file)
FONT_DIR = Path(__file__).parent.parent / 'fonts'

# Font file mapping
FONT_MAP = {
    'Calibri': 'calibri.ttf',
    'Calibri Bold': 'calibrib.ttf',
    'Arial': 'arial.ttf',
    'Arial Bold': 'arialbd.ttf',
    'Segoe UI': 'segoeui.ttf',
    'DejaVu Sans': 'DejaVuSans.ttf',
    'DejaVu Sans Bold': 'DejaVuSans-Bold.ttf',
}

# Fallback font (always available)
FALLBACK_FONT_FILE = 'DejaVuSans.ttf'

# Cache loaded fonts to avoid repeated disk access
_font_cache: Dict[Tuple[str, int, bool], ImageFont.FreeTypeFont] = {}


# =============================================================================
# FONT LOADING
# =============================================================================

def get_font(family: str, size_pt: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """
    Load a font for measurement. Falls back gracefully if not found.

    Args:
        family: Font family name (e.g., 'Calibri', 'Arial')
        size_pt: Font size in points
        bold: Whether to use bold variant

    Returns:
        PIL ImageFont object ready for measurement
    """
    cache_key = (family, size_pt, bold)
    if cache_key in _font_cache:
        return _font_cache[cache_key]

    # Determine font file
    font_key = f"{family} Bold" if bold else family
    filename = FONT_MAP.get(font_key, FONT_MAP.get(family, FALLBACK_FONT_FILE))
    font_path = FONT_DIR / filename

    # Fall back if not found
    if not font_path.exists():
        font_path = FONT_DIR / FALLBACK_FONT_FILE

    # Final fallback to system fonts
    if not font_path.exists():
        # Try common system font locations
        import platform
        system_fonts = []

        if platform.system() == 'Windows':
            windows_fonts = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
            system_fonts = [
                windows_fonts / 'arial.ttf',
                windows_fonts / 'calibri.ttf',
                windows_fonts / 'segoeui.ttf',
            ]
        else:
            system_fonts = [
                Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
                Path('/usr/share/fonts/TTF/DejaVuSans.ttf'),
            ]

        for sys_font in system_fonts:
            if sys_font.exists():
                font_path = sys_font
                break

    # Try to load the font
    try:
        font = ImageFont.truetype(str(font_path), size_pt)
        _font_cache[cache_key] = font
        return font
    except OSError:
        # Use PIL's default font as last resort
        font = ImageFont.load_default()
        _font_cache[cache_key] = font
        return font


def clear_font_cache():
    """Clear the font cache (useful for testing)."""
    _font_cache.clear()


# =============================================================================
# TEXT MEASUREMENT
# =============================================================================

def measure_text(
    text: str,
    font_family: str,
    font_size_pt: int,
    bold: bool = False
) -> Tuple[float, float]:
    """
    Measure text dimensions using Pillow.

    Args:
        text: Text string to measure
        font_family: Font family name
        font_size_pt: Font size in points
        bold: Whether text is bold

    Returns:
        Tuple of (width_inches, height_inches)
    """
    font = get_font(font_family, font_size_pt, bold)
    bbox = font.getbbox(text)
    width_px = bbox[2] - bbox[0]
    height_px = bbox[3] - bbox[1]

    # Convert pixels to inches (Pillow uses 72 DPI for point-based fonts)
    return (width_px / 72.0, height_px / 72.0)


def measure_text_lines(
    lines: List[str],
    font_family: str,
    font_size_pt: int,
    bold: bool = False,
    line_spacing: float = 1.3
) -> Tuple[float, float]:
    """
    Measure dimensions of multi-line text.

    Args:
        lines: List of text lines
        font_family: Font family name
        font_size_pt: Font size in points
        bold: Whether text is bold
        line_spacing: Line spacing multiplier (1.0 = single, 1.3 = default)

    Returns:
        Tuple of (max_width_inches, total_height_inches)
    """
    if not lines:
        return (0.0, 0.0)

    max_width = 0.0
    total_height = 0.0

    for i, line in enumerate(lines):
        w, h = measure_text(line, font_family, font_size_pt, bold)
        max_width = max(max_width, w)
        if i == 0:
            total_height = h
        else:
            total_height += h * line_spacing

    return (max_width, total_height)


# =============================================================================
# TEXT FITTING
# =============================================================================

@dataclass
class TextFitResult:
    """Result of fit_text_to_width()."""
    font_size: int            # Optimal font size in points
    lines: List[str]          # Text split into lines (ready to render)
    total_height: float       # Total height in inches
    fits: bool                # Whether text fits within constraints


def fit_text_to_width(
    text: str,
    max_width_inches: float,
    font_family: str = DEFAULT_FONT_FAMILY,
    max_font_size: int = BLOCK_LABEL_MAX_FONT_SIZE_PT,
    min_font_size: int = BLOCK_LABEL_MIN_FONT_SIZE_PT,
    bold: bool = False,
    allow_wrap: bool = True,
    max_lines: int = 3
) -> TextFitResult:
    """
    Find the largest font size that fits text within max_width, with optional wrapping.

    This is the CRITICAL function for preventing text overflow.
    Call this BEFORE creating any shape with text.

    Args:
        text: Text to fit
        max_width_inches: Maximum width available (excluding padding)
        font_family: Font family name
        max_font_size: Maximum font size to try
        min_font_size: Minimum acceptable font size
        bold: Whether text is bold
        allow_wrap: Whether to allow word wrapping
        max_lines: Maximum number of lines when wrapping

    Returns:
        TextFitResult with optimal font size, wrapped lines, and total height
    """
    # Account for padding
    available_width = max_width_inches - (2 * TEXT_PADDING_H)

    if not text or not text.strip():
        return TextFitResult(
            font_size=max_font_size,
            lines=[""],
            total_height=0.1,
            fits=True
        )

    text = text.strip()

    # Try each font size from largest to smallest
    for size in range(max_font_size, min_font_size - 1, -1):
        # Try single line first
        w, h = measure_text(text, font_family, size, bold)
        if w <= available_width:
            return TextFitResult(
                font_size=size,
                lines=[text],
                total_height=h + 0.1,  # Add breathing room
                fits=True
            )

        # Try word-wrapping if allowed
        if allow_wrap:
            result = _try_word_wrap(
                text, available_width, font_family, size, bold, max_lines
            )
            if result:
                return result

    # Couldn't fit — return minimum size with truncation
    truncated = text[:30] + '...' if len(text) > 30 else text
    _, h = measure_text(truncated, font_family, min_font_size, bold)

    return TextFitResult(
        font_size=min_font_size,
        lines=[truncated],
        total_height=h + 0.1,
        fits=False
    )


def _try_word_wrap(
    text: str,
    available_width: float,
    font_family: str,
    font_size: int,
    bold: bool,
    max_lines: int
) -> Optional[TextFitResult]:
    """
    Try to wrap text into multiple lines that fit within available_width.

    Returns TextFitResult if successful, None if it doesn't fit.
    """
    words = text.split()
    if len(words) < 2:
        return None

    # Try 2-line split
    if max_lines >= 2 and len(words) >= 2:
        result = _try_split(words, 2, available_width, font_family, font_size, bold)
        if result:
            return result

    # Try 3-line split for very long text at smaller sizes
    if max_lines >= 3 and len(words) >= 3 and font_size <= 14:
        result = _try_split(words, 3, available_width, font_family, font_size, bold)
        if result:
            return result

    return None


def _try_split(
    words: List[str],
    num_lines: int,
    available_width: float,
    font_family: str,
    font_size: int,
    bold: bool
) -> Optional[TextFitResult]:
    """
    Try to split words into num_lines lines that all fit within available_width.
    """
    n = len(words)

    if num_lines == 2:
        # Try each split point for 2 lines
        for i in range(1, n):
            line1 = ' '.join(words[:i])
            line2 = ' '.join(words[i:])
            w1, _ = measure_text(line1, font_family, font_size, bold)
            w2, _ = measure_text(line2, font_family, font_size, bold)
            if w1 <= available_width and w2 <= available_width:
                lines = [line1, line2]
                _, total_h = measure_text_lines(lines, font_family, font_size, bold)
                return TextFitResult(
                    font_size=font_size,
                    lines=lines,
                    total_height=total_h + 0.1,
                    fits=True
                )

    elif num_lines == 3:
        # Split into roughly equal thirds
        third = n // 3
        for i in range(max(1, third - 1), min(n - 1, third + 2)):
            for j in range(max(i + 1, 2 * third - 1), min(n, 2 * third + 2)):
                line1 = ' '.join(words[:i])
                line2 = ' '.join(words[i:j])
                line3 = ' '.join(words[j:])
                w1, _ = measure_text(line1, font_family, font_size, bold)
                w2, _ = measure_text(line2, font_family, font_size, bold)
                w3, _ = measure_text(line3, font_family, font_size, bold)
                if w1 <= available_width and w2 <= available_width and w3 <= available_width:
                    lines = [line1, line2, line3]
                    _, total_h = measure_text_lines(lines, font_family, font_size, bold)
                    return TextFitResult(
                        font_size=font_size,
                        lines=lines,
                        total_height=total_h + 0.1,
                        fits=True
                    )

    return None


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def estimate_block_height(
    text: str,
    block_width: float,
    font_family: str = DEFAULT_FONT_FAMILY,
    bold: bool = False,
    min_height: float = 0.7,
    max_height: float = 1.8
) -> float:
    """
    Estimate the height needed for a block to fit its text.

    Useful for initial layout planning before final text fitting.

    Args:
        text: Text content
        block_width: Width of the block in inches
        font_family: Font family name
        bold: Whether text is bold
        min_height: Minimum block height
        max_height: Maximum block height

    Returns:
        Estimated height in inches
    """
    fit_result = fit_text_to_width(
        text,
        block_width,
        font_family=font_family,
        bold=bold
    )

    # Add padding above and below text
    needed_height = fit_result.total_height + 0.2

    # Clamp to min/max
    return max(min_height, min(max_height, needed_height))
