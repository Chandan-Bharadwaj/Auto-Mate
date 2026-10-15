import numpy as np

from MateCore.MateGraph.model import AAGNode
from MateCore.MateGraph.search.comparators import DefaultNodeComparator
from MateCore.MateGraph.search.pattern import PatternSlot


def _slot(kind: str = "plane", radius: float = 0.0) -> PatternSlot:
    return PatternSlot(
        slot_id="s1",
        source_node_id="n1",
        surface_kind=kind,
        origin=np.zeros(3),
        axis=np.array([0.0, 0.0, 1.0]),
        area=10.0,
        radius=radius,
    )


def _node(kind: str = "plane", radius: float = 0.0, axis=None) -> AAGNode:
    if axis is None:
        axis = np.array([0.0, 0.0, 1.0])
    return AAGNode(
        node_id="t1",
        part_id="T",
        surface_kind=kind,
        origin=np.zeros(3),
        axis=axis,
        area=10.0,
        radius=radius,
    )


def test_default_comparator_surface_kind_mismatch():
    cmp = DefaultNodeComparator()
    reason = cmp.explain_node_rejection(_slot("plane"), _node("cylinder"))
    assert reason == "surface_kind_mismatch"
    assert cmp.similarity(_slot("plane"), _node("cylinder")) is None


def test_default_comparator_axis_misaligned():
    cmp = DefaultNodeComparator(angle_tol=0.1)
    reason = cmp.explain_node_rejection(
        _slot(),
        _node(axis=np.array([1.0, 0.0, 0.0])),
    )
    assert reason == "axis_misaligned"


def test_default_comparator_pass_returns_none():
    cmp = DefaultNodeComparator()
    assert cmp.explain_node_rejection(_slot(), _node()) is None
    assert cmp.similarity(_slot(), _node()) is not None


def test_default_comparator_below_min_similarity():
    cmp = DefaultNodeComparator(min_similarity=0.95)
    reason = cmp.explain_node_rejection(
        _slot("cylinder", radius=5.0), _node("cylinder", radius=1.0)
    )
    assert reason == "below_min_similarity"
