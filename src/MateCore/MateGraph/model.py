"""Host-independent attributed adjacency graph for B-Rep faces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

PLANE = "plane"
CYLINDER = "cylinder"
CONE = "cone"
SPHERE = "sphere"
TORUS = "torus"
FREEFORM = "freeform"
OTHER = "other"

CONVEX = "convex"
CONCAVE = "concave"
SMOOTH = "smooth"
UNKNOWN = "unknown"

ANALYTIC_KINDS = frozenset({PLANE, CYLINDER, CONE, SPHERE, TORUS})


@dataclass(frozen=True, slots=True)
class NormalSample:
    point: np.ndarray
    normal: np.ndarray


@dataclass(frozen=True, slots=True, eq=False)
class AAGNode:
    node_id: str
    part_id: str
    surface_kind: str
    origin: np.ndarray
    axis: np.ndarray
    area: float = 0.0
    radius: float = 0.0
    semi_angle: float = 0.0
    convex: bool = True
    secondary_radius: float = 0.0
    refs: tuple[Any, ...] = ()
    member_ids: tuple[str, ...] = ()
    normal_samples: tuple[NormalSample, ...] = ()
    bbox_diag: float = 0.0
    plane_aspect: float = 0.0
    ref: Any = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "origin", np.asarray(self.origin, dtype=float))
        ax = np.asarray(self.axis, dtype=float)
        n = float(np.linalg.norm(ax))
        if n > 0:
            object.__setattr__(self, "axis", ax / n)
        else:
            object.__setattr__(self, "axis", np.array([0.0, 0.0, 1.0]))


@dataclass(frozen=True, slots=True)
class AAGEdge:
    a: str
    b: str
    convexity: str = UNKNOWN
    dihedral_angle: float = 0.0


@dataclass(frozen=True, slots=True)
class PartGraph:
    part_id: str
    nodes: tuple[AAGNode, ...]
    edges: tuple[AAGEdge, ...]
    _adjacency: dict[str, frozenset[str]] = field(repr=False)
    _edge_lookup: dict[frozenset[str], AAGEdge] = field(repr=False)
    _by_id: dict[str, AAGNode] = field(repr=False)

    @staticmethod
    def build(
        part_id: str,
        nodes: list[AAGNode],
        edges: list[AAGEdge],
    ) -> PartGraph:
        by_id = {n.node_id: n for n in nodes}
        adj: dict[str, set[str]] = {n.node_id: set() for n in nodes}
        edge_lookup: dict[frozenset[str], AAGEdge] = {}
        for e in edges:
            if e.a not in by_id or e.b not in by_id:
                continue
            adj[e.a].add(e.b)
            adj[e.b].add(e.a)
            edge_lookup[frozenset((e.a, e.b))] = e
        return PartGraph(
            part_id=part_id,
            nodes=tuple(nodes),
            edges=tuple(edge_lookup.values()),
            _adjacency={k: frozenset(v) for k, v in adj.items()},
            _edge_lookup=edge_lookup,
            _by_id=by_id,
        )

    def node(self, node_id: str) -> AAGNode | None:
        return self._by_id.get(node_id)

    def neighbors(self, node_id: str) -> frozenset[str]:
        return self._adjacency.get(node_id, frozenset())

    def edge_between(self, a: str, b: str) -> AAGEdge | None:
        return self._edge_lookup.get(frozenset((a, b)))

    def degree(self, node_id: str) -> int:
        return len(self.neighbors(node_id))


PartAAG = PartGraph
