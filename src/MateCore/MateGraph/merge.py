"""Merge tangentially continuous faces on the same analytic surface."""

from __future__ import annotations

import numpy as np

from .model import SMOOTH, AAGEdge, AAGNode, PartGraph


def _same_surface(a: AAGNode, b: AAGNode, tol_len: float, tol_angle: float) -> bool:
    if a.surface_kind != b.surface_kind:
        return False
    if a.surface_kind not in ("plane", "cylinder", "cone", "sphere", "torus"):
        return False
    if a.surface_kind == "plane":
        if np.linalg.norm(a.axis - b.axis) > tol_angle and np.linalg.norm(a.axis + b.axis) > tol_angle:
            return False
        return abs(float(np.dot(b.origin - a.origin, a.axis))) <= tol_len
    if a.surface_kind == "cone":
        if abs(a.semi_angle - b.semi_angle) > tol_angle:
            return False
    if a.convex != b.convex or abs(a.radius - b.radius) > tol_len:
        return False
    if 1.0 - abs(float(np.dot(a.axis, b.axis))) > tol_angle**2:
        return False
    delta = b.origin - a.origin
    lateral = delta - float(np.dot(delta, a.axis)) * a.axis
    return float(np.linalg.norm(lateral)) <= tol_len


def merge_smooth_neighbors(graph: PartGraph, tol_len: float, tol_angle: float) -> PartGraph:
    parent = {n.node_id: n.node_id for n in graph.nodes}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    by_id = {n.node_id: n for n in graph.nodes}
    for e in graph.edges:
        if e.convexity != SMOOTH:
            continue
        if _same_surface(by_id[e.a], by_id[e.b], tol_len, tol_angle):
            parent[find(e.a)] = find(e.b)

    groups: dict[str, list[AAGNode]] = {}
    for n in graph.nodes:
        groups.setdefault(find(n.node_id), []).append(n)

    if len(groups) == len(graph.nodes):
        return graph

    new_nodes: list[AAGNode] = []
    old_to_new: dict[str, str] = {}
    for members in groups.values():
        rep = max(members, key=lambda m: m.area)
        new_id = rep.node_id
        for m in members:
            old_to_new[m.node_id] = new_id
        refs = []
        mids = []
        for m in members:
            refs.extend(m.refs if m.refs else ((m.ref,) if m.ref else ()))
            mids.extend(m.member_ids if m.member_ids else (m.node_id,))
        new_nodes.append(
            AAGNode(
                node_id=new_id,
                part_id=rep.part_id,
                surface_kind=rep.surface_kind,
                origin=rep.origin,
                axis=rep.axis,
                area=sum(m.area for m in members),
                radius=rep.radius,
                semi_angle=rep.semi_angle,
                convex=rep.convex,
                secondary_radius=rep.secondary_radius,
                refs=tuple(refs),
                member_ids=tuple(dict.fromkeys(mids)),
                normal_samples=rep.normal_samples,
                bbox_diag=rep.bbox_diag,
                plane_aspect=max(m.plane_aspect for m in members),
                ref=rep.ref,
            )
        )

    new_edges: list[AAGEdge] = []
    seen: set[frozenset[str]] = set()
    for e in graph.edges:
        a = old_to_new.get(e.a, e.a)
        b = old_to_new.get(e.b, e.b)
        if a == b:
            continue
        key = frozenset((a, b))
        if key in seen:
            continue
        seen.add(key)
        new_edges.append(AAGEdge(a, b, e.convexity, e.dihedral_angle))

    return PartGraph.build(graph.part_id, new_nodes, new_edges)
