"""Ready-made post-processing stages and rankers for any algorithm."""

from __future__ import annotations

from MateCore.algorithm import Match, PartMatch, RecognitionRequest, RunContext


def _face_key(match: Match) -> frozenset:
    return frozenset((f.object_name, f.face_name) for f in match.faces)


class DedupeByFaceSet:
    """Keep only the best-scoring match for each identical set of faces."""

    name = "dedupe-by-face-set"

    def process(
        self, matches: list[Match], request: RecognitionRequest, run: RunContext
    ) -> list[Match]:
        best: dict[frozenset, Match] = {}
        for m in matches:
            key = _face_key(m)
            if key not in best or m.score > best[key].score:
                best[key] = m
        return list(best.values())


class MinScore:
    name = "min-score"

    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def process(
        self, matches: list[Match], request: RecognitionRequest, run: RunContext
    ) -> list[Match]:
        return [m for m in matches if m.score >= self.threshold]


class MinPartScore:
    """Part-level filter: drop candidate parts whose score is below a threshold."""

    name = "min-part-score"

    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def process(self, parts: list[PartMatch], request, run: RunContext) -> list[PartMatch]:
        return [p for p in parts if p.score >= self.threshold]


class PartScoreRanker:
    """Best part score first; stable for ties."""

    def rank(self, parts: list[PartMatch]) -> list[PartMatch]:
        return sorted(parts, key=lambda p: -p.score)


class ScoreRanker:
    """Highest score first; stable for ties."""

    def rank(self, matches: list[Match]) -> list[Match]:
        return sorted(matches, key=lambda m: -m.score)
