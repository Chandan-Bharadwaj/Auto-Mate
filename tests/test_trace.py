from MateCore.algorithm import AlgorithmConfig
from MateCore.context import (
    DocumentContext,
    DocumentObjectContext,
    PartContext,
    RecognitionRequest,
    SurfaceRef,
)
from MateCore.dummy_algorithm import DummyMateAlgorithm
from MateCore.trace import (
    MODULE_REPORT,
    MODULE_RUN,
    TRACE_DEEP,
    TRACE_HIGH,
    TRACE_OFF,
    effective_level,
    get_default_trace_level,
    is_global_trace_enabled,
    reset_trace_state,
    set_default_trace_level,
    set_global_trace_enabled,
    set_module_trace_level,
    set_trace_sink,
    trace_emit,
    trace_span,
)


def test_production_defaults_global_off_report_on():
    reset_trace_state()
    assert not is_global_trace_enabled()
    assert get_default_trace_level() == TRACE_OFF
    assert effective_level(MODULE_RUN) == TRACE_OFF
    assert effective_level(MODULE_REPORT) == TRACE_HIGH
    reset_trace_state()


def test_trace_span_emits_at_level_one():
    lines: list[str] = []
    reset_trace_state()
    set_global_trace_enabled(True)
    set_default_trace_level(TRACE_HIGH)
    set_trace_sink(lines.append)
    try:
        with trace_span(MODULE_RUN, "stage.test"):
            pass
    finally:
        set_trace_sink(None)
        reset_trace_state()
    assert any("stage.test" in line for line in lines)


def test_trace_span_silent_at_level_zero():
    lines: list[str] = []
    reset_trace_state()
    set_default_trace_level(TRACE_OFF)
    set_trace_sink(lines.append)
    try:
        with trace_span(MODULE_RUN, "stage.test"):
            pass
    finally:
        set_trace_sink(None)
        reset_trace_state()
    assert lines == []


def test_global_off_suppresses_all_modules():
    lines: list[str] = []
    reset_trace_state()
    set_global_trace_enabled(False)
    set_default_trace_level(TRACE_HIGH)
    set_trace_sink(lines.append)
    try:
        trace_emit(MODULE_RUN, "silent", min_level=TRACE_HIGH)
    finally:
        set_trace_sink(None)
        reset_trace_state()
    assert lines == []


def test_module_override_can_disable_single_module():
    lines: list[str] = []
    reset_trace_state()
    set_global_trace_enabled(True)
    set_default_trace_level(TRACE_HIGH)
    set_module_trace_level(MODULE_RUN, TRACE_OFF)
    set_trace_sink(lines.append)
    try:
        trace_emit(MODULE_RUN, "silent", min_level=TRACE_HIGH)
        trace_emit("mategraph", "visible", min_level=TRACE_HIGH)
    finally:
        set_trace_sink(None)
        reset_trace_state()
    assert len(lines) == 1
    assert "mategraph" in lines[0]


def test_deep_emit_requires_level_two():
    lines: list[str] = []
    reset_trace_state()
    set_global_trace_enabled(True)
    set_default_trace_level(TRACE_HIGH)
    set_trace_sink(lines.append)
    try:
        trace_emit(MODULE_RUN, "deep.only", min_level=TRACE_DEEP)
    finally:
        set_trace_sink(None)
    assert lines == []

    set_default_trace_level(TRACE_DEEP)
    set_trace_sink(lines.append)
    try:
        trace_emit(MODULE_RUN, "deep.only", min_level=TRACE_DEEP)
    finally:
        set_trace_sink(None)
        reset_trace_state()
    assert any("deep.only" in line for line in lines)


def test_algorithm_run_emits_trace_stages():
    lines: list[str] = []
    reset_trace_state()
    set_global_trace_enabled(True)
    set_default_trace_level(TRACE_HIGH)
    set_trace_sink(lines.append)
    try:
        algo = DummyMateAlgorithm(config=AlgorithmConfig(max_parts=1))
        ref = SurfaceRef("P", "P", "Face1", None, None, part_id="P")
        ctx = DocumentContext(
            "Doc",
            (
                DocumentObjectContext(
                    "P",
                    "P",
                    "Part",
                    "part",
                    (),
                    (ref,),
                    (PartContext("P", "P", "P", faces=(ref,)),),
                ),
            ),
        )
        request = RecognitionRequest(ctx, (ref,))
        algo.run(request)
    finally:
        set_trace_sink(None)
        reset_trace_state()
    joined = "\n".join(lines)
    assert "run.start" in joined
    assert "run.complete" in joined
    assert get_default_trace_level() == TRACE_OFF
