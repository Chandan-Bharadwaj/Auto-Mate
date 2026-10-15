"""Extract GraphPattern from PartGraph."""

from __future__ import annotations

from MateCore.context import SurfaceRef

from ..model import PartGraph
from .pattern import GraphPattern, PatternEdge, PatternSlot


def _ref_key(ref: SurfaceRef) -> tuple[str, str]:
    return ref.object_name, ref.face_name


def node_for_ref(graph: PartGraph, ref: SurfaceRef) -> str | None:
    key = _ref_key(ref)
    for node in graph.nodes:
        if node.ref is not None and _ref_key(node.ref) == key:
            return node.node_id
        for r in node.refs:
            if r is not None and _ref_key(r) == key:
                return node.node_id
        if node.node_id == f"{ref.object_name}:{ref.face_name}":
            return node.node_id
        if key[1] in node.member_ids or node.node_id.endswith(f":{key[1]}"):
            return node.node_id
    return None


def _build_pattern(
    graph: PartGraph,
    chosen: set[str],
    anchor_node_ids: set[str],
) -> GraphPattern:
    node_list = [graph.node(nid) for nid in sorted(chosen)]
    nodes = [n for n in node_list if n is not None]
    if not nodes:
        raise ValueError("No nodes resolved for pattern")

    slot_ids = tuple(f"p{i}" for i in range(len(nodes)))
    node_to_slot = {n.node_id: slot_ids[i] for i, n in enumerate(nodes)}

    slots: list[PatternSlot] = []
    anchors: set[str] = set()
    for i, n in enumerate(nodes):
        sid = slot_ids[i]
        if n.node_id in anchor_node_ids:
            anchors.add(sid)
        slots.append(
            PatternSlot(
                slot_id=sid,
                source_node_id=n.node_id,
                surface_kind=n.surface_kind,
                origin=n.origin,
                axis=n.axis,
                area=n.area,
                radius=n.radius,
                semi_angle=n.semi_angle,
                convex=n.convex,
                plane_aspect=n.plane_aspect,
                member_ids=n.member_ids or (n.node_id,),
            )
        )

    edges: list[PatternEdge] = []
    seen: set[frozenset[str]] = set()
    for e in graph.edges:
        if e.a not in node_to_slot or e.b not in node_to_slot:
            continue
        sa, sb = node_to_slot[e.a], node_to_slot[e.b]
        key = frozenset((sa, sb))
        if key in seen:
            continue
        seen.add(key)
        edges.append(PatternEdge(sa, sb, e.convexity, e.dihedral_angle))

    adj: dict[str, set[str]] = {s: set() for s in slot_ids}
    for e in edges:
        adj[e.a].add(e.b)
        adj[e.b].add(e.a)

    by_slot = {s.slot_id: s for s in slots}
    return GraphPattern(
        part_id=graph.part_id,
        slots=tuple(slots),
        edges=tuple(edges),
        anchor_slots=frozenset(anchors),
        _adjacency={k: frozenset(v) for k, v in adj.items()},
        _by_slot=by_slot,
    )


def extract_pattern(graph: PartGraph, node_ids: tuple[str, ...] | set[str]) -> GraphPattern:
    chosen = set(node_ids)
    if not chosen:
        raise ValueError("At least one node id is required")
    return _build_pattern(graph, chosen, chosen)


def extract_pattern_from_refs(
    graph: PartGraph,
    selected: tuple[SurfaceRef, ...],
) -> GraphPattern:
    chosen: set[str] = set()
    anchor_nodes: set[str] = set()
    for ref in selected:
        nid = node_for_ref(graph, ref)
        if nid is not None:
            chosen.add(nid)
            anchor_nodes.add(nid)
    if not chosen:
        raise ValueError("None of the selected faces appear in the part graph")
    return _build_pattern(graph, chosen, anchor_nodes)
