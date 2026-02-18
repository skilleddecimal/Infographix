"""
grid_layout.py — Grid computation for block layouts.

This module computes positions for blocks in various grid configurations.
All outputs are in INCHES — the renderer converts to EMU/pixels.

Grid layouts support:
- Equal-width columns with gutters
- Row-based layouts with vertical spacing
- Centered single blocks
- Full-width horizontal bands (cross-cutting layers)
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass

from .units import (
    CONTENT_LEFT,
    CONTENT_TOP,
    CONTENT_WIDTH,
    CONTENT_HEIGHT,
    GUTTER_H,
    GUTTER_V,
    MIN_BLOCK_WIDTH,
    MAX_BLOCK_WIDTH,
    MIN_BLOCK_HEIGHT,
    MAX_BLOCK_HEIGHT,
    CROSS_CUT_HEIGHT,
    clamp,
)


# =============================================================================
# GRID COMPUTATION RESULTS
# =============================================================================

@dataclass
class GridCell:
    """A single cell in the grid with its computed position."""
    row: int
    col: int
    x_inches: float
    y_inches: float
    width_inches: float
    height_inches: float

    @property
    def center_x(self) -> float:
        return self.x_inches + self.width_inches / 2

    @property
    def center_y(self) -> float:
        return self.y_inches + self.height_inches / 2


@dataclass
class GridLayout:
    """Result of compute_grid() with all cell positions."""
    cells: List[GridCell]
    num_rows: int
    num_cols: int
    cell_width: float
    cell_height: float
    total_width: float
    total_height: float

    def get_cell(self, row: int, col: int) -> Optional[GridCell]:
        """Get cell at specific row/column."""
        for cell in self.cells:
            if cell.row == row and cell.col == col:
                return cell
        return None

    def get_row(self, row: int) -> List[GridCell]:
        """Get all cells in a specific row."""
        return [c for c in self.cells if c.row == row]

    def get_column(self, col: int) -> List[GridCell]:
        """Get all cells in a specific column."""
        return [c for c in self.cells if c.col == col]


# =============================================================================
# GRID COMPUTATION
# =============================================================================

def compute_grid(
    num_items: int,
    max_cols: int = 5,
    content_left: float = CONTENT_LEFT,
    content_top: float = CONTENT_TOP,
    content_width: float = CONTENT_WIDTH,
    content_height: float = CONTENT_HEIGHT,
    gutter_h: float = GUTTER_H,
    gutter_v: float = GUTTER_V,
    min_block_width: float = MIN_BLOCK_WIDTH,
    max_block_width: float = MAX_BLOCK_WIDTH,
    min_block_height: float = MIN_BLOCK_HEIGHT,
    max_block_height: float = MAX_BLOCK_HEIGHT,
    uniform_height: bool = True
) -> GridLayout:
    """
    Compute a grid layout for N items.

    Automatically determines optimal rows/cols based on item count and constraints.
    Distributes items left-to-right, top-to-bottom.

    Args:
        num_items: Number of items to place in grid
        max_cols: Maximum columns per row
        content_left: Left edge of content area
        content_top: Top edge of content area
        content_width: Available width for grid
        content_height: Available height for grid
        gutter_h: Horizontal spacing between cells
        gutter_v: Vertical spacing between rows
        min_block_width: Minimum cell width
        max_block_width: Maximum cell width
        min_block_height: Minimum cell height
        max_block_height: Maximum cell height
        uniform_height: If True, all rows have same height

    Returns:
        GridLayout with computed cell positions
    """
    if num_items == 0:
        return GridLayout(
            cells=[],
            num_rows=0,
            num_cols=0,
            cell_width=0,
            cell_height=0,
            total_width=0,
            total_height=0
        )

    # Determine optimal column count
    num_cols = _optimal_column_count(num_items, max_cols, content_width, min_block_width, gutter_h)
    num_rows = (num_items + num_cols - 1) // num_cols  # Ceiling division

    # Calculate cell dimensions
    total_gutter_h = gutter_h * (num_cols - 1) if num_cols > 1 else 0
    cell_width = (content_width - total_gutter_h) / num_cols
    cell_width = clamp(cell_width, min_block_width, max_block_width)

    total_gutter_v = gutter_v * (num_rows - 1) if num_rows > 1 else 0
    cell_height = (content_height - total_gutter_v) / num_rows
    cell_height = clamp(cell_height, min_block_height, max_block_height)

    # Generate cells
    cells = []
    for i in range(num_items):
        row = i // num_cols
        col = i % num_cols

        # Calculate position
        x = content_left + col * (cell_width + gutter_h)
        y = content_top + row * (cell_height + gutter_v)

        cells.append(GridCell(
            row=row,
            col=col,
            x_inches=x,
            y_inches=y,
            width_inches=cell_width,
            height_inches=cell_height
        ))

    # Calculate actual grid dimensions
    actual_width = num_cols * cell_width + total_gutter_h
    actual_height = num_rows * cell_height + total_gutter_v

    return GridLayout(
        cells=cells,
        num_rows=num_rows,
        num_cols=num_cols,
        cell_width=cell_width,
        cell_height=cell_height,
        total_width=actual_width,
        total_height=actual_height
    )


def _optimal_column_count(
    num_items: int,
    max_cols: int,
    available_width: float,
    min_block_width: float,
    gutter: float
) -> int:
    """
    Determine optimal number of columns for given item count and constraints.

    Tries to balance aesthetics (not too many/few columns) with space efficiency.
    """
    # Calculate maximum possible columns that fit
    max_possible = 1
    for n in range(1, max_cols + 1):
        total_gutter = gutter * (n - 1) if n > 1 else 0
        cell_width = (available_width - total_gutter) / n
        if cell_width >= min_block_width:
            max_possible = n
        else:
            break

    # Don't use more columns than items
    max_possible = min(max_possible, num_items)

    # Aesthetic preferences for different item counts
    if num_items == 1:
        return 1
    elif num_items == 2:
        return 2
    elif num_items == 3:
        return 3
    elif num_items == 4:
        return 4 if max_possible >= 4 else 2  # 4x1 or 2x2
    elif num_items == 5:
        return min(5, max_possible)  # 5x1 or 3+2
    elif num_items == 6:
        return 3 if max_possible >= 3 else 2  # 3x2
    elif num_items <= 9:
        return 3 if max_possible >= 3 else 2  # 3xN
    else:
        return min(4, max_possible)  # 4xN for larger grids


# =============================================================================
# CENTERED BLOCK
# =============================================================================

def compute_centered_block(
    width: float,
    height: float,
    content_left: float = CONTENT_LEFT,
    content_top: float = CONTENT_TOP,
    content_width: float = CONTENT_WIDTH,
    content_height: float = CONTENT_HEIGHT
) -> Tuple[float, float]:
    """
    Compute position to center a block in the content area.

    Args:
        width: Block width in inches
        height: Block height in inches
        content_left: Left edge of content area
        content_top: Top edge of content area
        content_width: Content area width
        content_height: Content area height

    Returns:
        Tuple of (x_inches, y_inches) for top-left corner
    """
    x = content_left + (content_width - width) / 2
    y = content_top + (content_height - height) / 2
    return (x, y)


def compute_centered_row(
    num_items: int,
    item_width: float,
    item_height: float,
    gutter: float = GUTTER_H,
    content_left: float = CONTENT_LEFT,
    content_top: float = CONTENT_TOP,
    content_width: float = CONTENT_WIDTH,
    content_height: float = CONTENT_HEIGHT,
    vertical_position: str = "center"
) -> List[Tuple[float, float]]:
    """
    Compute positions for a centered row of items.

    Args:
        num_items: Number of items in row
        item_width: Width of each item
        item_height: Height of each item
        gutter: Spacing between items
        content_left: Left edge of content area
        content_top: Top edge of content area
        content_width: Content area width
        content_height: Content area height
        vertical_position: "top", "center", or "bottom"

    Returns:
        List of (x, y) tuples for each item's top-left corner
    """
    if num_items == 0:
        return []

    total_width = num_items * item_width + (num_items - 1) * gutter
    start_x = content_left + (content_width - total_width) / 2

    # Vertical positioning
    if vertical_position == "top":
        y = content_top
    elif vertical_position == "bottom":
        y = content_top + content_height - item_height
    else:  # center
        y = content_top + (content_height - item_height) / 2

    positions = []
    for i in range(num_items):
        x = start_x + i * (item_width + gutter)
        positions.append((x, y))

    return positions


# =============================================================================
# FULL-WIDTH BANDS (Cross-Cutting Layers)
# =============================================================================

def compute_full_width_band(
    y_position: float,
    height: float = CROSS_CUT_HEIGHT,
    content_left: float = CONTENT_LEFT,
    content_width: float = CONTENT_WIDTH
) -> Tuple[float, float, float, float]:
    """
    Compute position for a full-width horizontal band.

    Used for cross-cutting layers (e.g., "Security", "Monitoring" bands).

    Args:
        y_position: Vertical position (top edge) in inches
        height: Band height in inches
        content_left: Left edge of content area
        content_width: Content area width

    Returns:
        Tuple of (x, y, width, height)
    """
    return (content_left, y_position, content_width, height)


def compute_stacked_bands(
    num_bands: int,
    content_top: float = CONTENT_TOP,
    content_height: float = CONTENT_HEIGHT,
    content_left: float = CONTENT_LEFT,
    content_width: float = CONTENT_WIDTH,
    gutter: float = GUTTER_V,
    band_height: Optional[float] = None
) -> List[Tuple[float, float, float, float]]:
    """
    Compute positions for vertically stacked full-width bands.

    Args:
        num_bands: Number of bands to stack
        content_top: Top of content area
        content_height: Height of content area
        content_left: Left edge
        content_width: Content width
        gutter: Vertical spacing between bands
        band_height: Fixed band height (None = auto-calculate to fill space)

    Returns:
        List of (x, y, width, height) tuples for each band
    """
    if num_bands == 0:
        return []

    total_gutter = gutter * (num_bands - 1) if num_bands > 1 else 0

    if band_height is None:
        # Auto-calculate to fill available space
        band_height = (content_height - total_gutter) / num_bands

    bands = []
    for i in range(num_bands):
        y = content_top + i * (band_height + gutter)
        bands.append((content_left, y, content_width, band_height))

    return bands


# =============================================================================
# LAYERED LAYOUT (Rows with Different Configs)
# =============================================================================

@dataclass
class RowConfig:
    """Configuration for a single row in a layered layout."""
    num_items: int
    height: Optional[float] = None  # None = auto
    is_band: bool = False  # True for full-width bands


def compute_layered_layout(
    row_configs: List[RowConfig],
    content_left: float = CONTENT_LEFT,
    content_top: float = CONTENT_TOP,
    content_width: float = CONTENT_WIDTH,
    content_height: float = CONTENT_HEIGHT,
    gutter_h: float = GUTTER_H,
    gutter_v: float = GUTTER_V
) -> List[List[Tuple[float, float, float, float]]]:
    """
    Compute positions for a multi-row layout with varying items per row.

    Useful for "pyramid" or irregular layouts like:
    - Row 0: 1 item (title/hero)
    - Row 1: 3 items (main features)
    - Row 2: full-width band (cross-cutting)
    - Row 3: 4 items (secondary features)

    Args:
        row_configs: List of RowConfig for each row
        content_left: Left edge of content area
        content_top: Top edge of content area
        content_width: Content area width
        content_height: Content area height
        gutter_h: Horizontal spacing within rows
        gutter_v: Vertical spacing between rows

    Returns:
        List of rows, each row is a list of (x, y, width, height) tuples
    """
    if not row_configs:
        return []

    num_rows = len(row_configs)
    total_gutter_v = gutter_v * (num_rows - 1) if num_rows > 1 else 0

    # Calculate heights for rows without explicit height
    fixed_height_total = sum(rc.height or 0 for rc in row_configs)
    auto_height_count = sum(1 for rc in row_configs if rc.height is None)

    if auto_height_count > 0:
        auto_height = (content_height - total_gutter_v - fixed_height_total) / auto_height_count
        auto_height = max(0.5, auto_height)  # Minimum height
    else:
        auto_height = 0

    # Build layout
    result = []
    current_y = content_top

    for rc in row_configs:
        row_height = rc.height if rc.height is not None else auto_height
        row_items = []

        if rc.is_band:
            # Full-width band
            row_items.append((content_left, current_y, content_width, row_height))
        else:
            # Regular row with multiple items
            if rc.num_items > 0:
                total_gutter_h = gutter_h * (rc.num_items - 1) if rc.num_items > 1 else 0
                item_width = (content_width - total_gutter_h) / rc.num_items

                for i in range(rc.num_items):
                    x = content_left + i * (item_width + gutter_h)
                    row_items.append((x, current_y, item_width, row_height))

        result.append(row_items)
        current_y += row_height + gutter_v

    return result
