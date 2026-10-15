"""Debug algorithm: build part graphs for every part in the document."""

from __future__ import annotations

import time
from contextlib import nullcontext
from typing import Callable

from MateCore.algorithm import (
    AlgorithmConfig,
    AlgorithmResult,
    MateAlgorithm,
    RunContext,
)
from MateCore.context import PartContext, RecognitionRequest
from MateCore.trace import (
    MODULE_MATEGRAPH,
    TRACE_HIGH,
    trace_at_least,
    trace_duration,
    trace_emit,
    trace_span,
)

from .options import GraphBuildOptions
from .store import PartGraphStore


class MateAlgorithm_DebugMateGraph(MateAlgorithm):
    name = "mate-algorithm-debug-mate-graph"
    supported_surface_kinds = ()
    single_source_part = True

    def __init__(
        self,
        store: PartGraphStore,
        options: GraphBuildOptions | None = None,
        config: AlgorithmConfig | None = None,
    ) -> None:
        super().__init__(config or AlgorithmConfig())
        self._store = store
        self._options = options or store.default_options

    def run(
        self,
        request: RecognitionRequest,
        *,
        is_cancelled: Callable[[], bool] | None = None,
        on_progress: Callable[[float, str], None] | None = None,
    ) -> AlgorithmResult:
        run = RunContext(self.config, is_cancelled, on_progress)
        if trace_at_least(MODULE_MATEGRAPH, TRACE_HIGH):
            trace_emit(
                MODULE_MATEGRAPH,
                f"run.start algorithm={self.name}",
                min_level=TRACE_HIGH,
            )
        self.validate(request, run)
        parts = list(request.context.all_parts)
        total = max(1, len(parts))
        build_time = 0.0
        for index, part in enumerate(parts):
            if run.should_stop:
                break
            run.progress(index / total, f"Building graph for {part.name}")
            label = f"debug_mate_graph part={part.part_id}"
            ctx = (
                trace_span(MODULE_MATEGRAPH, label, min_level=TRACE_HIGH)
                if trace_at_least(MODULE_MATEGRAPH, TRACE_HIGH)
                else nullcontext()
            )
            start = time.monotonic()
            with ctx:
                graph = self._store.get(part, self._options)
            elapsed = time.monotonic() - start
            build_time += elapsed
            summary = (
                f"{label} nodes={len(graph.nodes)} edges={len(graph.edges)} "
                f"elapsed={elapsed:.3f}s"
            )
            if trace_at_least(MODULE_MATEGRAPH, TRACE_HIGH):
                trace_duration(MODULE_MATEGRAPH, summary, elapsed, min_level=TRACE_HIGH)
        run.progress(1.0, "Done")
        if trace_at_least(MODULE_MATEGRAPH, TRACE_HIGH):
            trace_emit(
                MODULE_MATEGRAPH,
                f"run.complete debug_mate_graph parts={len(parts)} "
                f"build_time={build_time:.3f}s",
                min_level=TRACE_HIGH,
            )
        return AlgorithmResult(
            part_matches=(),
            diagnostics=tuple(run.diagnostics),
            timings={"build_graphs": build_time},
            cancelled=run.should_stop,
        )

    def prepare(self, request: RecognitionRequest, run: RunContext):
        return request

    def match_part(
        self, state, part: PartContext, run: RunContext
    ):  # pragma: no cover - unused
        return []
