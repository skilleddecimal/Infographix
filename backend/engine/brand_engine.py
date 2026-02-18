"""
brand_engine.py — Color management and brand presets.

Provides:
- Color extraction from logo images using k-means clustering
- Palette generation from a primary color
- Pre-defined brand color palettes

Dependencies: Pillow, scikit-learn (for k-means)
"""

import colorsys
from typing import List, Optional, Tuple
from io import BytesIO

from PIL import Image
import numpy as np

from .data_models import ColorPalette


# =============================================================================
# BRAND PRESETS
# =============================================================================

BRAND_PRESETS = {
    "microsoft": ColorPalette(
        primary="#0078D4",
        secondary="#50E6FF",
        tertiary="#00A4EF",
        quaternary="#FFB900",
        background="#FFFFFF",
        text_dark="#333333",
        text_light="#FFFFFF",
        border="#CCCCCC",
        connector="#666666",
    ),
    "google": ColorPalette(
        primary="#4285F4",
        secondary="#EA4335",
        tertiary="#FBBC05",
        quaternary="#34A853",
        background="#FFFFFF",
        text_dark="#202124",
        text_light="#FFFFFF",
        border="#DADCE0",
        connector="#5F6368",
    ),
    "opentext": ColorPalette(
        primary="#1B365D",
        secondary="#00A3E0",
        tertiary="#6CC24A",
        quaternary="#FFB81C",
        background="#FFFFFF",
        text_dark="#333333",
        text_light="#FFFFFF",
        border="#CCCCCC",
        connector="#666666",
    ),
    "aws": ColorPalette(
        primary="#FF9900",
        secondary="#232F3E",
        tertiary="#146EB4",
        quaternary="#1B660F",
        background="#FFFFFF",
        text_dark="#232F3E",
        text_light="#FFFFFF",
        border="#CCCCCC",
        connector="#666666",
    ),
    "azure": ColorPalette(
        primary="#0078D4",
        secondary="#50E6FF",
        tertiary="#00BCF2",
        quaternary="#7719AA",
        background="#FFFFFF",
        text_dark="#333333",
        text_light="#FFFFFF",
        border="#CCCCCC",
        connector="#666666",
    ),
    "gcp": ColorPalette(
        primary="#4285F4",
        secondary="#DB4437",
        tertiary="#F4B400",
        quaternary="#0F9D58",
        background="#FFFFFF",
        text_dark="#202124",
        text_light="#FFFFFF",
        border="#DADCE0",
        connector="#5F6368",
    ),
    "salesforce": ColorPalette(
        primary="#00A1E0",
        secondary="#1798C1",
        tertiary="#032D60",
        quaternary="#FF6D00",
        background="#FFFFFF",
        text_dark="#333333",
        text_light="#FFFFFF",
        border="#CCCCCC",
        connector="#666666",
    ),
    "slack": ColorPalette(
        primary="#4A154B",
        secondary="#36C5F0",
        tertiary="#2EB67D",
        quaternary="#ECB22E",
        background="#FFFFFF",
        text_dark="#1D1C1D",
        text_light="#FFFFFF",
        border="#CCCCCC",
        connector="#666666",
    ),
    "github": ColorPalette(
        primary="#24292E",
        secondary="#0366D6",
        tertiary="#28A745",
        quaternary="#6F42C1",
        background="#FFFFFF",
        text_dark="#24292E",
        text_light="#FFFFFF",
        border="#E1E4E8",
        connector="#586069",
    ),
    "stripe": ColorPalette(
        primary="#635BFF",
        secondary="#00D4FF",
        tertiary="#80E9FF",
        quaternary="#FF80B4",
        background="#FFFFFF",
        text_dark="#0A2540",
        text_light="#FFFFFF",
        border="#E3E8EF",
        connector="#6B7C93",
    ),
}


# =============================================================================
# COLOR UTILITIES
# =============================================================================

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to hex color string."""
    return f"#{r:02X}{g:02X}{b:02X}"


def hex_to_hsl(hex_color: str) -> Tuple[float, float, float]:
    """Convert hex color to HSL (hue, saturation, lightness)."""
    r, g, b = hex_to_rgb(hex_color)
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s, l


def hsl_to_hex(h: float, s: float, l: float) -> str:
    """Convert HSL to hex color string."""
    h = h / 360.0  # Normalize hue to 0-1
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return rgb_to_hex(int(r * 255), int(g * 255), int(b * 255))


def get_luminance(hex_color: str) -> float:
    """Calculate relative luminance of a color (0-1)."""
    r, g, b = hex_to_rgb(hex_color)

    def linearize(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def get_contrast_text_color(bg_color: str) -> str:
    """Return black or white text color based on background luminance."""
    luminance = get_luminance(bg_color)
    return "#FFFFFF" if luminance < 0.5 else "#333333"


# =============================================================================
# BRAND PRESET LOOKUP
# =============================================================================

def get_brand_preset(brand_name: str) -> Optional[ColorPalette]:
    """
    Look up a brand color palette by name.

    Args:
        brand_name: Case-insensitive brand name

    Returns:
        ColorPalette if found, None otherwise
    """
    return BRAND_PRESETS.get(brand_name.lower())


def list_brand_presets() -> List[str]:
    """Return list of available brand preset names."""
    return list(BRAND_PRESETS.keys())


# =============================================================================
# COLOR EXTRACTION FROM LOGOS
# =============================================================================

def extract_colors_from_logo(image_bytes: bytes, k: int = 5) -> List[str]:
    """
    Extract dominant colors from a logo image using k-means clustering.

    Args:
        image_bytes: Raw image bytes (PNG, JPG, etc.)
        k: Number of colors to extract (default 5)

    Returns:
        List of hex color strings, sorted by dominance
    """
    try:
        from sklearn.cluster import KMeans
    except ImportError:
        raise ImportError(
            "scikit-learn is required for color extraction. "
            "Install with: pip install scikit-learn"
        )

    # Load image
    image = Image.open(BytesIO(image_bytes))

    # Convert to RGB if necessary
    if image.mode != 'RGB':
        # Handle RGBA by compositing on white background
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        else:
            image = image.convert('RGB')

    # Resize for faster processing (max 200px on longest side)
    max_size = 200
    ratio = max_size / max(image.size)
    if ratio < 1:
        new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    # Convert to numpy array
    pixels = np.array(image)
    pixels = pixels.reshape(-1, 3)

    # Filter out near-white and near-black pixels
    mask = ~(
        ((pixels[:, 0] > 240) & (pixels[:, 1] > 240) & (pixels[:, 2] > 240)) |
        ((pixels[:, 0] < 15) & (pixels[:, 1] < 15) & (pixels[:, 2] < 15))
    )
    filtered_pixels = pixels[mask]

    # If too few pixels remain, use original
    if len(filtered_pixels) < k * 10:
        filtered_pixels = pixels

    # Run k-means clustering
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(filtered_pixels)

    # Get cluster centers and their counts
    centers = kmeans.cluster_centers_
    labels = kmeans.labels_

    # Sort by cluster size (most dominant first)
    unique, counts = np.unique(labels, return_counts=True)
    sorted_indices = np.argsort(-counts)

    # Convert to hex colors
    colors = []
    for idx in sorted_indices:
        r, g, b = centers[idx].astype(int)
        colors.append(rgb_to_hex(r, g, b))

    return colors


def create_palette_from_extracted_colors(colors: List[str]) -> ColorPalette:
    """
    Create a ColorPalette from extracted logo colors.

    Args:
        colors: List of hex colors (at least 1, ideally 4+)

    Returns:
        ColorPalette with colors assigned to appropriate roles
    """
    if not colors:
        return ColorPalette()

    # Ensure we have enough colors by cycling if needed
    while len(colors) < 4:
        colors = colors + colors

    # Use first 4 colors as primary, secondary, etc.
    return ColorPalette(
        primary=colors[0],
        secondary=colors[1],
        tertiary=colors[2],
        quaternary=colors[3],
        background="#FFFFFF",
        text_dark="#333333",
        text_light="#FFFFFF",
        border="#CCCCCC",
        connector=colors[0] if len(colors) > 0 else "#666666",
    )


# =============================================================================
# PALETTE GENERATION FROM PRIMARY COLOR
# =============================================================================

def generate_palette_from_primary(primary_hex: str) -> ColorPalette:
    """
    Generate a complete color palette from a primary color.

    Uses color theory to create complementary, analogous, and triadic colors.

    Args:
        primary_hex: Primary brand color in hex format

    Returns:
        Complete ColorPalette
    """
    h, s, l = hex_to_hsl(primary_hex)

    # Secondary: analogous (30 degrees offset)
    secondary_h = (h + 30) % 360
    secondary = hsl_to_hex(secondary_h, s, l)

    # Tertiary: analogous other direction
    tertiary_h = (h + 210) % 360  # Complementary-ish
    tertiary = hsl_to_hex(tertiary_h, min(s, 0.7), min(l + 0.1, 0.6))

    # Quaternary: triadic
    quaternary_h = (h + 120) % 360
    quaternary = hsl_to_hex(quaternary_h, min(s, 0.8), min(l + 0.15, 0.55))

    # Connector: desaturated version of primary
    connector = hsl_to_hex(h, s * 0.3, 0.4)

    return ColorPalette(
        primary=primary_hex,
        secondary=secondary,
        tertiary=tertiary,
        quaternary=quaternary,
        background="#FFFFFF",
        text_dark="#333333",
        text_light="#FFFFFF",
        border="#CCCCCC",
        connector=connector,
    )


def generate_monochromatic_palette(primary_hex: str) -> ColorPalette:
    """
    Generate a monochromatic palette (variations of one hue).

    Args:
        primary_hex: Primary brand color in hex format

    Returns:
        ColorPalette with varying lightness of the same hue
    """
    h, s, l = hex_to_hsl(primary_hex)

    # Lighter and darker variants
    secondary = hsl_to_hex(h, s, min(l + 0.2, 0.85))
    tertiary = hsl_to_hex(h, s, max(l - 0.15, 0.25))
    quaternary = hsl_to_hex(h, s * 0.7, min(l + 0.35, 0.9))

    return ColorPalette(
        primary=primary_hex,
        secondary=secondary,
        tertiary=tertiary,
        quaternary=quaternary,
        background="#FFFFFF",
        text_dark="#333333",
        text_light="#FFFFFF",
        border="#CCCCCC",
        connector=hsl_to_hex(h, s * 0.3, 0.4),
    )


def generate_complementary_palette(primary_hex: str) -> ColorPalette:
    """
    Generate a complementary color palette (opposite colors on color wheel).

    Args:
        primary_hex: Primary brand color in hex format

    Returns:
        ColorPalette with complementary colors
    """
    h, s, l = hex_to_hsl(primary_hex)

    # Complementary: 180 degrees opposite
    comp_h = (h + 180) % 360
    secondary = hsl_to_hex(comp_h, s, l)

    # Split complementary
    tertiary = hsl_to_hex((comp_h + 30) % 360, s * 0.8, min(l + 0.1, 0.6))
    quaternary = hsl_to_hex((comp_h - 30) % 360, s * 0.8, min(l + 0.1, 0.6))

    return ColorPalette(
        primary=primary_hex,
        secondary=secondary,
        tertiary=tertiary,
        quaternary=quaternary,
        background="#FFFFFF",
        text_dark="#333333",
        text_light="#FFFFFF",
        border="#CCCCCC",
        connector=hsl_to_hex(h, s * 0.3, 0.4),
    )


# =============================================================================
# PALETTE VALIDATION
# =============================================================================

def validate_palette_contrast(palette: ColorPalette) -> List[str]:
    """
    Validate that palette colors have sufficient contrast for accessibility.

    Returns list of warnings for low-contrast combinations.
    """
    warnings = []

    # Check text on background
    text_lum = get_luminance(palette.text_dark)
    bg_lum = get_luminance(palette.background)

    # WCAG AA requires 4.5:1 ratio for normal text
    ratio = (max(text_lum, bg_lum) + 0.05) / (min(text_lum, bg_lum) + 0.05)
    if ratio < 4.5:
        warnings.append(f"Low contrast between text_dark and background: {ratio:.2f}:1")

    # Check primary colors for sufficient distinction
    colors = [palette.primary, palette.secondary, palette.tertiary, palette.quaternary]
    for i, c1 in enumerate(colors):
        for c2 in colors[i+1:]:
            # Simple hue difference check
            h1, _, _ = hex_to_hsl(c1)
            h2, _, _ = hex_to_hsl(c2)
            hue_diff = min(abs(h1 - h2), 360 - abs(h1 - h2))
            if hue_diff < 20:
                warnings.append(f"Colors {c1} and {c2} may be too similar (hue diff: {hue_diff:.0f}°)")

    return warnings
