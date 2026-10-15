from MateCore.trace import (
    MODULE_RUN,
    TRACE_DEEP,
    TRACE_HIGH,
    reset_trace_state,
    set_global_trace_enabled,
    set_module_trace_level,
    set_trace_sink,
    trace_milestone,
)


def test_milestone_emits_at_deep_not_high():
    lines: list[str] = []
    reset_trace_state()
    set_global_trace_enabled(True)
    set_module_trace_level(MODULE_RUN, TRACE_HIGH)
    set_trace_sink(lines.append)
    trace_milestone(MODULE_RUN, "validate", context={"algorithm": "test"})
    assert lines == []

    set_module_trace_level(MODULE_RUN, TRACE_DEEP)
    trace_milestone(MODULE_RUN, "validate", context={"algorithm": "test"})
    assert any("--- validate ---" in line for line in lines)
    assert any("algorithm=test" in line for line in lines)
    set_trace_sink(None)
    reset_trace_state()
