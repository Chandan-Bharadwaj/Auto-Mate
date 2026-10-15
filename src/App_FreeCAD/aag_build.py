"""Build a PartAAG from FreeCAD Part face topology (legacy entry point)."""

from __future__ import annotations

from MateCore.MateGraph.model import PartAAG
from MateCore.MateGraph.options import GraphBuildOptions
from MateCore.context import PartContext

from .aag_nodes import face_id, node_from_ref
from .part_graph_build import build_part_graph

_node_from_ref = node_from_ref


def build_part_aag(
    part: PartContext,
    *,
    tol_len: float = 1e-3,
    tol_angle: float = 1e-3,
    merge_smooth: bool = True,
) -> PartAAG:
    options = GraphBuildOptions(
        tol_len=tol_len,
        tol_angle=tol_angle,
        merge_smooth=merge_smooth,
    )
    return build_part_graph(part, options)
