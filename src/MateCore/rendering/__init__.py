"""Host-independent render planning (no FreeCAD imports)."""

from .plan import GroupPlan, RenderPlan, build_render_plan, legend_lines
from .style import DEFAULT_STYLE, RenderStyle, brighten, style_from_mapping

__all__ = [
    "DEFAULT_STYLE",
    "GroupPlan",
    "RenderPlan",
    "RenderStyle",
    "brighten",
    "build_render_plan",
    "legend_lines",
    "style_from_mapping",
]
