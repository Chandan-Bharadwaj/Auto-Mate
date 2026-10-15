"""FreeCAD result rendering."""

from MateCore.rendering import RenderStyle, build_render_plan, legend_lines

from .preferences import load_style
from .renderer import FreeCADResultRenderer, ResultRenderer

__all__ = [
    "FreeCADResultRenderer",
    "RenderStyle",
    "ResultRenderer",
    "build_render_plan",
    "legend_lines",
    "load_style",
]
