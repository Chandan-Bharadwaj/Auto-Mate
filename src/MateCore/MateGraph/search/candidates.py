"""Fit-aware candidate pools per pattern slot."""

from __future__ import annotations

from ..model import PartGraph
from .index import TargetIndex
from .pattern import PatternSlot


def candidates_for_slot(
    slot: PatternSlot,
    target: PartGraph,
    index: TargetIndex,
    *,
    len_tol: float = 1e-3,
    angle_tol: float = 0.1,
    size_band: tuple[float, float] | None = None,
) -> tuple[str, ...]:
    pool = index.candidates_for_kind(slot.surface_kind)
    if slot.surface_kind == "cone" and slot.semi_angle > 0:
        lo = slot.semi_angle - angle_tol
        hi = slot.semi_angle + angle_tol
        banded = index.candidates_in_semi_angle_band(slot.surface_kind, lo, hi)
        if banded:
            pool = banded
    if slot.surface_kind == "cylinder" and slot.radius > 0:
        if size_band is not None:
            lo, hi = size_band
        else:
            tol = len_tol + 0.01 * slot.radius
            lo, hi = slot.radius - tol, slot.radius + tol
        banded = index.candidates_in_radius_band(slot.surface_kind, lo, hi)
        if banded:
            pool = banded
    if slot.surface_kind == "cone" and slot.radius > 0:
        if size_band is not None:
            lo, hi = size_band
        else:
            tol = len_tol + 0.01 * slot.radius
            lo, hi = slot.radius - tol, slot.radius + tol
        banded = index.candidates_in_radius_band(slot.surface_kind, lo, hi)
        if banded:
            pool = tuple(nid for nid in pool if nid in banded) or banded
    if pool:
        return pool
    return tuple(n.node_id for n in target.nodes)
