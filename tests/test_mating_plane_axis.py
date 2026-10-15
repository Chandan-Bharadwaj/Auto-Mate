import numpy as np

from MateCore.MateAlgo_Heuristic.policy import MatingNodeComparator
from MateCore.MateFit import FitResolver
from MateCore.MateGraph.model import AAGNode
from MateCore.MateGraph.search.comparators import DefaultNodeComparator
from MateCore.MateGraph.search.pattern import PatternSlot


def _comparator(angle_tol: float = 0.1) -> MatingNodeComparator:
    return MatingNodeComparator(
        FitResolver(),
        "P",
        DefaultNodeComparator(
            angle_tol=angle_tol,
            min_similarity=0.3,
            compare_node_axis=False,
        ),
    )


def _plane_slot(axis):
    return PatternSlot(
        "s0",
        "n0",
        "plane",
        np.zeros(3),
        np.asarray(axis, dtype=float),
    )


def _plane_node(node_id: str, axis):
    return AAGNode(
        node_id,
        "T",
        "plane",
        np.zeros(3),
        np.asarray(axis, dtype=float),
        area=1.0,
    )


def test_opposing_normals_pass_when_partial_mapping_empty():
    cmp = _comparator()
    slot = _plane_slot((1.0, 0.0, 0.0))
    node = _plane_node("t0", (-1.0, 0.0, 0.0))
    assert cmp.explain_node_rejection(slot, node, {}) is None
    assert cmp.similarity(slot, node, {}) is not None


def test_opposing_normals_pass_when_partial_mapping_nonempty():
    cmp = _comparator()
    slot = _plane_slot((1.0, 0.0, 0.0))
    node = _plane_node("t0", (-1.0, 0.0, 0.0))
    partial = {"other": "T:other"}
    assert cmp.explain_node_rejection(slot, node, partial) is None
    assert cmp.similarity(slot, node, partial) is not None


def test_skew_normals_pass_when_partial_mapping_empty_kind_only():
    cmp = _comparator()
    slot = _plane_slot((1.0, 0.0, 0.0))
    node = _plane_node("t0", (0.0, 1.0, 0.0))
    assert cmp.explain_node_rejection(slot, node, {}) is None
    assert cmp.similarity(slot, node, {}) == 1.0


def test_surface_kind_mismatch_on_empty_partial_mapping():
    cmp = _comparator()
    slot = _plane_slot((1.0, 0.0, 0.0))
    node = AAGNode(
        "t0",
        "T",
        "cylinder",
        np.zeros(3),
        np.array([0.0, 0.0, 1.0]),
        radius=1.0,
    )
    assert cmp.explain_node_rejection(slot, node, {}) == "surface_kind_mismatch"
    assert cmp.similarity(slot, node, {}) is None


def test_skew_normals_pass_when_partial_mapping_nonempty_no_direct_axis_gate():
    cmp = _comparator()
    slot = _plane_slot((1.0, 0.0, 0.0))
    node = _plane_node("t0", (0.0, 1.0, 0.0))
    partial = {"other": "T:other"}
    assert cmp.explain_node_rejection(slot, node, partial) is None
    assert cmp.similarity(slot, node, partial) is not None
