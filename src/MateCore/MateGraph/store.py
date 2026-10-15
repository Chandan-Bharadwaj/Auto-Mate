"""Lazy per-part graph cache."""

from __future__ import annotations

import time
from typing import Protocol

from MateCore.context import PartContext
from MateCore.trace import (
    MODULE_MATEGRAPH,
    TRACE_DEEP,
    TRACE_HIGH,
    trace_at_least,
    trace_duration,
    trace_emit,
    trace_milestone,
)

from .model import PartGraph
from .options import GraphBuildOptions
from .reporting import GraphBuildReporter, NullGraphBuildReporter, TraceGraphBuildReporter


class PartGraphBuilder(Protocol):
    def __call__(
        self,
        part: PartContext,
        options: GraphBuildOptions,
        reporter: GraphBuildReporter,
        /,
    ) -> PartGraph: ...


class PartGraphStore:
    """Document-scoped cache: builds one part graph per ``get`` on cache miss."""

    def __init__(
        self,
        document_name: str,
        builder: PartGraphBuilder,
        default_options: GraphBuildOptions | None = None,
    ) -> None:
        self.document_name = document_name
        self._builder = builder
        self._default_options = default_options or GraphBuildOptions()
        self._entries: dict[tuple[str, tuple[float, float, bool]], PartGraph] = {}

    @property
    def default_options(self) -> GraphBuildOptions:
        return self._default_options

    def _key(
        self, part_id: str, options: GraphBuildOptions
    ) -> tuple[str, tuple[float, float, bool]]:
        return (part_id, options.cache_key())

    def get(
        self,
        part: PartContext,
        options: GraphBuildOptions | None = None,
    ) -> PartGraph:
        opts = options or self._default_options
        key = self._key(part.part_id, opts)
        cached = self._entries.get(key)
        if cached is not None:
            if trace_at_least(MODULE_MATEGRAPH, TRACE_DEEP):
                trace_emit(
                    MODULE_MATEGRAPH,
                    f"cache hit part={part.part_id} doc={self.document_name}",
                    min_level=TRACE_DEEP,
                )
            return cached

        label = f"mate_graph.build part={part.part_id} faces={len(part.faces)}"
        trace_milestone(
            MODULE_MATEGRAPH,
            "graph_build",
            context={"part_id": part.part_id, "faces": len(part.faces)},
        )
        start = time.monotonic()
        if trace_at_least(MODULE_MATEGRAPH, TRACE_HIGH):
            trace_emit(MODULE_MATEGRAPH, f"{label} …", min_level=TRACE_HIGH)
        reporter: GraphBuildReporter = (
            TraceGraphBuildReporter(_root=label)
            if trace_at_least(MODULE_MATEGRAPH, TRACE_DEEP)
            else NullGraphBuildReporter()
        )
        graph = self._builder(part, opts, reporter)
        elapsed = time.monotonic() - start
        self._entries[key] = graph
        if trace_at_least(MODULE_MATEGRAPH, TRACE_HIGH):
            trace_duration(
                MODULE_MATEGRAPH,
                f"{label} nodes={len(graph.nodes)} edges={len(graph.edges)}",
                elapsed,
                min_level=TRACE_HIGH,
            )
        return graph

    def invalidate(self, part_id: str | None = None) -> None:
        if part_id is None:
            self._entries.clear()
            return
        self._entries = {
            k: v for k, v in self._entries.items() if k[0] != part_id
        }
