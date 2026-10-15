"""Pure graph assembly stages."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .model import AAGEdge, AAGNode, PartGraph
from .options import GraphBuildOptions
from .topology import FaceAdjacencyEdge


def assemble_graph(
    part_id: str,
    nodes: list[AAGNode],
    adjacency: tuple[FaceAdjacencyEdge, ...],
    edge_attributes: Callable[[FaceAdjacencyEdge], tuple[str, float]],
) -> PartGraph:
    edges: list[AAGEdge] = []
    seen: set[frozenset[str]] = set()
    for link in adjacency:
        key = frozenset((link.face_a, link.face_b))
        if key in seen:
            continue
        seen.add(key)
        convexity, angle = edge_attributes(link)
        edges.append(AAGEdge(link.face_a, link.face_b, convexity, angle))
    return PartGraph.build(part_id, nodes, edges)


def apply_merge(graph: PartGraph, options: GraphBuildOptions) -> PartGraph:
    if not options.merge_smooth:
        return graph
    from MateCore.MateGraph.merge import merge_smooth_neighbors

    return merge_smooth_neighbors(graph, options.tol_len, options.tol_angle)
