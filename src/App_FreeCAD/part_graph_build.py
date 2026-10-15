"""Build a PartGraph from FreeCAD Part face topology."""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from MateCore.MateGraph.model import CONCAVE, CONVEX, SMOOTH, UNKNOWN, AAGNode
from MateCore.MateGraph.options import GraphBuildOptions
from MateCore.MateGraph.pipeline import apply_merge, assemble_graph
from MateCore.MateGraph.reporting import GraphBuildReporter, NullGraphBuildReporter
from MateCore.MateGraph.topology import FaceAdjacencyEdge
from MateCore.context import PartContext, SurfaceRef

from .aag_nodes import face_id, node_from_ref


def _vec(v: Any) -> np.ndarray:
    return np.array([v.x, v.y, v.z], dtype=float)


def _discover_adjacency(
    refs: tuple[SurfaceRef, ...],
) -> tuple[FaceAdjacencyEdge, ...]:
    by_hash: dict[int, list[tuple[str, Any]]] = {}
    for ref in refs:
        fid = face_id(ref)
        for edge in getattr(ref.shape, "Edges", ()):
            by_hash.setdefault(edge.hashCode(), []).append((fid, edge))

    links: list[FaceAdjacencyEdge] = []
    seen: set[frozenset[str]] = set()
    for entries in by_hash.values():
        clusters: list[list[tuple[str, Any]]] = []
        for fid, edge in entries:
            placed = False
            for cluster in clusters:
                rep_edge = cluster[0][1]
                if edge.isSame(rep_edge):
                    cluster.append((fid, edge))
                    placed = True
                    break
            if not placed:
                clusters.append([(fid, edge)])
        for cluster in clusters:
            for i, (fa, ea) in enumerate(cluster):
                for fb, _eb in cluster[i + 1 :]:
                    if fa == fb:
                        continue
                    key = frozenset((fa, fb))
                    if key in seen:
                        continue
                    seen.add(key)
                    links.append(FaceAdjacencyEdge(fa, fb, ea))
    return tuple(links)


def _edge_convexity(
    ref_a: SurfaceRef, ref_b: SurfaceRef, shared_edge: Any
) -> tuple[str, float]:
    try:
        u0, u1 = shared_edge.ParameterRange
        mid = 0.5 * (u0 + u1)
        p = _vec(shared_edge.valueAt(mid))
        na = _vec(ref_a.shape.normalAt(*_uv_near(ref_a.shape, p)))
        nb = _vec(ref_b.shape.normalAt(*_uv_near(ref_b.shape, p)))
        cross = np.cross(na, nb)
        tangent = _vec(shared_edge.tangentAt(mid))
        if np.linalg.norm(cross) < 1e-9:
            return SMOOTH, 0.0
        angle = float(np.arccos(np.clip(np.dot(na, nb), -1.0, 1.0)))
        sign = float(np.dot(cross, tangent))
        if abs(sign) < 1e-6:
            return SMOOTH, angle
        return (CONVEX if sign > 0 else CONCAVE), angle
    except Exception:
        return UNKNOWN, 0.0


def _uv_near(face: Any, point: np.ndarray) -> tuple[float, float]:
    u0, u1, v0, v1 = face.ParameterRange
    return 0.5 * (u0 + u1), 0.5 * (v0 + v1)


def build_part_graph(
    part: PartContext,
    options: GraphBuildOptions,
    reporter: GraphBuildReporter | None = None,
):
    """Return ``PartGraph`` for one part (no document cache)."""
    rep = reporter or NullGraphBuildReporter()

    rep.stage_started("nodes")
    t0 = time.monotonic()
    nodes: list[AAGNode] = [node_from_ref(ref) for ref in part.faces]
    rep.stage_finished("nodes", time.monotonic() - t0, faces=len(nodes))

    rep.stage_started("adjacency")
    t0 = time.monotonic()
    adjacency = _discover_adjacency(part.faces)
    rep.stage_finished("adjacency", time.monotonic() - t0, edges=len(adjacency))

    by_ref = {face_id(ref): ref for ref in part.faces}

    def attributes(link: FaceAdjacencyEdge) -> tuple[str, float]:
        ref_a = by_ref.get(link.face_a)
        ref_b = by_ref.get(link.face_b)
        if ref_a is None or ref_b is None:
            return UNKNOWN, 0.0
        return _edge_convexity(ref_a, ref_b, link.shared_edge)

    rep.stage_started("edge_attrs")
    t0 = time.monotonic()
    graph = assemble_graph(part.part_id, nodes, adjacency, attributes)
    rep.stage_finished("edge_attrs", time.monotonic() - t0, edges=len(graph.edges))

    rep.stage_started("merge_smooth")
    t0 = time.monotonic()
    graph = apply_merge(graph, options)
    rep.stage_finished(
        "merge_smooth",
        time.monotonic() - t0,
        nodes=len(graph.nodes),
        edges=len(graph.edges),
    )
    return graph
