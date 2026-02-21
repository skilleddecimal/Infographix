"""PPTX Parser module - extracts DSL scene graph from PowerPoint files.

This module provides complete extraction of PowerPoint content into a
structured DSL format including:
- Shapes with bounding boxes and transformations (flip, rotation)
- Freeform shapes with Bezier path commands
- Fill styles (solid, gradient, pattern)
- Stroke/line styles
- Effects (shadow, glow, reflection, bevel, soft edges)
- Text content with formatting and alignment
- Theme colors from slide masters
"""

from backend.parser.path_parser import PathParser
from backend.parser.pptx_reader import PPTXReader
from backend.parser.shape_extractor import ShapeExtractor
from backend.parser.style_extractor import StyleExtractor
from backend.parser.theme_parser import ThemeParser
from backend.parser.transform_parser import TransformParser

__all__ = [
    "PathParser",
    "PPTXReader",
    "ShapeExtractor",
    "StyleExtractor",
    "ThemeParser",
    "TransformParser",
]
