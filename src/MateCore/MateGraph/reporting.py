"""Optional build reporting (store-level observability)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol

from MateCore.trace import (
    MODULE_MATEGRAPH,
    TRACE_DEEP,
    trace_at_least,
    trace_duration,
    trace_emit,
)


class GraphBuildReporter(Protocol):
    def stage_started(self, name: str) -> None: ...

    def stage_finished(self, name: str, seconds: float, **counts: int) -> None: ...


@dataclass
class NullGraphBuildReporter:
    def stage_started(self, name: str) -> None:
        return

    def stage_finished(self, name: str, seconds: float, **counts: int) -> None:
        return


@dataclass
class TraceGraphBuildReporter:
    """Emit build substeps when mategraph trace level is at least TRACE_DEEP."""

    _root: str = ""
    _starts: dict[str, float] = field(default_factory=dict)

    def stage_started(self, name: str) -> None:
        if not trace_at_least(MODULE_MATEGRAPH, TRACE_DEEP):
            return
        label = f"{self._root}.{name}" if self._root else name
        trace_emit(MODULE_MATEGRAPH, f"{label} …", min_level=TRACE_DEEP)
        self._starts[name] = time.monotonic()

    def stage_finished(self, name: str, seconds: float, **counts: int) -> None:
        if not trace_at_least(MODULE_MATEGRAPH, TRACE_DEEP):
            return
        label = f"{self._root}.{name}" if self._root else name
        extra = " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        suffix = f" {extra}" if extra else ""
        trace_duration(
            MODULE_MATEGRAPH, f"{label} done{suffix}", seconds, min_level=TRACE_DEEP
        )
