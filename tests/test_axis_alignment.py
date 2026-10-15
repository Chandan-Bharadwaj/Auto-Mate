import numpy as np

from MateCore.MateAlgo_Heuristic.axis_alignment import pattern_axis_alignment
from MateCore.MateGraph.search.pattern import GraphPattern, PatternSlot


def _pattern(*slots: PatternSlot) -> GraphPattern:
    by = {s.slot_id: s for s in slots}
    adj = {s.slot_id: frozenset() for s in slots}
    return GraphPattern(
        "P",
        slots,
        (),
        frozenset(s.slot_id for s in slots),
        _adjacency=adj,
        _by_slot=by,
    )


def _cyl(sid: str, axis):
    return PatternSlot(
        sid,
        f"n{sid}",
        "cylinder",
        np.zeros(3),
        np.asarray(axis, dtype=float),
        radius=5.0,
    )


def _plane(sid: str, normal):
    return PatternSlot(
        sid,
        f"n{sid}",
        "plane",
        np.zeros(3),
        np.asarray(normal, dtype=float),
    )


def test_two_coaxial_cylinders_aligned():
    pat = _pattern(_cyl("a", (0, 0, 1)), _cyl("b", (0, 0, 1)))
    m = pattern_axis_alignment(pat, angle_tol=0.1)
    assert m.axis_aligned is True
    assert m.max_misalignment_rad == 0.0


def test_uslot_not_axis_aligned():
    pat = _pattern(
        _plane("hub", (0, 0, 1)),
        _plane("left", (1, 0, 0)),
        _plane("right", (-1, 0, 0)),
    )
    m = pattern_axis_alignment(pat, angle_tol=0.1)
    assert m.axis_aligned is False
    assert m.reason == "axes_not_parallel"


def test_shoulder_plane_perpendicular_to_cylinder_not_aligned():
    pat = _pattern(_cyl("shaft", (0, 0, 1)), _plane("shoulder", (1, 0, 0)))
    m = pattern_axis_alignment(pat, angle_tol=0.1)
    assert m.axis_aligned is False
