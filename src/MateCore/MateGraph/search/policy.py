"""Search policy protocol and test reference implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .comparators import DefaultEdgeComparator, DefaultNodeComparator
from .pattern import GraphPattern, PatternSlot


class AlignmentSearchPolicy(Protocol):
    @property
    def beam_width(self) -> int: ...

    @property
    def max_candidates(self) -> int: ...

    @property
    def node_min_similarity(self) -> float: ...

    @property
    def missing_edge_penalty(self) -> float: ...

    @property
    def unmapped_slot_penalty(self) -> float: ...

    @property
    def unmapped_anchor_penalty(self) -> float: ...

    @property
    def weight_node(self) -> float: ...

    @property
    def weight_edge(self) -> float: ...

    @property
    def weight_coverage(self) -> float: ...

    @property
    def weight_anchor_coverage(self) -> float: ...

    def node_comparator(self) -> DefaultNodeComparator: ...

    def edge_comparator(self) -> DefaultEdgeComparator: ...

    def slot_order(self, pattern: GraphPattern) -> tuple[str, ...]:
        """Search order for pattern slots."""
        ...

    def should_prune_partial(self, mapped_count: int, partial_score: float) -> bool:
        """Return True to abandon this partial alignment branch."""
        ...

    def slot_node_weight(self, slot: PatternSlot) -> float:
        """Weight for this slot in alignment node_term (default 1.0)."""
        ...


@dataclass(frozen=True, slots=True)
class DefaultSearchPolicy:
    """Reference policy for unit tests; not prescriptive for production."""

    beam_width: int = 32
    max_candidates: int = 16
    node_min_similarity: float = 0.3
    missing_edge_penalty: float = 0.25
    unmapped_slot_penalty: float = 0.15
    unmapped_anchor_penalty: float = 0.5
    weight_node: float = 0.4
    weight_edge: float = 0.35
    weight_coverage: float = 0.15
    weight_anchor_coverage: float = 0.1
    len_tol: float = 1e-3
    angle_tol: float = 0.1

    def node_comparator(self) -> DefaultNodeComparator:
        return DefaultNodeComparator(
            min_similarity=self.node_min_similarity,
            len_tol=self.len_tol,
            angle_tol=self.angle_tol,
        )

    def edge_comparator(self) -> DefaultEdgeComparator:
        return DefaultEdgeComparator(angle_tol=self.angle_tol)

    def slot_order(self, pattern: GraphPattern) -> tuple[str, ...]:
        return tuple(
            sorted(
                (s.slot_id for s in pattern.slots),
                key=lambda sid: pattern.degree(sid),
                reverse=True,
            )
        )

    def should_prune_partial(self, mapped_count: int, partial_score: float) -> bool:
        return False

    def slot_node_weight(self, slot: PatternSlot) -> float:
        return 1.0
