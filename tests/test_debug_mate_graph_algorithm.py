import numpy as np

from MateCore.MateGraph.debug_mate_graph_algorithm import MateAlgorithm_DebugMateGraph
from MateCore.MateGraph.model import AAGNode, PartGraph
from MateCore.MateGraph.options import GraphBuildOptions
from MateCore.MateGraph.store import PartGraphStore
from MateCore.context import (
    DocumentContext,
    DocumentObjectContext,
    PartContext,
    RecognitionRequest,
    SurfaceRef,
)
from MateCore.trace import (
    MODULE_MATEGRAPH,
    TRACE_HIGH,
    reset_trace_state,
    set_global_trace_enabled,
    set_module_trace_level,
    set_trace_sink,
)


def _part(part_id: str) -> PartContext:
    ref = SurfaceRef(part_id, part_id, "Face1", None, None, part_id=part_id)
    return PartContext(part_id, part_id, part_id, faces=(ref,))


def _doc(*part_ids: str) -> DocumentContext:
    parts = tuple(_part(pid) for pid in part_ids)
    obj = DocumentObjectContext("O", "O", "Part::Feature", "solid", (), parts=parts)
    return DocumentContext("Doc", (obj,))


def test_debug_algorithm_builds_every_part():
    built: list[str] = []

    def builder(part: PartContext, options: GraphBuildOptions, reporter) -> PartGraph:
        built.append(part.part_id)
        node = AAGNode(
            node_id="n",
            part_id=part.part_id,
            surface_kind="plane",
            origin=np.zeros(3),
            axis=np.array([0, 0, 1.0]),
        )
        return PartGraph.build(part.part_id, [node], [])

    store = PartGraphStore("Doc", builder)
    algo = MateAlgorithm_DebugMateGraph(store)
    request = RecognitionRequest(
        _doc("A", "B", "C"),
        (_part("A").faces[0],),
    )
    result = algo.run(request)
    assert built == ["A", "B", "C"]
    assert not result.part_matches
    assert not result.diagnostics


def test_debug_algorithm_emits_trace_per_part():
    messages: list[str] = []
    reset_trace_state()
    set_global_trace_enabled(True)
    set_module_trace_level(MODULE_MATEGRAPH, TRACE_HIGH)
    set_trace_sink(messages.append)

    def builder(part: PartContext, options: GraphBuildOptions, reporter) -> PartGraph:
        node = AAGNode(
            node_id="n",
            part_id=part.part_id,
            surface_kind="plane",
            origin=np.zeros(3),
            axis=np.array([0, 0, 1.0]),
        )
        return PartGraph.build(part.part_id, [node], [])

    store = PartGraphStore("Doc", builder)
    algo = MateAlgorithm_DebugMateGraph(store)
    request = RecognitionRequest(_doc("X", "Y"), (_part("X").faces[0],))
    algo.run(request)
    set_trace_sink(None)
    reset_trace_state()
    assert any("debug_mate_graph part=X" in m for m in messages)
    assert any("debug_mate_graph part=Y" in m for m in messages)
