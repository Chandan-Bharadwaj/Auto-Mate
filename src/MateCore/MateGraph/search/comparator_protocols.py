"""Comparator protocols for alignment search (Tier 1)."""

from __future__ import annotations

from typing import Protocol

from ..model import AAGEdge, AAGNode
from .pattern import PatternEdge, PatternSlot


class NodeComparator(Protocol):
    def similarity(
        self,
        slot: PatternSlot,
        node: AAGNode,
        partial_mapping: dict[str, str] | None = None,
    ) -> float | None: ...


class EdgeComparator(Protocol):
    def similarity(self, pattern_edge: PatternEdge, target_edge: AAGEdge | None) -> float: ...
