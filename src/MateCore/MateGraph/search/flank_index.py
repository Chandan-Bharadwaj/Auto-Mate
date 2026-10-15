"""Flanked-face topology: hub between two opposing parallel neighbors."""

from __future__ import annotations

import itertools

import numpy as np

from ..model import AAGNode
from .pattern import GraphPattern, PatternSlot

PLANE = "plane"
FLANK_ROLE_HUB = "hub"
FLANK_ROLE_FLANK = "flank"
SLOT_ORDER_FLANK = 0
SLOT_ORDER_HUB = 1
SLOT_ORDER_DEFAULT = 2


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n < 1e-12:
        return v
    return v / n


def parallel_plane_span_slots(
    a: PatternSlot, b: PatternSlot, angle_tol: float
) -> float | None:
    if a.surface_kind != PLANE or b.surface_kind != PLANE:
        return None
    na = _unit(a.axis)
    nb = _unit(b.axis)
    if float(np.dot(na, nb)) > -float(np.cos(angle_tol)):
        return None
    return abs(float(np.dot(na, b.origin - a.origin)))


def parallel_plane_span_nodes(
    a: AAGNode, b: AAGNode, angle_tol: float
) -> float | None:
    if a.surface_kind != PLANE or b.surface_kind != PLANE:
        return None
    na = _unit(a.axis)
    nb = _unit(b.axis)
    if float(np.dot(na, nb)) > -float(np.cos(angle_tol)):
        return None
    return abs(float(np.dot(na, b.origin - a.origin)))


def _hub_between_flanks(
    center: PatternSlot,
    flank_a: PatternSlot,
    flank_b: PatternSlot,
    angle_tol: float,
) -> bool:
    if center.surface_kind != PLANE:
        return False
    sin_tol = float(np.sin(angle_tol))
    for fa, fb in ((flank_a, flank_b), (flank_b, flank_a)):
        if fa.surface_kind != PLANE or fb.surface_kind != PLANE:
            return False
        na, nb = _unit(fa.axis), _unit(fb.axis)
        if float(np.dot(na, nb)) > -float(np.cos(angle_tol)):
            return False
        nc = _unit(center.axis)
        if abs(float(np.dot(nc, na))) > sin_tol:
            return False
        if parallel_plane_span_slots(fa, fb, angle_tol) is None:
            return False
    return True


def annotate_flank_topology(
    pattern: GraphPattern,
    *,
    angle_tol: float = 0.1,
    hub_node_weight: float = 2.0,
    flank_node_weight: float = 1.0,
) -> GraphPattern:
    """Tag slots sandwiched between opposing parallel plane neighbors."""
    hub_meta: dict[str, dict] = {}
    flank_slots: set[str] = set()

    for center_id in (s.slot_id for s in pattern.slots):
        center = pattern.slot(center_id)
        if center is None:
            continue
        neighbor_ids = list(pattern.neighbors(center_id))
        best: tuple[float, str, str] | None = None
        for id_a, id_b in itertools.combinations(neighbor_ids, 2):
            slot_a = pattern.slot(id_a)
            slot_b = pattern.slot(id_b)
            if slot_a is None or slot_b is None:
                continue
            if not _hub_between_flanks(center, slot_a, slot_b, angle_tol):
                continue
            na, nb = _unit(slot_a.axis), _unit(slot_b.axis)
            score = -float(np.dot(na, nb))
            if best is None or score > best[0]:
                best = (score, id_a, id_b)
        if best is None:
            continue
        _, id_a, id_b = best
        if id_a > id_b:
            id_a, id_b = id_b, id_a
        slot_a = pattern.slot(id_a)
        slot_b = pattern.slot(id_b)
        assert slot_a is not None and slot_b is not None
        span = parallel_plane_span_slots(slot_a, slot_b, angle_tol)
        if span is None:
            continue
        hub_meta[center_id] = {
            "flank_role": FLANK_ROLE_HUB,
            "flank_slot_ids": (id_a, id_b),
            "flank_span": span,
            "node_weight": hub_node_weight,
            "slot_order_group": SLOT_ORDER_HUB,
            "search_priority": 2,
        }
        flank_slots.update((id_a, id_b))

    def transform(slot: PatternSlot) -> PatternSlot:
        meta = dict(slot.metadata)
        if slot.slot_id in hub_meta:
            meta.update(hub_meta[slot.slot_id])
        elif slot.slot_id in flank_slots:
            meta.setdefault("flank_role", FLANK_ROLE_FLANK)
            meta.setdefault("node_weight", flank_node_weight)
            meta.setdefault("slot_order_group", SLOT_ORDER_FLANK)
            meta.setdefault("search_priority", 1)
        else:
            meta.setdefault("node_weight", 1.0)
            meta.setdefault("slot_order_group", SLOT_ORDER_DEFAULT)
            meta.setdefault("search_priority", 0)
        return PatternSlot(
            slot_id=slot.slot_id,
            source_node_id=slot.source_node_id,
            surface_kind=slot.surface_kind,
            origin=slot.origin,
            axis=slot.axis,
            area=slot.area,
            radius=slot.radius,
            semi_angle=slot.semi_angle,
            convex=slot.convex,
            plane_aspect=slot.plane_aspect,
            member_ids=slot.member_ids,
            metadata=meta,
        )

    return pattern.map_slots(transform)


def slot_node_weight_from_metadata(slot: PatternSlot) -> float:
    w = slot.metadata.get("node_weight")
    if w is None:
        return 1.0
    return float(w)
