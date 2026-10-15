"""PatternSlot / graph node helpers for fit and pose."""

from __future__ import annotations

from MateCore.MateFit.descriptors import CONE, CYLINDER, PLANE, FaceDescriptor
from MateCore.MateGraph.node_adapter import node_to_face_descriptor
from MateCore.MateGraph.model import AAGNode, PLANE as GRAPH_PLANE
from MateCore.MateGraph.search.pattern import PatternSlot

_KIND_MAP = {
    GRAPH_PLANE: PLANE,
    "cylinder": CYLINDER,
    "cone": CONE,
}


def slot_to_face_descriptor(slot: PatternSlot, part_id: str) -> FaceDescriptor | None:
    kind = _KIND_MAP.get(slot.surface_kind)
    if kind is None:
        return None
    if kind == CONE and slot.semi_angle <= 0.0:
        return None
    return FaceDescriptor(
        id=slot.source_node_id,
        part_id=part_id,
        kind=kind,
        origin=slot.origin,
        axis=slot.axis,
        radius=slot.radius,
        semi_angle=slot.semi_angle,
        convex=slot.convex,
        area=slot.area,
    )


def node_to_descriptor(node: AAGNode) -> FaceDescriptor | None:
    return node_to_face_descriptor(node)
