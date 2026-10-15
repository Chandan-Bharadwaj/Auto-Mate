import numpy as np

from MateCore.MateGraph.metadata import PartMetadata
from MateCore.MateGraph.metadata_requirements import PatternMetadataRequirements
from MateCore.MateGraph.search.pattern import GraphPattern, PatternSlot
from MateCore.MateAlgo_Heuristic.metadata_predicate import MatingMetadataPredicate


def _pattern(*kinds: str) -> GraphPattern:
    slots = tuple(
        PatternSlot(
            f"p{i}",
            f"n{i}",
            kind,
            np.zeros(3),
            np.array([0.0, 0.0, 1.0]),
        )
        for i, kind in enumerate(kinds)
    )
    by = {s.slot_id: s for s in slots}
    return GraphPattern("P", slots, (), frozenset(), _adjacency={}, _by_slot=by)


def test_requirements_from_pattern_counts():
    pat = _pattern("plane", "cylinder", "cylinder")
    req = PatternMetadataRequirements.from_pattern(pat)
    assert req.min_face_count == 3
    assert req.min_faces_by_kind == {"plane": 1, "cylinder": 2}


def test_mating_predicate_filters_by_kind():
    req = PatternMetadataRequirements.from_pattern(_pattern("plane"))
    pred = MatingMetadataPredicate(req)
    ok = PartMetadata("B", 2, 1.0, 2.0, {"plane": 1, "cylinder": 1})
    bad = PartMetadata("C", 1, 1.0, 1.0, {"cylinder": 1})
    assert pred.accept(ok)
    assert not pred.accept(bad)
