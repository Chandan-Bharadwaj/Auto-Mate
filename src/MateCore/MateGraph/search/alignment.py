"""Alignment results and scoring."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class GraphAlignment:
    """Injective map pattern slot_id -> target graph node_id."""

    mapping: tuple[tuple[str, str], ...]

    def as_dict(self) -> dict[str, str]:
        return dict(self.mapping)

    def mapped_slots(self) -> frozenset[str]:
        return frozenset(s for s, _ in self.mapping)

    def target_nodes(self) -> frozenset[str]:
        return frozenset(t for _, t in self.mapping)


@dataclass(frozen=True, slots=True)
class AlignmentScore:
    node_term: float
    edge_term: float
    coverage: float
    anchor_coverage: float
    penalty: float
    total: float


@dataclass(frozen=True, slots=True)
class ScoredAlignment:
    alignment: GraphAlignment
    score: AlignmentScore
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SearchResult:
    candidates: tuple[ScoredAlignment, ...]
    elapsed_s: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)

    def with_candidates(
        self, candidates: tuple[ScoredAlignment, ...]
    ) -> SearchResult:
        return SearchResult(
            candidates=candidates,
            elapsed_s=self.elapsed_s,
            metadata=dict(self.metadata),
        )
