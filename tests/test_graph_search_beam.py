import numpy as np

from MateCore.MateGraph.model import AAGEdge, AAGNode, PartGraph
from MateCore.MateGraph.search import DefaultSearchPolicy, SearchResult, extract_pattern, run_search
from tests.test_aag_world import part_aag_from_descriptors
from MateCore.MateFit.descriptors import FaceDescriptor


def _desc(
    fid: str, kind: str, adjacent: tuple[str, ...] = (), radius: float = 0.0
) -> FaceDescriptor:
    return FaceDescriptor(
        id=fid,
        part_id="P",
        kind=kind,
        origin=np.zeros(3),
        axis=np.array([0.0, 0.0, 1.0]),
        radius=radius,
        area=1.0,
        adjacent=adjacent,
    )


def test_search_finds_better_match_on_identical_target():
    descs = [
        _desc("f1", "plane", ("f2",)),
        _desc("f2", "plane", ("f1",)),
        _desc("f3", "cylinder", (), radius=5.0),
    ]
    source = part_aag_from_descriptors("P", descs, merge=False)
    target = part_aag_from_descriptors("T", descs, merge=False)
    pattern = extract_pattern(source, ("f1", "f2"))
    result = run_search(pattern, target, DefaultSearchPolicy(max_candidates=8))
    assert result.candidates
    assert result.candidates[0].score.total > 0.5


def test_search_ranks_perturbed_target_lower():
    base = [
        _desc("f1", "plane", ("f2",)),
        _desc("f2", "plane", ("f1",)),
    ]
    source = part_aag_from_descriptors("P", base, merge=False)
    good = part_aag_from_descriptors("T1", base, merge=False)
    bad_descs = [
        _desc("g1", "plane", ("g2",)),
        _desc("g2", "cylinder", ("g1",), radius=1.0),
    ]
    bad = part_aag_from_descriptors("T2", bad_descs, merge=False)
    pattern = extract_pattern(source, ("f1", "f2"))
    good_score = run_search(pattern, good).candidates[0].score.total
    bad_score = run_search(pattern, bad).candidates[0].score.total
    assert good_score > bad_score


class _MinScoreFilter:
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def apply(self, result: SearchResult, pattern, target: PartGraph) -> SearchResult:
        kept = tuple(c for c in result.candidates if c.score.total >= self.threshold)
        return result.with_candidates(kept)


def test_result_filter_applied_by_consumer():
    descs = [_desc("f1", "plane"), _desc("f2", "cylinder", radius=2.0)]
    source = part_aag_from_descriptors("P", descs, merge=False)
    target = part_aag_from_descriptors("T", descs, merge=False)
    pattern = extract_pattern(source, ("f1",))
    raw = run_search(pattern, target)
    filt = _MinScoreFilter(threshold=0.99)
    filtered = filt.apply(raw, pattern, target)
    assert len(filtered.candidates) <= len(raw.candidates)
