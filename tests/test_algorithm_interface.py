import pytest

from MateCore.algorithm import (
    AlgorithmConfig,
    AlgorithmRegistry,
    Match,
    MateAlgorithm,
)
from MateCore.context import (
    DocumentContext,
    DocumentObjectContext,
    PartContext,
    RecognitionRequest,
    SurfaceRef,
)
from MateCore.postprocessors import MinPartScore


def face(part, n):
    return SurfaceRef(part, part, f"Face{n}", None, None, part_id=part)


def make_context(*part_ids):
    parts = tuple(
        PartContext(pid, pid, pid, faces=tuple(face(pid, i) for i in (1, 2)))
        for pid in part_ids
    )
    objects = tuple(
        DocumentObjectContext(p.part_id, p.name, "Part::Feature", "part", (), p.faces, (p,))
        for p in parts
    )
    return DocumentContext("Doc", objects)


def request(source="P", others=("Q", "R", "S")):
    return RecognitionRequest(make_context(source, *others), (face(source, 1),))


class Stub(MateAlgorithm):
    """Each candidate part yields configurations scored from ``scores[part_id]``."""

    name = "stub"

    def __init__(self, scores=None, **kw):
        super().__init__(**kw)
        self.scores = scores or {"Q": [1.0], "R": [3.0, 2.0], "S": []}
        self.calls = []

    def validate(self, req, run):
        self.calls.append("validate")
        super().validate(req, run)

    def prepare(self, req, run):
        self.calls.append("prepare")
        return req

    def match_part(self, state, part, run):
        self.calls.append(f"match:{part.part_id}")
        run.warn(f"saw {part.part_id}")
        if not self.scores[part.part_id]:
            run.explain(part.part_id, "nothing fits")
        return [
            Match((face(part.part_id, i),), score=s)
            for i, s in enumerate(self.scores[part.part_id], start=1)
        ]


class DropLow:
    name = "drop-low"

    def process(self, matches, request, run):
        return [m for m in matches if m.score >= 2.0]


class ByScore:
    def rank(self, matches):
        return sorted(matches, key=lambda m: -m.score)


def test_hook_order_and_source_part_excluded():
    algo = Stub()
    assert algo.postprocessors == ()
    result = algo.run(request())
    assert algo.calls == ["validate", "prepare", "match:Q", "match:R", "match:S"]
    assert [p.part_id for p in result.part_matches] == ["R", "Q"]


def test_parts_are_ranked_and_matches_carry_part_id():
    result = Stub().run(request())
    best = result.part_matches[0]
    assert best.part_name == "R" and best.score == 3.0
    assert [m.score for m in best.matches] == [3.0, 2.0]
    assert {m.part_id for m in result.matches} == {"R", "Q"}
    assert [g[0].object_name for g in result.as_surface_groups()] == ["R", "R", "Q"]
    assert [p.part_id for p, _ in result.as_part_groups()] == ["R", "Q"]


def test_rejected_parts_report_reasons():
    result = Stub().run(request())
    assert [(r.part_id, r.reason) for r in result.rejected_parts] == [("S", "nothing fits")]


def test_default_validation_requires_surfaces():
    with pytest.raises(ValueError):
        Stub().compute(RecognitionRequest(make_context("P", "Q"), ()))


def test_source_part_must_be_single_and_known():
    ctx = make_context("P", "Q")
    mixed = RecognitionRequest(ctx, (face("P", 1), face("Q", 1)))
    with pytest.raises(ValueError, match="one part"):
        Stub().run(mixed)
    unknown = RecognitionRequest(ctx, (SurfaceRef("X", "X", "Face1", None, None),))
    with pytest.raises(ValueError, match="known part"):
        Stub().run(unknown)


def test_match_postprocessors_ranker_and_caps():
    algo = Stub(config=AlgorithmConfig(max_results=1))
    algo.add_postprocessor(DropLow())
    algo.set_ranker(ByScore())
    result = algo.run(request())
    assert [m.score for m in result.matches] == [3.0]
    assert "saw R" in result.warnings
    assert any(r.part_id == "Q" and "post" not in r.reason for r in result.rejected_parts)
    algo.clear_postprocessors()
    assert algo.describe()["postprocessors"] == []


def test_many_configurations_of_one_part_do_not_crowd_out_other_parts():
    algo = Stub(
        scores={"Q": [9.0, 8.0, 7.0, 6.0], "R": [1.0], "S": [0.5]},
        config=AlgorithmConfig(max_matches_per_part=1, max_parts=2),
    )
    result = algo.run(request())
    assert [(p.part_id, len(p.matches)) for p in result.part_matches] == [("Q", 1), ("R", 1)]


def test_part_postprocessor_filters_and_records_rejection():
    algo = Stub()
    algo.add_part_postprocessor(MinPartScore(2.5))
    result = algo.run(request())
    assert [p.part_id for p in result.part_matches] == ["R"]
    assert ("Q", "removed by min-part-score") in [
        (r.part_id, r.reason) for r in result.rejected_parts
    ]


def test_custom_part_score_and_ranker():
    class SumScore(Stub):
        def score_part(self, part, matches):
            return sum(m.score for m in matches)

    class Reverse:
        def rank(self, parts):
            return list(reversed(sorted(parts, key=lambda p: -p.score)))

    algo = SumScore()
    algo.set_part_ranker(Reverse())
    result = algo.run(request())
    assert [(p.part_id, p.score) for p in result.part_matches] == [("Q", 1.0), ("R", 5.0)]


def test_cancellation_stops_part_loop():
    result = Stub().run(request(), is_cancelled=lambda: True)
    assert result.cancelled
    assert result.part_matches == ()


def test_config_validation():
    for field in ("max_results", "max_parts", "max_matches_per_part"):
        with pytest.raises(ValueError):
            AlgorithmConfig(**{field: 0})


def test_registry_creates_by_name():
    reg = AlgorithmRegistry()
    reg.register("stub", Stub)
    assert isinstance(reg.create("stub"), Stub)
    assert reg.names() == ("stub",)
    with pytest.raises(ValueError):
        reg.register("stub", Stub)
    with pytest.raises(KeyError):
        reg.create("nope")
