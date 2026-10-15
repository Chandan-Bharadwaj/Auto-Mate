"""Pattern slot constraint ordering for search."""

from __future__ import annotations

import numpy as np

from .pattern import GraphPattern


def independent_neighbor_count(pattern: GraphPattern, slot_id: str, angle_tol: float = 0.1) -> int:
    slot = pattern.slot(slot_id)
    if slot is None:
        return 0
    count = 0
    for nid in pattern.neighbors(slot_id):
        neighbor = pattern.slot(nid)
        if neighbor is None:
            continue
        if neighbor.surface_kind != "plane" or slot.surface_kind != "plane":
            count += 1
            continue
        dot = abs(float(np.dot(slot.axis, neighbor.axis)))
        if dot < np.cos(angle_tol):
            count += 1
    return count


def slot_constraint_key(
    pattern: GraphPattern, slot_id: str, angle_tol: float = 0.1
) -> tuple[int, float, str]:
    slot = pattern.slot(slot_id)
    area = slot.area if slot is not None else 0.0
    rank = independent_neighbor_count(pattern, slot_id, angle_tol) + pattern.degree(slot_id)
    return (-rank, -area, slot_id)
