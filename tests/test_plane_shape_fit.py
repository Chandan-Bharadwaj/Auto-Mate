import numpy as np
import pytest

from MateCore.MateAlgo_Heuristic.plane_shape_fit import (
    PLANE_SHAPE_MISMATCH,
    apply_plane_shape_penalty,
    explain_plane_shape_rejection,
    plane_shape_raw,
)
from MateCore.MateAlgo_Heuristic.policy import MatingNodeComparator
from MateCore.MateFit import FitResolver
from MateCore.MateGraph.model import AAGNode, PLANE
from MateCore.MateGraph.search.comparators import DefaultNodeComparator
from MateCore.MateGraph.search.pattern import PatternSlot


def _plane_slot(area: float = 100.0, aspect: float = 1.0) -> PatternSlot:
    return PatternSlot(
        slot_id="p0",
        source_node_id="A:Face1",
        surface_kind=PLANE,
        origin=np.zeros(3),
        axis=np.array([0.0, 0.0, 1.0]),
        area=area,
        plane_aspect=aspect,
    )


def _plane_node(area: float = 100.0, aspect: float = 1.0, nid: str = "B:Face1") -> AAGNode:
    return AAGNode(
        node_id=nid,
        part_id="B",
        surface_kind=PLANE,
        origin=np.zeros(3),
        axis=np.array([0.0, 0.0, 1.0]),
        area=area,
        plane_aspect=aspect,
    )


def test_plane_shape_raw_area_and_aspect():
    slot = _plane_slot(100.0, 2.0)
    node = _plane_node(25.0, 8.0)
    assert plane_shape_raw(slot, node) == pytest.approx(0.0625)


def test_plane_shape_raw_non_plane_returns_one():
    slot = _plane_slot()
    node = _plane_node()
    node_cyl = AAGNode(
        node_id="B:Face2",
        part_id="B",
        surface_kind="cylinder",
        origin=np.zeros(3),
        axis=np.array([0.0, 0.0, 1.0]),
        radius=5.0,
    )
    assert plane_shape_raw(slot, node_cyl) == 1.0


def test_apply_plane_shape_penalty_reject_floor():
    assert apply_plane_shape_penalty(0.9, 0.1, exponent=2.0, reject_floor=0.15) is None
    assert apply_plane_shape_penalty(0.9, 0.5, exponent=2.0, reject_floor=0.15) == 0.9 * 0.25


def test_explain_plane_shape_rejection():
    slot = _plane_slot(100.0, 4.0)
    node = _plane_node(400.0, 16.0)
    assert explain_plane_shape_rejection(slot, node, reject_floor=0.15) == PLANE_SHAPE_MISMATCH


def test_mating_comparator_plane_shape_with_partial_mapping():
    cmp = MatingNodeComparator(
        FitResolver(),
        "A",
        DefaultNodeComparator(compare_node_axis=False, min_similarity=0.3),
        plane_shape_reject_floor=0.15,
        plane_shape_penalty_exponent=2.0,
    )
    slot = _plane_slot(100.0, 2.0)
    good = _plane_node(100.0, 2.0)
    bad = _plane_node(400.0, 8.0)
    mapping = {"p1": "B:Face9"}

    assert cmp.similarity(slot, good, mapping) is not None
    assert cmp.similarity(slot, bad, mapping) is None
    assert (
        cmp.explain_node_rejection(slot, bad, mapping) == PLANE_SHAPE_MISMATCH
    )

    assert cmp.similarity(slot, bad, {}) == 1.0
