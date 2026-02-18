"""
data_models.py — Shared data models used by both engine and archetypes.

This module contains dataclasses that are shared across the system
to avoid circular imports between engine and archetypes modules.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from .positioned import ConnectorStyle


# =============================================================================
# COLOR PALETTE
# =============================================================================

@dataclass
class ColorPalette:
    """Color scheme for diagram elements."""
    primary: str = "#0073E6"       # Main accent color
    secondary: str = "#00A3E0"     # Secondary accent
    tertiary: str = "#6CC24A"      # Third accent
    quaternary: str = "#FFB81C"    # Fourth accent
    background: str = "#FFFFFF"    # Slide background
    text_dark: str = "#333333"     # Dark text
    text_light: str = "#FFFFFF"    # Light text (on dark backgrounds)
    border: str = "#CCCCCC"        # Border color
    connector: str = "#666666"     # Connector line color

    def get_color_for_index(self, index: int) -> str:
        """Get color for element at given index (cycles through palette)."""
        colors = [self.primary, self.secondary, self.tertiary, self.quaternary]
        return colors[index % len(colors)]


# =============================================================================
# INPUT DATA MODELS
# =============================================================================

@dataclass
class BlockData:
    """Input data for a single block/entity."""
    id: str
    label: str
    description: Optional[str] = None
    color: Optional[str] = None  # Override palette color
    icon: Optional[str] = None   # Icon identifier
    layer_id: Optional[str] = None  # Which layer this belongs to
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectorData:
    """Input data for a connector between blocks."""
    from_id: str
    to_id: str
    label: Optional[str] = None
    style: ConnectorStyle = ConnectorStyle.ARROW
    color: Optional[str] = None  # Override palette color


@dataclass
class LayerData:
    """Input data for a layer/grouping."""
    id: str
    label: str
    blocks: List[str] = field(default_factory=list)  # List of block IDs in this layer
    color: Optional[str] = None
    is_cross_cutting: bool = False  # If True, renders as full-width band


@dataclass
class DiagramInput:
    """
    Complete input for diagram generation.

    This is the normalized input that archetypes consume.
    AI parsing produces this structure from natural language.
    """
    title: str
    subtitle: Optional[str] = None
    blocks: List[BlockData] = field(default_factory=list)
    connectors: List[ConnectorData] = field(default_factory=list)
    layers: List[LayerData] = field(default_factory=list)
    palette: Optional[ColorPalette] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
