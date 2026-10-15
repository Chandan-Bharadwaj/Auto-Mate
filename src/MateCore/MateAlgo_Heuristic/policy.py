"""Mating-specific graph search policy."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from MateCore.MateFit.descriptors import CYLINDER
from MateCore.MateFit import FitResolver
from MateCore.MateGraph.model import AAGNode
from MateCore.MateGraph.search.candidates import candidates_for_slot
from MateCore.MateGraph.search.comparators import DefaultEdgeComparator, DefaultNodeComparator
from MateCore.MateGraph.search.constraint_index import slot_constraint_key
from MateCore.MateGraph.search.flank_index import (
    parallel_plane_span_nodes,
    slot_node_weight_from_metadata,
)
from MateCore.MateGraph.search.index import TargetIndex
from MateCore.MateGraph.search.pattern import GraphPattern, PatternSlot

from .plane_shape_fit import (
    apply_plane_shape_penalty,
    explain_plane_shape_rejection,
    plane_shape_raw,
)
from .slot_descriptor import node_to_descriptor, slot_to_face_descriptor

_FIRST_SLOT_SIMILARITY = 1.0


def _first_slot_rejection(slot: PatternSlot, node: AAGNode) -> str | None:
    if slot.surface_kind != node.surface_kind:
        return "surface_kind_mismatch"
    return None


@dataclass(frozen=True, slots=True)
class MatingNodeComparator:
    resolver: FitResolver
    part_id: str
    inner: DefaultNodeComparator
    pattern: GraphPattern | None = None
    target: object | None = None
    flank_spacing_rel_tol: float = 0.05
    plane_shape_reject_floor: float = 0.15
    plane_shape_penalty_exponent: float = 2.0

    def _selection_descriptor(self, slot: PatternSlot):
        sel = slot_to_face_descriptor(slot, self.part_id)
        if sel is None:
            return None
        if slot.surface_kind in ("cylinder", "cone"):
            orig = slot.metadata.get("original_convex")
            if orig is not None:
                sel = replace(sel, convex=bool(orig))
        return sel

    def _neighbor_angle_ok(
        self,
        slot: PatternSlot,
        node: AAGNode,
        partial_mapping: dict[str, str],
    ) -> bool:
        if self.pattern is None or self.target is None:
            return True
        target_graph = self.target
        for neighbor_slot_id in self.pattern.neighbors(slot.slot_id):
            mapped_nid = partial_mapping.get(neighbor_slot_id)
            if mapped_nid is None:
                continue
            neighbor_slot = self.pattern.slot(neighbor_slot_id)
            t_neighbor = target_graph.node(mapped_nid)
            if neighbor_slot is None or t_neighbor is None:
                continue
            if neighbor_slot.surface_kind != "plane" or slot.surface_kind != "plane":
                continue
            pat_ang = abs(float(np.dot(neighbor_slot.axis, slot.axis)))
            tgt_ang = abs(float(np.dot(t_neighbor.axis, node.axis)))
            if pat_ang < np.cos(self.inner.angle_tol) or tgt_ang < np.cos(
                self.inner.angle_tol
            ):
                continue
            if abs(pat_ang - tgt_ang) > 0.15:
                return False
        return True

    def _flank_spacing_ok(
        self,
        slot: PatternSlot,
        partial_mapping: dict[str, str],
    ) -> bool:
        flank_ids = slot.metadata.get("flank_slot_ids")
        if not flank_ids or len(flank_ids) != 2:
            return True
        id_a, id_b = flank_ids
        if id_a not in partial_mapping or id_b not in partial_mapping:
            return True
        span_pat = slot.metadata.get("flank_span")
        if span_pat is None or self.pattern is None or self.target is None:
            return True
        target_graph = self.target
        ta = target_graph.node(partial_mapping[id_a])
        tb = target_graph.node(partial_mapping[id_b])
        if ta is None or tb is None:
            return False
        span_tgt = parallel_plane_span_nodes(ta, tb, self.inner.angle_tol)
        if span_tgt is None:
            return False
        span_pat_f = float(span_pat)
        tol = self.inner.len_tol + self.flank_spacing_rel_tol * span_pat_f
        return abs(span_tgt - span_pat_f) <= tol

    def explain_node_rejection(
        self,
        slot: PatternSlot,
        node: AAGNode,
        partial_mapping: dict[str, str] | None = None,
    ) -> str | None:
        mapping = partial_mapping or {}
        if not mapping:
            return _first_slot_rejection(slot, node)
        sel = self._selection_descriptor(slot)
        cand = node_to_descriptor(node)
        if sel is None or cand is None:
            return "descriptor_missing"
        if not self.resolver.kinds_compatible(sel, cand):
            return "kinds_incompatible"
        if mapping and not self._neighbor_angle_ok(slot, node, mapping):
            return "neighbor_angle_mismatch"
        if mapping and not self._flank_spacing_ok(slot, mapping):
            return "flank_spacing_mismatch"
        inner_reason = self.inner.explain_node_rejection(slot, node, partial_mapping)
        if inner_reason is not None:
            return inner_reason
        return explain_plane_shape_rejection(
            slot,
            node,
            reject_floor=self.plane_shape_reject_floor,
        )

    def similarity(
        self,
        slot: PatternSlot,
        node: AAGNode,
        partial_mapping: dict[str, str] | None = None,
    ) -> float | None:
        mapping = partial_mapping or {}
        if not mapping:
            if _first_slot_rejection(slot, node) is not None:
                return None
            return _FIRST_SLOT_SIMILARITY
        sel = self._selection_descriptor(slot)
        cand = node_to_descriptor(node)
        if sel is None or cand is None:
            return None
        if not self.resolver.kinds_compatible(sel, cand):
            return None
        if mapping and not self._neighbor_angle_ok(slot, node, mapping):
            return None
        if mapping and not self._flank_spacing_ok(slot, mapping):
            return None
        sim = self.inner.similarity(slot, node, partial_mapping)
        if sim is None or slot.surface_kind != "plane":
            return sim
        raw = plane_shape_raw(slot, node)
        penalized = apply_plane_shape_penalty(
            sim,
            raw,
            exponent=self.plane_shape_penalty_exponent,
            reject_floor=self.plane_shape_reject_floor,
        )
        if penalized is not None and penalized < self.inner.min_similarity:
            return None
        return penalized


@dataclass(frozen=True, slots=True)
class MatingAlignmentSearchPolicy:
    resolver: FitResolver
    source_part_id: str
    beam_width: int = 32
    max_candidates: int = 16
    node_min_similarity: float = 0.3
    missing_edge_penalty: float = 0.25
    unmapped_slot_penalty: float = 0.15
    unmapped_anchor_penalty: float = 0.5
    weight_node: float = 0.4
    weight_edge: float = 0.35
    weight_coverage: float = 0.15
    weight_anchor_coverage: float = 0.1
    len_tol: float = 1e-3
    angle_tol: float = 0.1
    flank_spacing_rel_tol: float = 0.05
    hub_node_weight: float = 2.0
    plane_shape_reject_floor: float = 0.15
    plane_shape_penalty_exponent: float = 2.0
    _pattern: GraphPattern | None = None
    _target: object | None = None

    def with_search_context(self, pattern: GraphPattern, target) -> MatingAlignmentSearchPolicy:
        return replace(self, _pattern=pattern, _target=target)

    def node_comparator(self) -> MatingNodeComparator:
        return MatingNodeComparator(
            self.resolver,
            self.source_part_id,
            DefaultNodeComparator(
                min_similarity=self.node_min_similarity,
                len_tol=self.len_tol,
                angle_tol=self.angle_tol,
                compare_node_axis=False,
            ),
            pattern=self._pattern,
            target=self._target,
            flank_spacing_rel_tol=self.flank_spacing_rel_tol,
            plane_shape_reject_floor=self.plane_shape_reject_floor,
            plane_shape_penalty_exponent=self.plane_shape_penalty_exponent,
        )

    def edge_comparator(self) -> DefaultEdgeComparator:
        return DefaultEdgeComparator(angle_tol=self.angle_tol)

    def slot_order(self, pattern: GraphPattern) -> tuple[str, ...]:
        def sort_key(sid: str) -> tuple:
            slot = pattern.slot(sid)
            group = 2
            if slot is not None:
                group = int(slot.metadata.get("slot_order_group", 2))
            return (group, slot_constraint_key(pattern, sid, self.angle_tol))

        return tuple(
            sid for sid in sorted((s.slot_id for s in pattern.slots), key=sort_key)
        )

    def slot_node_weight(self, slot: PatternSlot) -> float:
        return slot_node_weight_from_metadata(slot)

    def candidates_for_slot(
        self, slot: PatternSlot, target, index: TargetIndex
    ) -> tuple[str, ...]:
        band = None
        if slot.surface_kind in ("cylinder", "cone"):
            sel = slot_to_face_descriptor(slot, self.source_part_id)
            if sel is not None:
                orig = slot.metadata.get("original_convex")
                if orig is not None:
                    sel = replace(sel, convex=bool(orig))
                band = self.resolver.policy.fit_for(sel.kind, sel.kind).size_band(sel)
        return candidates_for_slot(
            slot,
            target,
            index,
            len_tol=self.len_tol,
            angle_tol=self.angle_tol,
            size_band=band,
        )

    def should_prune_partial(self, mapped_count: int, partial_score: float) -> bool:
        return False

    @classmethod
    def coarse_topology(
        cls,
        resolver: FitResolver,
        source_part_id: str,
        **kwargs,
    ) -> MatingAlignmentSearchPolicy:
        return cls(
            resolver,
            source_part_id,
            weight_edge=0.1,
            missing_edge_penalty=0.05,
            **kwargs,
        )
