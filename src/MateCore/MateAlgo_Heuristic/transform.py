"""Complement pattern geometry for mating-aligned graph search."""

from __future__ import annotations

from MateCore.MateGraph.model import PLANE as GRAPH_PLANE
from MateCore.MateGraph.search.pattern import GraphPattern, PatternSlot


def _complement_slot(slot: PatternSlot) -> PatternSlot:
    meta = dict(slot.metadata)
    meta.setdefault("source_node_id", slot.source_node_id)
    meta["original_convex"] = slot.convex
    axis = slot.axis
    convex = slot.convex
    if slot.surface_kind == GRAPH_PLANE:
        axis = -axis
    elif slot.surface_kind in ("cylinder", "cone"):
        convex = not convex
    return PatternSlot(
        slot_id=slot.slot_id,
        source_node_id=slot.source_node_id,
        surface_kind=slot.surface_kind,
        origin=slot.origin,
        axis=axis,
        area=slot.area,
        radius=slot.radius,
        semi_angle=slot.semi_angle,
        convex=convex,
        member_ids=slot.member_ids,
        metadata=meta,
    )


def mating_search_pattern(reference: GraphPattern) -> GraphPattern:
    """Build complemented pattern used as the search template."""
    return reference.map_slots(_complement_slot)
