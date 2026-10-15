"""Symmetric node/edge similarity (domain-neutral)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..model import AAGEdge, AAGNode, UNKNOWN
from .pattern import PatternEdge, PatternSlot


@dataclass(frozen=True, slots=True)
class DefaultNodeComparator:
    min_similarity: float = 0.3
    len_tol: float = 1e-3
    angle_tol: float = 0.1
    compare_node_axis: bool = True

    def _total_similarity(
        self,
        kind: str,
        axis_score: float,
        size_score: float,
        area_score: float,
        taper_score: float,
    ) -> float:
        if kind == "cone":
            if self.compare_node_axis:
                return (
                    0.55 * taper_score
                    + 0.15 * axis_score
                    + 0.25 * size_score
                    + 0.05 * area_score
                )
            return 0.65 * taper_score + 0.25 * size_score + 0.1 * area_score
        if self.compare_node_axis:
            return 0.5 * axis_score + 0.3 * size_score + 0.2 * area_score
        return 0.6 * size_score + 0.4 * area_score

    def _similarity_parts(
        self,
        slot: PatternSlot,
        node: AAGNode,
    ) -> tuple[float | None, float, float, float]:
        """Returns (reject_reason_key, axis_score, size_score, area_score) or None as first if hard reject."""
        if slot.surface_kind != node.surface_kind:
            return ("surface_kind_mismatch", 0.0, 0.0, 0.0)
        kind = slot.surface_kind
        axis_score = 1.0
        taper_score = 1.0
        if self.compare_node_axis and kind in (
            "plane",
            "cylinder",
            "cone",
            "sphere",
            "torus",
        ):
            dot = abs(float(np.dot(slot.axis, node.axis)))
            if dot < np.cos(self.angle_tol):
                return ("axis_misaligned", 0.0, 0.0, 0.0)
            axis_score = dot
        if kind == "cone":
            delta = abs(float(slot.semi_angle - node.semi_angle))
            if delta > self.angle_tol:
                return ("taper_mismatch", 0.0, 0.0, 0.0)
            taper_score = max(0.0, 1.0 - delta / max(self.angle_tol, 1e-9))
        size_score = 1.0
        if slot.radius > 0 or node.radius > 0:
            denom = max(slot.radius, node.radius, 1e-12)
            if abs(slot.radius - node.radius) > self.len_tol + 0.01 * denom:
                rel = abs(slot.radius - node.radius) / denom
                size_score = max(0.0, 1.0 - rel)
        area_score = 1.0
        if slot.area > 0 and node.area > 0:
            ratio = min(slot.area, node.area) / max(slot.area, node.area)
            area_score = ratio
        total = self._total_similarity(kind, axis_score, size_score, area_score, taper_score)
        if total < self.min_similarity:
            return ("below_min_similarity", axis_score, size_score, area_score)
        return (None, axis_score, size_score, area_score)

    def explain_node_rejection(
        self,
        slot: PatternSlot,
        node: AAGNode,
        partial_mapping: dict[str, str] | None = None,
    ) -> str | None:
        key, _, _, _ = self._similarity_parts(slot, node)
        return key

    def similarity(
        self,
        slot: PatternSlot,
        node: AAGNode,
        partial_mapping: dict[str, str] | None = None,
    ) -> float | None:
        key, axis_score, size_score, area_score = self._similarity_parts(slot, node)
        if key is not None:
            return None
        taper_score = 1.0
        if slot.surface_kind == "cone":
            delta = abs(float(slot.semi_angle - node.semi_angle))
            taper_score = max(0.0, 1.0 - delta / max(self.angle_tol, 1e-9))
        total = self._total_similarity(
            slot.surface_kind, axis_score, size_score, area_score, taper_score
        )
        return float(total)


@dataclass(frozen=True, slots=True)
class DefaultEdgeComparator:
    angle_tol: float = 0.1

    def similarity(self, pattern_edge: PatternEdge, target_edge: AAGEdge | None) -> float:
        if target_edge is None:
            return 0.0
        conv_match = 1.0 if pattern_edge.convexity == target_edge.convexity else 0.0
        if pattern_edge.convexity == UNKNOWN or target_edge.convexity == UNKNOWN:
            conv_match = 0.75
        ang = abs(pattern_edge.dihedral_angle - target_edge.dihedral_angle)
        ang_score = max(0.0, 1.0 - ang / max(self.angle_tol, 1e-9))
        return 0.6 * conv_match + 0.4 * ang_score
