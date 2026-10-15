"""Trace helpers for the Auto-Mate command compute/display path."""

from __future__ import annotations

from contextlib import nullcontext
from typing import Any, Callable

from MateCore.trace import MODULE_COMMAND, TRACE_DEEP, trace_at_least, trace_span


def trace_compute_context():
    """Context manager wrapping the full compute+display path (level >= 2)."""
    if trace_at_least(MODULE_COMMAND, TRACE_DEEP):
        return trace_span(MODULE_COMMAND, "compute", min_level=TRACE_DEEP)
    return nullcontext()


def maybe_trace_span(label: str, min_level: int = TRACE_DEEP):
    if trace_at_least(MODULE_COMMAND, min_level):
        return trace_span(MODULE_COMMAND, label, min_level=min_level)
    return nullcontext()


def trace_sink_for_freecad(console: Any) -> Callable[[str], None]:
    return lambda msg: console.PrintMessage(f"[Auto-Mate trace] {msg}\n")
