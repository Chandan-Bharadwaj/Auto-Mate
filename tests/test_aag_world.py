"""Build PartAAG from synthetic FaceDescriptor lists (unit tests)."""

from MateCore.MateFit.descriptors import FaceDescriptor
from MateCore.MateGraph.merge import merge_smooth_neighbors
from MateCore.MateGraph.model import AAGEdge, AAGNode, PartAAG, SMOOTH


def part_aag_from_descriptors(
    part_id: str,
    descs: list[FaceDescriptor],
    *,
    tol_len: float = 1e-3,
    tol_angle: float = 1e-3,
    merge: bool = True,
) -> PartAAG:
    nodes = [
        AAGNode(
            node_id=d.id,
            part_id=d.part_id,
            surface_kind=d.kind,
            origin=d.origin,
            axis=d.axis,
            radius=d.radius,
            semi_angle=d.semi_angle,
            convex=d.convex,
            area=d.area,
            plane_aspect=d.plane_aspect,
            ref=d.ref,
            member_ids=(d.id,),
        )
        for d in descs
    ]
    edges: list[AAGEdge] = []
    seen: set[frozenset[str]] = set()
    for d in descs:
        for adj in d.adjacent:
            key = frozenset((d.id, adj))
            if key in seen:
                continue
            seen.add(key)
            edges.append(AAGEdge(d.id, adj, SMOOTH, 0.0))
    graph = PartAAG.build(part_id, nodes, edges)
    if merge:
        graph = merge_smooth_neighbors(graph, tol_len, tol_angle)
    return graph
