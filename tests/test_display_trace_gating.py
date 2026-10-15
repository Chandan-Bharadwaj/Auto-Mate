from types import SimpleNamespace

from MateCore.algorithm import AlgorithmResult, RejectedPart
from MateCore.context import (
    DocumentContext,
    DocumentObjectContext,
    PartContext,
    RecognitionRequest,
    SurfaceRef,
)
from MateCore.trace import (
    MODULE_REPORT,
    reset_trace_state,
    set_global_trace_enabled,
    set_module_trace_level,
)

from App_FreeCAD.display import display_part_results, display_results


class _Console:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def PrintMessage(self, msg: str) -> None:
        self.messages.append(msg)

    def PrintWarning(self, msg: str) -> None:
        self.messages.append(msg)


def _minimal_context() -> DocumentContext:
    ref = SurfaceRef("P", "P", "Face1", None, None, part_id="P")
    obj = DocumentObjectContext(
        "P",
        "P",
        "Part",
        "part",
        (),
        (ref,),
        (PartContext("P", "P", "P", faces=(ref,)),),
    )
    return DocumentContext("Doc", (obj,))


def _gui():
    return SimpleNamespace(
        Selection=SimpleNamespace(
            clearSelection=lambda: None,
            addSelection=lambda *args: None,
        )
    )


def test_display_results_hides_inventory_when_report_below_deep():
    reset_trace_state()
    set_global_trace_enabled(True)
    set_module_trace_level(MODULE_REPORT, 1)
    console = _Console()
    freecad = SimpleNamespace(Console=console)
    context = _minimal_context()
    display_results(freecad, _gui(), context, ((context.objects[0].faces[0],),))
    joined = "".join(console.messages)
    assert "document object(s)" not in joined
    assert "Part 1" not in joined
    reset_trace_state()


def test_display_results_shows_inventory_when_report_deep():
    reset_trace_state()
    set_global_trace_enabled(True)
    set_module_trace_level(MODULE_REPORT, 2)
    console = _Console()
    freecad = SimpleNamespace(Console=console)
    context = _minimal_context()
    display_results(freecad, _gui(), context, ((context.objects[0].faces[0],),))
    joined = "".join(console.messages)
    assert "document object(s)" in joined
    reset_trace_state()


def test_display_part_results_shows_mating_report_by_default():
    reset_trace_state()
    set_global_trace_enabled(False)
    console = _Console()
    freecad = SimpleNamespace(Console=console)
    context = _minimal_context()
    ref = context.objects[0].faces[0]
    request = RecognitionRequest(context, (ref,))
    result = AlgorithmResult(part_matches=())
    display_part_results(
        freecad,
        _gui(),
        context,
        result,
        request=request,
    )
    joined = "".join(console.messages)
    assert "mating report" in joined
    reset_trace_state()


def test_display_part_results_summarizes_rejections_not_per_part():
    reset_trace_state()
    console = _Console()
    freecad = SimpleNamespace(Console=console)
    context = _minimal_context()
    ref = context.objects[0].faces[0]
    request = RecognitionRequest(context, (ref,))
    reason = "graph aligned but no pose satisfied fit tolerance"
    result = AlgorithmResult(
        part_matches=(),
        rejected_parts=(
            RejectedPart("Pad", "Pad", reason),
            RejectedPart("Pad001", "Pad001", reason),
            RejectedPart("Pad002", "Pad002", reason),
        ),
    )
    display_part_results(
        freecad,
        _gui(),
        context,
        result,
        request=request,
    )
    joined = "".join(console.messages)
    assert joined.count(reason) == 3
    assert joined.count("3 part(s) rejected") == 1
    assert "see mating report" in joined
    assert "Rejected (3):" in joined
    reset_trace_state()


def test_display_part_results_rejection_summary_when_report_off():
    reset_trace_state()
    set_module_trace_level(MODULE_REPORT, 0)
    console = _Console()
    freecad = SimpleNamespace(Console=console)
    context = _minimal_context()
    ref = context.objects[0].faces[0]
    request = RecognitionRequest(context, (ref,))
    result = AlgorithmResult(
        part_matches=(),
        rejected_parts=(RejectedPart("Pad", "Pad", "no match"),),
    )
    display_part_results(
        freecad,
        _gui(),
        context,
        result,
        request=request,
    )
    joined = "".join(console.messages)
    assert "  - Pad:" not in joined
    assert "1 part(s) did not mate" in joined
    assert "mating report" not in joined
    reset_trace_state()


def test_display_part_results_hides_mating_report_when_report_off():
    reset_trace_state()
    set_module_trace_level(MODULE_REPORT, 0)
    console = _Console()
    freecad = SimpleNamespace(Console=console)
    context = _minimal_context()
    ref = context.objects[0].faces[0]
    request = RecognitionRequest(context, (ref,))
    result = AlgorithmResult(part_matches=())
    display_part_results(
        freecad,
        _gui(),
        context,
        result,
        request=request,
    )
    joined = "".join(console.messages)
    assert "mating report" not in joined
    reset_trace_state()
