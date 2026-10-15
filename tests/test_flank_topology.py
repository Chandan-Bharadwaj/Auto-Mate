import numpy as np

from MateCore.MateGraph.search.flank_index import (
    FLANK_ROLE_FLANK,
    FLANK_ROLE_HUB,
    annotate_flank_topology,
    parallel_plane_span_slots,
)
from MateCore.MateGraph.search.pattern import GraphPattern, PatternSlot


def _uslot_pattern(half_width: float = 5.0) -> GraphPattern:
    hw = half_width
    slots = (
        PatternSlot(
            "bottom",
            "n1",
            "plane",
            np.array([0.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 1.0]),
        ),
        PatternSlot(
            "left",
            "n2",
            "plane",
            np.array([-hw, 0.0, 0.0]),
            np.array([1.0, 0.0, 0.0]),
        ),
        PatternSlot(
            "right",
            "n3",
            "plane",
            np.array([hw, 0.0, 0.0]),
            np.array([-1.0, 0.0, 0.0]),
        ),
    )
    by = {s.slot_id: s for s in slots}
    adj = {
        "bottom": frozenset({"left", "right"}),
        "left": frozenset({"bottom"}),
        "right": frozenset({"bottom"}),
    }
    return GraphPattern(
        "P",
        slots,
        (),
        frozenset(s.slot_id for s in slots),
        _adjacency=adj,
        _by_slot=by,
    )


def test_parallel_plane_span_opposing_walls():
    pat = _uslot_pattern(5.0)
    left, right = pat.slot("left"), pat.slot("right")
    assert left is not None and right is not None
    span = parallel_plane_span_slots(left, right, angle_tol=0.1)
    assert span is not None and np.isclose(span, 10.0)


def test_annotate_flank_topology_hub_and_span():
    pat = annotate_flank_topology(_uslot_pattern(5.0), angle_tol=0.1, hub_node_weight=2.0)
    hub = pat.slot("bottom")
    assert hub is not None
    assert hub.metadata.get("flank_role") == FLANK_ROLE_HUB
    assert hub.metadata.get("flank_slot_ids") == ("left", "right")
    assert np.isclose(hub.metadata["flank_span"], 10.0)
    assert hub.metadata["node_weight"] == 2.0
    left = pat.slot("left")
    assert left is not None
    assert left.metadata.get("flank_role") == FLANK_ROLE_FLANK
    assert left.metadata.get("slot_order_group") == 0


def test_mating_search_pattern_preserves_flank_metadata():
    from MateCore.MateAlgo_Heuristic.transform import mating_search_pattern

    ref = annotate_flank_topology(_uslot_pattern(), angle_tol=0.1)
    search = mating_search_pattern(ref)
    hub = search.slot("bottom")
    assert hub is not None
    assert hub.metadata.get("flank_span") == ref.slot("bottom").metadata.get("flank_span")
