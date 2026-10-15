"""Post-search filtration protocol (implemented by consumers)."""

from __future__ import annotations

from typing import Protocol

from ..model import PartGraph
from .alignment import SearchResult
from .pattern import GraphPattern


class AlignmentResultFilter(Protocol):
    def apply(
        self,
        result: SearchResult,
        pattern: GraphPattern,
        target: PartGraph,
    ) -> SearchResult: ...
