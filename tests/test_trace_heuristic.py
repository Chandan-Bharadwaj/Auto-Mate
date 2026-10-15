"""Trace module registration and heuristic algorithm emitters."""

from MateCore.trace import (
    KNOWN_MODULES,
    MODULE_HEURISTIC,
    MODULE_MATEGRAPH,
    TRACE_DEEP,
    TRACE_HIGH,
    TRACE_OFF,
    reset_trace_state,
    set_global_trace_enabled,
    set_module_trace_level,
    set_trace_sink,
)
from tests.test_heuristic_mate import World, cyl, matches


def test_heuristic_module_registered():
    assert MODULE_HEURISTIC == "heuristic"
    assert MODULE_HEURISTIC in KNOWN_MODULES


def test_heuristic_trace_emits_on_run():
    lines: list[str] = []
    reset_trace_state()
    set_global_trace_enabled(True)
    set_trace_sink(lines.append)
    set_module_trace_level(MODULE_HEURISTIC, TRACE_HIGH)
    w = World()
    a = w.add("A", [cyl((0, 0, 0), (0, 0, 1), 5, True)])
    w.add("B", [cyl((10, 0, 0), (0, 0, 1), 5, False)])
    matches(w, a)
    reset_trace_state()
    assert any("[heuristic]" in line for line in lines)
    assert any("prepare" in line or "slots=" in line for line in lines)


def test_mategraph_deep_alignment_search_trace():
    lines: list[str] = []
    reset_trace_state()
    set_global_trace_enabled(True)
    set_trace_sink(lines.append)
    set_module_trace_level(MODULE_HEURISTIC, TRACE_OFF)
    set_module_trace_level(MODULE_MATEGRAPH, TRACE_DEEP)
    w = World()
    a = w.add("A", [cyl((0, 0, 0), (0, 0, 1), 5, True)])
    w.add("B", [cyl((10, 0, 0), (0, 0, 1), 5, False)])
    matches(w, a)
    reset_trace_state()
    assert any("[mategraph]" in line and "alignment search" in line for line in lines)
