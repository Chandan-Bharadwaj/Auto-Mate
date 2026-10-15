import numpy as np

from MateCore.MateGraph.model import AAGNode, PartGraph
from MateCore.MateGraph.options import GraphBuildOptions
from MateCore.MateGraph.reporting import NullGraphBuildReporter
from MateCore.MateGraph.store import PartGraphStore
from MateCore.context import PartContext, SurfaceRef
from App_FreeCAD.geometry_cache import clear_registry, get_or_create, get_part_graph_store


def _part(part_id: str) -> PartContext:
    ref = SurfaceRef(part_id, part_id, "Face1", None, None, part_id=part_id)
    return PartContext(part_id, part_id, part_id, faces=(ref,))


def test_store_builds_once_per_part():
    calls: list[str] = []

    def builder(part: PartContext, options: GraphBuildOptions, reporter) -> PartGraph:
        calls.append(part.part_id)
        ref = part.faces[0]
        node = AAGNode(
            node_id=f"{part.part_id}:Face1",
            part_id=part.part_id,
            surface_kind="plane",
            origin=np.zeros(3),
            axis=np.array([0, 0, 1.0]),
            ref=ref,
        )
        return PartGraph.build(part.part_id, [node], [])

    store = PartGraphStore("Doc", builder)
    part = _part("P")
    first = store.get(part)
    second = store.get(part)
    assert first is second
    assert calls == ["P"]


def test_store_lazy_per_part():
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
    store.get(_part("A"))
    assert built == ["A"]
    store.get(_part("B"))
    assert built == ["A", "B"]


def test_get_part_graph_store_separates_documents():
    clear_registry()
    assert get_part_graph_store("A") is not get_part_graph_store("B")
    assert get_or_create("A").part_graph_store() is get_part_graph_store("A")
