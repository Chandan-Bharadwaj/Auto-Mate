"""Unified module-scoped trace protocol (timing and stage markers).

Levels (shared by all modules):
  0 — off
  1 — high-level (run stages, heuristic/mategraph summaries, mating report)
  2 — deep (phase milestones, command compute, graph build substeps, factory)
  3 — verbose (milestones plus per-step decisions)
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Callable, Iterator

TRACE_OFF = 0
TRACE_HIGH = 1
TRACE_DEEP = 2
TRACE_VERBOSE = 3

# Registered trace module ids (stable for preferences and docs).
MODULE_RUN = "run"
MODULE_HEURISTIC = "heuristic"
MODULE_MATEGRAPH = "mategraph"
MODULE_CACHE = "cache"
MODULE_FACTORY = "factory"
MODULE_COMMAND = "command"
MODULE_REPORT = "report"

KNOWN_MODULES = (
    MODULE_RUN,
    MODULE_HEURISTIC,
    MODULE_MATEGRAPH,
    MODULE_CACHE,
    MODULE_FACTORY,
    MODULE_COMMAND,
    MODULE_REPORT,
)

_global_enabled: bool = False
_default_level: int = TRACE_OFF
_module_levels: dict[str, int] = {}
_sink: Callable[[str], None] | None = None


def effective_level(module: str) -> int:
    """Effective trace level for a module.

    Module ``report`` defaults to TRACE_HIGH even when global trace is off or
    the default level is 0. Tests that must silence the mating report should
    call ``set_module_trace_level(MODULE_REPORT, TRACE_OFF)``.
    """
    if module == MODULE_REPORT:
        if module in _module_levels:
            return max(TRACE_OFF, int(_module_levels[module]))
        return TRACE_HIGH
    if not _global_enabled:
        return TRACE_OFF
    if module in _module_levels:
        return max(TRACE_OFF, int(_module_levels[module]))
    return max(TRACE_OFF, int(_default_level))


def is_global_trace_enabled() -> bool:
    return _global_enabled


def set_global_trace_enabled(enabled: bool) -> None:
    global _global_enabled
    _global_enabled = bool(enabled)


def get_default_trace_level() -> int:
    return _default_level


def set_default_trace_level(level: int) -> None:
    global _default_level
    _default_level = max(TRACE_OFF, int(level))


def get_module_trace_level(module: str) -> int | None:
    if module not in _module_levels:
        return None
    return _module_levels[module]


def set_module_trace_level(module: str, level: int) -> None:
    _module_levels[module] = max(TRACE_OFF, int(level))


def clear_module_trace_level(module: str) -> None:
    _module_levels.pop(module, None)


def module_trace_levels() -> dict[str, int]:
    return dict(_module_levels)


def reset_trace_state() -> None:
    """Restore production defaults for unit tests (global off; report still default-on)."""
    global _global_enabled, _default_level, _sink
    _global_enabled = False
    _default_level = TRACE_OFF
    _module_levels.clear()
    _sink = None


def set_trace_sink(sink: Callable[[str], None] | None) -> None:
    global _sink
    _sink = sink


def trace_at_least(module: str, min_level: int) -> bool:
    return effective_level(module) >= min_level


def trace_emit(
    module: str, message: str, *, min_level: int = TRACE_HIGH
) -> None:
    if not trace_at_least(module, min_level) or _sink is None:
        return
    _sink(f"[{module}] {message}")


@contextmanager
def trace_span(
    module: str, label: str, *, min_level: int = TRACE_HIGH
) -> Iterator[None]:
    if not trace_at_least(module, min_level):
        yield
        return
    trace_emit(module, f"{label} …", min_level=min_level)
    start = time.monotonic()
    try:
        yield
    finally:
        elapsed = time.monotonic() - start
        trace_emit(module, f"{label} done ({elapsed:.3f}s)", min_level=min_level)


def trace_duration(
    module: str,
    label: str,
    seconds: float,
    *,
    min_level: int = TRACE_HIGH,
) -> None:
    trace_emit(module, f"{label} ({seconds:.3f}s)", min_level=min_level)


def trace_milestone(
    module: str,
    title: str,
    *,
    context: dict[str, str | int | float] | None = None,
    min_level: int = TRACE_DEEP,
) -> None:
    """Decorated phase header for deep/verbose (not emitted at high-only)."""
    if not trace_at_least(module, min_level) or _sink is None:
        return
    _sink(f"[{module}] --- {title} ---")
    if context:
        for key, value in context.items():
            if value is None or value == "":
                continue
            _sink(f"[{module}]   {key}={value}")


# --- Legacy shims (default level only; use module API in new code) ---

def get_trace_level() -> int:
    return _default_level


def set_trace_level(level: int) -> None:
    set_default_trace_level(level)


def set_trace_enabled(enabled: bool) -> None:
    set_default_trace_level(TRACE_HIGH if enabled else TRACE_OFF)


def is_trace_enabled() -> bool:
    return _global_enabled and _default_level >= TRACE_HIGH
