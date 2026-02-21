"""PPTX Renderer module - generates PowerPoint files from DSL scene graph.

Renders DSL scene graphs to pixel-perfect PPTX files including:
- Auto shapes with proper MSO mapping
- Freeform paths with Bezier curve support
- Text boxes with formatting
- Images and groups
- Fill styles (solid, gradient)
- Stroke styles (color, width, dash)
- Effects (shadow, glow, reflection, bevel, soft edges)
- Transform properties (rotation, flip_h, flip_v)
"""

from backend.renderer.path_renderer import PathRenderer
from backend.renderer.pptx_writer import PPTXWriter
from backend.renderer.shape_renderer import ShapeRenderer
from backend.renderer.style_renderer import StyleRenderer
from backend.renderer.text_renderer import TextRenderer

__all__ = [
    "PathRenderer",
    "PPTXWriter",
    "ShapeRenderer",
    "StyleRenderer",
    "TextRenderer",
]
