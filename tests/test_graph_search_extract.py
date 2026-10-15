import numpy as np

from MateCore.MateGraph.model import AAGEdge, AAGNode, PartGraph
from MateCore.MateGraph.search import extract_pattern, extract_pattern_from_refs
from MateCore.context import SurfaceRef


def _graph() -> PartGraph:
    nodes = [
        AAGNode("a", "P", "plane", np.zeros(3), np.array([0, 0, 1.0]), area=1.0),
        AAGNode("b", "P", "plane", np.ones(3), np.array([0, 0, 1.0]), area=1.0),
        AAGNode("c", "P", "cylinder", np.zeros(3), np.array([1, 0, 0.0]), radius=2.0, area=3.0),
    ]
    edges = [AAGEdge("a", "b", "convex", 1.0)]
    return PartGraph.build("P", nodes, edges)


def test_extract_pattern_induced_edges():
    pat = extract_pattern(_graph(), ("a", "b"))
    assert len(pat.slots) == 2
    assert len(pat.edges) == 1
    assert pat.slots[0].slot_id == "p0"


def test_extract_from_refs_sets_anchors():
    ref = SurfaceRef("P", "P", "Face1", None, None, part_id="P")
    n0 = AAGNode(
        "P:Face1",
        "P",
        "plane",
        np.zeros(3),
        np.array([0, 0, 1.0]),
        area=1.0,
        ref=ref,
    )
    n1 = AAGNode("b", "P", "plane", np.ones(3), np.array([0, 0, 1.0]), area=1.0)
    graph = PartGraph.build("P", [n0, n1], [AAGEdge("P:Face1", "b", "convex", 1.0)])
    pat = extract_pattern_from_refs(graph, (ref,))
    assert len(pat.anchor_slots) == 1
    assert next(iter(pat.anchor_slots)).startswith("p")
