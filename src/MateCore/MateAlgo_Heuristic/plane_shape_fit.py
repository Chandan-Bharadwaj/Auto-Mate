"""Plane-only size and in-plane aspect similarity for heuristic mating."""

from __future__ import annotations

from MateCore.MateGraph.model import AAGNode, PLANE
from MateCore.MateGraph.search.pattern import PatternSlot

PLANE_SHAPE_MISMATCH = "plane_shape_mismatch"


def plane_shape_raw(slot: PatternSlot, node: AAGNode) -> float:
    if slot.surface_kind != PLANE or node.surface_kind != PLANE:
        return 1.0
    area_ratio = 1.0
    if slot.area > 0.0 and node.area > 0.0:
        area_ratio = min(slot.area, node.area) / max(slot.area, node.area)
    aspect_ratio = 1.0
    sa, na = float(slot.plane_aspect), float(node.plane_aspect)
    if sa > 1.0 and na > 1.0:
        aspect_ratio = min(sa, na) / max(sa, na)
    return area_ratio * aspect_ratio


def explain_plane_shape_rejection(
    slot: PatternSlot,
    node: AAGNode,
    *,
    reject_floor: float,
) -> str | None:
    if slot.surface_kind != PLANE:
        return None
    raw = plane_shape_raw(slot, node)
    if raw < reject_floor:
        return PLANE_SHAPE_MISMATCH
    return None


def apply_plane_shape_penalty(
    sim: float,
    raw: float,
    *,
    exponent: float,
    reject_floor: float,
) -> float | None:
    if raw < reject_floor:
        return None
    factor = raw ** exponent
    return sim * factor
