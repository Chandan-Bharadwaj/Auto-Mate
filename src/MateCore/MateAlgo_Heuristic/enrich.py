"""Pattern enrichment before mating transform."""

from __future__ import annotations

from MateCore.MateGraph.model import PartGraph
from MateCore.MateGraph.search.extract import _build_pattern
from MateCore.MateGraph.search.pattern import GraphPattern

from .config import EnricherMode


def enrich_selection_only(pattern: GraphPattern, graph: PartGraph | None = None) -> GraphPattern:
    """Reference pattern only (no neighborhood expansion)."""
    return pattern


def enrich_one_hop_analytic(graph: PartGraph, pattern: GraphPattern) -> GraphPattern:
    """Add one-hop analytic neighbors of anchor nodes to the pattern."""
    chosen = {s.source_node_id for s in pattern.slots}
    anchor_nodes = {
        s.source_node_id
        for s in pattern.slots
        if s.slot_id in pattern.anchor_slots
    }
    expanded = set(chosen)
    for nid in list(chosen):
        for edge in graph.edges:
            if edge.a == nid:
                expanded.add(edge.b)
            elif edge.b == nid:
                expanded.add(edge.a)
    if expanded == chosen:
        return pattern
    return _build_pattern(graph, expanded, anchor_nodes or chosen)


def apply_enricher(
    graph: PartGraph,
    pattern: GraphPattern,
    mode: EnricherMode,
) -> GraphPattern:
    if mode == "one_hop_analytic":
        return enrich_one_hop_analytic(graph, pattern)
    return enrich_selection_only(pattern, graph)
