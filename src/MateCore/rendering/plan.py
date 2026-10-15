"""Pure conversion of result groups into a render plan (no FreeCAD imports)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .style import Color, RenderStyle, brighten


@dataclass(frozen=True, slots=True)
class GroupPlan:
    index: int  # 1-based
    color: Color
    surfaces: tuple[Any, ...]  # SurfaceRef-like
    part_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RenderPlan:
    style: RenderStyle
    groups: tuple[GroupPlan, ...]
    part_owners: tuple[Any, ...]  # unique owning objects to render transparent


def build_render_plan(groups: Sequence[Sequence[Any]], style: RenderStyle) -> RenderPlan:
    seen_faces: set[tuple[str, str]] = set()
    owners: dict[str, Any] = {}
    planned: list[GroupPlan] = []
    highlight = brighten(style.highlight_color, style.surface_brightness)
    for number, group in enumerate(groups, start=1):
        color = highlight
        surfaces: list[Any] = []
        names: list[str] = []
        for surface in group:
            owners.setdefault(surface.object_name, surface.owner)
            if surface.object_label not in names:
                names.append(surface.object_label)
            key = (surface.object_name, surface.face_name)
            if key not in seen_faces:
                seen_faces.add(key)
                surfaces.append(surface)
        planned.append(GroupPlan(number, color, tuple(surfaces), tuple(names)))
    return RenderPlan(style, tuple(planned), tuple(owners.values()))


def color_name(color: Color) -> str:
    return "#%02x%02x%02x" % tuple(round(c * 255) for c in color)


def legend_lines(plan: RenderPlan) -> list[str]:
    return [
        f"  Group {g.index} [{color_name(g.color)}] on {', '.join(g.part_names)}"
        for g in plan.groups
    ]
