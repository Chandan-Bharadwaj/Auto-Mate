"""Topology discovery for part graphs (mock B-Rep, no FreeCAD)."""

from __future__ import annotations

from App_FreeCAD.part_graph_build import _discover_adjacency
from MateCore.context import SurfaceRef


class _Edge:
    def __init__(self, code: int, same_group: int) -> None:
        self._code = code
        self._group = same_group

    def hashCode(self) -> int:
        return self._code

    def isSame(self, other: object) -> bool:
        return isinstance(other, _Edge) and self._group == other._group


def _face(name: str, edges: list[_Edge]) -> SurfaceRef:
    class Shape:
        Edges = edges

    return SurfaceRef("P", "P", name, Shape(), None, part_id="P")


def test_adjacency_chain_three_faces():
    e1 = _Edge(1, 1)
    e2 = _Edge(2, 2)
    e3 = _Edge(3, 3)
    refs = (
        _face("Face1", [e1, e2]),
        _face("Face2", [e1, e3]),
        _face("Face3", [e2, e3]),
    )
    links = _discover_adjacency(refs)
    pairs = {frozenset((link.face_a, link.face_b)) for link in links}
    assert pairs == {
        frozenset(("P:Face1", "P:Face2")),
        frozenset(("P:Face1", "P:Face3")),
        frozenset(("P:Face2", "P:Face3")),
    }
    assert all(link.shared_edge is not None for link in links)


def test_adjacency_one_shared_edge_per_pair():
    shared = _Edge(10, 10)
    refs = (
        _face("Face1", [shared]),
        _face("Face2", [shared]),
    )
    links = _discover_adjacency(refs)
    assert len(links) == 1
    assert links[0].shared_edge is shared
