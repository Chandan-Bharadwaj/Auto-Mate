"""Pattern-based axis-alignment measure for heuristic mates."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from MateCore.MateGraph.search.pattern import GraphPattern, PatternSlot

_ANALYTIC_KINDS = frozenset({"plane", "cylinder", "cone"})


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n == 0.0:
        return v
    return v / n


def _reference_axis(slots: tuple[PatternSlot, ...]) -> np.ndarray | None:
    for slot in slots:
        if slot.surface_kind in ("cylinder", "cone"):
            return _unit(slot.axis)
    if slots:
        return _unit(slots[0].axis)
    return None


@dataclass(frozen=True, slots=True)
class AxisAlignmentMeasure:
    axis_aligned: bool
    reference_axis: np.ndarray | None
    max_misalignment_rad: float
    reason: str | None = None


def pattern_axis_alignment(
    pattern: GraphPattern,
    angle_tol: float,
) -> AxisAlignmentMeasure:
    slots = pattern.slots
    if not slots:
        return AxisAlignmentMeasure(
            False, None, float(np.pi), reason="empty_pattern"
        )
    for slot in slots:
        if slot.surface_kind not in _ANALYTIC_KINDS:
            return AxisAlignmentMeasure(
                False, None, float(np.pi), reason="unsupported_kind"
            )
    a0 = _reference_axis(slots)
    if a0 is None:
        return AxisAlignmentMeasure(
            False, None, float(np.pi), reason="empty_pattern"
        )
    max_mis = 0.0
    for slot in slots:
        ai = _unit(slot.axis)
        dot = abs(float(np.dot(ai, a0)))
        mis = float(np.arccos(np.clip(dot, 0.0, 1.0)))
        max_mis = max(max_mis, mis)
    aligned = max_mis <= angle_tol
    return AxisAlignmentMeasure(
        aligned,
        a0,
        max_mis,
        reason=None if aligned else "axes_not_parallel",
    )
